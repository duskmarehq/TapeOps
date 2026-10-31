from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(require_admin)])


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(datos: ClienteCreate, db: AsyncSession = Depends(get_db)) -> Cliente:
    cliente = Cliente(**datos.model_dump())
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(db: AsyncSession = Depends(get_db)) -> list[Cliente]:
    result = await db.scalars(select(Cliente))
    return list(result)


@router.get("/{cliente_id}", response_model=ClienteOut)
async def obtener_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)) -> Cliente:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
async def actualizar_cliente(
    cliente_id: int, datos: ClienteUpdate, db: AsyncSession = Depends(get_db)
) -> Cliente:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)

    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)) -> None:
    cliente = await db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    await db.delete(cliente)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: hay pedidos asociados a este cliente",
        ) from exc
