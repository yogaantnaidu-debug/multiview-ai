"""Hype maths. Time is passed in by hand, so a "5 minute" test runs instantly."""
import pytest

from app.hype import RATE_FLOOR, WARMUP, WINDOW, StreamStats


def feed(stats, start, end, per_second):
    """Simulate chat: `per_second` messages in each second, baseline updated every second.

    Messages sit mid-interval (+0.5), not on whole seconds: a message exactly
    WINDOW seconds old is outside the window, so whole-second timestamps would
    always lose one message at the edge and read 0.9 instead of 1.0.
    """
    for sec in range(start, end):
        for k in range(per_second):
            stats.add_message(sec + (k + 0.5) / per_second)
        stats.update_baseline(sec + 1.0)


def test_rate_counts_only_the_last_window():
    s = StreamStats(0.0)
    for t in range(1, 6):
        s.add_message(float(t))
    assert s.rate(5.0) == pytest.approx(5 / WINDOW)
    # 20 s later every message is older than the window.
    assert s.rate(20.0) == 0.0


def test_no_baseline_and_zero_hype_until_window_is_full():
    s = StreamStats(0.0)
    feed(s, 0, 5, per_second=3)
    assert s.baseline is None
    assert s.hype(5.0) == 0.0


def test_steady_chat_scores_about_one():
    s = StreamStats(0.0)
    feed(s, 0, 300, per_second=1)
    assert s.baseline == pytest.approx(1.0, abs=0.05)
    assert s.hype(300.0) == pytest.approx(1.0, abs=0.1)


def test_spike_scores_above_two_while_baseline_moves_slowly():
    s = StreamStats(0.0)
    feed(s, 0, 300, per_second=1)
    feed(s, 300, 310, per_second=4)
    assert s.hype(310.0) > 2.0
    # The EMA absorbs a 10 s spike only a little; that's what makes it a "normal" level.
    assert s.baseline < 1.5


def test_floor_prevents_huge_scores_for_silent_chats():
    s = StreamStats(0.0)
    s.update_baseline(WINDOW)  # 10 s of silence: baseline = 0
    assert s.baseline == 0.0
    s.add_message(WINDOW + 1)
    # 0.1 msg/s divided by the floor (0.2), not by 0.
    assert s.hype(WINDOW + 1) == pytest.approx((1 / WINDOW) / RATE_FLOOR)


def test_warming_up_flag():
    s = StreamStats(100.0)
    assert s.warming_up(100.0 + WARMUP - 1)
    assert not s.warming_up(100.0 + WARMUP)
