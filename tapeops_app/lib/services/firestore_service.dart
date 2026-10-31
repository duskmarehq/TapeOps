import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

/// Escucha el documento `rutas_activas/{rutaId}` en Firestore para
/// refrescar la pantalla del operario cuando el backend re-optimiza su
/// ruta por una incidencia — reportada desde este mismo dispositivo o
/// desde cualquier otro proceso.
///
/// Si Firebase no está configurado todavía (firebase_options.dart sigue
/// con los valores placeholder, sin reemplazar por `flutterfire
/// configure`), esto no debe tumbar la app: la pantalla de ruta sigue
/// funcionando con el pull-to-refresh manual, solo sin push en tiempo
/// real. Mismo criterio best-effort que el backend y que rubik-web.
class FirestoreService {
  StreamSubscription<DocumentSnapshot>? _suscripcion;

  bool get disponible {
    try {
      Firebase.app();
      return true;
    } catch (_) {
      return false;
    }
  }

  void escucharRuta(int rutaId, void Function() onCambio) {
    if (!disponible) return;

    var primeraInstantanea = true;

    _suscripcion = FirebaseFirestore.instanceFor(
      app: Firebase.app(),
      databaseId: 'default',
    ).collection('rutas_activas').doc(rutaId.toString()).snapshots().listen(
      (snapshot) {
        if (primeraInstantanea) {
          primeraInstantanea = false;
          return;
        }
        if (snapshot.exists) onCambio();
      },
      onError: (Object err) {
        debugPrint('Error del listener de Firestore: $err');
      },
    );
  }

  void detener() {
    _suscripcion?.cancel();
    _suscripcion = null;
  }
}
