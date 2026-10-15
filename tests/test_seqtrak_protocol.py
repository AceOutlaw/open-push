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


def test_generated_reference_is_current():
    assert sp.OUT.read_text(encoding="utf-8") == sp.render(sp.load()), \
        "PROTOCOL.md is stale: run python3 tools/seqtrak_protocol.py render"
