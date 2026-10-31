import logging

import firebase_admin
from app.core.config import settings
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_app = None


def _get_firestore_client():
    global _app
    if _app is None:
        if not settings.firebase_credentials_path:
            return None
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred)
        return firestore.client(database_id="default")


async def notificar_ruta_actualizada(ruta_id: int, payload: dict) -> None:
    """
    Escribe el estado actualizado de una ruta en Firestore, para que el
    dashboard del gestor (rubik-web) se refresque sin polling.

    Si Firebase no está configurado todavía (falta el service account),
    esto no interrumpe el flujo: Postgres sigue siendo la fuente de
    verdad, y esta escritura es señalización best-effort, no persistencia
    de negocio. Un fallo acá nunca debe tirar abajo el reporte de una
    incidencia ni la re-optimización que ya se guardó en la base.
    """
    try:
        client = _get_firestore_client()
        if client is None:
            logger.warning(
                "Firebase no configurado — se omite notificación en tiempo real"
            )
            return
        client.collection("rutas_activas").document(str(ruta_id)).set(payload)
    except Exception:
        logger.exception("Fallo al notificar a Firebase para ruta_id=%s", ruta_id)
