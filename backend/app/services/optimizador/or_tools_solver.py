from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# Trabajamos la capacidad/demanda en centésimas de kg (no en kg enteros)
# porque peso_kg en la base es NUMERIC(8,2) y OR-Tools exige enteros.
# Sin esta escala, truncar los decimales podría subestimar la demanda
# real y dejar sobrecargar un vehículo por error de redondeo.
ESCALA_PESO = 100


@dataclass
class ParadaOptimizar:
    id: int  # pedido_id
    ventana_inicio_seg: int
    ventana_fin_seg: int
    demanda_kg: float
    # Índices (posición en capacidades_vehiculos) de los vehículos que pueden
    # atender esta parada. None = cualquiera.
    vehiculos_permitidos: list[int] | None = None


@dataclass
class ResultadoRuta:
    vehiculo_index: int
    paradas_en_orden: list[int]  # pedido_id, en el orden asignado
    llegada_estimada_seg: list[int]


def resolver_vrptw(
    matriz_tiempos: list[list[float]],
    paradas: list[ParadaOptimizar],
    capacidades_vehiculos: list[float],
    horizonte_seg: int = 24 * 3600,
    tiempo_limite_busqueda_seg: int = 10,
) -> list[ResultadoRuta] | None:
    """
    matriz_tiempos: matriz NxN en segundos, índice 0 = depósito.
    paradas: N-1 paradas, en el mismo orden que las filas 1..N-1 de la matriz.
    capacidades_vehiculos: una entrada por vehículo disponible para esta corrida.

    Devuelve None solo si el solver no encuentra ninguna solución factible
    (caso raro dado que los pedidos individuales se pueden dejar sin asignar
    vía AddDisjunction — ver nota más abajo). Si hay pedidos que no entraron
    en ninguna ruta, van a estar ausentes de paradas_en_orden en todos los
    resultados; es responsabilidad de quien llama a esta función detectarlos
    comparando contra la lista completa de `paradas` de entrada.
    """
    num_nodos = len(matriz_tiempos)
    num_vehiculos = len(capacidades_vehiculos)

    manager = pywrapcp.RoutingIndexManager(num_nodos, num_vehiculos, 0)
    routing = pywrapcp.RoutingModel(manager)

    def tiempo_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(matriz_tiempos[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(tiempo_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    routing.AddDimension(
        transit_callback_index,
        horizonte_seg,  # slack máximo: cuánto puede esperar un vehículo
        horizonte_seg,  # tiempo máximo acumulado por vehículo
        False,
        "Tiempo",
    )
    dimension_tiempo = routing.GetDimensionOrDie("Tiempo")

    for i, parada in enumerate(paradas, start=1):
        index = manager.NodeToIndex(i)
        dimension_tiempo.CumulVar(index).SetRange(
            parada.ventana_inicio_seg, parada.ventana_fin_seg
        )

    def demanda_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        if from_node == 0:
            return 0
        return round(paradas[from_node - 1].demanda_kg * ESCALA_PESO)

    demand_callback_index = routing.RegisterUnaryTransitCallback(demanda_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [round(c * ESCALA_PESO) for c in capacidades_vehiculos],
        True,
        "Capacidad",
    )

    # Un pedido irresoluble (ventana imposible con la flota disponible) queda
    # sin asignar en vez de tirar abajo toda la optimización. La penalización
    # alta asegura que el solver solo lo descarte como último recurso.
    # Quien consuma el resultado tiene que revisar qué pedidos quedaron
    # fuera y mostrarlo en la interfaz — el solver no avisa por sí solo.
    penalizacion = 100_000
    for i in range(1, num_nodos):
        routing.AddDisjunction([manager.NodeToIndex(i)], penalizacion)

    # Pedidos preasignados a un operario: solo sus vehículos pueden visitarlos.
    for i, parada in enumerate(paradas, start=1):
        if parada.vehiculos_permitidos is None:
            continue
        if any(v < 0 or v >= num_vehiculos for v in parada.vehiculos_permitidos):
            raise ValueError(f"vehiculos_permitidos fuera de rango en la parada {parada.id}")
        # RemoveValue sobre la variable de vehículo del nodo: equivale a
        # SetAllowedVehiclesForIndex, pero esa función cambió de firma entre
        # versiones de OR-Tools y esta forma no depende de ella.
        variable_vehiculo = routing.VehicleVar(manager.NodeToIndex(i))
        for vehiculo in range(num_vehiculos):
            if vehiculo not in parada.vehiculos_permitidos:
                variable_vehiculo.RemoveValue(vehiculo)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(tiempo_limite_busqueda_seg)

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        return None

    resultados = []
    for vehiculo_id in range(num_vehiculos):
        index = routing.Start(vehiculo_id)
        orden_paradas = []
        llegadas = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:
                orden_paradas.append(paradas[node - 1].id)
                llegadas.append(solution.Value(dimension_tiempo.CumulVar(index)))
            index = solution.Value(routing.NextVar(index))

        if orden_paradas:
            resultados.append(
                ResultadoRuta(
                    vehiculo_index=vehiculo_id,
                    paradas_en_orden=orden_paradas,
                    llegada_estimada_seg=llegadas,
                )
            )

    return resultados
