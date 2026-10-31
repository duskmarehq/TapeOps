from datetime import datetime, time

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EstadoPedido


class Pedido(Base):
    __tablename__ = "pedido"
    __table_args__ = (
        CheckConstraint("ventana_fin > ventana_inicio", name="ventana_valida"),
        Index("idx_pedido_estado", "estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id"), nullable=False)
    # Operario al que se preasigna el pedido (opcional). Si está definido,
    # la optimización solo puede ponerlo en un vehículo de ese operario.
    operario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    peso_kg: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    ventana_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    ventana_fin: Mapped[time] = mapped_column(Time, nullable=False)
    estado: Mapped[EstadoPedido] = mapped_column(
        Enum(EstadoPedido, name="estado_pedido", create_type=False),
        default=EstadoPedido.pendiente,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cliente = relationship("Cliente")
