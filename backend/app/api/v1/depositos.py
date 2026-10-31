from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.deposito import Deposito
from app.schemas.deposito import DepositoCreate, DepositoOut, DepositoUpdate

router = APIRouter(prefix="/depositos", tags=["depositos"], dependencies=[Depends(require_admin)])


@router.post("", response_model=DepositoOut, status_code=status.HTTP_201_CREATED)
async def crear_deposito(datos: DepositoCreate, db: AsyncSession = Depends(get_db)) -> Deposito:
    deposito = Deposito(**datos.model_dump())
    db.add(deposito)
    await db.commit()
    await db.refresh(deposito)
    return deposito


@router.get("", response_model=list[DepositoOut])
async def listar_depositos(db: AsyncSession = Depends(get_db)) -> list[Deposito]:
    result = await db.scalars(select(Deposito))
    return list(result)


@router.get("/{deposito_id}", response_model=DepositoOut)
async def obtener_deposito(deposito_id: int, db: AsyncSession = Depends(get_db)) -> Deposito:
    deposito = await db.get(Deposito, deposito_id)
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depósito no encontrado")
    return deposito


@router.put("/{deposito_id}", response_model=DepositoOut)
async def actualizar_deposito(
    deposito_id: int, datos: DepositoUpdate, db: AsyncSession = Depends(get_db)
) -> Deposito:
    deposito = await db.get(Deposito, deposito_id)
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depósito no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(deposito, campo, valor)

    await db.commit()
    await db.refresh(deposito)
    return deposito


@router.delete("/{deposito_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_deposito(deposito_id: int, db: AsyncSession = Depends(get_db)) -> None:
    deposito = await db.get(Deposito, deposito_id)
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depósito no encontrado")

    await db.delete(deposito)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: hay vehículos asociados a este depósito",
        ) from exc
