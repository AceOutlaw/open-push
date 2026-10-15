"""The Seqtrak protocol spec is valid, and every SysEx address the bridge uses is in it."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("seqtrak_protocol", ROOT / "tools" / "seqtrak_protocol.py")
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)


def test_spec_is_valid():
    entries = sp.load()
    assert entries
    assert sp.validate(entries) == []


def test_bridge_addresses_are_in_the_spec():
    _, missing = sp.bridge_report(sp.load())
    assert missing == [], f"bridge uses SysEx addresses missing from the spec: {missing}"


def test_bridge_midi_is_in_the_spec():
    _, missing = sp.midi_report(sp.load())
    assert missing == [], f"bridge sends plain MIDI missing from the spec: {missing}"


def test_midi_cross_check_sees_the_bridge():
    # Guards the scanner: if a regex stops matching, the check above would pass vacuously
    used = sp.bridge_midi()
    assert {("cc", 7), ("cc", 23), ("cc", 0), ("program",), ("note",), ("realtime", "start")} <= set(used)
    assert ("cc", 50) not in used  # a Push LED CC (to push_out), not a Seqtrak message


def test_midi_cross_check_catches_a_gap():
    entries = [e for e in sp.load() if e["id"] != "midi.mute_solo_cc"]
    _, missing = sp.midi_report(entries)
    assert {m[0] for m in missing} == {"cc 23", "cc 24"}


def test_generated_reference_is_current():
    assert sp.OUT.read_text(encoding="utf-8") == sp.render(sp.load()), \
        "PROTOCOL.md is stale: run python3 tools/seqtrak_protocol.py render"


_vspec = importlib.util.spec_from_file_location("seqtrak_verify", ROOT / "tools" / "seqtrak_verify.py")
sv = importlib.util.module_from_spec(_vspec)
_vspec.loader.exec_module(sv)


def test_verify_resolves_test_addresses():
    assert sv.test_addresses({"address": "30 5p 00"}) == (["30 50 00"], [])
    assert sv.test_addresses({"address": "48 09 nn"}) == ([], ["48 09 nn"])
    assert sv.test_addresses({"address": "48 09 nn", "test": {"address": ["48 09 04"]}}) == (["48 09 04"], [])


class _FakeSeqtrak:
    def __init__(self, state, sticky=True):
        self.state, self.sticky = state, sticky

    def read(self, addr):
        return self.state.get(tuple(addr))

    def write(self, addr, data):
        if self.sticky:
            self.state[tuple(addr)] = list(data)


def test_verify_write_reads_back_and_restores():
    dev = _FakeSeqtrak({(0x00, 0x00, 0x25): [0x00]})
    r = sv.write_test(dev, {"id": "system.metronome", "status": "app"}, "00 00 25", ["01", "00"])
    assert r["result"] == "pass" and r["wrote"] == "01" and r["restored"] == "00"
    assert dev.state[(0x00, 0x00, 0x25)] == [0x00]


def test_verify_write_reports_a_failed_command():
    dev = _FakeSeqtrak({(0x30, 0x40, 0x7C): [0x01, 0x00]}, sticky=False)
    r = sv.write_test(dev, {"id": "project.swing", "status": "verified"}, "30 40 7C", ["01 05"])
    assert r["result"] == "FAIL"
