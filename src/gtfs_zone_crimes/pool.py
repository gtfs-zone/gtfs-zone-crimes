"""Run a function in a process of its own, killed when its resident memory
passes a cap, so one oversized feed fails alone instead of taking the host
down. An address-space rlimit would be simpler, but polars reserves far more
address space than it touches and aborts under one."""

from __future__ import annotations

import multiprocessing
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from multiprocessing.connection import Connection

POLL_SECONDS = 0.25
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


class WorkerError(Exception):
    """An item's failure, as "ExceptionType: message"."""


def guarded[T, R](fn: Callable[[T], R], item: T) -> R | WorkerError:
    """The result or a WorkerError. The error is formatted inside `except` and
    returned after it, so the failed call's frames, and the memory they hold,
    are gone before the result is sent back."""
    try:
        return fn(item)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return WorkerError(error)


def child[T, R](fn: Callable[[T], R], item: T, conn: Connection) -> None:
    conn.send(guarded(fn, item))
    conn.close()


def resident_bytes(pid: int) -> int:
    try:
        with open(f"/proc/{pid}/statm") as handle:
            return int(handle.read().split()[1]) * PAGE_SIZE
    except (OSError, IndexError, ValueError):
        return 0


def isolated[T, R](
    fn: Callable[[T], R], item: T, max_bytes: int | None
) -> tuple[R | WorkerError, int]:
    """`fn(item)` in a process of its own, killed past `max_bytes` resident,
    and the peak resident bytes seen. Without a cap it runs in this process."""
    if not max_bytes:
        return guarded(fn, item), 0
    context = multiprocessing.get_context("forkserver")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=child, args=(fn, item, send))
    process.start()
    send.close()
    peak = 0
    try:
        while True:
            if receive.poll(POLL_SECONDS):
                try:
                    return receive.recv(), peak
                except EOFError:
                    return WorkerError("BrokenProcessPool: worker died"), peak
            if not process.is_alive():
                return WorkerError("BrokenProcessPool: worker died"), peak
            peak = max(peak, resident_bytes(process.pid or 0))
            if peak > max_bytes:
                process.kill()
                return WorkerError(
                    f"MemoryError: over {max_bytes} bytes resident"
                ), peak
    finally:
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join()
        receive.close()
