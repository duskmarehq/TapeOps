class ParadaDetalle {
  final int stopId;
  final int pedidoId;
  final int orden;
  final double latitud;
  final double longitud;
  final double pesoKg;
  final String ventanaInicio;
  final String ventanaFin;
  final String? horaEstimadaLlegada;
  final String estado;

  ParadaDetalle({
    required this.stopId,
    required this.pedidoId,
    required this.orden,
    required this.latitud,
    required this.longitud,
    required this.pesoKg,
    required this.ventanaInicio,
    required this.ventanaFin,
    required this.horaEstimadaLlegada,
    required this.estado,
  });

  factory ParadaDetalle.fromJson(Map<String, dynamic> json) => ParadaDetalle(
        stopId: json['stop_id'] as int,
        pedidoId: json['pedido_id'] as int,
        orden: json['orden'] as int,
        latitud: (json['latitud'] as num).toDouble(),
        longitud: (json['longitud'] as num).toDouble(),
        pesoKg: (json['peso_kg'] as num).toDouble(),
        ventanaInicio: json['ventana_inicio'] as String,
        ventanaFin: json['ventana_fin'] as String,
        horaEstimadaLlegada: json['hora_estimada_llegada'] as String?,
        estado: json['estado'] as String,
      );
}

class MiRuta {
  final int rutaId;
  final int vehiculoId;
  final String fecha;
  final String estado;
  final List<ParadaDetalle> paradas;

  MiRuta({
    required this.rutaId,
    required this.vehiculoId,
    required this.fecha,
    required this.estado,
    required this.paradas,
  });

  factory MiRuta.fromJson(Map<String, dynamic> json) => MiRuta(
        rutaId: json['ruta_id'] as int,
        vehiculoId: json['vehiculo_id'] as int,
        fecha: json['fecha'] as String,
        estado: json['estado'] as String,
        paradas: (json['paradas'] as List)
            .map((p) => ParadaDetalle.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}
