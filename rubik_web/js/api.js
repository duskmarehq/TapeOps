import { API_BASE_URL } from "./config.js";
import { obtenerToken, cerrarSesion } from "./auth.js";

async function solicitud(path, opciones = {}) {
  const token = obtenerToken();
  const headers = { "Content-Type": "application/json", ...(opciones.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${path}`, { ...opciones, headers });

  if (res.status === 401) {
    cerrarSesion();
    throw new Error("Sesión expirada — volvé a iniciar sesión");
  }

  if (!res.ok) {
    let detalle = res.statusText;
    try {
      const data = await res.json();
      detalle = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      // la respuesta no trajo cuerpo JSON — se conserva el statusText
    }
    throw new Error(detalle);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => solicitud(path),
  post: (path, body) => solicitud(path, { method: "POST", body: JSON.stringify(body) }),
  put: (path, body) => solicitud(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path) => solicitud(path, { method: "DELETE" }),
};
