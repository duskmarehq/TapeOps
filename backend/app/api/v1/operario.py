from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operario
from app.core.database import get_db
from app.models.enums import EstadoRuta
from app.models.pedido import Pedido
from app.models.ruta import Ruta
from app.models.stop import Stop
from app.models.usuario import Usuario
from app.schemas.mi_ruta import MiRutaResponse, ParadaDetalle

router = APIRouter(prefix="/mi-ruta", tags=["operario"])


@router.get("", response_model=MiRutaResponse)
async def obtener_mi_ruta(
    usuario: Usuario = Depends(require_operario),
    db: AsyncSession = Depends(get_db),
) -> MiRutaResponse:
    """
    Devuelve la ruta activa (no finalizada) más reciente asignada al
    operario autenticado, con el detalle completo de cada parada —
    coordenadas, peso y ventana horaria incluidos — para que la app
    móvil no necesite golpear ningún endpoint admin-only (/pedidos,
    /rutas/{id}) a los que un operario no tiene acceso.
    """
    ruta = await db.scalar(
        select(Ruta)
        .where(Ruta.operario_id == usuario.id, Ruta.estado != EstadoRuta.finalizada)
        .order_by(Ruta.fecha.desc())
        .limit(1)
    )
    if ruta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenés ninguna ruta activa asignada",
        )

    stops = list(
        await db.scalars(select(Stop).where(Stop.ruta_id == ruta.id).order_by(Stop.orden))
    )

    paradas = []
    for s in stops:
        pedido = await db.get(Pedido, s.pedido_id)
        paradas.append(
            ParadaDetalle(
                stop_id=s.id,
                pedido_id=pedido.id,
                orden=s.orden,
                latitud=float(pedido.latitud),
                longitud=float(pedido.longitud),
                peso_kg=float(pedido.peso_kg),
                ventana_inicio=pedido.ventana_inicio.isoformat(),
                ventana_fin=pedido.ventana_fin.isoformat(),
                hora_estimada_llegada=(
                    s.hora_estimada_llegada.isoformat() if s.hora_estimada_llegada else None
                ),
                estado=s.estado,
            )
        )

    return MiRutaResponse(
        ruta_id=ruta.id,
        vehiculo_id=ruta.vehiculo_id,
        fecha=ruta.fecha.isoformat(),
        estado=ruta.estado,
        paradas=paradas,
    )
