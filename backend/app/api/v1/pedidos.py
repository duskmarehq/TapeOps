from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.enums import EstadoPedido, RolUsuario
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.schemas.pedido import PedidoCreate, PedidoOut

router = APIRouter(prefix="/pedidos", tags=["pedidos"], dependencies=[Depends(require_admin)])


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
async def crear_pedido(datos: PedidoCreate, db: AsyncSession = Depends(get_db)) -> Pedido:
    if datos.ventana_fin <= datos.ventana_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ventana de fin debe ser posterior a la de inicio",
        )

    if datos.operario_id is not None:
        operario = await db.get(Usuario, datos.operario_id)
        if operario is None or operario.rol != RolUsuario.operario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El operario indicado no existe o no tiene rol operario",
            )

    pedido = Pedido(**datos.model_dump())
    db.add(pedido)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente inexistente"
        ) from exc
    await db.refresh(pedido)
    return pedido


@router.get("", response_model=list[PedidoOut])
async def listar_pedidos(
    estado: EstadoPedido | None = None, db: AsyncSession = Depends(get_db)
) -> list[Pedido]:
    query = select(Pedido)
    if estado is not None:
        query = query.where(Pedido.estado == estado)
    result = await db.scalars(query)
    return list(result)


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pedido(pedido_id: int, db: AsyncSession = Depends(get_db)) -> None:
    pedido = await db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    # Solo un pedido pendiente puede borrarse: los demás ya tienen un stop
    # (y el historial de la entrega) que depende de él.
    if pedido.estado != EstadoPedido.pendiente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solo se pueden eliminar pedidos pendientes; este figura como {pedido.estado.value}",
        )

    await db.delete(pedido)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: el pedido tiene registros asociados",
        ) from exc
