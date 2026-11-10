"""Integer simulated costs and wall-clock plus simulated-work time."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def iso(value):
    return value.astimezone(timezone.utc).isoformat()


class Clock:
    def now(self):
        return datetime.now(timezone.utc)

    def monotonic(self):
        return time.monotonic()


class FrozenClock(Clock):
    """Injected deterministic clock, never selected in real mode."""
    def __init__(self, start):
        self.current = datetime.fromisoformat(start).astimezone(timezone.utc)
        self.tick = 0.0

    def now(self):
        return self.current

    def monotonic(self):
        return self.tick

    def advance(self, seconds):
        self.current += timedelta(seconds=seconds)
        self.tick += seconds


def effective_now(snapshot, clock):
    return clock.now() + timedelta(seconds=snapshot["cumulative_sim_elapsed_s"])


class Rejection(Exception):
    def __init__(self, code, message, details=None):
        self.code, self.message, self.details = code, message, details or {}
        super().__init__(message)

