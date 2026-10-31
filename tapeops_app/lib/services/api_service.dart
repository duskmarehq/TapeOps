import '../core/api_client.dart';
import '../models/mi_ruta.dart';

class ApiService {
  final ApiClient _client;
  ApiService(this._client);

  /// Devuelve null si el operario no tiene ninguna ruta activa (404 del
  /// backend), en vez de propagar la excepción — es un estado normal
  /// (todavía no le asignaron nada hoy), no un error.
  Future<MiRuta?> obtenerMiRuta() async {
    try {
      final data = await _client.get('/mi-ruta');
      return MiRuta.fromJson(data as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<void> confirmarEntrega(int stopId) async {
    await _client.post('/entregas/$stopId/confirmar', {});
  }

  Future<void> reportarIncidencia({
    required int stopId,
    required String tipo,
    String? descripcion,
  }) async {
    await _client.post('/incidencias', {
      'stop_id': stopId,
      'tipo': tipo,
      'descripcion': descripcion,
    });
  }
}
