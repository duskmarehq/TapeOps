from datetime import date

from pydantic import BaseModel


class AsignacionVehiculo(BaseModel):
    vehiculo_id: int
    operario_id: int


class OptimizacionRequest(BaseModel):
    fecha: date
    asignaciones: list[AsignacionVehiculo]


class ParadaAsignada(BaseModel):
    pedido_id: int
    orden: int
    hora_estimada_llegada: str


class RutaCreada(BaseModel):
    ruta_id: int
    vehiculo_id: int
    operario_id: int
    paradas: list[ParadaAsignada]


class OptimizacionResponse(BaseModel):
    rutas: list[RutaCreada]
    pedidos_no_asignados: list[int]
