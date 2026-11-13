"""The coordinator's lazy FIFO worker, tested only with fake toast callbacks."""
from __future__ import annotations

import threading

from execution_launch.toast_queue import ToastQueue


def _join(queue):
    worker = queue._thread
    if worker is not None:
        worker.join(5)
        assert not worker.is_alive(), "toast worker did not become idle"


def test_put_returns_while_a_toast_is_showing_and_order_is_kept():
    entered, release, shown = threading.Event(), threading.Event(), []

    def show(title, body):
        shown.append((title, body))
        if len(shown) == 1:
            entered.set()
            release.wait(5)
        return True

    queue = ToastQueue(show)
    try:
        queue.put("t1", "b1")
        assert entered.wait(5), "first toast did not start"
        worker = queue._thread
        queue.put("t2", "b2")
        assert queue._thread is worker and worker.daemon
        assert shown == [("t1", "b1")]
    finally:
        release.set()
        _join(queue)
    assert shown == [("t1", "b1"), ("t2", "b2")]


def test_a_failing_toast_is_dropped_and_the_next_one_still_shows():
    shown, attempted, gate = [], [], threading.Event()

    def show(title, body):
        gate.wait(5)
        attempted.append(title)
        if title == "bad":
            raise RuntimeError("fake toast failure")
        if title == "false":
            return False
        shown.append(title)
        return True

    queue = ToastQueue(show)
    try:
        queue.put("bad", "x")
        queue.put("false", "z")
        queue.put("good", "y")
    finally:
        gate.set()
        _join(queue)
    assert attempted == ["bad", "false", "good"] and shown == ["good"]
    assert queue._thread is None


def test_construction_starts_no_thread_and_the_worker_ends_when_idle():
    before, shown = threading.active_count(), []
    queue = ToastQueue(lambda title, body: shown.append(title) or True)
    assert threading.active_count() == before and queue._thread is None
    queue.put("a", "b")
    _join(queue)
    assert queue._thread is None and shown == ["a"]
    queue.put("c", "d")
    _join(queue)
    assert queue._thread is None and shown == ["a", "c"]


def test_worker_start_failure_does_not_leave_the_queue_permanently_stuck():
    shown = []
    queue = ToastQueue(lambda title, body: shown.append(title) or True)
    start = threading.Thread.start

    def unavailable(worker):
        raise RuntimeError("fake thread capacity failure")

    try:
        threading.Thread.start = unavailable
        try:
            queue.put("first", "a")
        except RuntimeError as exc:
            assert str(exc) == "fake thread capacity failure"
        else:
            raise AssertionError("thread start unexpectedly succeeded")
    finally:
        threading.Thread.start = start
    assert queue._thread is None and shown == []
    queue.put("next", "b")
    _join(queue)
    assert queue._thread is None and shown == ["first", "next"]
