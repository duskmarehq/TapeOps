import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../models/mi_ruta.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/firestore_service.dart';
import 'incidencia_screen.dart';

class RutaScreen extends StatefulWidget {
  const RutaScreen({super.key});

  @override
  State<RutaScreen> createState() => _RutaScreenState();
}

class _RutaScreenState extends State<RutaScreen> {
  final _firestoreService = FirestoreService();
  MiRuta? _ruta;
  bool _cargando = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  @override
  void dispose() {
    _firestoreService.detener();
    super.dispose();
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final ruta = await context.read<ApiService>().obtenerMiRuta();
      if (!mounted) return;
      setState(() {
        _ruta = ruta;
        _cargando = false;
      });

      _firestoreService.detener();
      if (ruta != null) {
        _firestoreService.escucharRuta(ruta.rutaId, () {
          // El payload de Firestore no trae el detalle de cada parada —
          // solo avisa que algo cambió. Se recarga desde la API en vez
          // de intentar reconstruir el estado a partir de ese payload.
          _cargar();
        });
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.mensaje;
        _cargando = false;
      });
    }
  }

  Future<void> _confirmarEntrega(ParadaDetalle parada) async {
    final confirmar = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar entrega'),
        content: Text(
          '¿Confirmás que el pedido #${parada.pedidoId} fue entregado? '
          'No se puede deshacer desde la app.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
    if (confirmar != true || !mounted) return;

    try {
      await context.read<ApiService>().confirmarEntrega(parada.stopId);
      if (!mounted) return;
      await _cargar();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi ruta'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthService>().cerrarSesion(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: _construirCuerpo(),
      ),
    );
  }

  Widget _construirCuerpo() {
    if (_cargando) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return ListView(
        children: [
          const SizedBox(height: 80),
          Icon(Icons.error_outline, size: 48, color: Theme.of(context).colorScheme.error),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(_error!, textAlign: TextAlign.center),
          ),
        ],
      );
    }

    if (_ruta == null || _ruta!.paradas.isEmpty) {
      return ListView(
        children: const [
          SizedBox(height: 80),
          Icon(Icons.local_shipping_outlined, size: 48),
          SizedBox(height: 12),
          Text('No tenés ninguna ruta activa asignada', textAlign: TextAlign.center),
        ],
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: _ruta!.paradas.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        final parada = _ruta!.paradas[i];
        return _ParadaCard(
          parada: parada,
          onConfirmar: () => _confirmarEntrega(parada),
          onReportar: () async {
            final reportado = await Navigator.of(context).push<bool>(
              MaterialPageRoute(builder: (_) => IncidenciaScreen(parada: parada)),
            );
            if (reportado == true) _cargar();
          },
        );
      },
    );
  }
}

class _ParadaCard extends StatelessWidget {
  final ParadaDetalle parada;
  final VoidCallback onReportar;
  final VoidCallback onConfirmar;

  const _ParadaCard({
    required this.parada,
    required this.onReportar,
    required this.onConfirmar,
  });

  Color _colorEstado(BuildContext context) {
    switch (parada.estado) {
      case 'completado':
        return Colors.green;
      case 'fallido':
        return Colors.redAccent;
      default:
        return Theme.of(context).colorScheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final esAccionable = parada.estado == 'pendiente';

    return Card(
      child: Column(
        children: [
          ListTile(
            leading: CircleAvatar(
              backgroundColor: _colorEstado(context),
              child: Text('${parada.orden}'),
            ),
            title: Text('Pedido #${parada.pedidoId} — ${parada.pesoKg} kg'),
            subtitle: Text(
              'Ventana ${parada.ventanaInicio}–${parada.ventanaFin}'
              '${parada.horaEstimadaLlegada != null ? "\nETA ${parada.horaEstimadaLlegada}" : ""}',
            ),
            isThreeLine: parada.horaEstimadaLlegada != null,
            trailing: esAccionable
                ? null
                : Icon(
                    parada.estado == 'fallido' ? Icons.cancel : Icons.check_circle,
                    color: _colorEstado(context),
                  ),
          ),
          if (esAccionable)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(onPressed: onReportar, child: const Text('Reportar incidencia')),
                  const SizedBox(width: 8),
                  FilledButton(onPressed: onConfirmar, child: const Text('Confirmar entrega')),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
