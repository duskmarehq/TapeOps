import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../models/mi_ruta.dart';
import '../services/api_service.dart';

class IncidenciaScreen extends StatefulWidget {
  final ParadaDetalle parada;
  const IncidenciaScreen({super.key, required this.parada});

  @override
  State<IncidenciaScreen> createState() => _IncidenciaScreenState();
}

class _IncidenciaScreenState extends State<IncidenciaScreen> {
  String _tipo = 'retraso';
  final _descripcionCtrl = TextEditingController();
  bool _enviando = false;
  String? _error;

  static const _tipos = {
    'retraso': 'Retraso',
    'ruta_bloqueada': 'Ruta bloqueada',
    'entrega_fallida': 'Entrega fallida',
  };

  Future<void> _enviar() async {
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      await context.read<ApiService>().reportarIncidencia(
            stopId: widget.parada.stopId,
            tipo: _tipo,
            descripcion: _descripcionCtrl.text.trim().isEmpty ? null : _descripcionCtrl.text.trim(),
          );
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  void dispose() {
    _descripcionCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Reportar — Pedido #${widget.parada.pedidoId}')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Tipo de incidencia', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            RadioGroup<String>(
              groupValue: _tipo,
              onChanged: (v) => setState(() => _tipo = v!),
              child: Column(
                children: _tipos.entries
                    .map((e) => RadioListTile<String>(value: e.key, title: Text(e.value)))
                    .toList(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _descripcionCtrl,
              decoration: const InputDecoration(
                labelText: 'Descripción (opcional)',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            if (_tipo == 'entrega_fallida')
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Text(
                  'Esta entrega va a quedar marcada como fallida y no entra en la '
                  're-optimización. Reprogramarla a otra fecha todavía no está '
                  'soportado — hay que coordinarlo con el gestor.',
                  style: TextStyle(fontSize: 12, color: Colors.orangeAccent),
                ),
              ),
            if (_error != null) ...[
              Text(_error!, style: const TextStyle(color: Colors.redAccent)),
              const SizedBox(height: 12),
            ],
            FilledButton(
              onPressed: _enviando ? null : _enviar,
              child: _enviando
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Enviar reporte'),
            ),
          ],
        ),
      ),
    );
  }
}
