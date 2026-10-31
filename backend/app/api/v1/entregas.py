from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_operario
from app.core.database import get_db
from app.models.enums import EstadoPedido, EstadoRuta, EstadoStop
from app.models.pedido import Pedido
from app.models.ruta import Ruta
from app.models.stop import Stop
from app.models.usuario import Usuario
from app.services.firebase_service import notificar_ruta_actualizada

router = APIRouter(prefix="/entregas", tags=["entregas"])

ZONA_OPERACION = ZoneInfo("America/Asuncion")


class EntregaConfirmada(BaseModel):
    stop_id: int
    pedido_id: int
    ruta_id: int
    ruta_estado: EstadoRuta
    hora_real_llegada: str


@router.post("/{stop_id}/confirmar", response_model=EntregaConfirmada)
async def confirmar_entrega(
    stop_id: int,
    usuario: Usuario = Depends(require_operario),
    db: AsyncSession = Depends(get_db),
) -> EntregaConfirmada:
    """
    El operario confirma que entregó el pedido de una parada propia:
    stop -> completado (con hora real), pedido -> entregado, y la ruta
    pasa a en_curso o, si no quedan paradas pendientes, a finalizada.
    """
    # with_for_update bloquea la fila del stop hasta el commit: dos
    # confirmaciones simultáneas de la misma parada no pueden pasar
    # ambas el chequeo de estado.
    stop = await db.scalar(select(Stop).where(Stop.id == stop_id).with_for_update())
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
            detail=f"La parada ya figura como {stop.estado.value}",
        )

    pedido = await db.get(Pedido, stop.pedido_id)
    ahora = datetime.now(ZONA_OPERACION)

    stop.estado = EstadoStop.completado
    stop.hora_real_llegada = ahora
    pedido.estado = EstadoPedido.entregado
    await db.flush()

    pendientes = await db.scalar(
        select(func.count())
        .select_from(Stop)
        .where(Stop.ruta_id == ruta.id, Stop.estado == EstadoStop.pendiente)
    )
    ruta.estado = EstadoRuta.finalizada if pendientes == 0 else EstadoRuta.en_curso

    await db.commit()

    # Después del commit, por la misma razón que en incidencias: los
    # clientes reaccionan al aviso pidiendo datos a la API.
    await notificar_ruta_actualizada(
        ruta.id,
        {
            "ruta_id": ruta.id,
            "vehiculo_id": ruta.vehiculo_id,
            "evento": "entrega_confirmada",
            "pedido_id": pedido.id,
            "ruta_estado": ruta.estado.value,
            "actualizada_en": ahora.isoformat(),
        },
    )

    return EntregaConfirmada(
        stop_id=stop.id,
        pedido_id=pedido.id,
        ruta_id=ruta.id,
        ruta_estado=ruta.estado,
        hora_real_llegada=ahora.isoformat(),
    )
