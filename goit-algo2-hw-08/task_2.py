"""Limit chat messages with a precise sliding-window rate limiter."""

from __future__ import annotations

import random
import time
from collections import deque


class SlidingWindowRateLimiter:
    """Rate limiter that stores message timestamps in a sliding window."""

    def __init__(self, window_size: int = 10, max_requests: int = 1) -> None:
        """Initialize limiter settings and per-user message history."""
        if window_size <= 0:
            raise ValueError("window_size must be greater than 0")
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")

        self.window_size = window_size
        self.max_requests = max_requests
        self.user_history: dict[str, deque[float]] = {}

    def _cleanup_window(self, user_id: str, current_time: float) -> None:
        """Remove timestamps that are outside the active sliding window."""
        history = self.user_history.get(user_id)
        if history is None:
            return

        window_start = current_time - self.window_size
        while history and history[0] <= window_start:
            history.popleft()

        if not history:
            del self.user_history[user_id]

    def can_send_message(self, user_id: str) -> bool:
        """Return True when the user can send a message right now."""
        current_time = time.time()
        self._cleanup_window(user_id, current_time)

        history = self.user_history.get(user_id)
        return history is None or len(history) < self.max_requests

    def record_message(self, user_id: str) -> bool:
        """Record a new message if the user is inside the allowed limit."""
        current_time = time.time()
        self._cleanup_window(user_id, current_time)

        history = self.user_history.get(user_id)
        if history is not None and len(history) >= self.max_requests:
            return False

        self.user_history.setdefault(user_id, deque()).append(current_time)
        return True

    def time_until_next_allowed(self, user_id: str) -> float:
        """Return seconds until the next message is allowed for a user."""
        current_time = time.time()
        self._cleanup_window(user_id, current_time)

        history = self.user_history.get(user_id)
        if history is None or len(history) < self.max_requests:
            return 0.0

        oldest_request = history[0]
        wait_time = self.window_size - (current_time - oldest_request)
        return max(0.0, wait_time)


def test_rate_limiter() -> None:
    """Demonstrate rate limiting for a small stream of chat messages."""
    limiter = SlidingWindowRateLimiter(window_size=10, max_requests=1)

    print("\n=== Симуляція потоку повідомлень ===")
    for message_id in range(1, 11):
        user_id = message_id % 5 + 1

        result = limiter.record_message(str(user_id))
        wait_time = limiter.time_until_next_allowed(str(user_id))

        print(
            f"Повідомлення {message_id:2d} | Користувач {user_id} | "
            f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}"
        )

        time.sleep(random.uniform(0.1, 1.0))

    print("\nОчікуємо 4 секунди...")
    time.sleep(4)

    print("\n=== Нова серія повідомлень після очікування ===")
    for message_id in range(11, 21):
        user_id = message_id % 5 + 1
        result = limiter.record_message(str(user_id))
        wait_time = limiter.time_until_next_allowed(str(user_id))

        print(
            f"Повідомлення {message_id:2d} | Користувач {user_id} | "
            f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}"
        )

        time.sleep(random.uniform(0.1, 1.0))


if __name__ == "__main__":
    test_rate_limiter()
