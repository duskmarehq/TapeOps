from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoStop


class Stop(Base):
    __tablename__ = "stop"
    __table_args__ = (
        UniqueConstraint("ruta_id", "orden", name="orden_unico_por_ruta"),
        Index("idx_stop_ruta", "ruta_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("ruta.id", ondelete="CASCADE"), nullable=False)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedido.id"), unique=True, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    hora_estimada_llegada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hora_real_llegada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoStop] = mapped_column(
        Enum(EstadoStop, name="estado_stop", create_type=False),
        default=EstadoStop.pendiente,
        nullable=False,
    )

    ruta = relationship("Ruta", back_populates="stops")
    pedido = relationship("Pedido")
