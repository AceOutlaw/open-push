#!/usr/bin/env python3
"""Read a .dawproject file and print what the open-push sequencer would care about.

Read-only: the zip is never extracted, only project.xml is parsed (plus small JSON state
files, which is where our own device data goes; see make_roundtrip.py).

    python3 -I dawproject_read.py SONG.dawproject           # readable summary
    python3 -I dawproject_read.py SONG.dawproject --json    # the parsed model as JSON

The model keeps DAWproject's own structure (tracks, scenes x clip slots, clips, notes in
beats) and only converts what MIDI needs: velocities from 0-1 to 0-127, notes sorted by time.
"""

import json
import sys
import zipfile
import xml.etree.ElementTree as ET

DEVICE_TAGS = ('Device', 'Vst2Plugin', 'Vst3Plugin', 'ClapPlugin', 'AuPlugin', 'BuiltinDevice',
               'Equalizer', 'Compressor', 'NoiseGate', 'Limiter')
MAX_STATE_BYTES = 64 * 1024  # only small state files are read (our JSON), never plug-in presets


def _float(value, default=None):
    return float(value) if value is not None else default


def _velocity(value):
    """DAWproject velocities are 0-1 (Bitwig writes 0.787402 for 100); MIDI wants 0-127."""
    return round(float(value) * 127) if value is not None else None


def _read_state(zf, path):
    """Return a device's state file as JSON if it is small and JSON, else just its size."""
    try:
        info = zf.getinfo(path)
    except KeyError:
        return {'missing': True}
    if info.file_size > MAX_STATE_BYTES:
        return {'bytes': info.file_size}
    data = zf.read(path)
    try:
        return {'json': json.loads(data)}
    except ValueError:
        return {'bytes': info.file_size}


def parse_devices(channel, zf):
    devices = []
    container = channel.find('Devices')
    if container is None:
        return devices
    for dev in container:
        if dev.tag not in DEVICE_TAGS:
            continue
        state = dev.find('State')
        entry = {
            'type': dev.tag,
            'name': dev.get('deviceName'),
            'role': dev.get('deviceRole'),
            'vendor': dev.get('deviceVendor'),
            'deviceID': dev.get('deviceID'),
        }
        if state is not None:
            entry['state_path'] = state.get('path')
            entry['state'] = _read_state(zf, state.get('path'))
        devices.append(entry)
    return devices


def parse_notes(notes_el):
    notes = []
    for n in notes_el.findall('Note'):
        notes.append({
            'time': float(n.get('time')),
            'duration': float(n.get('duration')),
            'channel': int(n.get('channel')),      # 0-based: 0 = MIDI channel 1
            'key': int(n.get('key')),
            'vel': _velocity(n.get('vel')),
            'rel': _velocity(n.get('rel')),
            'expression': n.find('Points') is not None,
        })
    notes.sort(key=lambda n: (n['time'], n['key']))   # exporters don't keep time order
    return notes


def parse_clip(clip):
    """One clip: its loop and either notes or audio. Clips may nest (outer = placement)."""
    out = {
        'name': clip.get('name'),
        'time': _float(clip.get('time')),
        'duration': _float(clip.get('duration')),
        'loop': [_float(clip.get('loopStart')), _float(clip.get('loopEnd'))]
                if clip.get('loopStart') is not None else None,
        'contentTimeUnit': clip.get('contentTimeUnit'),
    }
    notes = clip.find('Notes')
    if notes is not None:
        out['notes'] = parse_notes(notes)
    audio = clip.find('Audio')
    if audio is not None:
        f = audio.find('File')
        out['audio'] = f.get('path') if f is not None else None
    inner = clip.find('Clips')
    if inner is not None:
        out['clips'] = [parse_clip(c) for c in inner.findall('Clip')]
    return out


def parse_tracks(structure, zf):
    """Tracks (Bitwig style) and bare channels (Cubasis puts master and FX channels there)."""
    tracks = []

    def add(track_el, channel):
        entry = {
            'id': track_el.get('id') if track_el is not None else channel.get('id'),
            'name': (track_el if track_el is not None else channel).get('name'),
            'contentType': track_el.get('contentType') if track_el is not None else None,
            'role': channel.get('role') if channel is not None else None,
            'devices': parse_devices(channel, zf) if channel is not None else [],
        }
        if channel is not None:
            for param in ('Volume', 'Pan'):
                p = channel.find(param)
                if p is not None:
                    entry[param.lower()] = _float(p.get('value'))
            mute = channel.find('Mute')
            if mute is not None:
                entry['mute'] = mute.get('value') == 'true'
        tracks.append(entry)

    for el in structure:
        if el.tag == 'Track':
            add(el, el.find('Channel'))
            for sub in el.findall('Track'):   # group tracks
                add(sub, sub.find('Channel'))
        elif el.tag == 'Channel':
            add(None, el)
    return tracks


def parse_scenes(root):
    scenes = []
    for scene in root.findall('./Scenes/Scene'):
        slots = []
        for slot in scene.iter('ClipSlot'):
            clip = slot.find('Clip')
            slots.append({
                'track': slot.get('track'),
                'hasStop': slot.get('hasStop') == 'true',
                # A clip's 'time' inside a slot is leftover (Bitwig keeps the arrangement
                # position), so the sequencer should ignore it.
                'clip': parse_clip(clip) if clip is not None else None,
            })
        scenes.append({'id': scene.get('id'), 'name': scene.get('name'), 'slots': slots})
    return scenes


def parse_arrangement(root):
    lanes_out = []
    top = root.find('./Arrangement/Lanes')
    if top is None:
        return lanes_out
    for lane in top.findall('Lanes'):
        clips = lane.find('Clips')
        lanes_out.append({
            'track': lane.get('track'),
            'clips': [parse_clip(c) for c in clips.findall('Clip')] if clips is not None else [],
        })
    return lanes_out


def read_dawproject(path):
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read('project.xml'))
        app = root.find('Application')
        tempo = root.find('./Transport/Tempo')
        sig = root.find('./Transport/TimeSignature')
        structure = root.find('Structure')
        return {
            'version': root.get('version'),
            'application': {'name': app.get('name'), 'version': app.get('version')},
            'tempo': _float(tempo.get('value')) if tempo is not None else None,
            'timeSignature': [int(sig.get('numerator')), int(sig.get('denominator'))]
                             if sig is not None else None,
            'tracks': parse_tracks(structure, zf) if structure is not None else [],
            'scenes': parse_scenes(root),
            'arrangement': parse_arrangement(root),
            'files': sorted(i.filename for i in zf.infolist() if not i.is_dir()),
        }


def _clip_line(clip):
    if clip is None:
        return '-'
    inner = clip.get('clips') or []
    notes = clip.get('notes') or [n for c in inner for n in c.get('notes') or []]
    audio = clip.get('audio') or next((c.get('audio') for c in inner if c.get('audio')), None)
    loop = clip['loop']
    loop_txt = f" loop {loop[0]:g}-{loop[1]:g}" if loop else ''
    what = f"{len(notes)} notes" if notes else (f"audio {audio}" if audio else 'empty')
    return f"{clip.get('name') or '(unnamed)'}: {clip['duration']:g} beats{loop_txt}, {what}"


def print_summary(model):
    names = {t['id']: t['name'] for t in model['tracks']}
    app = model['application']
    print(f"{app['name']} {app['version']} · DAWproject {model['version']} · "
          f"{model['tempo']:g} bpm · {model['timeSignature'][0]}/{model['timeSignature'][1]}")

    print(f"\nTracks ({len(model['tracks'])})")
    for t in model['tracks']:
        print(f"  {t['id']:>6}  {t['name']:<24} {t['contentType'] or '-':<12} {t['role'] or '-'}")
        for d in t['devices']:
            print(f"          {d['type']} '{d['name']}' ({d['role']})"
                  + (f" vendor={d['vendor']}" if d['vendor'] else ''))
            state = d.get('state') or {}
            if 'json' in state:
                print(f"            state {d['state_path']}: {json.dumps(state['json'])}")
            elif d.get('state_path'):
                print(f"            state {d['state_path']}: {state}")

    print(f"\nScenes ({len(model['scenes'])})")
    for s in model['scenes']:
        filled = [sl for sl in s['slots'] if sl['clip']]
        print(f"  {s['name']}: {len(s['slots'])} slots, {len(filled)} with clips")
        for sl in filled:
            print(f"    {names.get(sl['track'], sl['track'])}: {_clip_line(sl['clip'])}")
            for n in sl['clip'].get('notes') or []:
                print(f"      t={n['time']:<9g} len={n['duration']:<9g} ch={n['channel'] + 1:<2} "
                      f"key={n['key']:<3} vel={n['vel']}" + ('  +expression' if n['expression'] else ''))

    print("\nArrangement")
    for lane in model['arrangement']:
        for c in lane['clips']:
            print(f"  {names.get(lane['track'], lane['track'])} @ {c['time']:g}: {_clip_line(c)}")

    print(f"\nFiles in the zip: {len(model['files'])}")
    for f in model['files']:
        if not f.startswith('audio/'):
            print(f"  {f}")
    audio = [f for f in model['files'] if f.startswith('audio/')]
    if audio:
        print(f"  audio/: {len(audio)} files")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    model = read_dawproject(sys.argv[1])
    if '--json' in sys.argv[2:]:
        print(json.dumps(model, indent=2))
    else:
        print_summary(model)


if __name__ == '__main__':
    main()
