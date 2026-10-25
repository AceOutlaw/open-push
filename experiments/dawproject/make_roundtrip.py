#!/usr/bin/env python3
"""Write roundtrip-test.dawproject: a tiny song in the shape the open-push sequencer would use.

    python3 -I make_roundtrip.py [OUT.dawproject]

Open it in Bitwig and Cubasis, export it again, and compare the two with dawproject_read.py.
The question is what survives, above all the generic <Device> on each track: DAWproject has no
element for hardware, so our routing (which device, port and MIDI channel) rides in a small JSON
state file, the same way plug-ins keep their presets (<State path="plugins/....vstpreset"/>).

Contents:
  Seqtrak Kick   -> Seqtrak track 1 (KICK, MIDI ch 1)
  Orchid Chords  -> Orchid (MIDI ch 1 on its own port)
  Master
  Scene 1: kick four on the floor (1 bar loop) + C / F chords (2 bar loop)
  Scene 2: kick with a pickup, chords slot empty
  Arrangement: the kick, 2 bars at beat 0
"""

import json
import sys
import zipfile
import xml.etree.ElementTree as ET

VEL_100 = 100 / 127   # DAWproject velocities are 0-1

DEVICES = {
    'kick': {'openpush': 1, 'device': 'seqtrak', 'port': 'SEQTRAK', 'midiChannel': 1,
             'seqtrakTrack': 1, 'seqtrakTrackName': 'KICK'},
    'chords': {'openpush': 1, 'device': 'orchid', 'port': 'Orchid', 'midiChannel': 1},
}


class Ids:
    """Sequential ids, as Bitwig writes them (id1, id2, ...)."""

    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f'id{self.n}'


def sub(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items() if v is not None})


def num(x):
    return f'{x:.6f}'


def add_track(structure, ids, name, color, content, role='regular', device=None, state=None,
              master_id=None):
    track = sub(structure, 'Track', id=ids(), name=name, color=color, contentType=content, loaded='true')
    channel = sub(track, 'Channel', id=ids(), role=role, audioChannels=2, destination=master_id)
    if device:
        devices = sub(channel, 'Devices')
        dev = sub(devices, 'Device', id=ids(), deviceName=device[0], deviceVendor=device[1],
                  deviceRole='instrument', deviceID=device[2], loaded='true')
        sub(dev, 'Enabled', id=ids(), value='true', name='On/Off')
        sub(dev, 'State', path=state)
    sub(channel, 'Mute', id=ids(), value='false', name='Mute')
    sub(channel, 'Pan', id=ids(), unit='normalized', min=num(0), max=num(1), value=num(0.5), name='Pan')
    sub(channel, 'Volume', id=ids(), unit='linear', min=num(0), max=num(2), value=num(1), name='Volume')
    return track, channel


def add_notes(parent, ids, notes):
    """notes: (time, duration, key) in beats, MIDI channel 1."""
    el = sub(parent, 'Notes', id=ids())
    for time, duration, key in notes:
        sub(el, 'Note', time=num(time), duration=num(duration), channel=0, key=key,
            vel=num(VEL_100), rel=num(VEL_100))
    return el


def add_clip(parent, ids, name, color, length, notes, time=0.0):
    clip = sub(parent, 'Clip', time=num(time), duration=num(length), playStart=num(0),
               loopStart=num(0), loopEnd=num(length), enable='true', name=name, color=color)
    add_notes(clip, ids, notes)
    return clip


def build():
    ids = Ids()
    project = ET.Element('Project', version='1.0')
    sub(project, 'Application', name='open-push', version='0.1-roundtrip-test')
    transport = sub(project, 'Transport')
    sub(transport, 'Tempo', id=ids(), unit='bpm', min=num(20), max=num(666), value=num(120), name='Tempo')
    sub(transport, 'TimeSignature', id=ids(), numerator=4, denominator=4)

    structure = sub(project, 'Structure')
    kick, _ = add_track(structure, ids, 'Seqtrak Kick', '#e05a47', 'notes',
                        device=('SEQTRAK', 'Yamaha', 'openpush.seqtrak'),
                        state='openpush/seqtrak-kick.json')
    chords, _ = add_track(structure, ids, 'Orchid Chords', '#848ae0', 'notes',
                          device=('Orchid', 'Telepathic Instruments', 'openpush.orchid'),
                          state='openpush/orchid-chords.json')
    master_track, master_channel = add_track(structure, ids, 'Master', None, 'audio notes', role='master')
    master_id = master_channel.get('id')
    for track in (kick, chords):
        track.find('Channel').set('destination', master_id)

    four_floor = [(b, 0.25, 36) for b in (0, 1, 2, 3)]
    pickup = four_floor + [(3.5, 0.25, 36)]
    c_then_f = [(0, 4, k) for k in (60, 64, 67)] + [(4, 4, k) for k in (65, 69, 72)]

    arrangement = sub(project, 'Arrangement', id=ids())
    lanes = sub(arrangement, 'Lanes', id=ids(), timeUnit='beats')
    for track, clips in ((kick, [('Kick', 8, [(b, 0.25, 36) for b in range(8)])]), (chords, []), (master_track, [])):
        lane = sub(lanes, 'Lanes', id=ids(), track=track.get('id'))
        clips_el = sub(lane, 'Clips', id=ids())
        for name, length, notes in clips:
            add_clip(clips_el, ids, name, track.get('color'), length, notes)

    scenes = sub(project, 'Scenes')
    for scene_name, kick_notes, chord_notes in (('Scene 1', four_floor, c_then_f), ('Scene 2', pickup, None)):
        scene = sub(scenes, 'Scene', id=ids(), name=scene_name)
        slots = sub(scene, 'Lanes', id=ids())
        slot = sub(slots, 'ClipSlot', id=ids(), track=kick.get('id'), hasStop='true')
        add_clip(slot, ids, f'Kick {scene_name[-1]}', kick.get('color'), 4, kick_notes)
        slot = sub(slots, 'ClipSlot', id=ids(), track=chords.get('id'), hasStop='true')
        if chord_notes:
            add_clip(slot, ids, 'C / F', chords.get('color'), 8, chord_notes)
        sub(slots, 'ClipSlot', id=ids(), track=master_track.get('id'), hasStop='true')

    return project


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'roundtrip-test.dawproject'
    project = build()
    ET.indent(project)
    xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(project, encoding='utf-8')
    metadata = ET.Element('MetaData')
    sub(metadata, 'Title').text = 'open-push round trip test'
    sub(metadata, 'Comment').text = 'Device state files under openpush/ hold the hardware routing.'
    ET.indent(metadata)
    meta = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(metadata, encoding='utf-8')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('project.xml', xml)
        zf.writestr('metadata.xml', meta)
        zf.writestr('openpush/seqtrak-kick.json', json.dumps(DEVICES['kick'], indent=2))
        zf.writestr('openpush/orchid-chords.json', json.dumps(DEVICES['chords'], indent=2))
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
