"""Bridge regressions found in the 2026-10-15 review, checked against fake Push and Seqtrak ports."""
import sys
import pathlib
import time

import pytest

mido = pytest.importorskip("mido")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from open_push.seqtrak import app as A  # noqa: E402

HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]


class Port:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


@pytest.fixture
def bridge():
    b = A.SeqtrakBridge()
    b.push_out, b.seqtrak = Port(), Port()
    b.protocol = A.SeqtrakProtocol(b.seqtrak)
    b.requests.send = b.protocol.request_parameter
    b.protocol.request_parameter = b.requests.add
    b._set_mode('note')
    return b


def requests_sent(b):
    return [list(m.data[5:8]) for m in b.seqtrak.sent if m.type == 'sysex' and m.data[1] == 0x30]


def notes(b, kind):
    return [(m.channel + 1, m.note) for m in b.seqtrak.sent if m.type == kind]


def test_blocking_note_list_read_sends_its_requests(bridge):
    """The Delete menu's note-list read must reach the wire through the request queue."""
    class SeqtrakIn:
        def iter_pending(self):
            for m in list(bridge.seqtrak.sent):
                if m.type == 'sysex' and m.data[1] == 0x30 and list(m.data[5:7]) == [0x75, 0x30]:
                    bridge.seqtrak.sent.remove(m)
                    index = m.data[7]
                    data = [0, 0, 0, 60, 100, 0, 0, 120] if index < 2 else []
                    yield mido.Message('sysex', data=HEADER + [0x75, 0x30, index] + data)
    bridge.seqtrak_in = SeqtrakIn()
    assert bridge._read_note_list_blocking(11, timeout=0.5) == 2


def test_sampler_list_completes_when_replies_arrive_out_of_order(bridge):
    bridge._request_sampler_notes()
    note = [0, 0, 0, 60, 100, 0, 0, 120]
    bridge._handle_sampler_note_reply(1, [])       # end of list arrives first...
    assert not bridge._sampler_read_done
    bridge._handle_sampler_note_reply(0, note)     # ...then the (resent) first note
    assert bridge._sampler_read_done and len(bridge.sampler_notes) == 1


def test_project_switch_cancels_a_duplicate_in_progress(bridge):
    bridge._seqtrak_project, bridge._project_known = 1, True
    bridge._timed_sends = [(time.time() + 1, lambda: None)]
    bridge.handle_seqtrak_sysex(HEADER + [0x01, 0x10, 0x15, 0x04])
    assert bridge._timed_sends == []


def test_held_note_is_released_on_the_track_it_started_on(bridge):
    bridge.keyboard_track = 8                      # SYNTH 1
    bridge._update_pad_mode()
    pad = 36 + 3
    bridge.handle_pad(pad, 100)
    started = notes(bridge, 'note_on')[-1]
    bridge.keyboard_track = 9                      # change track while holding
    bridge._update_pad_mode()
    bridge.handle_pad(pad, 0)
    assert notes(bridge, 'note_off')[-1] == started


def test_release_reaches_the_seqtrak_after_song_view_opens(bridge):
    bridge.keyboard_track = 8
    bridge._update_pad_mode()
    bridge.handle_pad(40, 100)
    started = notes(bridge, 'note_on')[-1]
    bridge._enter_session_mode()
    bridge.handle_pad(40, 0)
    assert notes(bridge, 'note_off')[-1] == started


def test_two_pads_on_the_same_note_release_once_both_are_up(bridge):
    bridge.sounding = {}
    bridge._sound_note(40, 8, 60, 100)
    bridge._sound_note(45, 8, 60, 100)             # isomorphic layouts repeat notes
    bridge._release_sounding(40)
    assert notes(bridge, 'note_off') == []
    bridge._release_sounding(45)
    assert notes(bridge, 'note_off') == [(8, 60)]
