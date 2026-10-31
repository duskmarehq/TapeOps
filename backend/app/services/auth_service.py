from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioSignup


class EmailYaRegistradoError(Exception):
    pass


class CredencialesInvalidasError(Exception):
    pass


async def registrar_usuario(db: AsyncSession, datos: UsuarioSignup) -> Usuario:
    existente = await db.scalar(select(Usuario).where(Usuario.email == datos.email))
    if existente is not None:
        raise EmailYaRegistradoError

    usuario = Usuario(
        email=datos.email,
        password_hash=hash_password(datos.password),
        nombre=datos.nombre,
        rol=datos.rol,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def autenticar_usuario(db: AsyncSession, email: str, password: str) -> str:
    usuario = await db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise CredencialesInvalidasError

    return create_access_token(subject=str(usuario.id), rol=usuario.rol.value)
