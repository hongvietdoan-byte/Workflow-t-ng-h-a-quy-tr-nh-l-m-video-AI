import os
from pathlib import Path
from unittest import mock
import pytest

@pytest.fixture
def isolated():
    with mock.patch.object(os, 'environ', {'SYSTEMROOT': 'C:\\Windows', 'PATH': 'C:\\Windows\\System32'}):
        yield

def test_metadata_ranges_and_missing(isolated, tmp_path):
    from core import ref_audio
    source = tmp_path / 'original.mp4'
    source.write_bytes(b'x')
    with mock.patch.object(ref_audio, '_source_duration', return_value=4):
        value = ref_audio.validate_metadata({'source_path': str(source), 'start': 1, 'end': 3, 'speed': .5})
        assert value['speed'] == .5
        for field, bad in [('start', -1), ('end', 8), ('speed', float('nan')), ('speed', 0)]:
            changed = dict(value, **{field: bad})
            with pytest.raises(ValueError):
                ref_audio.validate_metadata(changed)
        with pytest.raises(ValueError):
            ref_audio.validate_metadata(None)


def test_ref_sync_experimental_requires_explicit_opt_in(isolated):
    from core import features
    with mock.patch.object(features, 'settings', return_value={'preset':'experimental','flags':{},'modes':{}}):
        assert features.state('ref_audio_sync') == 'off'


def test_setter_rejects_other_project_before_probe(isolated, tmp_path):
    import sqlite3
    from core.pipeline import Pipeline
    from core import ref_audio
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE projects(id INT, name TEXT, created_by TEXT); CREATE TABLE project_watchers(project_id INT,email TEXT,level TEXT); CREATE TABLE scenes(id INT,project_id INT); CREATE TABLE motion_prompts(scene_id INT,ref_video_path TEXT,ref_video_type TEXT,ref_audio_metadata TEXT); INSERT INTO projects VALUES(1,"A","actor-a"),(2,"B","actor-b"); INSERT INTO scenes VALUES(1,1); INSERT INTO motion_prompts VALUES(1,"old","feature",NULL);')
    p = Pipeline(conn)
    p.data_dir = str(tmp_path)
    p.user = {'email': 'actor-a', 'role': 'member'}
    source = tmp_path / '2' / 'motion_ref' / 'source.mp4'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'x')
    meta = dict(source_path=str(source),start=0,end=1,speed=1)
    with mock.patch.object(ref_audio, '_source_duration', return_value=2) as probe:
        with pytest.raises(ValueError):
            p.set_motion_ref_video(1,str(source),ref_audio_metadata=meta)
        probe.assert_not_called()
    assert conn.execute('SELECT ref_video_path FROM motion_prompts').fetchone()[0] == 'old'
    own = tmp_path / '1' / 'motion_ref' / 'source.mp4'
    own.parent.mkdir(parents=True)
    own.write_bytes(b'x')
    with mock.patch.object(ref_audio, '_source_duration', return_value=2):
        p.set_motion_ref_video(1,str(own),ref_audio_metadata=dict(meta,source_path=str(own)))
    assert conn.execute('SELECT ref_video_path FROM motion_prompts').fetchone()[0] == str(own)
    conn.close()


@pytest.mark.parametrize('used', [False, True])
def test_source_bytes_change_invalidates_proposal(isolated, tmp_path, used):
    import sqlite3, json
    from types import SimpleNamespace
    from core import ref_audio, features, audio_lib
    source = tmp_path / '1' / 'motion_ref' / 'source.mp4'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'old bytes')
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE scenes(id INT,idx INT,project_id INT); CREATE TABLE motion_prompts(scene_id INT,ref_video_path TEXT,ref_audio_metadata TEXT); INSERT INTO scenes VALUES(1,1,1);')
    meta = dict(source_path=str(source),start=0,end=1,speed=1)
    conn.execute('INSERT INTO motion_prompts VALUES(?,?,?)',(1,str(source),json.dumps(meta)))
    def extract(meta, dst, ff):
        Path(dst).write_bytes(b'fake wave')
    with mock.patch.object(features,'on',return_value=True), mock.patch.object(ref_audio,'_source_duration',return_value=2), mock.patch.object(ref_audio,'_source_probe',return_value='Stream #0:0: Audio: pcm_s16le'), mock.patch.object(ref_audio.ffmpeg_studio,'find_ffmpeg',return_value='ffmpeg'), mock.patch.object(ref_audio,'_extract_segment',side_effect=extract):
        p = SimpleNamespace(conn=conn)
        assert ref_audio.propose(p,str(tmp_path),1)['added'] == [1]
        directory = audio_lib.assets_dir(str(tmp_path),1)
        old = audio_lib.load(directory)
        old[0]['use'] = used
        audio_lib._save(directory,old)
        source.write_bytes(b'new bytes')
        result = ref_audio.propose(p,str(tmp_path),1)
        assert result['added'] == [1]
        assert result['stale_used' if used else 'removed'] == [1]
        entries = audio_lib.load(directory)
        assert len(entries) == (2 if used else 1)
        if used:
            assert entries[0]['ref_stale']
    conn.close()


def test_fingerprint_read_is_bounded(isolated, tmp_path):
    from core import ref_audio
    source = tmp_path / 'source.mp4'
    source.write_bytes(b'0123456789')
    with mock.patch.object(ref_audio, 'MAX_SOURCE_BYTES', 9):
        with pytest.raises(ValueError, match='VÀNG:'):
            ref_audio._source_fingerprint(str(source))
    with mock.patch.object(ref_audio, 'MAX_SOURCE_BYTES', 10):
        assert len(ref_audio._source_fingerprint(str(source))) == 64


@pytest.mark.parametrize('change', ['bytes', 'lost', 'overflow'])
def test_source_mutation_during_extract_rejected(isolated, tmp_path, change):
    import sqlite3, json
    from types import SimpleNamespace
    from core import ref_audio, features, audio_lib
    source = tmp_path / '1' / 'source.mp4'
    source.parent.mkdir()
    source.write_bytes(b'old')
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE scenes(id INT,idx INT,project_id INT); CREATE TABLE motion_prompts(scene_id INT,ref_video_path TEXT,ref_audio_metadata TEXT); INSERT INTO scenes VALUES(1,1,1);')
    conn.execute('INSERT INTO motion_prompts VALUES(?,?,?)',(1,str(source),json.dumps(dict(source_path=str(source),start=0,end=1,speed=1))))
    destinations = []
    def extract(meta,dst,ff):
        destinations.append(dst)
        Path(dst).write_bytes(b'partial audio')
        if change == 'lost':
            source.unlink()
        else:
            source.write_bytes(b'0123456789' if change == 'overflow' else b'new')
    with mock.patch.object(ref_audio,'MAX_SOURCE_BYTES',9), mock.patch.object(features,'on',return_value=True), mock.patch.object(ref_audio,'_source_duration',return_value=2), mock.patch.object(ref_audio,'_source_probe',return_value='Stream #0:0: Audio: pcm_s16le'), mock.patch.object(ref_audio.ffmpeg_studio,'find_ffmpeg',return_value='ffmpeg'), mock.patch.object(ref_audio,'_extract_segment',side_effect=extract):
        result = ref_audio.propose(SimpleNamespace(conn=conn),str(tmp_path),1)
    assert result['added'] == []
    assert result['failed'][0][1].startswith('VÀNG:')
    assert audio_lib.load(audio_lib.assets_dir(str(tmp_path),1)) == []
    assert not Path(destinations[0]).parent.exists()
    conn.close()


def test_sync_fit_huge_duration_rejected_before_spawn(isolated, tmp_path):
    from core import ref_audio, features
    entry = dict(file='audio.wav',ref_audio_metadata={'speed':1})
    with mock.patch.object(features,'on',return_value=True), mock.patch.object(ref_audio.subprocess,'run') as run:
        ref_audio.fit(str(tmp_path),entry,1e300,'ffmpeg')
    run.assert_not_called()
    assert entry['fit_skipped'].startswith('VÀNG:')


def test_sync_fit_failure_preserves_previous_file(isolated, tmp_path):
    import subprocess
    from core import ref_audio, features
    original = tmp_path / 'audio_sync.wav'
    original.write_bytes(b'good old audio')
    entry = dict(file='audio.wav',ref_audio_metadata={'speed':1},fit_file=original.name,fit_shot_seconds=2)
    outputs = []
    def fail(args,**kwargs):
        outputs.append(args[-1])
        Path(args[-1]).write_bytes(b'partial corrupt')
        raise subprocess.TimeoutExpired('ffmpeg',60)
    with mock.patch.object(features,'on',return_value=True), mock.patch.object(ref_audio.subprocess,'run',side_effect=fail):
        with pytest.raises(subprocess.TimeoutExpired):
            ref_audio.fit(str(tmp_path),entry,3,'ffmpeg')
    assert original.read_bytes() == b'good old audio'
    assert entry['fit_shot_seconds'] == 2
    assert all(not Path(path).exists() for path in outputs)

def test_extract_uses_original_segment_and_speed(isolated, tmp_path):
    from core import ref_audio
    meta = {'source_path': str(tmp_path / 'original.mp4'), 'start': 1., 'end': 3., 'speed': .5}
    with mock.patch.object(ref_audio.subprocess, 'run') as run:
        ref_audio._extract_segment(meta, str(tmp_path / 'out.wav'), 'ffmpeg')
    args = run.call_args.args[0]
    assert args[args.index('-i') + 1] == meta['source_path']
    assert 'atrim=start=1.0:end=3.0,asetpts=PTS-STARTPTS,atempo=0.5' == args[args.index('-af') + 1]

def test_propose_sync_legacy_yellow_and_off_unchanged(isolated, tmp_path):
    import sqlite3
    from types import SimpleNamespace
    from core import ref_audio, features, audio_lib
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE scenes(id INT, idx INT, project_id INT); CREATE TABLE motion_prompts(scene_id INT, ref_video_path TEXT, ref_audio_metadata TEXT); INSERT INTO scenes VALUES(1,1,1); INSERT INTO motion_prompts VALUES(1,"cut.mp4",NULL);')
    p = SimpleNamespace(conn=conn)
    with mock.patch.object(features, 'on', return_value=True), mock.patch.object(ref_audio, '_extract_segment') as extract:
        result = ref_audio.propose(p, str(tmp_path), 1)
        assert result['added'] == []
        assert result['failed'][0][0] == 1
        assert result['failed'][0][1].startswith('VÀNG:')
        extract.assert_not_called()
    with mock.patch.object(features, 'on', return_value=False):
        result = ref_audio.propose(p, str(tmp_path), 1)
        assert result['missing'] == [1]
        assert result['failed'] == []
    conn.close()


def test_ffmpeg_real_original_segment_speed_and_shot_fit(isolated, tmp_path):
    import json
    import sqlite3
    import subprocess
    import wave
    import math
    import struct
    from types import SimpleNamespace
    from core import ref_audio, features, audio_lib
    candidates = list(Path('C:/Users').glob('*/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg*/bin/ffmpeg.exe')) if os.name == 'nt' else [Path('/usr/bin/ffmpeg')]
    ff = next((path for path in candidates if path.is_file()), Path('missing-ffmpeg'))
    if not ff.is_file():
        pytest.skip('ffmpeg fixture local unavailable')
    source_dir = tmp_path / '1' / 'motion_ref'
    source_dir.mkdir(parents=True)
    original = source_dir / 'original.wav'
    rate = 48000
    with wave.open(str(original), 'wb') as out:
        out.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(b''.join(struct.pack('<h', int(10000 * math.sin(2 * math.pi * (440 if i < rate else 880) * i / rate))) for i in range(3 * rate)))
    cut = tmp_path / 'silent.mp4'
    subprocess.run([str(ff), '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=blue:s=32x32:d=2', '-an', str(cut)], check=True, capture_output=True, env=ref_audio._native_env())
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE scenes(id INT, idx INT, project_id INT); CREATE TABLE motion_prompts(scene_id INT, ref_video_path TEXT, ref_audio_metadata TEXT); INSERT INTO scenes VALUES(1,1,1);')
    meta = dict(source_path=str(original), start=1., end=2., speed=.5)
    conn.execute('INSERT INTO motion_prompts VALUES(?,?,?)', (1,str(cut),json.dumps(meta)))
    with mock.patch.object(features, 'on', return_value=True), mock.patch.object(ref_audio.ffmpeg_studio, 'find_ffmpeg', return_value=str(ff)):
        result = ref_audio.propose(SimpleNamespace(conn=conn), str(tmp_path), 1)
        assert result['added'] == [1]
        directory = audio_lib.assets_dir(str(tmp_path), 1)
        entry = audio_lib.load(directory)[0]
        with wave.open(str(Path(directory) / entry['file']), 'rb') as audio:
            duration = audio.getnframes() / audio.getframerate()
            samples = struct.unpack('<' + 'h' * audio.getnframes() * 2, audio.readframes(audio.getnframes()))[::2]
        crossings = sum(a <= 0 < b for a,b in zip(samples,samples[1:]))
        assert 1.94 < duration < 2.04
        assert 850 < crossings / duration < 910
        ref_audio.fit(directory, entry, 2.5, str(ff))
        with wave.open(str(Path(directory) / entry['fit_file']), 'rb') as audio:
            assert abs(audio.getnframes() / audio.getframerate() - 2.5) < .001
        again = ref_audio.propose(SimpleNamespace(conn=conn), str(tmp_path), 1)
        assert again['already'] == [1]
    conn.close()
