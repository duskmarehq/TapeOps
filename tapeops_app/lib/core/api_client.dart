import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

class ApiException implements Exception {
  final String mensaje;
  final int? statusCode;
  ApiException(this.mensaje, {this.statusCode});

  @override
  String toString() => mensaje;
}

class ApiClient {
  final _storage = const FlutterSecureStorage();
  static const _tokenKey = 'tapeops_token';

  Future<String?> obtenerToken() => _storage.read(key: _tokenKey);

  Future<void> guardarToken(String token) => _storage.write(key: _tokenKey, value: token);

  Future<void> borrarToken() => _storage.delete(key: _tokenKey);

  Future<Map<String, String>> _headers({bool conAuth = true}) async {
    final headers = {'Content-Type': 'application/json'};
    if (conAuth) {
      final token = await obtenerToken();
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<dynamic> get(String path) async {
    final res = await http.get(
      Uri.parse('${AppConfig.apiBaseUrl}$path'),
      headers: await _headers(),
    );
    return _procesarRespuesta(res);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body, {bool conAuth = true}) async {
    final res = await http.post(
      Uri.parse('${AppConfig.apiBaseUrl}$path'),
      headers: await _headers(conAuth: conAuth),
      body: jsonEncode(body),
    );
    return _procesarRespuesta(res);
  }

  dynamic _procesarRespuesta(http.Response res) {
    if (res.statusCode == 401) {
      borrarToken();
      throw ApiException('Sesión expirada — volvé a iniciar sesión', statusCode: 401);
    }

    if (res.statusCode < 200 || res.statusCode >= 300) {
      String detalle = res.reasonPhrase ?? 'Error de red';
      try {
        final data = jsonDecode(res.body);
        if (data is Map && data['detail'] != null) {
          detalle = data['detail'] is String ? data['detail'] as String : jsonEncode(data['detail']);
        }
      } catch (_) {
        // el cuerpo de la respuesta no era JSON — se conserva reasonPhrase
      }
      throw ApiException(detalle, statusCode: res.statusCode);
    }

    if (res.body.isEmpty) return null;
    return jsonDecode(res.body);
  }
}
