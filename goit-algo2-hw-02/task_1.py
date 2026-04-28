from typing import Union

Number = Union[int, float]


def find_min_max(numbers: list[Number]) -> tuple[Number, Number]:
    """Find minimum and maximum values using divide and conquer."""
    if not numbers:
        raise ValueError("numbers must not be empty")

    def search(left: int, right: int) -> tuple[Number, Number]:
        if left == right:
            return numbers[left], numbers[left]

        if right - left == 1:
            first, second = numbers[left], numbers[right]
            return (first, second) if first <= second else (second, first)

        middle = (left + right) // 2
        left_min, left_max = search(left, middle)
        right_min, right_max = search(middle + 1, right)

        return min(left_min, right_min), max(left_max, right_max)

    return search(0, len(numbers) - 1)


if __name__ == "__main__":
    examples = [
        [8, 3, 12, 5, 1, 9, 4],
        [42],
        [-7, 2.5, 0, -3.1, 10],
    ]

    for values in examples:
        minimum, maximum = find_min_max(values)
        print(f"Масив: {values}")
        print(f"Мінімум: {minimum}, максимум: {maximum}\n")

    try:
        find_min_max([])
    except ValueError as error:
        print(f"Порожній масив: {error}")
