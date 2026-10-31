from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    id: Mapped[int] = mapped_column(primary_key=True)
    patente: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    capacidad_kg: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    deposito_id: Mapped[int] = mapped_column(ForeignKey("deposito.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    deposito = relationship("Deposito")
