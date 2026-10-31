from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import RolUsuario
from app.models.usuario import Usuario

# tokenUrl solo sirve para que Swagger UI sepa dónde pedir el token;
# el login real recibe JSON, no form-data, así que esto no obliga
# a que /auth/login use el flujo de formulario de OAuth2.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    try:
        payload = decode_access_token(token)
        usuario_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        ) from exc

    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    return usuario


def requiere_rol(rol_requerido: RolUsuario):
    async def dependencia(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol != rol_requerido:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
        return usuario

    return dependencia


require_admin = requiere_rol(RolUsuario.admin)
require_operario = requiere_rol(RolUsuario.operario)
