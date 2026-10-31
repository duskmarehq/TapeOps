// PLACEHOLDER — reemplazar corriendo:
//   flutterfire configure
// Esto genera este mismo archivo con los valores reales de tu proyecto
// Firebase. Mientras no se reemplace, Firebase.initializeApp() falla en
// tiempo de ejecución con estos valores falsos — el try/catch de
// main.dart lo captura y la app sigue funcionando sin actualizaciones en
// tiempo real (ver firestore_service.dart).
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return web;
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions no están configuradas para esta plataforma — '
          'correr `flutterfire configure` para generar las reales.',
        );
    }
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyBNjWL8uuZswtECCTesvvoIIsVlyUvFb1o',
    appId: '1:12726871170:web:f6f08dce65f8801cd9809b',
    messagingSenderId: '12726871170',
    projectId: 'tapeops-6b4bd',
    authDomain: 'tapeops-6b4bd.firebaseapp.com',
    storageBucket: 'tapeops-6b4bd.firebasestorage.app',
    measurementId: 'G-WKSYKS9MD0',
  );

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyDqFBAaauSFLWDFdvX0S2BQ29uQybe12ak',
    appId: '1:12726871170:android:c5612d917f919b2ed9809b',
    messagingSenderId: '12726871170',
    projectId: 'tapeops-6b4bd',
    storageBucket: 'tapeops-6b4bd.firebasestorage.app',
  );
  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'PLACEHOLDER',
    appId: 'PLACEHOLDER',
    messagingSenderId: 'PLACEHOLDER',
    projectId: 'PLACEHOLDER',
  );
}
