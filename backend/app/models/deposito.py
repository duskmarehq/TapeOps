from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Deposito(Base):
    __tablename__ = "deposito"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(255))
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
