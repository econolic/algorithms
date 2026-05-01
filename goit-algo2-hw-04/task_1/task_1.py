from config import STORES, TERMINALS
from max_flow import solve_logistics_network


def print_terminal_store_table(flows: dict[tuple[str, str], int]) -> None:
    print("Термінал | Магазин | Фактичний Потік (одиниць)")
    for terminal in TERMINALS:
        for store in STORES:
            print(f"{terminal} | {store} | {flows[(terminal, store)]}")


def main() -> None:
    result = solve_logistics_network()

    print(f"Максимальний потік: {result.max_flow}")
    print("\nЗбільшуючі шляхи:")
    for index, path in enumerate(result.augmenting_paths, start=1):
        print(f"{index}. {' -> '.join(path.nodes)}: {path.flow}")

    print("\nПотоки між терміналами та магазинами:")
    print_terminal_store_table(result.terminal_store_flows)

    total_store_flow = sum(result.terminal_store_flows.values())
    print(f"\nСума потоків у таблиці: {total_store_flow}")


if __name__ == "__main__":
    main()
