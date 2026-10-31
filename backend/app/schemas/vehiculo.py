from pydantic import BaseModel


class VehiculoCreate(BaseModel):
    patente: str
    capacidad_kg: float
    deposito_id: int
    activo: bool = True


class VehiculoUpdate(BaseModel):
    patente: str | None = None
    capacidad_kg: float | None = None
    deposito_id: int | None = None
    activo: bool | None = None


class VehiculoOut(BaseModel):
    id: int
    patente: str
    capacidad_kg: float
    deposito_id: int
    activo: bool

    class Config:
        from_attributes = True
