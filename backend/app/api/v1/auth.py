import secrets

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.enums import RolUsuario
from app.models.usuario import Usuario
from app.schemas.auth import (
    AdminSignup,
    OperarioSignup,
    Token,
    UsuarioLogin,
    UsuarioOut,
    UsuarioSignup,
)
from app.services.auth_service import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    autenticar_usuario,
    registrar_usuario,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


async def _registrar(
    db: AsyncSession, datos: OperarioSignup, rol: RolUsuario
) -> Usuario:
    try:
        return await registrar_usuario(
            db,
            UsuarioSignup(
                email=datos.email, password=datos.password, nombre=datos.nombre, rol=rol
            ),
        )
    except EmailYaRegistradoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado"
        ) from exc


@router.post(
    "/signup/operario", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED
)
async def signup_operario(
    datos: OperarioSignup, db: AsyncSession = Depends(get_db)
) -> Usuario:
    # Registro público, pero el rol lo fija el servidor: nadie puede elegirlo.
    return await _registrar(db, datos, RolUsuario.operario)


@router.post(
    "/signup/admin", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED
)
async def signup_admin(
    datos: AdminSignup, db: AsyncSession = Depends(get_db)
) -> Usuario:
    if not settings.admin_invite_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El registro de administradores está deshabilitado",
        )
    if not secrets.compare_digest(
        datos.codigo_invitacion.encode(), settings.admin_invite_code.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Código de invitación inválido",
        )
    return await _registrar(db, datos, RolUsuario.admin)


@router.post("/login", response_model=Token)
async def login(datos: UsuarioLogin, db: AsyncSession = Depends(get_db)) -> Token:
    try:
        access_token = await autenticar_usuario(db, datos.email, datos.password)
    except CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        ) from exc

    return Token(access_token=access_token)


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
