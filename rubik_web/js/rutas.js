import { api } from "./api.js";
import {
  activarSeleccionPunto,
  desactivarSeleccionPunto,
  renderizarDeposito,
  renderizarPedidos,
  renderizarRuta,
} from "./mapa.js";

function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

function chipEstado(estado) {
  return `<span class="estado-chip estado-chip--${estado}">${estado}</span>`;
}

// ---------- Carga inicial ----------

export async function cargarDatosIniciales(estado) {
  const [depositos, pedidos, vehiculos, clientes, operarios] = await Promise.all([
    api.get("/depositos"),
    api.get("/pedidos"),
    api.get("/vehiculos"),
    api.get("/clientes"),
    api.get("/usuarios?rol=operario"),
  ]);

  estado.deposito = depositos[0] ?? null;
  estado.pedidos = pedidos;
  estado.vehiculos = vehiculos;
  estado.clientes = clientes;
  estado.operarios = operarios;

  if (estado.deposito) {
    renderizarDeposito(estado.mapa, estado.capas, estado.deposito);
  }
  renderizarPedidos(estado.mapa, estado.capas, estado.pedidos);
}

async function recargarPedidos(estado) {
  estado.pedidos = await api.get("/pedidos");
  renderizarPedidos(estado.mapa, estado.capas, estado.pedidos);
}

// ---------- Fusión de paradas con coordenadas de pedidos ----------
// El endpoint de rutas solo persiste pedido_id + orden; las coordenadas
// para dibujar en el mapa salen de la lista de pedidos ya cargada.
function fusionarParadasConPedidos(paradas, pedidos) {
  const pedidosPorId = new Map(pedidos.map((p) => [p.id, p]));
  return paradas
    .map((parada) => {
      const pedido = pedidosPorId.get(parada.pedido_id);
      if (!pedido) return null;
      return { ...parada, latitud: pedido.latitud, longitud: pedido.longitud };
    })
    .filter(Boolean);
}

// ---------- Trazado de rutas ----------
// Dibuja la ruta de inmediato con líneas rectas (para no dejar el mapa
// vacío) y la reemplaza por el recorrido real por calles apenas el backend
// lo devuelve. Si OSRM no responde, queda la línea recta.
async function trazarRuta(estado, rutaId, vehiculoId, paradas) {
  renderizarRuta(estado.mapa, estado.capas, rutaId, vehiculoId, estado.deposito, paradas);
  try {
    const trazado = await api.get(`/rutas/${rutaId}/trazado`);
    renderizarRuta(estado.mapa, estado.capas, rutaId, vehiculoId, estado.deposito, paradas, trazado.geometria);
  } catch (err) {
    console.warn(`No se pudo obtener el trazado de la ruta #${rutaId}:`, err.message);
  }
}

// ---------- Secciones del panel lateral ----------

export function mostrarSeccion(seccion, estado) {
  // Cada sección arranca sin el modo "elegir punto"; el panel de pedidos
  // lo vuelve a activar si corresponde.
  desactivarSeleccionPunto(estado.mapa, estado.capas);
  const contenedor = document.getElementById("panel-contenido");
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.seccion === seccion);
  });

  const render = {
    pedidos: renderPanelPedidos,
    vehiculos: renderPanelVehiculos,
    clientes: renderPanelClientes,
    depositos: renderPanelDepositos,
  }[seccion];

  if (render) render(contenedor, estado);
}

function nombreOperario(estado, id) {
  const operario = estado.operarios.find((o) => o.id === id);
  return operario ? operario.nombre : `#${id}`;
}

function renderPanelPedidos(contenedor, estado) {
  contenedor.innerHTML = `
    <h2>Pedidos (${estado.pedidos.length})</h2>
    <div id="lista-pedidos"></div>
    <form class="form-rapido" id="form-pedido">
      <label>Cliente
        <select name="cliente_id" required>
          ${estado.clientes.map((c) => `<option value="${c.id}">${escaparHtml(c.razon_social)}</option>`).join("")}
        </select>
      </label>
      <label>Operario destino
        <select name="operario_id">
          <option value="">Sin preasignar (cualquiera)</option>
          ${estado.operarios
            .map((o) => `<option value="${o.id}">${escaparHtml(o.nombre)} — ${escaparHtml(o.email)}</option>`)
            .join("")}
        </select>
      </label>
      <p class="pista-mapa">Hacé clic en el mapa para marcar el punto de entrega.</p>
      <div class="coords-lectura">
        <label>Latitud<input type="number" step="0.000001" name="latitud" readonly></label>
        <label>Longitud<input type="number" step="0.000001" name="longitud" readonly></label>
      </div>
      <label>Peso (kg)<input type="number" step="0.01" name="peso_kg" required></label>
      <label>Ventana inicio<input type="time" name="ventana_inicio" required></label>
      <label>Ventana fin<input type="time" name="ventana_fin" required></label>
      <button type="submit">Cargar pedido</button>
    </form>
  `;

  const lista = contenedor.querySelector("#lista-pedidos");
  lista.innerHTML = estado.pedidos
    .map((p) => {
      const operario = p.operario_id
        ? `<br><span class="etiqueta">Operario:</span> ${escaparHtml(nombreOperario(estado, p.operario_id))}`
        : "";
      // Solo un pedido pendiente puede borrarse: los demás ya tienen un
      // stop con el historial de la entrega.
      const eliminar =
        p.estado === "pendiente"
          ? `<button class="btn-eliminar" type="button" data-id="${p.id}">Eliminar</button>`
          : "";
      return `
      <div class="lista-item lista-item--fila">
        <div>
          <span class="dato">#${p.id}</span> — ${p.peso_kg} kg — ${chipEstado(p.estado)}<br>
          <span class="etiqueta">Ventana:</span> <span class="dato">${p.ventana_inicio}–${p.ventana_fin}</span>${operario}
        </div>
        ${eliminar}
      </div>`;
    })
    .join("");

  lista.querySelectorAll(".btn-eliminar").forEach((boton) => {
    boton.addEventListener("click", async () => {
      const id = Number(boton.dataset.id);
      if (!confirm(`¿Eliminar el pedido #${id}? No se puede deshacer.`)) return;
      try {
        await api.delete(`/pedidos/${id}`);
        await recargarPedidos(estado);
        mostrarSeccion("pedidos", estado);
      } catch (err) {
        alert(`No se pudo eliminar el pedido: ${err.message}`);
      }
    });
  });

  const form = contenedor.querySelector("#form-pedido");
  const inputLat = form.querySelector('input[name="latitud"]');
  const inputLng = form.querySelector('input[name="longitud"]');
  activarSeleccionPunto(estado.mapa, estado.capas, (lat, lng) => {
    inputLat.value = lat.toFixed(6);
    inputLng.value = lng.toFixed(6);
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const datos = Object.fromEntries(new FormData(ev.target));
    // Los campos de solo lectura no pasan por la validación del navegador.
    if (!datos.latitud || !datos.longitud) {
      alert("Marcá el punto de entrega haciendo clic en el mapa.");
      return;
    }
    try {
      await api.post("/pedidos", {
        cliente_id: Number(datos.cliente_id),
        operario_id: datos.operario_id ? Number(datos.operario_id) : null,
        latitud: Number(datos.latitud),
        longitud: Number(datos.longitud),
        peso_kg: Number(datos.peso_kg),
        ventana_inicio: `${datos.ventana_inicio}:00`,
        ventana_fin: `${datos.ventana_fin}:00`,
      });
      await recargarPedidos(estado);
      mostrarSeccion("pedidos", estado);
    } catch (err) {
      alert(`No se pudo cargar el pedido: ${err.message}`);
    }
  });
}

function renderPanelVehiculos(contenedor, estado) {
  contenedor.innerHTML = `
    <h2>Vehículos (${estado.vehiculos.length})</h2>
    <div id="lista-vehiculos"></div>
    <form class="form-rapido" id="form-vehiculo">
      <label>Patente<input type="text" name="patente" required></label>
      <label>Capacidad (kg)<input type="number" step="0.01" name="capacidad_kg" required></label>
      <label>Depósito
        <select name="deposito_id" required>
          ${estado.deposito ? `<option value="${estado.deposito.id}">${escaparHtml(estado.deposito.nombre)}</option>` : ""}
        </select>
      </label>
      <button type="submit">Agregar vehículo</button>
    </form>
  `;

  const lista = contenedor.querySelector("#lista-vehiculos");
  lista.innerHTML = estado.vehiculos
    .map(
      (v) => `
      <div class="lista-item">
        <span class="dato">${escaparHtml(v.patente)}</span> — ${v.capacidad_kg} kg
        ${v.activo ? "" : ' <span class="etiqueta">(inactivo)</span>'}
      </div>`
    )
    .join("");

  contenedor.querySelector("#form-vehiculo").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const datos = Object.fromEntries(new FormData(ev.target));
    try {
      await api.post("/vehiculos", {
        patente: datos.patente,
        capacidad_kg: Number(datos.capacidad_kg),
        deposito_id: Number(datos.deposito_id),
      });
      estado.vehiculos = await api.get("/vehiculos");
      mostrarSeccion("vehiculos", estado);
    } catch (err) {
      alert(`No se pudo agregar el vehículo: ${err.message}`);
    }
  });
}

function renderPanelClientes(contenedor, estado) {
  contenedor.innerHTML = `
    <h2>Clientes (${estado.clientes.length})</h2>
    <div id="lista-clientes"></div>
    <form class="form-rapido" id="form-cliente">
      <label>Razón social<input type="text" name="razon_social" required></label>
      <label>Dirección<input type="text" name="direccion"></label>
      <label>Latitud<input type="number" step="0.000001" name="latitud" required></label>
      <label>Longitud<input type="number" step="0.000001" name="longitud" required></label>
      <button type="submit">Agregar cliente</button>
    </form>
  `;

  const lista = contenedor.querySelector("#lista-clientes");
  lista.innerHTML = estado.clientes
    .map(
      (c) => `
      <div class="lista-item">
        ${escaparHtml(c.razon_social)}<br>
        <span class="etiqueta">${escaparHtml(c.direccion ?? "sin dirección")}</span>
      </div>`
    )
    .join("");

  contenedor.querySelector("#form-cliente").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const datos = Object.fromEntries(new FormData(ev.target));
    try {
      await api.post("/clientes", {
        razon_social: datos.razon_social,
        direccion: datos.direccion || null,
        latitud: Number(datos.latitud),
        longitud: Number(datos.longitud),
      });
      estado.clientes = await api.get("/clientes");
      mostrarSeccion("clientes", estado);
    } catch (err) {
      alert(`No se pudo agregar el cliente: ${err.message}`);
    }
  });
}

function renderPanelDepositos(contenedor, estado) {
  contenedor.innerHTML = `
    <h2>Depósito</h2>
    <div id="lista-depositos"></div>
    <p class="etiqueta" style="padding: 0 8px; font-size: 0.78rem;">
      El MVP asume un único depósito por negocio. El endpoint de
      optimización toma siempre el primero que encuentra en esta lista.
    </p>
  `;

  const lista = contenedor.querySelector("#lista-depositos");
  lista.innerHTML = estado.deposito
    ? `<div class="lista-item">${escaparHtml(estado.deposito.nombre)}<br>
       <span class="etiqueta">${escaparHtml(estado.deposito.direccion ?? "")}</span></div>`
    : `<div class="lista-item etiqueta">Sin depósito cargado todavía.</div>`;
}

// ---------- Modal de optimización ----------

export function configurarModalOptimizar(estado) {
  const modal = document.getElementById("modal-optimizar");
  const contenedorAsignaciones = document.getElementById("opt-asignaciones");
  const btnAgregar = document.getElementById("btn-agregar-asignacion");
  const btnCancelar = document.getElementById("btn-cancelar-optimizar");
  const btnConfirmar = document.getElementById("btn-confirmar-optimizar");
  const errorEl = document.getElementById("optimizar-error");

  function opcionesVehiculos() {
    return estado.vehiculos.map((v) => `<option value="${v.id}">${escaparHtml(v.patente)}</option>`).join("");
  }

  function opcionesOperarios() {
    return estado.operarios.map((o) => `<option value="${o.id}">${escaparHtml(o.email)}</option>`).join("");
  }

  function agregarFilaAsignacion() {
    const fila = document.createElement("div");
    fila.className = "fila-asignacion";
    fila.innerHTML = `
      <label>Vehículo<select class="sel-vehiculo">${opcionesVehiculos()}</select></label>
      <label>Operario<select class="sel-operario">${opcionesOperarios()}</select></label>
      <button type="button" class="btn-quitar" title="Quitar">×</button>
    `;
    fila.querySelector(".btn-quitar").addEventListener("click", () => fila.remove());
    contenedorAsignaciones.appendChild(fila);
  }

  document.getElementById("btn-optimizar").addEventListener("click", async () => {
    errorEl.hidden = true;
    contenedorAsignaciones.innerHTML = "";

    if (estado.vehiculos.length === 0 || estado.operarios.length === 0) {
      alert("Hace falta al menos un vehículo y un operario cargados antes de optimizar.");
      return;
    }

    agregarFilaAsignacion();
    document.getElementById("opt-fecha").value = new Date().toISOString().slice(0, 10);
    modal.hidden = false;
  });

  btnAgregar.addEventListener("click", agregarFilaAsignacion);
  btnCancelar.addEventListener("click", () => { modal.hidden = true; });

  btnConfirmar.addEventListener("click", async () => {
    const fecha = document.getElementById("opt-fecha").value;
    const filas = [...contenedorAsignaciones.querySelectorAll(".fila-asignacion")];

    if (!fecha || filas.length === 0) {
      errorEl.textContent = "Completá la fecha y al menos una asignación.";
      errorEl.hidden = false;
      return;
    }

    const asignaciones = filas.map((fila) => ({
      vehiculo_id: Number(fila.querySelector(".sel-vehiculo").value),
      operario_id: Number(fila.querySelector(".sel-operario").value),
    }));

    btnConfirmar.disabled = true;
    try {
      const resultado = await api.post("/rutas/optimizar", { fecha, asignaciones });
      modal.hidden = true;
      await recargarPedidos(estado);

      // El panel lateral conserva la lista vieja hasta que se vuelve a dibujar:
      // sin esto, los pedidos recién asignados siguen mostrando "Eliminar".
      const activa = document.querySelector(".nav-item.is-active");
      if (activa && activa.dataset.seccion === "pedidos") mostrarSeccion("pedidos", estado);

      resultado.rutas.forEach((ruta) => {
        const paradas = fusionarParadasConPedidos(ruta.paradas, estado.pedidos);
        trazarRuta(estado, ruta.ruta_id, ruta.vehiculo_id, paradas);
      });

      if (resultado.pedidos_no_asignados.length > 0) {
        alert(
          `Optimización completa. Pedidos sin asignar (ventana imposible, capacidad insuficiente o su operario no participa de esta corrida): ` +
            resultado.pedidos_no_asignados.join(", ")
        );
      }
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    } finally {
      btnConfirmar.disabled = false;
    }
  });
}

// ---------- Notificaciones en tiempo real ----------

export async function manejarNotificacionRuta(payload, estado) {
  if (!payload.ruta_id) return;

  try {
    const [ruta] = await Promise.all([api.get(`/rutas/${payload.ruta_id}`), recargarPedidos(estado)]);

    const paradas = fusionarParadasConPedidos(ruta.paradas, estado.pedidos);
    trazarRuta(estado, ruta.id, ruta.vehiculo_id, paradas);

    const titulo =
      payload.evento === "entrega_confirmada"
        ? `Entrega confirmada: pedido #${payload.pedido_id}`
        : `Ruta #${ruta.id} re-optimizada`;
    mostrarNotificacion(titulo, `ruta #${ruta.id} · vehículo #${ruta.vehiculo_id}`);

    // Si el panel de pedidos está abierto, se vuelve a dibujar para que
    // el chip de estado cambie sin tener que salir y volver a entrar.
    const activa = document.querySelector(".nav-item.is-active");
    if (activa && activa.dataset.seccion === "pedidos") mostrarSeccion("pedidos", estado);
  } catch (err) {
    console.error("No se pudo aplicar la actualización en vivo:", err);
  }
}

function mostrarNotificacion(titulo, detalle) {
  const contenedor = document.getElementById("notificaciones");
  const el = document.createElement("div");
  el.className = "notificacion";
  el.innerHTML = `<div class="titulo">${escaparHtml(titulo)}</div><div class="detalle">${escaparHtml(detalle)}</div>`;
  contenedor.appendChild(el);
  setTimeout(() => el.remove(), 8000);
}
