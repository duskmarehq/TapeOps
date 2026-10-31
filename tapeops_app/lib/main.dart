import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'firebase_options.dart';
import 'screens/login_screen.dart';
import 'screens/ruta_screen.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase es opcional: si firebase_options.dart todavía tiene los
  // valores placeholder (no se corrió `flutterfire configure`), esto
  // falla acá y la app sigue funcionando igual — mismo criterio
  // best-effort que el backend y que rubik-web. Sin esto, solo se pierde
  // la actualización en tiempo real; el pull-to-refresh manual alcanza.
  try {
    await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  } catch (e) {
    debugPrint('Firebase no se pudo inicializar (¿falta flutterfire configure?): $e');
  }

  final apiClient = ApiClient();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService(apiClient)),
        Provider(create: (_) => ApiService(apiClient)),
      ],
      child: const TapeOpsApp(),
    ),
  );
}

class TapeOpsApp extends StatelessWidget {
  const TapeOpsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TapeOps',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFFE8A33D),
        brightness: Brightness.dark,
      ),
      home: Consumer<AuthService>(
        builder: (context, auth, _) {
          if (auth.cargando) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          return auth.usuarioActual == null ? const LoginScreen() : const RutaScreen();
        },
      ),
    );
  }
}
