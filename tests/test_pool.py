import time

from gtfs_zone_crimes.pool import WorkerError, isolated


def hog(size: int) -> int:
    """Touch `size` bytes and hold them past the watchdog's next look."""
    block = bytearray(size)
    for i in range(0, size, 4096):
        block[i] = 1
    if size > 1_000_000:
        time.sleep(2)
    return len(block)


def fail(_: int) -> int:
    raise ValueError("nope")


def test_isolated_returns_the_result():
    result, peak = isolated(hog, 1000, 500_000_000)
    assert result == 1000
    assert peak >= 0


def test_isolated_kills_a_hog():
    result, _ = isolated(hog, 400_000_000, 150_000_000)
    assert isinstance(result, WorkerError)
    assert str(result).startswith("MemoryError")


def test_isolated_reports_exceptions():
    result, _ = isolated(fail, 0, 500_000_000)
    assert str(result) == "ValueError: nope"


def test_uncapped_runs_in_process():
    assert isolated(hog, 10, None) == (10, 0)
