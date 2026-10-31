import { API_BASE_URL } from "./config.js";

const TOKEN_KEY = "rubik_token";

export function obtenerToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function guardarToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function cerrarSesion() {
  sessionStorage.removeItem(TOKEN_KEY);
  window.location.reload();
}

export async function obtenerUsuarioActual() {
  const token = obtenerToken();
  if (!token) return null;

  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    cerrarSesion();
    return null;
  }

  return res.json();
}

export async function registrarAdmin({ nombre, email, password, codigo }) {
  const res = await fetch(`${API_BASE_URL}/auth/signup/admin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, email, password, codigo_invitacion: codigo }),
  });

  if (!res.ok) {
    let detalle = "No se pudo crear la cuenta";
    try {
      const data = await res.json();
      // Los errores de validación (422) traen una lista, no un texto.
      if (typeof data.detail === "string") detalle = data.detail;
    } catch {
      // respuesta sin cuerpo JSON: se conserva el mensaje genérico
    }
    throw new Error(detalle);
  }

  // Cuenta creada: se inicia sesión directo con las mismas credenciales.
  return iniciarSesion(email, password);
}

export async function iniciarSesion(email, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    throw new Error("Credenciales inválidas");
  }

  const { access_token: token } = await res.json();
  guardarToken(token);

  const meRes = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const usuario = await meRes.json();

  if (usuario.rol !== "admin") {
    cerrarSesion();
    throw new Error("Esta cuenta no tiene rol de administrador");
  }

  return usuario;
}
