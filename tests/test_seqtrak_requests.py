"""The Seqtrak request queue paces, tracks and retries Parameter Requests."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("seqtrak_requests", ROOT / "src" / "open_push" / "seqtrak" / "requests.py")
rq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rq)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(**kw):
    sent, logs, clock = [], [], Clock()
    q = rq.RequestQueue(send=sent.append, clock=clock, log=logs.append, **kw)
    return q, sent, logs, clock


def test_window_limits_requests_waiting_for_a_reply():
    q, sent, _, _ = make(window=3)
    for i in range(10):
        q.add([0x70, 0x40, i])
    q.pump()
    assert len(sent) == 3
    q.answered([0x70, 0x40, 0])
    q.pump()
    assert len(sent) == 4 and sent[-1] == [0x70, 0x40, 3]


def test_unanswered_request_is_retried_then_logged():
    q, sent, logs, clock = make(window=2, timeout=1.0, retries=2)
    q.add([0x30, 0x40, 0x76])
    q.pump()
    for _ in range(3):
        clock.t += 1.1
        q.pump()
    assert sent.count([0x30, 0x40, 0x76]) == 3       # first send + 2 retries
    assert q.failed == 1 and "30 40 76" in logs[0]
    assert q.idle()


def test_reply_stops_the_retry():
    q, sent, _, clock = make(timeout=1.0)
    q.add([0x30, 0x40, 0x76])
    q.pump()
    q.answered([0x30, 0x40, 0x76])
    clock.t += 5
    q.pump()
    assert sent == [[0x30, 0x40, 0x76]] and q.failed == 0


def test_duplicates_are_not_queued_twice():
    q, sent, _, _ = make()
    q.add([0x30, 0x40, 0x76])
    q.add([0x30, 0x40, 0x76])
    q.pump()
    q.add([0x30, 0x40, 0x76])    # still waiting for the reply
    q.pump()
    assert sent == [[0x30, 0x40, 0x76]]


def test_pause_and_clear():
    q, sent, _, clock = make()
    q.add([0x01, 0x10, 0x15])
    q.pause(1.0)
    q.pump()
    assert sent == []
    clock.t += 1.0
    q.pump()
    assert sent == [[0x01, 0x10, 0x15]]
    q.add([0x30, 0x40, 0x76])
    q.clear()
    q.pump()
    assert q.idle() and len(sent) == 1


def test_low_priority_feeder_waits_for_room():
    q, _, _, _ = make(window=1)
    assert q.has_room()
    q.add([0x30, 0x40, 0x76])
    assert not q.has_room()          # something queued: high-priority first
    q.pump()
    assert not q.has_room()          # window full
    q.answered([0x30, 0x40, 0x76])
    assert q.has_room()
