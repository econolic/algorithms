from collections import deque
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from config import DEFAULT_EDGES_PATH, SINK, SOURCE, STORES, TERMINALS, WAREHOUSES

REQUIRED_EDGE_COLUMNS = {"start", "end", "capacity"}
ALLOWED_NODES = set(TERMINALS + WAREHOUSES + STORES)


@dataclass(frozen=True)
class Edge:
    start: str
    end: str
    capacity: int


@dataclass(frozen=True)
class AugmentingPath:
    nodes: List[str]
    flow: int


@dataclass(frozen=True)
class MaxFlowResult:
    max_flow: int
    augmenting_paths: List[AugmentingPath]
    terminal_store_flows: Dict[tuple[str, str], int]


def load_edges(path: Path | str = DEFAULT_EDGES_PATH) -> List[Edge]:
    edges_path = Path(path)
    edges = []

    with edges_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        validate_csv_header(reader.fieldnames, edges_path)

        for row_number, row in enumerate(reader, start=2):
            edges.append(parse_edge_row(row, row_number, edges_path))

    validate_edges(edges)
    return edges


def validate_csv_header(fieldnames: Sequence[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise ValueError(f"CSV file is empty: {path}")

    missing_columns = REQUIRED_EDGE_COLUMNS - set(fieldnames)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV file {path} is missing required columns: {columns}")


def parse_edge_row(row: dict[str, str], row_number: int, path: Path) -> Edge:
    start = row["start"].strip()
    end = row["end"].strip()
    capacity_raw = row["capacity"].strip()

    try:
        capacity = int(capacity_raw)
    except ValueError as error:
        raise ValueError(
            f"CSV file {path}, row {row_number}: capacity must be an integer"
        ) from error

    edge = Edge(start=start, end=end, capacity=capacity)
    validate_edge(edge, row_number=row_number, path=path)
    return edge


def validate_edges(edges: List[Edge]) -> None:
    if not edges:
        raise ValueError("At least one logistics edge is required")

    for edge in edges:
        validate_edge(edge)


def validate_edge(
    edge: Edge, row_number: int | None = None, path: Path | None = None
) -> None:
    location = ""
    if path is not None and row_number is not None:
        location = f"CSV file {path}, row {row_number}: "

    if not edge.start or not edge.end:
        raise ValueError(f"{location}edge endpoints must not be empty")

    if edge.start not in ALLOWED_NODES:
        raise ValueError(f"{location}unknown start node: {edge.start}")

    if edge.end not in ALLOWED_NODES:
        raise ValueError(f"{location}unknown end node: {edge.end}")

    if edge.capacity < 0:
        raise ValueError(f"{location}capacity must not be negative")


def build_network(edges: List[Edge]) -> tuple[List[str], List[Edge]]:
    """Build the homework network with helper source and sink vertices."""
    validate_edges(edges)

    nodes = [SOURCE, *TERMINALS, *WAREHOUSES, *STORES, SINK]
    network_edges = list(edges)

    terminal_capacity = {terminal: 0 for terminal in TERMINALS}
    store_capacity = {store: 0 for store in STORES}

    for edge in edges:
        if edge.start in TERMINALS:
            terminal_capacity[edge.start] += edge.capacity
        if edge.end in STORES:
            store_capacity[edge.end] += edge.capacity

    for terminal, capacity in terminal_capacity.items():
        network_edges.append(Edge(SOURCE, terminal, capacity))
    for store, capacity in store_capacity.items():
        network_edges.append(Edge(store, SINK, capacity))

    return nodes, network_edges


def create_capacity_matrix(
    nodes: List[str], edges: List[Edge]
) -> tuple[List[List[int]], Dict[str, int]]:
    node_indexes = {node: index for index, node in enumerate(nodes)}
    capacity_matrix = [[0] * len(nodes) for _ in nodes]

    for edge in edges:
        start = node_indexes[edge.start]
        end = node_indexes[edge.end]
        capacity_matrix[start][end] += edge.capacity

    return capacity_matrix, node_indexes


def bfs(
    capacity_matrix: List[List[int]],
    flow_matrix: List[List[int]],
    source: int,
    sink: int,
) -> List[int] | None:
    parent = [-1] * len(capacity_matrix)
    parent[source] = source
    queue = deque([source])

    while queue:
        current = queue.popleft()

        for neighbor in range(len(capacity_matrix)):
            residual_capacity = (
                capacity_matrix[current][neighbor] - flow_matrix[current][neighbor]
            )
            if parent[neighbor] == -1 and residual_capacity > 0:
                parent[neighbor] = current
                if neighbor == sink:
                    return parent
                queue.append(neighbor)

    return None


def edmonds_karp(
    capacity_matrix: List[List[int]], source: int, sink: int, nodes: List[str]
) -> tuple[int, List[List[int]], List[AugmentingPath]]:
    flow_matrix = [[0] * len(capacity_matrix) for _ in capacity_matrix]
    max_flow = 0
    augmenting_paths = []

    while True:
        parent = bfs(capacity_matrix, flow_matrix, source, sink)
        if parent is None:
            break

        path_flow = max(max(row) for row in capacity_matrix)
        current = sink
        path_indexes = [sink]

        while current != source:
            previous = parent[current]
            residual_capacity = (
                capacity_matrix[previous][current] - flow_matrix[previous][current]
            )
            path_flow = min(path_flow, residual_capacity)
            current = previous
            path_indexes.append(current)

        current = sink
        while current != source:
            previous = parent[current]
            flow_matrix[previous][current] += path_flow
            flow_matrix[current][previous] -= path_flow
            current = previous

        max_flow += path_flow
        path_indexes.reverse()
        augmenting_paths.append(
            AugmentingPath(
                nodes=[nodes[index] for index in path_indexes],
                flow=int(path_flow),
            )
        )

    return int(max_flow), flow_matrix, augmenting_paths


def calculate_terminal_store_flows(
    augmenting_paths: List[AugmentingPath],
) -> Dict[tuple[str, str], int]:
    flows = {(terminal, store): 0 for terminal in TERMINALS for store in STORES}

    for path in augmenting_paths:
        terminal = next(node for node in path.nodes if node in TERMINALS)
        store = next(node for node in path.nodes if node in STORES)
        flows[(terminal, store)] += path.flow

    return flows


def solve_logistics_network(
    edges: List[Edge] | None = None,
    edges_path: Path | str = DEFAULT_EDGES_PATH,
) -> MaxFlowResult:
    logistics_edges = list(edges) if edges is not None else load_edges(edges_path)
    nodes, network_edges = build_network(logistics_edges)
    capacity_matrix, node_indexes = create_capacity_matrix(nodes, network_edges)
    max_flow, _, augmenting_paths = edmonds_karp(
        capacity_matrix,
        node_indexes[SOURCE],
        node_indexes[SINK],
        nodes,
    )
    terminal_store_flows = calculate_terminal_store_flows(augmenting_paths)

    return MaxFlowResult(
        max_flow=max_flow,
        augmenting_paths=augmenting_paths,
        terminal_store_flows=terminal_store_flows,
    )
