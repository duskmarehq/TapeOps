import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/usuario.dart';

class AuthService extends ChangeNotifier {
  final ApiClient _client;
  Usuario? usuarioActual;
  bool cargando = true;

  AuthService(this._client) {
    _restaurarSesion();
  }

  Future<void> _restaurarSesion() async {
    final token = await _client.obtenerToken();
    if (token != null) {
      try {
        final data = await _client.get('/auth/me');
        usuarioActual = Usuario.fromJson(data as Map<String, dynamic>);
      } catch (_) {
        await _client.borrarToken();
      }
    }
    cargando = false;
    notifyListeners();
  }

  /// Crea una cuenta de operario (el rol lo fija el servidor) y abre
  /// sesión con ella.
  Future<void> registrarOperario(String nombre, String email, String password) async {
    await _client.post(
      '/auth/signup/operario',
      {'nombre': nombre, 'email': email, 'password': password},
      conAuth: false,
    );
    await iniciarSesion(email, password);
  }

  Future<void> iniciarSesion(String email, String password) async {
    final data = await _client.post(
      '/auth/login',
      {'email': email, 'password': password},
      conAuth: false,
    );
    await _client.guardarToken(data['access_token'] as String);

    final usuarioData = await _client.get('/auth/me');
    final usuario = Usuario.fromJson(usuarioData as Map<String, dynamic>);

    if (usuario.rol != 'operario') {
      await _client.borrarToken();
      throw ApiException('Esta cuenta no tiene rol de operario');
    }

    usuarioActual = usuario;
    notifyListeners();
  }

  Future<void> cerrarSesion() async {
    await _client.borrarToken();
    usuarioActual = null;
    notifyListeners();
  }
}
