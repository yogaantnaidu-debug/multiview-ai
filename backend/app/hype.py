"""Hype score maths. Plain arithmetic, no AI, and no I/O so it's easy to test.

Every function takes `now` as an argument instead of reading the clock,
so tests can fake time ("pretend 30 seconds passed").
"""
import math
from collections import deque

WINDOW = 10.0         # seconds of chat that count as "right now"
BASELINE_TAU = 120.0  # EMA time constant: the baseline mostly reflects the last few minutes
RATE_FLOOR = 0.2      # msgs/s. Without it, a quiet chat (baseline ~0) gives absurd scores
WARMUP = 30.0         # seconds before a newly added stream may win focus


class StreamStats:
    def __init__(self, now):
        self.started = now
        self.last_update = now
        self.times = deque()  # message timestamps inside the window, oldest first
        self.baseline = None  # msgs/s that is "normal" for this stream

    def add_message(self, now):
        self.times.append(now)

    def rate(self, now):
        """Messages per second over the last WINDOW seconds."""
        # Timestamps arrive in order, so old ones are always at the left end.
        while self.times and self.times[0] <= now - WINDOW:
            self.times.popleft()
        return len(self.times) / WINDOW

    def update_baseline(self, now):
        """Move the baseline a little towards the current rate (EMA).

        alpha depends on the time since the last update, so the maths stays
        correct even if the tick loop runs late.
        """
        rate = self.rate(now)
        dt = now - self.last_update
        self.last_update = now
        if now - self.started < WINDOW:
            return  # the window isn't full yet, so `rate` underestimates
        if self.baseline is None:
            self.baseline = rate  # first real measurement: start from it, not from 0
        else:
            alpha = 1 - math.exp(-dt / BASELINE_TAU)
            self.baseline += alpha * (rate - self.baseline)

    def hype(self, now):
        """2.0 means chat is twice as busy as normal for this stream."""
        if self.baseline is None:
            return 0.0
        return self.rate(now) / max(self.baseline, RATE_FLOOR)

    def warming_up(self, now):
        return now - self.started < WARMUP
