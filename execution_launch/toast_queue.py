"""One lazy background worker for coordinator notifications (universe spec section 15).

The synchronous toast callback can take up to sixty seconds. Putting a message
does not wait for it. Construction starts no thread; the worker stops when idle.
Deduplication and authoritative event status remain with the caller.
"""
from __future__ import annotations

from collections import deque
import threading
from typing import Callable


class ToastQueue:
    """FIFO toasts shown by one daemon worker without holding the queue lock."""

    def __init__(self, show: Callable[[str, str], bool]) -> None:
        self._show, self._queue, self._lock, self._thread = show, deque(), threading.Lock(), None

    def put(self, title: str, body: str) -> None:
        with self._lock:
            self._queue.append((title, body))
            if self._thread is None:
                self._thread = threading.Thread(target=self._drain, name="coordinator-toasts", daemon=True)
                try:
                    self._thread.start()
                except Exception:
                    self._thread = None
                    raise

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._thread = None
                    return
                title, body = self._queue.popleft()
            try:
                self._show(title, body)
            except Exception:
                pass  # A failed notification does not discard the following ones.
