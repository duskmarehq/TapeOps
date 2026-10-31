from datetime import datetime, time

from pydantic import BaseModel

from app.models.enums import EstadoPedido


class PedidoCreate(BaseModel):
    cliente_id: int
    operario_id: int | None = None
    latitud: float
    longitud: float
    peso_kg: float
    ventana_inicio: time
    ventana_fin: time


class PedidoOut(BaseModel):
    id: int
    cliente_id: int
    operario_id: int | None = None
    latitud: float
    longitud: float
    peso_kg: float
    ventana_inicio: time
    ventana_fin: time
    estado: EstadoPedido
    created_at: datetime

    class Config:
        from_attributes = True
