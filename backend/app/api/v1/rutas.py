from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Las ventanas horarias de los pedidos se cargan en hora local de la
# zona de operación, no en UTC. Sin fijar esto explícitamente, el
# datetime queda "naive" y Postgres lo interpreta según el TimeZone
# de la sesión — que varía entre entornos y puede desfasar los
# horarios reales sin que ningún test lo detecte.
ZONA_OPERACION = ZoneInfo("America/Asuncion")

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.deposito import Deposito
from app.models.enums import EstadoPedido, EstadoStop, RolUsuario
from app.models.pedido import Pedido
from app.models.ruta import Ruta
from app.models.stop import Stop
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.schemas.optimizacion import (
    OptimizacionRequest,
    OptimizacionResponse,
    ParadaAsignada,
    RutaCreada,
)
from app.services.optimizador.or_tools_solver import ParadaOptimizar, resolver_vrptw
from app.services.optimizador.osrm_client import (
    OSRMError,
    obtener_matriz_tiempos,
    obtener_trazado_ruta,
)

router = APIRouter(prefix="/rutas", tags=["rutas"], dependencies=[Depends(require_admin)])


def _segundos_desde_medianoche(t: time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second


@router.post("/optimizar", response_model=OptimizacionResponse)
async def optimizar_rutas(
    datos: OptimizacionRequest, db: AsyncSession = Depends(get_db)
) -> OptimizacionResponse:
    # Depósito único para el MVP: toma el primero que encuentre en la
    # tabla. Si en algún momento se carga un segundo depósito, esto lo
    # ignora sin avisar — aceptable como recorte de alcance, pero hay
    # que revisitarlo si el proyecto crece más allá del MVP.
    deposito = await db.scalar(select(Deposito).limit(1))
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay depósito cargado")

    vehiculo_ids = [a.vehiculo_id for a in datos.asignaciones]
    vehiculos = await db.scalars(select(Vehiculo).where(Vehiculo.id.in_(vehiculo_ids)))
    vehiculos_por_id = {v.id: v for v in vehiculos}
    if len(vehiculos_por_id) != len(set(vehiculo_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Algún vehículo no existe")

    operario_ids = [a.operario_id for a in datos.asignaciones]
    operarios = await db.scalars(
        select(Usuario).where(Usuario.id.in_(operario_ids), Usuario.rol == RolUsuario.operario)
    )
    operarios_por_id = {u.id: u for u in operarios}
    if len(operarios_por_id) != len(set(operario_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Algún operario no existe o no tiene rol operario",
        )

    pendientes = list(
        await db.scalars(select(Pedido).where(Pedido.estado == EstadoPedido.pendiente))
    )
    if not pendientes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay pedidos pendientes")

    # Posición (índice de vehículo para el solver) de cada operario en esta corrida.
    vehiculos_por_operario: dict[int, list[int]] = {}
    for indice, asignacion in enumerate(datos.asignaciones):
        vehiculos_por_operario.setdefault(asignacion.operario_id, []).append(indice)

    # Un pedido preasignado a un operario que no participa de esta corrida no
    # se puede planificar ahora: queda pendiente y se informa como sin asignar.
    pedidos = [
        p for p in pendientes
        if p.operario_id is None or p.operario_id in vehiculos_por_operario
    ]
    ids_incluidos = {p.id for p in pedidos}
    ids_de_operario_ausente = [p.id for p in pendientes if p.id not in ids_incluidos]
    if not pedidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ningún pedido pendiente corresponde a los operarios de esta corrida",
        )

    pedidos_por_id = {p.id: p for p in pedidos}

    # obtener_matriz_tiempos espera (longitud, latitud), al revés del
    # orden en que guardamos latitud/longitud en la base.
    coordenadas = [(float(deposito.longitud), float(deposito.latitud))]
    coordenadas += [(float(p.longitud), float(p.latitud)) for p in pedidos]

    try:
        matriz = await obtener_matriz_tiempos(coordenadas)
    except OSRMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    paradas_optimizar = [
        ParadaOptimizar(
            id=p.id,
            ventana_inicio_seg=_segundos_desde_medianoche(p.ventana_inicio),
            ventana_fin_seg=_segundos_desde_medianoche(p.ventana_fin),
            demanda_kg=float(p.peso_kg),
            vehiculos_permitidos=(
                vehiculos_por_operario[p.operario_id] if p.operario_id is not None else None
            ),
        )
        for p in pedidos
    ]

    capacidades = [float(vehiculos_por_id[a.vehiculo_id].capacidad_kg) for a in datos.asignaciones]

    resultado = resolver_vrptw(
        matriz_tiempos=matriz,
        paradas=paradas_optimizar,
        capacidades_vehiculos=capacidades,
    )

    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El solver no encontró ninguna solución factible",
        )

    rutas_por_indice = {r.vehiculo_index: r for r in resultado}

    rutas_creadas: list[RutaCreada] = []
    pedidos_asignados_ids: set[int] = set()

    for indice, asignacion in enumerate(datos.asignaciones):
        ruta_resultado = rutas_por_indice.get(indice)
        if ruta_resultado is None:
            continue  # este vehículo no recibió pedidos en esta corrida

        ruta = Ruta(
            vehiculo_id=asignacion.vehiculo_id,
            operario_id=asignacion.operario_id,
            fecha=datos.fecha,
        )
        db.add(ruta)
        await db.flush()  # necesitamos ruta.id antes de crear los stops

        paradas_out = []
        for orden, (pedido_id, llegada_seg) in enumerate(
            zip(ruta_resultado.paradas_en_orden, ruta_resultado.llegada_estimada_seg),
            start=1,
        ):
            pedido = pedidos_por_id[pedido_id]
            hora_estimada = datetime.combine(
                datos.fecha, time.min, tzinfo=ZONA_OPERACION
            ) + timedelta(seconds=llegada_seg)

            db.add(
                Stop(
                    ruta_id=ruta.id,
                    pedido_id=pedido.id,
                    orden=orden,
                    hora_estimada_llegada=hora_estimada,
                    estado=EstadoStop.pendiente,
                )
            )
            pedido.estado = EstadoPedido.asignado
            pedidos_asignados_ids.add(pedido_id)

            paradas_out.append(
                ParadaAsignada(
                    pedido_id=pedido.id,
                    orden=orden,
                    hora_estimada_llegada=hora_estimada.isoformat(),
                )
            )

        rutas_creadas.append(
            RutaCreada(
                ruta_id=ruta.id,
                vehiculo_id=asignacion.vehiculo_id,
                operario_id=asignacion.operario_id,
                paradas=paradas_out,
            )
        )

    pedidos_no_asignados = [p.id for p in pedidos if p.id not in pedidos_asignados_ids]
    pedidos_no_asignados += ids_de_operario_ausente

    await db.commit()

    return OptimizacionResponse(rutas=rutas_creadas, pedidos_no_asignados=pedidos_no_asignados)


@router.get("/{ruta_id}")
async def obtener_ruta(ruta_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    ruta = await db.get(Ruta, ruta_id)
    if ruta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ruta no encontrada")

    stops = await db.scalars(select(Stop).where(Stop.ruta_id == ruta_id).order_by(Stop.orden))

    return {
        "id": ruta.id,
        "vehiculo_id": ruta.vehiculo_id,
        "operario_id": ruta.operario_id,
        "fecha": ruta.fecha.isoformat(),
        "estado": ruta.estado.value,
        "paradas": [
            {
                "pedido_id": s.pedido_id,
                "orden": s.orden,
                "hora_estimada_llegada": (
                    s.hora_estimada_llegada.isoformat() if s.hora_estimada_llegada else None
                ),
                "estado": s.estado.value,
            }
            for s in stops
        ],
    }


@router.get("/{ruta_id}/trazado")
async def obtener_trazado(ruta_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Recorrido por calles de la ruta: depósito, cada parada en su orden y
    regreso al depósito (el modelo de optimización cierra la ruta ahí).
    """
    ruta = await db.get(Ruta, ruta_id)
    if ruta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ruta no encontrada")

    deposito = await db.scalar(select(Deposito).limit(1))
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay depósito cargado")

    stops = list(await db.scalars(select(Stop).where(Stop.ruta_id == ruta_id).order_by(Stop.orden)))
    if not stops:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La ruta no tiene paradas")

    origen = (float(deposito.longitud), float(deposito.latitud))
    coordenadas = [origen]
    for stop in stops:
        pedido = await db.get(Pedido, stop.pedido_id)
        coordenadas.append((float(pedido.longitud), float(pedido.latitud)))
    coordenadas.append(origen)

    try:
        trazado = await obtener_trazado_ruta(coordenadas)
    except OSRMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"ruta_id": ruta.id, **trazado}
