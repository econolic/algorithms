from pathlib import Path

SOURCE = "Source"
SINK = "Sink"
TERMINALS = ["Термінал 1", "Термінал 2"]
WAREHOUSES = ["Склад 1", "Склад 2", "Склад 3", "Склад 4"]
STORES = [f"Магазин {number}" for number in range(1, 15)]
DEFAULT_EDGES_PATH = Path(__file__).parent / "data" / "logistics_edges.csv"
