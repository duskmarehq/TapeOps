from pydantic import BaseModel

from app.models.enums import TipoIncidencia


class IncidenciaCreate(BaseModel):
    stop_id: int
    tipo: TipoIncidencia
    descripcion: str | None = None


class IncidenciaOut(BaseModel):
    id: int
    stop_id: int
    reportado_por: int
    tipo: TipoIncidencia
    descripcion: str | None
    resuelta: bool

    class Config:
        from_attributes = True
