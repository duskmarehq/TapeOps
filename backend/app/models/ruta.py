from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoRuta


class Ruta(Base):
    __tablename__ = "ruta"
    __table_args__ = (
        Index("idx_ruta_vehiculo", "vehiculo_id"),
        Index("idx_ruta_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vehiculo_id: Mapped[int] = mapped_column(ForeignKey("vehiculo.id"), nullable=False)
    operario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[EstadoRuta] = mapped_column(
        Enum(EstadoRuta, name="estado_ruta", create_type=False),
        default=EstadoRuta.planificada,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vehiculo = relationship("Vehiculo")
    operario = relationship("Usuario")
    stops = relationship("Stop", back_populates="ruta", order_by="Stop.orden")
