from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.enums import RolUsuario
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    rol: RolUsuario | None = None, db: AsyncSession = Depends(get_db)
) -> list[Usuario]:
    query = select(Usuario)
    if rol is not None:
        query = query.where(Usuario.rol == rol)
    result = await db.scalars(query)
    return list(result)
