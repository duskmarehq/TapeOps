from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TipoIncidencia


class Incidencia(Base):
    __tablename__ = "incidencia"
    __table_args__ = (
        Index("idx_incidencia_stop", "stop_id"),
        Index("idx_incidencia_no_resuelta", "stop_id", postgresql_where="resuelta = false"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("stop.id"), nullable=False)
    reportado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    tipo: Mapped[TipoIncidencia] = mapped_column(
        Enum(TipoIncidencia, name="tipo_incidencia", create_type=False), nullable=False
    )
    descripcion: Mapped[str | None] = mapped_column(Text)
    resuelta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stop = relationship("Stop")
    reportante = relationship("Usuario")
