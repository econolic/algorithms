from collections import defaultdict
from dataclasses import dataclass
import logging
from typing import Callable

from trie import Trie

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


TEST_WORDS = ["apple", "application", "banana", "cat"]
SUFFIX_CHECKS = {
    "e": 1,
    "ion": 1,
    "a": 1,
    "at": 1,
    "z": 0,
    "A": 0,
}
PREFIX_CHECKS = {
    "app": True,
    "bat": False,
    "ban": True,
    "ca": True,
    "App": False,
}
INVALID_INPUTS = (None, 42, ["app"])


def log_section(title: str) -> None:
    logger.info("\n%s\n%s", title, "-" * len(title))


@dataclass(frozen=True)
class InvalidInputCheck:
    label: str
    action: Callable[[object], object]

    def run(self, value) -> None:
        try:
            self.action(value)
        except TypeError:
            logger.info(
                "%s: %r, результат: TypeError для некоректного параметра",
                self.label,
                value,
            )
        else:
            raise AssertionError(f"{self.action.__name__} must reject non-strings")


class Homework(Trie):
    def __init__(self):
        super().__init__()
        self._words = set()
        self._suffix_counts = defaultdict(int)

    def put(self, key, value=None):
        if not isinstance(key, str) or not key:
            return super().put(key, value)

        is_new_word = key not in self._words
        super().put(key, value)

        if is_new_word:
            self._words.add(key)
            self._add_suffixes(key)

    def delete(self, key):
        if not isinstance(key, str) or not key:
            return super().delete(key)

        is_deleted = super().delete(key)

        if is_deleted:
            self._words.remove(key)
            self._remove_suffixes(key)

        return is_deleted

    def count_words_with_suffix(self, pattern) -> int:
        if not isinstance(pattern, str):
            raise TypeError(
                f"Illegal argument for count_words_with_suffix: pattern = {pattern} must be a string"
            )

        return self._suffix_counts.get(pattern, 0)

    def has_prefix(self, prefix) -> bool:
        if not isinstance(prefix, str):
            raise TypeError(
                f"Illegal argument for has_prefix: prefix = {prefix} must be a string"
            )

        current = self.root
        for char in prefix:
            if char not in current.children:
                return False
            current = current.children[char]

        return current.is_terminal or bool(current.children)

    def _add_suffixes(self, word):
        for index in range(len(word) + 1):
            self._suffix_counts[word[index:]] += 1

    def _remove_suffixes(self, word):
        for index in range(len(word) + 1):
            suffix = word[index:]
            self._suffix_counts[suffix] -= 1
            if self._suffix_counts[suffix] == 0:
                del self._suffix_counts[suffix]


def test_homework_trie() -> bool:
    trie = Homework()

    log_section("Етап 1. Додавання слів")
    logger.info("Перевіряємі слова: %s", ", ".join(TEST_WORDS))
    for i, word in enumerate(TEST_WORDS):
        trie.put(word, i)
        logger.info("Додано слово: %s, значення: %s", word, i)

    log_section("Етап 2. Перевірка суфіксів")
    for suffix, expected in SUFFIX_CHECKS.items():
        result = trie.count_words_with_suffix(suffix)
        logger.info("Суфікс: %r, результат: %s", suffix, result)
        assert result == expected

    log_section("Етап 3. Перевірка префіксів")
    for prefix, expected in PREFIX_CHECKS.items():
        result = trie.has_prefix(prefix)
        logger.info("Префікс: %r, результат: %s", prefix, result)
        assert result is expected

    log_section("Етап 4. Перевірка некоректних параметрів")
    invalid_input_checks = [
        InvalidInputCheck("Суфікс", trie.count_words_with_suffix),
        InvalidInputCheck("Префікс", trie.has_prefix),
    ]
    for invalid_value in INVALID_INPUTS:
        for check in invalid_input_checks:
            check.run(invalid_value)

    return True


if __name__ == "__main__":
    if test_homework_trie():
        logger.info("Усі тести пройдено успішно.")
