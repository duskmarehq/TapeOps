from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operario
from app.core.database import get_db
from app.models.deposito import Deposito
from app.models.enums import EstadoPedido, EstadoStop, TipoIncidencia
from app.models.incidencia import Incidencia
from app.models.pedido import Pedido
from app.models.ruta import Ruta
from app.models.stop import Stop
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.schemas.incidencia import IncidenciaCreate, IncidenciaOut
from app.services.firebase_service import notificar_ruta_actualizada
from app.services.optimizador.or_tools_solver import ParadaOptimizar, resolver_vrptw
from app.services.optimizador.osrm_client import OSRMError, obtener_matriz_tiempos

router = APIRouter(prefix="/incidencias", tags=["incidencias"])

ZONA_OPERACION = ZoneInfo("America/Asuncion")


def _segundos_desde_medianoche(t: time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second


async def _reoptimizar_vehiculo_afectado(db: AsyncSession, ruta: Ruta) -> None:
    """
    Re-optimiza únicamente los stops que siguen pendientes en esta ruta
    (no toca otros vehículos ni otras rutas — es la limitación de alcance
    que definimos desde el principio: re-optimización local, no de flota).

    Limitación conocida: el punto de partida para la nueva optimización
    es el depósito, no la posición real del vehículo en la calle, porque
    el sistema no trackea ubicación en vivo. El ORDEN resultante entre
    las paradas restantes sigue siendo válido; el ETA de la primera
    parada no representa "desde donde está el vehículo ahora" sino
    "como si saliera de cero desde el depósito" — hay que comunicar esto
    como aproximación, no como hora exacta, en cualquier interfaz que
    consuma este dato.
    """
    stops_restantes = list(
        await db.scalars(
            select(Stop)
            .where(Stop.ruta_id == ruta.id, Stop.estado == EstadoStop.pendiente)
            .order_by(Stop.orden)
        )
    )
    if not stops_restantes:
        return

    pedidos_restantes = [await db.get(Pedido, s.pedido_id) for s in stops_restantes]

    vehiculo = await db.get(Vehiculo, ruta.vehiculo_id)
    deposito = await db.scalar(select(Deposito).limit(1))

    coordenadas = [(float(deposito.longitud), float(deposito.latitud))]
    coordenadas += [(float(p.longitud), float(p.latitud)) for p in pedidos_restantes]

    try:
        matriz = await obtener_matriz_tiempos(coordenadas)
    except OSRMError:
        # Si OSRM no responde, se conserva el plan anterior en vez de
        # tirar abajo el reporte de la incidencia entera por un problema
        # de un servicio externo.
        return

    paradas_optimizar = [
        ParadaOptimizar(
            id=p.id,
            ventana_inicio_seg=_segundos_desde_medianoche(p.ventana_inicio),
            ventana_fin_seg=_segundos_desde_medianoche(p.ventana_fin),
            demanda_kg=float(p.peso_kg),
        )
        for p in pedidos_restantes
    ]

    resultado = resolver_vrptw(
        matriz_tiempos=matriz,
        paradas=paradas_optimizar,
        capacidades_vehiculos=[float(vehiculo.capacidad_kg)],
    )

    if not resultado:
        return  # no se pudo re-optimizar; se conserva el plan anterior

    ruta_resultado = resultado[0]
    stops_por_pedido_id = {s.pedido_id: s for s in stops_restantes}

    # Actualizamos los stops EXISTENTES en vez de borrarlos y recrearlos:
    # un stop con una incidencia reportada ya tiene una fila en
    # `incidencia` apuntándolo por FK (incidencia.stop_id), así que
    # borrarlo viola esa integridad referencial — es exactamente el bug
    # que esto reemplaza. Como el conjunto de pedidos no cambia, alcanza
    # con reasignarle a cada stop su nuevo `orden` y `hora_estimada_llegada`.
    #
    # La reasignación se hace en dos pasadas para no chocar contra el
    # UNIQUE(ruta_id, orden) a mitad de camino: si el stop A tenía
    # orden=1 y pasa a orden=2 mientras el stop B todavía tiene orden=2,
    # el UPDATE de A choca contra B antes de que B se actualice. Primero
    # los movemos a valores negativos (únicos por construcción, nunca
    # chocan con un orden real positivo), confirmamos ese cambio con un
    # flush, y recién ahí asignamos los valores finales.
    ordenes_originales = sorted(s.orden for s in stops_restantes)

    for stop in stops_restantes:
        stop.orden = -stop.id
    await db.flush()

    for orden_final, pedido_id, llegada_seg in zip(
        ordenes_originales,
        ruta_resultado.paradas_en_orden,
        ruta_resultado.llegada_estimada_seg,
    ):
        stop = stops_por_pedido_id[pedido_id]
        hora_estimada = datetime.combine(
            ruta.fecha, time.min, tzinfo=ZONA_OPERACION
        ) + timedelta(seconds=llegada_seg)

        stop.orden = orden_final
        stop.hora_estimada_llegada = hora_estimada



@router.post("", response_model=IncidenciaOut, status_code=status.HTTP_201_CREATED)
async def reportar_incidencia(
    datos: IncidenciaCreate,
    usuario: Usuario = Depends(require_operario),
    db: AsyncSession = Depends(get_db),
) -> Incidencia:
    stop = await db.get(Stop, datos.stop_id)
    if stop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop no encontrado")

    ruta = await db.get(Ruta, stop.ruta_id)
    if ruta is None or ruta.operario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este stop no pertenece a una ruta asignada a vos",
        )

    if stop.estado != EstadoStop.pendiente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede reportar sobre una parada {stop.estado.value}",
        )

    incidencia = Incidencia(
        stop_id=stop.id,
        reportado_por=usuario.id,
        tipo=datos.tipo,
        descripcion=datos.descripcion,
    )
    db.add(incidencia)

    if datos.tipo == TipoIncidencia.entrega_fallida:
        stop.estado = EstadoStop.fallido
        pedido_fallido = await db.get(Pedido, stop.pedido_id)
        pedido_fallido.estado = EstadoPedido.fallido
        # Nota: el pedido queda en 'fallido' sin ruta de reprogramación
        # automática — es la misma limitación de cardinalidad 1:1
        # pedido-stop que señalamos en el modelado de datos. Reprogramarlo
        # a otra fecha requiere una decisión de diseño que todavía no
        # tomamos.

    await db.flush()  # persistir la incidencia y el cambio de estado antes de re-optimizar

    await _reoptimizar_vehiculo_afectado(db, ruta)

    await db.commit()
    await db.refresh(incidencia)

    # El aviso a Firebase va DESPUÉS del commit: el dashboard reacciona
    # al aviso pidiendo datos a la API, y si el aviso saliera antes,
    # podría leer el estado anterior a esta transacción. Va acá y no
    # dentro de la re-optimización para que también avise cuando el
    # estado cambió sin que haya re-optimización (p. ej. una entrega
    # fallida sobre la última parada pendiente).
    await notificar_ruta_actualizada(
        ruta.id,
        {
            "ruta_id": ruta.id,
            "vehiculo_id": ruta.vehiculo_id,
            "evento": "reoptimizada",
            "reoptimizada_en": datetime.now(ZONA_OPERACION).isoformat(),
        },
    )

    return incidencia
