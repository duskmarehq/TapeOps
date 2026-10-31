from pydantic import BaseModel


class ClienteCreate(BaseModel):
    razon_social: str
    direccion: str | None = None
    latitud: float
    longitud: float


class ClienteUpdate(BaseModel):
    razon_social: str | None = None
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class ClienteOut(BaseModel):
    id: int
    razon_social: str
    direccion: str | None
    latitud: float
    longitud: float

    class Config:
        from_attributes = True
