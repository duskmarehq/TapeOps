import httpx

from app.core.config import settings


class OSRMError(Exception):
    pass


async def obtener_matriz_tiempos(coordenadas: list[tuple[float, float]]) -> list[list[float]]:
    """
    coordenadas: lista de (longitud, latitud) — OJO: OSRM espera lon,lat,
    al revés del orden en que guardamos latitud/longitud en la base.
    El primer elemento de `coordenadas` debe ser el depósito.

    Devuelve una matriz NxN de tiempos de viaje en segundos.
    """
    coords_str = ";".join(f"{lon},{lat}" for lon, lat in coordenadas)
    url = f"{settings.osrm_base_url}/table/v1/driving/{coords_str}"
    params = {"annotations": "duration"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OSRMError(f"Fallo al consultar OSRM: {exc}") from exc

    data = response.json()
    if data.get("code") != "Ok":
        raise OSRMError(f"OSRM devolvió código {data.get('code')}")

    matriz = data["durations"]
    if any(None in fila for fila in matriz):
        raise OSRMError(
            "OSRM no pudo rutear entre algunos de los puntos "
            "(coordenada fuera de la red vial cargada)"
        )

    return matriz


async def obtener_trazado_ruta(coordenadas: list[tuple[float, float]]) -> dict:
    """
    Pide a OSRM el recorrido real por calles que pasa, en orden, por todas
    las coordenadas (longitud, latitud). Devuelve la geometría en GeoJSON
    (LineString, con coordenadas [longitud, latitud]) más la distancia en
    metros y la duración en segundos.
    """
    coords_str = ";".join(f"{lon},{lat}" for lon, lat in coordenadas)
    url = f"{settings.osrm_base_url}/route/v1/driving/{coords_str}"
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OSRMError(f"Fallo al consultar OSRM: {exc}") from exc

    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise OSRMError(f"OSRM no pudo trazar la ruta (código {data.get('code')})")

    ruta = data["routes"][0]
    return {
        "geometria": ruta["geometry"],
        "distancia_m": ruta["distance"],
        "duracion_s": ruta["duration"],
    }
