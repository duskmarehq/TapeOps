/**
 * Listener en tiempo real sobre la colección `rutas_activas` de
 * Firestore, que el backend escribe (best-effort) cada vez que optimiza
 * o re-optimiza una ruta.
 *
 * La configuración de Firebase se importa dinámicamente, no de forma
 * estática: si `firebase-config.js` todavía no existe (porque no se
 * configuró un proyecto Firebase real), el panel completo no debe
 * romperse por un import fallido — simplemente queda sin actualizaciones
 * en vivo y hay que refrescar la página a mano, igual que el backend
 * sigue funcionando sin Firebase configurado.
 *
 * Devuelve una función para cancelar la suscripción (o un no-op si no
 * se pudo inicializar), que quien llama debe invocar si desmonta el panel.
 */
export async function iniciarListenerRutas(onCambio, onEstadoConexion) {
  let firebaseConfig;
  try {
    ({ firebaseConfig } = await import("./firebase-config.js"));
  } catch {
    onEstadoConexion(false, "Firebase sin configurar");
    return () => {};
  }

  let initializeApp, getFirestore, collection, onSnapshot;
  try {
    ({ initializeApp } = await import("https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js"));
    ({ getFirestore, collection, onSnapshot } = await import(
      "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js"
    ));
  } catch (err) {
    console.error("No se pudo cargar el SDK de Firebase:", err);
    onEstadoConexion(false, "Error al cargar Firebase");
    return () => {};
  }

  try {
    const app = initializeApp(firebaseConfig);
    const db = getFirestore(app, "default");
    const refColeccion = collection(db, "rutas_activas");

    return onSnapshot(
      refColeccion,
      { includeMetadataChanges: true },
      (snapshot) => {
        if (snapshot.metadata.fromCache) {
          onEstadoConexion(false, "Sin conexión al servidor");
        } else {
          onEstadoConexion(true, "En vivo");
        }
        snapshot.docChanges().forEach((cambio) => {
          if (cambio.type === "added" || cambio.type === "modified") {
            onCambio(cambio.doc.data());
          }
        });
      },
      (error) => {
        console.error("Error del listener de Firestore:", error);
        onEstadoConexion(false, "Desconectado");
      }
    );
  } catch (err) {
    console.error("No se pudo inicializar Firebase:", err);
    onEstadoConexion(false, "Error de configuración");
    return () => {};
  }
}
