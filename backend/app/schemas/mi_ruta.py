from pydantic import BaseModel

from app.models.enums import EstadoRuta, EstadoStop


class ParadaDetalle(BaseModel):
    stop_id: int
    pedido_id: int
    orden: int
    latitud: float
    longitud: float
    peso_kg: float
    ventana_inicio: str
    ventana_fin: str
    hora_estimada_llegada: str | None
    estado: EstadoStop


class MiRutaResponse(BaseModel):
    ruta_id: int
    vehiculo_id: int
    fecha: str
    estado: EstadoRuta
    paradas: list[ParadaDetalle]
