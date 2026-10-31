"""Director rules: threshold, minimum hold (hysteresis) and manual lock."""
from app.director import MANUAL_LOCK, MIN_HOLD, THRESHOLD, Director


def make_director(focus="a", now=0.0):
    d = Director()
    d.sync(["a", "b"], focus, now)
    return d


def test_switches_when_all_conditions_pass():
    d = make_director()
    event = d.decide({"a": 1.0, "b": 3.0}, MIN_HOLD)
    assert event["type"] == "focus"
    assert event["channel"] == "b"
    assert "3.0x" in event["reason"]
    assert d.focus == "b"


def test_no_switch_before_minimum_hold():
    d = make_director()
    assert d.decide({"a": 1.0, "b": 9.0}, MIN_HOLD - 1) is None
    assert d.focus == "a"


def test_threshold_is_strictly_above_two():
    d = make_director()
    assert d.decide({"a": 1.0, "b": THRESHOLD}, 100.0) is None
    assert d.decide({"a": 1.0, "b": THRESHOLD + 0.01}, 100.0) is not None


def test_no_event_when_best_is_already_focused():
    d = make_director()
    assert d.decide({"a": 5.0, "b": 1.0}, 100.0) is None


def test_hold_restarts_after_a_switch_so_focus_does_not_ping_pong():
    d = make_director()
    d.decide({"a": 1.0, "b": 3.0}, 30.0)  # switch to b at t=30
    assert d.decide({"a": 9.0, "b": 1.0}, 30.0 + MIN_HOLD - 1) is None
    assert d.decide({"a": 9.0, "b": 1.0}, 30.0 + MIN_HOLD)["channel"] == "a"


def test_manual_pick_locks_the_director():
    d = make_director()
    d.manual("a", 50.0)
    assert d.lock_remaining(60.0) == MANUAL_LOCK - 10
    assert d.decide({"a": 1.0, "b": 9.0}, 50.0 + MANUAL_LOCK - 1) is None
    assert d.decide({"a": 1.0, "b": 9.0}, 50.0 + MANUAL_LOCK)["channel"] == "b"


def test_empty_scores_do_nothing():
    assert make_director().decide({}, 100.0) is None


def test_sync_falls_back_to_first_channel_when_focus_is_removed():
    d = make_director(focus="b")
    d.sync(["a", "c"], None, 10.0)
    assert d.focus == "a"
    assert d.focus_since == 10.0
