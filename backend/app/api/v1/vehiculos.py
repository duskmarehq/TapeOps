from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.vehiculo import Vehiculo
from app.schemas.vehiculo import VehiculoCreate, VehiculoOut, VehiculoUpdate

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"], dependencies=[Depends(require_admin)])


@router.post("", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
async def crear_vehiculo(datos: VehiculoCreate, db: AsyncSession = Depends(get_db)) -> Vehiculo:
    vehiculo = Vehiculo(**datos.model_dump())
    db.add(vehiculo)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patente duplicada o depósito inexistente",
        ) from exc
    await db.refresh(vehiculo)
    return vehiculo


@router.get("", response_model=list[VehiculoOut])
async def listar_vehiculos(db: AsyncSession = Depends(get_db)) -> list[Vehiculo]:
    result = await db.scalars(select(Vehiculo))
    return list(result)


@router.get("/{vehiculo_id}", response_model=VehiculoOut)
async def obtener_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)) -> Vehiculo:
    vehiculo = await db.get(Vehiculo, vehiculo_id)
    if vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    return vehiculo


@router.put("/{vehiculo_id}", response_model=VehiculoOut)
async def actualizar_vehiculo(
    vehiculo_id: int, datos: VehiculoUpdate, db: AsyncSession = Depends(get_db)
) -> Vehiculo:
    vehiculo = await db.get(Vehiculo, vehiculo_id)
    if vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(vehiculo, campo, valor)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patente duplicada o depósito inexistente",
        ) from exc
    await db.refresh(vehiculo)
    return vehiculo


@router.delete("/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)) -> None:
    vehiculo = await db.get(Vehiculo, vehiculo_id)
    if vehiculo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    await db.delete(vehiculo)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: hay rutas asociadas a este vehículo",
        ) from exc
