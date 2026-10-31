import 'package:flutter/foundation.dart' show kIsWeb;

class AppConfig {
  // Según dónde corra la app:
  //  - Chrome / web: el navegador corre en tu máquina, así que "localhost"
  //    llega directo al backend.
  //  - Emulador Android: "localhost" NO llega a la máquina host; hay que
  //    usar la IP especial 10.0.2.2.
  //  - Dispositivo físico: ni localhost ni 10.0.2.2 sirven — hay que
  //    poner la IP real de tu máquina en la red local (ej. 192.168.x.x).
  //  - iOS Simulator: "localhost" funciona directo.
  static const String apiBaseUrl =
      kIsWeb ? 'http://localhost:8000/api/v1' : 'http://10.0.2.2:8000/api/v1';
}
