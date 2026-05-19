"""Compare range-sum query processing with and without an LRU cache."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterable

CACHE_CAPACITY = 1000
ARRAY_SIZE = 100_000
QUERY_COUNT = 50_000
RANDOM_SEED = 42


class Node:
    """Doubly linked list node used by LRUCache."""

    def __init__(self, key: tuple[int, int], value: int) -> None:
        """Initialize a cache node with a key-value pair."""
        self.data = (key, value)
        self.next: Node | None = None
        self.prev: Node | None = None


class DoublyLinkedList:
    """Minimal doubly linked list for tracking cache usage order."""

    def __init__(self) -> None:
        """Initialize an empty list."""
        self.head: Node | None = None
        self.tail: Node | None = None

    def push(self, key: tuple[int, int], value: int) -> Node:
        """Add a new node to the front of the list and return it."""
        new_node = Node(key, value)
        new_node.next = self.head

        if self.head:
            self.head.prev = new_node
        else:
            self.tail = new_node

        self.head = new_node
        return new_node

    def remove(self, node: Node) -> None:
        """Remove an existing node from the list."""
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next

        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev

        node.prev = None
        node.next = None

    def move_to_front(self, node: Node) -> None:
        """Move an existing node to the front of the usage list."""
        if node is self.head:
            return

        self.remove(node)
        node.next = self.head

        if self.head:
            self.head.prev = node
        else:
            self.tail = node

        self.head = node

    def remove_last(self) -> Node | None:
        """Remove and return the least recently used node."""
        if not self.tail:
            return None

        last = self.tail
        self.remove(last)
        return last


class LRUCache:
    """LRU cache with O(1) get and put operations."""

    def __init__(self, capacity: int) -> None:
        """Initialize an empty cache with a fixed capacity."""
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")

        self.capacity = capacity
        self.cache: dict[tuple[int, int], Node] = {}
        self.list = DoublyLinkedList()

    def get(self, key: tuple[int, int]) -> int:
        """Return a cached value or -1 when the key is absent."""
        node = self.cache.get(key)
        if node is None:
            return -1

        self.list.move_to_front(node)
        return node.data[1]

    def put(self, key: tuple[int, int], value: int) -> None:
        """Store a value and evict the least recently used item if needed."""
        node = self.cache.get(key)
        if node is not None:
            node.data = (key, value)
            self.list.move_to_front(node)
            return

        if len(self.cache) >= self.capacity:
            last = self.list.remove_last()
            if last is not None:
                del self.cache[last.data[0]]

        new_node = self.list.push(key, value)
        self.cache[key] = new_node

    def remove(self, key: tuple[int, int]) -> None:
        """Remove a key from the cache if it exists."""
        node = self.cache.pop(key, None)
        if node is not None:
            self.list.remove(node)

    def clear(self) -> None:
        """Remove all cached values."""
        self.cache.clear()
        self.list = DoublyLinkedList()


range_cache = LRUCache(CACHE_CAPACITY)


def range_sum_no_cache(array: list[int], left: int, right: int) -> int:
    """Return the sum of array elements in the inclusive range [left, right]."""
    return sum(array[left : right + 1])


def update_no_cache(array: list[int], index: int, value: int) -> None:
    """Update an array item without touching any cache."""
    array[index] = value


def range_sum_with_cache(array: list[int], left: int, right: int) -> int:
    """Return a range sum using an LRU cache for repeated queries."""
    key = (left, right)
    cached_sum = range_cache.get(key)
    if cached_sum != -1:
        return cached_sum

    calculated_sum = sum(array[left : right + 1])
    range_cache.put(key, calculated_sum)
    return calculated_sum


def update_with_cache(array: list[int], index: int, value: int) -> None:
    """Update an array item and invalidate cached ranges containing it."""
    array[index] = value

    keys_to_remove = [key for key in range_cache.cache if key[0] <= index <= key[1]]
    for key in keys_to_remove:
        range_cache.remove(key)


def make_queries(
    n: int,
    q: int,
    hot_pool: int = 30,
    p_hot: float = 0.95,
    p_update: float = 0.03,
) -> list[tuple[str, int, int]]:
    """Generate benchmark queries with mostly repeated hot ranges."""
    hot = [
        (random.randint(0, n // 2), random.randint(n // 2, n - 1))
        for _ in range(hot_pool)
    ]
    queries = []

    for _ in range(q):
        if random.random() < p_update:
            idx = random.randint(0, n - 1)
            val = random.randint(1, 100)
            queries.append(("Update", idx, val))
        else:
            if random.random() < p_hot:
                left, right = random.choice(hot)
            else:
                left = random.randint(0, n - 1)
                right = random.randint(left, n - 1)
            queries.append(("Range", left, right))

    return queries


def process_queries(
    array: list[int],
    queries: Iterable[tuple[str, int, int]],
    range_sum_func: Callable[[list[int], int, int], int],
    update_func: Callable[[list[int], int, int], None],
    clear_cache: bool = False,
) -> int:
    """Run all queries with selected handlers and return a range checksum."""
    checksum = 0

    if clear_cache:
        range_cache.clear()

    for operation, first, second in queries:
        if operation == "Range":
            checksum += range_sum_func(array, first, second)
        else:
            update_func(array, first, second)

    return checksum


def benchmark() -> dict[str, float | int]:
    """Benchmark query processing with and without LRU cache."""
    random.seed(RANDOM_SEED)
    source_array = [random.randint(1, 100) for _ in range(ARRAY_SIZE)]
    queries = make_queries(ARRAY_SIZE, QUERY_COUNT)

    no_cache_array = source_array.copy()
    cache_array = source_array.copy()

    no_cache_start = time.perf_counter()
    no_cache_checksum = process_queries(
        no_cache_array, queries, range_sum_no_cache, update_no_cache
    )
    no_cache_time = time.perf_counter() - no_cache_start

    cache_start = time.perf_counter()
    cache_checksum = process_queries(
        cache_array,
        queries,
        range_sum_with_cache,
        update_with_cache,
        clear_cache=True,
    )
    cache_time = time.perf_counter() - cache_start

    if no_cache_checksum != cache_checksum:
        raise RuntimeError("Checksums do not match")

    return {
        "no_cache_time": no_cache_time,
        "cache_time": cache_time,
        "speedup": no_cache_time / cache_time if cache_time else float("inf"),
        "checksum": no_cache_checksum,
    }


def print_benchmark_results(results: dict[str, float | int]) -> None:
    """Print benchmark results in the format required by the assignment."""
    print(f"Без кешу : {results['no_cache_time']:7.2f} c")
    print(
        f"LRU-кеш  : {results['cache_time']:7.2f} c  "
        f"(прискорення x{results['speedup']:.1f})"
    )
    print(f"Checksum : {results['checksum']}")


if __name__ == "__main__":
    benchmark_results = benchmark()
    print_benchmark_results(benchmark_results)
