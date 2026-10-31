// Usa el objeto global `L` cargado por el <script> de Leaflet en index.html
// (no se importa como módulo porque Leaflet no se distribuye como ES
// module en su build de CDN).

const COLORES_VEHICULO = ["#e8a33d", "#4fae7b", "#5eb1ef", "#c77dff", "#e2574c", "#8ecae6"];

function colorParaVehiculo(vehiculoId) {
  return COLORES_VEHICULO[vehiculoId % COLORES_VEHICULO.length];
}

const COLOR_ESTADO_PEDIDO = {
  pendiente: "#8b97a8",
  asignado: "#e8a33d",
  en_ruta: "#5eb1ef",
  entregado: "#4fae7b",
  fallido: "#e2574c",
};

export function crearMapa(contenedorId) {
  const mapa = L.map(contenedorId, { zoomControl: true }).setView([-25.3, -57.5], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; colaboradores de OpenStreetMap',
    maxZoom: 19,
  }).addTo(mapa);

  return mapa;
}

export function crearCapas() {
  return { deposito: null, pedidos: [], rutas: {}, seleccion: { handler: null, marcador: null } };
}

export function renderizarDeposito(mapa, capas, deposito) {
  if (capas.deposito) capas.deposito.remove();

  capas.deposito = L.marker([deposito.latitud, deposito.longitud], {
    icon: L.divIcon({ className: "marcador-deposito", html: "◆", iconSize: [20, 20] }),
  })
    .bindPopup(`<strong>${deposito.nombre}</strong><br>Depósito`)
    .addTo(mapa);

  mapa.setView([deposito.latitud, deposito.longitud], 12);
}

export function renderizarPedidos(mapa, capas, pedidos) {
  capas.pedidos.forEach((marcador) => marcador.remove());

  capas.pedidos = pedidos.map((pedido) => {
    const color = COLOR_ESTADO_PEDIDO[pedido.estado] || "#8b97a8";
    return L.circleMarker([pedido.latitud, pedido.longitud], {
      radius: 7,
      color,
      fillColor: color,
      fillOpacity: 0.85,
      weight: 2,
      // Sin esto, un clic sobre un pedido también cuenta como clic en el
      // mapa y movería el punto de selección al cargar un pedido nuevo.
      bubblingMouseEvents: false,
    })
      .bindPopup(
        `<strong>Pedido #${pedido.id}</strong><br>` +
          `Estado: ${pedido.estado}<br>` +
          `Peso: ${pedido.peso_kg} kg<br>` +
          `Ventana: ${pedido.ventana_inicio}–${pedido.ventana_fin}`
      )
      .addTo(mapa);
  });
}

/**
 * Dibuja una ruta como una polilínea depósito → paradas en orden.
 *
 * Limitación conocida: conecta las paradas con líneas rectas entre
 * coordenadas, no con la geometría real de las calles — el endpoint de
 * optimización solo persiste el ORDEN de las paradas, no el trazado
 * completo que devuelve OSRM. Alcanza para ver qué vehículo visita qué
 * secuencia de pedidos, no para leer el recorrido exacto sobre el mapa.
 *
 * `paradasConCoordenadas` debe ser el resultado de cruzar `ruta.paradas`
 * (que solo trae pedido_id) contra la lista de pedidos ya cargada — ver
 * `fusionarParadasConPedidos` en rutas.js.
 */
export function renderizarRuta(mapa, capas, rutaId, vehiculoId, deposito, paradasConCoordenadas, geometria = null) {
  if (capas.rutas[rutaId]) {
    capas.rutas[rutaId].forEach((capa) => capa.remove());
  }

  const color = colorParaVehiculo(vehiculoId);
  const puntos = [[deposito.latitud, deposito.longitud]];
  paradasConCoordenadas.forEach((p) => puntos.push([p.latitud, p.longitud]));

  let linea;
  if (geometria && geometria.coordinates && geometria.coordinates.length > 0) {
    // Recorrido real por calles. GeoJSON trae [longitud, latitud] y Leaflet
    // espera [latitud, longitud], por eso se invierte cada par.
    const trazado = geometria.coordinates.map(([lon, lat]) => [lat, lon]);
    linea = L.polyline(trazado, {
      color,
      weight: 4,
      opacity: 0.9,
      bubblingMouseEvents: false,
    }).addTo(mapa);
  } else {
    // Respaldo cuando todavía no hay trazado (o OSRM no respondió): línea
    // recta entre paradas, punteada para que se note que es aproximada.
    linea = L.polyline(puntos, {
      color,
      weight: 3,
      opacity: 0.85,
      dashArray: "6 4",
      bubblingMouseEvents: false,
    }).addTo(mapa);
  }

  const marcadoresOrden = paradasConCoordenadas.map((p) =>
    L.marker([p.latitud, p.longitud], {
      icon: L.divIcon({
        className: "marcador-orden",
        html: `<span style="background:${color};opacity:${p.estado === "completado" ? 0.45 : 1}">${p.orden}</span>`,
        iconSize: [20, 20],
      }),
    })
      .bindPopup(`<strong>Parada ${p.orden}</strong><br>Pedido #${p.pedido_id}<br>ETA: ${p.hora_estimada_llegada ?? "—"}`)
      .addTo(mapa)
  );

  capas.rutas[rutaId] = [linea, ...marcadoresOrden];
}

/**
 * Modo "elegir punto": cada clic en el mapa mueve un marcador de selección
 * y llama a `onSeleccion(lat, lng)`. Se desactiva al cambiar de sección.
 */
export function activarSeleccionPunto(mapa, capas, onSeleccion) {
  desactivarSeleccionPunto(mapa, capas);
  mapa.getContainer().classList.add("modo-seleccion");

  const handler = (ev) => {
    if (capas.seleccion.marcador) {
      capas.seleccion.marcador.setLatLng(ev.latlng);
    } else {
      capas.seleccion.marcador = L.marker(ev.latlng, {
        icon: L.divIcon({ className: "marcador-seleccion", html: "◎", iconSize: [26, 26] }),
        interactive: false,
      }).addTo(mapa);
    }
    onSeleccion(ev.latlng.lat, ev.latlng.lng);
  };

  mapa.on("click", handler);
  capas.seleccion.handler = handler;
}

export function desactivarSeleccionPunto(mapa, capas) {
  if (capas.seleccion.handler) mapa.off("click", capas.seleccion.handler);
  if (capas.seleccion.marcador) capas.seleccion.marcador.remove();
  capas.seleccion.handler = null;
  capas.seleccion.marcador = null;
  mapa.getContainer().classList.remove("modo-seleccion");
}
