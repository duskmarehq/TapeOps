"""
Prueba manual del solver con datos sintéticos.
No requiere OSRM, Postgres, ni el servidor FastAPI corriendo.

Correr con: uv run python scripts/test_solver.py
"""

from app.services.optimizador.or_tools_solver import ParadaOptimizar, resolver_vrptw

# Matriz de tiempos sintética (segundos). 4 nodos: 0 = depósito, 1-3 = pedidos.
matriz_tiempos = [
    [0, 600, 900, 1200],
    [600, 0, 500, 800],
    [900, 500, 0, 400],
    [1200, 800, 400, 0],
]

paradas = [
    ParadaOptimizar(id=101, ventana_inicio_seg=0, ventana_fin_seg=3600, demanda_kg=100),
    ParadaOptimizar(id=102, ventana_inicio_seg=0, ventana_fin_seg=3600, demanda_kg=150),
    ParadaOptimizar(id=103, ventana_inicio_seg=0, ventana_fin_seg=3600, demanda_kg=200),
]

resultado = resolver_vrptw(
    matriz_tiempos=matriz_tiempos,
    paradas=paradas,
    capacidades_vehiculos=[500],
)

if resultado is None:
    print("No se encontró ninguna solución factible.")
else:
    ids_asignados = {pid for ruta in resultado for pid in ruta.paradas_en_orden}
    ids_esperados = {p.id for p in paradas}

    for ruta in resultado:
        print(f"Vehículo {ruta.vehiculo_index}: paradas en orden {ruta.paradas_en_orden}")
        print(f"  Llegada estimada (segundos desde medianoche): {ruta.llegada_estimada_seg}")

    faltantes = ids_esperados - ids_asignados
    if faltantes:
        print(f"ADVERTENCIA: pedidos sin asignar: {faltantes}")
