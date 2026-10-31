from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Código que hay que presentar para registrarse como administrador.
    # Si no está definido en el .env, el registro de administradores
    # queda deshabilitado (más seguro que tener un valor por defecto).
    admin_invite_code: str | None = None

    osrm_base_url: str = "http://localhost:5001"

    # Ruta al JSON de la service account de Firebase (Admin SDK). Sin esto
    # configurado, las notificaciones en tiempo real quedan deshabilitadas
    # pero el resto del sistema sigue funcionando — Postgres es la fuente
    # de verdad, Firebase es señalización best-effort, no persistencia.
    firebase_credentials_path: str | None = None

    # Orígenes desde los que rubik-web puede llamar a esta API en
    # desarrollo. Live Server de VS Code usa 5500 por defecto, pero el
    # puerto exacto aparece en la barra de estado de VS Code al abrir
    # index.html — si no coincide con esta lista, el fetch sigue
    # bloqueado por el navegador aunque el backend esté funcionando bien.
    cors_origins: list[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
