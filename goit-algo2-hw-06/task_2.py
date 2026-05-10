"""Compare exact unique IP counting with a HyperLogLog approximation."""

import hashlib
import ipaddress
import json
import math
import time
from pathlib import Path
from typing import Iterable

LOG_FILE = Path(__file__).parent / "logs" / "lms-stage-access.log"


def iter_valid_ips(log_path: Path) -> Iterable[str]:
    """Yield valid IP addresses from JSON log lines.

    Invalid JSON rows, missing `remote_addr` fields, and malformed IP values
    are skipped so the caller can process large log files without interruption.
    """
    with log_path.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            try:
                log_record = json.loads(line)
            except json.JSONDecodeError:
                continue

            ip = log_record.get("remote_addr")
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                continue

            yield ip


def count_unique_exact(log_path: Path) -> int:
    """Count unique valid IP addresses exactly using a set."""
    return len(set(iter_valid_ips(log_path)))


class HyperLogLog:
    """Small standalone HyperLogLog implementation based on 64-bit hashes."""

    def __init__(self, precision: int = 14) -> None:
        """Initialize registers for a chosen HyperLogLog precision.

        Args:
            precision: Number of hash bits used as the register index. The
                register count is `2 ** precision`.

        Raises:
            ValueError: If precision is outside the supported range.
        """
        if not 4 <= precision <= 16:
            raise ValueError("precision must be between 4 and 16")

        self.precision = precision
        self.register_count = 1 << precision
        self.registers = [0] * self.register_count

    @staticmethod
    def _hash(value: str) -> int:
        """Return a deterministic 64-bit integer hash for a string value."""
        digest = hashlib.sha256(value.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big")

    @staticmethod
    def _alpha(register_count: int) -> float:
        """Return the bias-correction constant for a register count."""
        if register_count == 16:
            return 0.673
        if register_count == 32:
            return 0.697
        if register_count == 64:
            return 0.709

        return 0.7213 / (1 + 1.079 / register_count)

    @staticmethod
    def _rank(value: int, bit_count: int) -> int:
        """Return the position of the first significant bit in suffix bits."""
        if value == 0:
            return bit_count + 1

        return bit_count - value.bit_length() + 1

    def add(self, value: str) -> None:
        """Add one value to the HyperLogLog registers."""
        hash_value = self._hash(value)
        index = hash_value >> (64 - self.precision)
        suffix_bits = 64 - self.precision
        suffix = hash_value & ((1 << suffix_bits) - 1)
        rank = self._rank(suffix, suffix_bits)

        self.registers[index] = max(self.registers[index], rank)

    def count(self) -> float:
        """Estimate the number of unique values added to the structure."""
        indicator = sum(2.0**-register for register in self.registers)
        estimate = self._alpha(self.register_count) * self.register_count**2 / indicator

        empty_registers = self.registers.count(0)
        if estimate <= 2.5 * self.register_count and empty_registers:
            return self.register_count * math.log(self.register_count / empty_registers)

        return estimate


def count_unique_hll(log_path: Path, precision: int = 14) -> float:
    """Estimate unique valid IP addresses with HyperLogLog."""
    hll = HyperLogLog(precision=precision)

    for ip in iter_valid_ips(log_path):
        hll.add(ip)

    return hll.count()


def compare_methods(log_path: Path) -> dict[str, dict[str, float]]:
    """Run both counting methods and return their counts and timings."""
    exact_start = time.perf_counter()
    exact_count = count_unique_exact(log_path)
    exact_time = time.perf_counter() - exact_start

    hll_start = time.perf_counter()
    hll_count = count_unique_hll(log_path)
    hll_time = time.perf_counter() - hll_start

    return {
        "Точний підрахунок": {
            "Унікальні елементи": float(exact_count),
            "Час виконання (сек.)": exact_time,
        },
        "HyperLogLog": {
            "Унікальні елементи": hll_count,
            "Час виконання (сек.)": hll_time,
        },
    }


def print_comparison_table(results: dict[str, dict[str, float]]) -> None:
    """Print comparison results in the table format required by the task."""
    exact = results["Точний підрахунок"]
    hll = results["HyperLogLog"]

    print("Результати порівняння:")
    print(f"{'':<24}{'Точний підрахунок':>20}{'HyperLogLog':>15}")
    print(
        f"{'Унікальні елементи':<24}"
        f"{exact['Унікальні елементи']:>20.1f}"
        f"{hll['Унікальні елементи']:>15.1f}"
    )
    print(
        f"{'Час виконання (сек.)':<24}"
        f"{exact['Час виконання (сек.)']:>20.6f}"
        f"{hll['Час виконання (сек.)']:>15.6f}"
    )


if __name__ == "__main__":
    comparison_results = compare_methods(LOG_FILE)
    print_comparison_table(comparison_results)
