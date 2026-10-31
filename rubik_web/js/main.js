import { obtenerToken, obtenerUsuarioActual, iniciarSesion, registrarAdmin, cerrarSesion } from "./auth.js";
import { crearMapa, crearCapas } from "./mapa.js";
import { cargarDatosIniciales, mostrarSeccion, configurarModalOptimizar, manejarNotificacionRuta } from "./rutas.js";
import { iniciarListenerRutas } from "./firebase-listener.js";

const estado = {
  mapa: null,
  capas: null,
  deposito: null,
  pedidos: [],
  vehiculos: [],
  clientes: [],
  operarios: [],
};

function actualizarIndicadorConexion(conectado, texto) {
  const punto = document.getElementById("conexion-indicador");
  const label = document.getElementById("conexion-texto");
  punto.classList.toggle("indicador--on", conectado);
  punto.classList.toggle("indicador--off", !conectado);
  label.textContent = texto;
}

async function mostrarApp(usuario) {
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app").hidden = false;
  document.getElementById("usuario-email").textContent = usuario.email;

  estado.mapa = crearMapa("mapa");
  estado.capas = crearCapas();

  await cargarDatosIniciales(estado);
  mostrarSeccion("pedidos", estado);
  configurarModalOptimizar(estado);

  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => mostrarSeccion(btn.dataset.seccion, estado));
  });

  document.getElementById("btn-logout").addEventListener("click", cerrarSesion);

  iniciarListenerRutas(
    (payload) => manejarNotificacionRuta(payload, estado),
    actualizarIndicadorConexion
  );
}

async function iniciar() {
  const token = obtenerToken();
  if (token) {
    const usuario = await obtenerUsuarioActual();
    if (usuario) {
      await mostrarApp(usuario);
      return;
    }
  }

  document.getElementById("login-screen").hidden = false;
}

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.hidden = true;

  try {
    const usuario = await iniciarSesion(email, password);
    await mostrarApp(usuario);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  }
});

function alternarFormulario(mostrarRegistro) {
  document.getElementById("login-form").hidden = mostrarRegistro;
  document.getElementById("registro-form").hidden = !mostrarRegistro;
}

document.getElementById("btn-ir-registro").addEventListener("click", () => alternarFormulario(true));
document.getElementById("btn-ir-login").addEventListener("click", () => alternarFormulario(false));

document.getElementById("registro-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const errorEl = document.getElementById("registro-error");
  errorEl.hidden = true;

  try {
    const usuario = await registrarAdmin({
      nombre: document.getElementById("reg-nombre").value.trim(),
      email: document.getElementById("reg-email").value.trim(),
      password: document.getElementById("reg-password").value,
      codigo: document.getElementById("reg-codigo").value,
    });
    await mostrarApp(usuario);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.hidden = false;
  }
});

iniciar();
