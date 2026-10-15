"""SyncState: which Seqtrak values the bridge knows to be current."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("seqtrak_sync", ROOT / "src" / "open_push" / "seqtrak" / "sync.py")
sy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sy)

TEMPO, SWING, NAME = [0x30, 0x40, 0x76], [0x30, 0x40, 0x7C], [0x01, 0x10, 0x35]


def test_syncing_until_every_essential_value_is_confirmed():
    s = sy.SyncState()
    s.begin([TEMPO, SWING])
    assert s.status() == sy.SYNCING and s.quality(TEMPO) == sy.UNKNOWN
    s.confirm(TEMPO)
    assert s.status() == sy.SYNCING
    s.confirm(SWING)
    assert s.status() == sy.SYNCED


def test_project_switch_makes_values_stale():
    s = sy.SyncState()
    s.begin([TEMPO])
    s.confirm(TEMPO)
    s.confirm(NAME)                  # not essential, still tracked
    s.begin([TEMPO])                 # new project
    assert s.epoch == 2
    assert s.quality(TEMPO) == sy.STALE and s.quality(NAME) == sy.STALE
    assert s.status() == sy.SYNCING


def test_a_failed_read_gives_partial_sync_and_retries_next_time():
    s = sy.SyncState()
    s.begin([TEMPO, SWING])
    s.confirm(TEMPO)
    s.failed(SWING)
    assert s.status() == sy.PARTIAL
    s.begin([TEMPO, SWING])          # next load asks again
    assert s.quality(SWING) == sy.UNKNOWN and s.status() == sy.SYNCING


def test_a_late_failure_does_not_override_a_confirmation():
    s = sy.SyncState()
    s.begin([TEMPO])
    s.confirm(TEMPO)                 # reported by the device meanwhile
    s.failed(TEMPO)
    assert s.quality(TEMPO) == sy.CONFIRMED
