from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PrintJob:
    id: str
    volume: float
    priority: int
    print_time: int


@dataclass
class PrinterConstraints:
    max_volume: float
    max_items: int


def optimize_printing(print_jobs: List[Dict], constraints: Dict) -> Dict:
    """
    Оптимізує чергу 3D-друку згідно з пріоритетами та обмеженнями принтера

    Args:
        print_jobs: Список завдань на друк
        constraints: Обмеження принтера

    Returns:
        Dict з порядком друку та загальним часом
    """
    printer_constraints = PrinterConstraints(**constraints)
    jobs = [PrintJob(**job) for job in print_jobs]

    if printer_constraints.max_volume <= 0:
        raise ValueError("max_volume must be greater than 0")
    if printer_constraints.max_items <= 0:
        raise ValueError("max_items must be greater than 0")

    for job in jobs:
        if job.volume <= 0:
            raise ValueError(f"Job {job.id} has invalid volume")
        if job.print_time <= 0:
            raise ValueError(f"Job {job.id} has invalid print_time")
        if job.priority not in (1, 2, 3):
            raise ValueError(f"Job {job.id} has invalid priority")
        if job.volume > printer_constraints.max_volume:
            raise ValueError(f"Job {job.id} exceeds max printer volume")

    sorted_jobs = sorted(jobs, key=lambda job: job.priority)
    print_order = []
    total_time = 0
    current_group = []
    current_volume = 0.0

    def complete_current_group() -> None:
        nonlocal total_time, current_group, current_volume
        if not current_group:
            return

        print_order.extend(job.id for job in current_group)
        total_time += max(job.print_time for job in current_group)
        current_group = []
        current_volume = 0.0

    for job in sorted_jobs:
        has_item_capacity = len(current_group) < printer_constraints.max_items
        has_volume_capacity = (
            current_volume + job.volume <= printer_constraints.max_volume
        )

        if current_group and (not has_item_capacity or not has_volume_capacity):
            complete_current_group()

        current_group.append(job)
        current_volume += job.volume

    complete_current_group()

    return {
        "print_order": print_order,
        "total_time": total_time,
    }


def test_printing_optimization() -> None:
    # Тест 1: Моделі однакового пріоритету
    test1_jobs = [
        {"id": "M1", "volume": 100, "priority": 1, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 1, "print_time": 150},
    ]

    # Тест 2: Моделі різних пріоритетів
    test2_jobs = [
        {"id": "M1", "volume": 100, "priority": 2, "print_time": 120},
        {"id": "M2", "volume": 150, "priority": 1, "print_time": 90},
        {"id": "M3", "volume": 120, "priority": 3, "print_time": 150},
    ]

    # Тест 3: Перевищення обмежень об'єму групи
    test3_jobs = [
        {"id": "M1", "volume": 250, "priority": 1, "print_time": 180},
        {"id": "M2", "volume": 200, "priority": 1, "print_time": 150},
        {"id": "M3", "volume": 180, "priority": 2, "print_time": 120},
    ]

    constraints = {
        "max_volume": 300,
        "max_items": 2,
    }

    print("Тест 1 (однаковий пріоритет):")
    result1 = optimize_printing(test1_jobs, constraints)
    print(f"Порядок друку: {result1['print_order']}")
    print(f"Загальний час: {result1['total_time']} хвилин")

    print("\nТест 2 (різні пріоритети):")
    result2 = optimize_printing(test2_jobs, constraints)
    print(f"Порядок друку: {result2['print_order']}")
    print(f"Загальний час: {result2['total_time']} хвилин")

    print("\nТест 3 (перевищення обмежень):")
    result3 = optimize_printing(test3_jobs, constraints)
    print(f"Порядок друку: {result3['print_order']}")
    print(f"Загальний час: {result3['total_time']} хвилин")


if __name__ == "__main__":
    test_printing_optimization()
