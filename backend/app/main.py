from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.auth import router as auth_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.depositos import router as depositos_router
from app.api.v1.entregas import router as entregas_router
from app.api.v1.incidencias import router as incidencias_router
from app.api.v1.operario import router as operario_router
from app.api.v1.pedidos import router as pedidos_router
from app.api.v1.rutas import router as rutas_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.vehiculos import router as vehiculos_router
from app.core.config import settings
from app.core.database import engine

app = FastAPI(title="Rubik API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Flutter web (`flutter run -d chrome`) usa un puerto aleatorio de
    # localhost en cada ejecución, imposible de listar de antemano.
    # Esto acepta cualquier puerto de localhost/127.0.0.1 — solo
    # para desarrollo; en producción hay que sacarlo y usar la lista.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(depositos_router, prefix="/api/v1")
app.include_router(vehiculos_router, prefix="/api/v1")
app.include_router(clientes_router, prefix="/api/v1")
app.include_router(pedidos_router, prefix="/api/v1")
app.include_router(rutas_router, prefix="/api/v1")
app.include_router(incidencias_router, prefix="/api/v1")
app.include_router(usuarios_router, prefix="/api/v1")
app.include_router(operario_router, prefix="/api/v1")
app.include_router(entregas_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}
