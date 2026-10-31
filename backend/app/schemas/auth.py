from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RolUsuario


class UsuarioSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str
    rol: RolUsuario


class OperarioSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre: str = Field(min_length=1)


class AdminSignup(OperarioSignup):
    codigo_invitacion: str


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    rol: RolUsuario

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
