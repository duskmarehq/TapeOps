from pydantic import BaseModel


class DepositoCreate(BaseModel):
    nombre: str
    direccion: str | None = None
    latitud: float
    longitud: float


class DepositoUpdate(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class DepositoOut(BaseModel):
    id: int
    nombre: str
    direccion: str | None
    latitud: float
    longitud: float

    class Config:
        from_attributes = True
