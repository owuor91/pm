from __future__ import annotations

import time

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60

_state: dict[str, dict[str, float]] = {}


def is_locked_out(key: str, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    entry = _state.get(key)
    if not entry or not entry.get("locked_until"):
        return False
    if now >= entry["locked_until"]:
        _state.pop(key, None)
        return False
    return True


def record_failure(key: str, now: float | None = None) -> None:
    now = now if now is not None else time.time()
    entry = _state.setdefault(key, {"count": 0, "locked_until": 0})
    entry["count"] += 1
    if entry["count"] >= MAX_FAILED_ATTEMPTS:
        entry["locked_until"] = now + LOCKOUT_SECONDS


def reset(key: str) -> None:
    _state.pop(key, None)
