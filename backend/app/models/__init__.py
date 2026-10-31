# Importar todos los modelos acá es lo que le permite a Base.metadata
# (y por lo tanto a Alembic autogenerate) verlos. Un modelo que exista
# como archivo pero no se importe acá es invisible para las migraciones.
from app.models.cliente import Cliente
from app.models.deposito import Deposito
from app.models.incidencia import Incidencia
from app.models.pedido import Pedido
from app.models.ruta import Ruta
from app.models.stop import Stop
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo

__all__ = [
    "Cliente",
    "Deposito",
    "Incidencia",
    "Pedido",
    "Ruta",
    "Stop",
    "Usuario",
    "Vehiculo",
]
