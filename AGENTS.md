# Repository Guidelines

Contributor notes for `open-push`, an open-source Python project that unlocks Ableton Push hardware outside Ableton Live.

## Project Structure & Module Organization
- `src/open_push/`: core package.
  - `core/`: hardware I/O (`hardware.py`), LCD handling (`display.py`), and shared constants.
  - `music/`: scales and isomorphic layout logic.
  - `reason/`: Reason bridge (`app.py`, `bridge.py`, `ports.py`, `protocol.py`) and Lua codecs (`codecs/`).
- `src/open_push/reason/codecs/`: `.lua`, `.luacodec`, and `.remotemap` files for Reason Remote.
- `src/experiments/`: runnable scripts and hardware demos (e.g., `isomorphic_controller.py`).
- `tests/`: lightweight, hardware-free tests.
- `docs/`: protocol research and integration guides (see `docs/09-reason-integration-guide.md`).
- `reference files/`: Remote SDK and other external references.

## Build, Test, and Development Commands
- `pip3 install mido python-rtmidi`: install runtime deps for MIDI I/O.
- `python3 src/experiments/push_wakeup.py`: wake Push and verify LEDs/LCD.
- `python3 src/experiments/isomorphic_controller.py`: main playable controller.
- `python3 src/open_push/reason/app.py`: run the Reason bridge (virtual ports + Push I/O).
- `python3 src/open_push/reason/bridge.py`: alternate bridge prototype.
- `./src/open_push/reason/codecs/install_codecs.sh`: install Reason Lua codecs.
- `python3 tests/test_core.py`: run core tests without hardware.

## Coding Style & Naming Conventions
- Python 3 + Lua; 4-space indentation, `snake_case` for functions/vars, `CamelCase` for classes.
- Constants are uppercase and live in `src/open_push/core/constants.py`.
- Prefer small, testable helpers; keep hardware I/O behind `mido` ports.
- Follow LCD segment formatting rules when writing display text.

## Testing Guidelines
- Tests are plain Python scripts with `assert` (no pytest harness).
- Add new tests to `tests/test_core.py` with `test_*` functions.
- Keep tests hardware-free and run from the repo root.

## Commit & Pull Request Guidelines
- Commit subjects are short and imperative; type prefixes like `feat:` or `docs:` are used in history.
- PRs should describe hardware/DAW tested, key commands run, and any protocol changes.
- Include screenshots or short GIFs only if UI/LED behavior changed.

## Configuration Tips
- Virtual MIDI ports are created via `mido` (no manual IAC setup required on macOS).
- Reason auto-detection depends on exact virtual port names in the `.luacodec` files.
- Push uses MIDI channel 0; Reason codecs expect channel 15 (bridge must translate).
