class Usuario {
  final int id;
  final String email;
  final String nombre;
  final String rol;

  Usuario({required this.id, required this.email, required this.nombre, required this.rol});

  factory Usuario.fromJson(Map<String, dynamic> json) => Usuario(
        id: json['id'] as int,
        email: json['email'] as String,
        nombre: json['nombre'] as String,
        rol: json['rol'] as String,
      );
}
