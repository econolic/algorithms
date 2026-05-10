"""Check password uniqueness with a memory-efficient Bloom filter."""

import hashlib
from typing import Iterable

USED_STATUS = "вже використаний"
UNIQUE_STATUS = "унікальний"
INVALID_STATUS = "некоректний"


class BloomFilter:
    """Memory-efficient Bloom filter for string membership checks."""

    def __init__(self, size: int, num_hashes: int) -> None:
        """Initialize the filter with a fixed bit array and hash count.

        Args:
            size: Number of positions in the internal bit array.
            num_hashes: Number of independent hash positions per item.

        Raises:
            ValueError: If size or num_hashes is not positive.
        """
        if size <= 0:
            raise ValueError("size must be greater than 0")
        if num_hashes <= 0:
            raise ValueError("num_hashes must be greater than 0")

        self.size = size
        self.num_hashes = num_hashes
        self._bits = bytearray(size)

    def _hashes(self, item: str) -> Iterable[int]:
        """Generate deterministic bit-array indexes for a string item."""
        for seed in range(self.num_hashes):
            digest = hashlib.sha256(f"{seed}:{item}".encode("utf-8")).digest()
            yield int.from_bytes(digest, byteorder="big") % self.size

    @staticmethod
    def _validate_item(item: str) -> None:
        """Validate that an item can be stored in the Bloom filter."""
        if not isinstance(item, str):
            raise TypeError("item must be a string")
        if item == "":
            raise ValueError("item must not be empty")

    def add(self, item: str) -> None:
        """Add a non-empty string to the filter without storing the string."""
        self._validate_item(item)

        for index in self._hashes(item):
            self._bits[index] = 1

    def contains(self, item: str) -> bool:
        """Return True when the item may be present in the filter.

        Bloom filters can return false positives, so True means "possibly
        present". False means the item is definitely absent.
        """
        self._validate_item(item)

        return all(self._bits[index] for index in self._hashes(item))

    def __contains__(self, item: object) -> bool:
        """Support the `item in bloom_filter` syntax for valid strings."""
        if not isinstance(item, str) or item == "":
            return False

        return self.contains(item)


def _result_key(password: object) -> str:
    """Return a readable dictionary key for any checked password value."""
    return password if isinstance(password, str) else repr(password)


def check_password_uniqueness(
    bloom_filter: BloomFilter, passwords: Iterable[object]
) -> dict[str, str]:
    """Check whether each password is unique according to the Bloom filter.

    Args:
        bloom_filter: Pre-filled BloomFilter with previously used passwords.
        passwords: Values to check. Only non-empty strings are valid passwords.

    Returns:
        A mapping from each checked value to one of three Ukrainian statuses:
        already used, unique, or invalid.
    """
    results: dict[str, str] = {}

    for password in passwords:
        key = _result_key(password)

        if not isinstance(password, str) or password == "":
            results[key] = INVALID_STATUS
            continue

        results[password] = (
            USED_STATUS if bloom_filter.contains(password) else UNIQUE_STATUS
        )

    return results


if __name__ == "__main__":
    bloom = BloomFilter(size=1000, num_hashes=3)

    existing_passwords = ["password123", "admin123", "qwerty123"]
    for existing_password in existing_passwords:
        bloom.add(existing_password)

    new_passwords_to_check = ["password123", "newpassword", "admin123", "guest"]
    check_results = check_password_uniqueness(bloom, new_passwords_to_check)

    for password, status in check_results.items():
        print(f"Пароль '{password}' - {status}.")
