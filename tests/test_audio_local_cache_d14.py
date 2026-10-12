from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import os
import pytest
from core import sound_lib, ambience, ffmpeg_studio


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sound_lib.tempfile, "gettempdir", lambda: str(tmp_path))


def test_cache_reuses_and_refreshes(tmp_path):
    src = tmp_path / 'drive' / 'pop.wav'
    src.parent.mkdir(); src.write_bytes(b'abc')
    cache = tmp_path / 'project' / 'work'
    local = sound_lib.local_audio(str(src), str(cache))
    assert Path(local).read_bytes() == b'abc'
    with patch('core.sound_lib.shutil.copyfile', side_effect=AssertionError('copied again')):
        assert sound_lib.local_audio(str(src), str(cache)) == local
    src.write_bytes(b'new-long')
    changed = sound_lib.local_audio(str(src), str(cache))
    assert Path(changed).read_bytes() == b'new-long'
    assert changed != local


def test_cache_path_is_reused_only_in_its_own_scope(tmp_path):
    src = tmp_path / 'pop.wav'; src.write_bytes(b'abc')
    scope = str(tmp_path / 'project')
    cached = sound_lib.local_audio(str(src), scope)
    assert sound_lib.local_audio(cached, scope) == cached
    assert sound_lib.local_audio(cached, str(tmp_path / 'other')) != cached


def test_cleanup_error_does_not_hide_source_error(tmp_path):
    src = tmp_path / 'pop.wav'; src.write_bytes(b'abc')
    with patch('core.sound_lib.shutil.copyfile', side_effect=PermissionError('original offline')), \
         patch('core.sound_lib.os.remove', side_effect=PermissionError('cleanup denied')):
        with pytest.raises(sound_lib.SoundError, match='original offline'):
            sound_lib.local_audio(str(src), str(tmp_path / 'project'))


def test_two_processes_share_the_cache_cap(tmp_path):
    import subprocess
    import sys
    a, b = tmp_path / 'a.wav', tmp_path / 'b.wav'
    a.write_bytes(b'aaa'); b.write_bytes(b'bbb')
    script = '''import sys,time
from core import sound_lib
sound_lib.tempfile.gettempdir=lambda:sys.argv[1]
sound_lib.LOCAL_AUDIO_MAX_FILES=1
real=sound_lib.shutil.copyfile
def slow(a,b):
 time.sleep(.3)
 return real(a,b)
sound_lib.shutil.copyfile=slow
try:
 sound_lib.local_audio(sys.argv[2],sys.argv[3]); print('ok')
except sound_lib.SoundError as e:
 print('full' if 'cache tạm âm thanh đầy' in str(e) else str(e))
'''
    procs = [subprocess.Popen([sys.executable, '-c', script, str(tmp_path), str(src), str(tmp_path/'project')],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                             env=dict(os.environ, PYTHONUTF8='1')) for src in (a,b)]
    results = [p.communicate(timeout=15) for p in procs]
    assert sorted(out.strip() for out, err in results) == ['full', 'ok'], results
    assert len(list((tmp_path/'ai-video-audio-cache').rglob('*.wav'))) == 1


def test_pop_cache_failure_keeps_overlay(tmp_path):
    from core import end_popup
    with patch.object(end_popup, 'resolve', return_value=[{'label': 'icon'}]), \
         patch.object(end_popup, 'pop_sound', return_value='pop.wav'), \
         patch.object(end_popup, 'frames'), \
         patch.object(ffmpeg_studio, 'probe_size', return_value=(320, 180)), \
         patch.object(ffmpeg_studio, 'probe_duration', return_value=2), \
         patch.object(ffmpeg_studio, 'find_ffmpeg', return_value='ffmpeg'), \
         patch.object(ffmpeg_studio, 'local_audio_source', side_effect=sound_lib.SoundError('chép về máy')), \
         patch.object(ffmpeg_studio, 'run') as run:
        result = end_popup.apply(None, 'film.mp4', str(tmp_path / 'out.mp4'),
                                 {'seconds': 1, 'hold': False, 'headline': ''})
    assert 'overlay=' in ' '.join(run.call_args.args[0])
    assert result['pops_s'] == [] and 'chép về máy' in result['sound_note']


def test_render_reports_ambience_cache_failure(tmp_path):
    from contextlib import ExitStack
    from types import SimpleNamespace
    from core import delivery
    p = SimpleNamespace(conn=object(), project=lambda pid: {})
    reason = 'hãy chép về máy rồi chọn lại: ' + 'long-path/' * 40 + 'pop.wav'
    class ReachedMix(Exception):
        pass
    with ExitStack() as stack:
        values = {
            'core.delivery.access.need_edit': None,
            'core.final_cut.collect_clips_for_render': [{'path': 'clip.mp4', 'scene_id': 1}],
            'core.final_cut.require_delivery_resolution': None,
            'core.final_cut.render_problems': [],
            'core.voice.place_on_timeline': [],
            'core.sfx_plan.place_on_timeline': [],
            'core.audio_lib.mix_list': [], 'core.audio_lib.missing_in_mix': [],
            'core.formats.project_aspect': '16:9',
            'core.delivery._fit_edits': [], 'core.delivery._colour_match': [],
            'core.delivery._flashbacks': [], 'core.delivery._edge_transitions': [],
            'core.delivery._hold_end': None, 'core.post_fx.apply': [],
        }
        for target, value in values.items():
            stack.enter_context(patch(target, return_value=value))
        stack.enter_context(patch('core.features.on', side_effect=lambda flag: flag == 'ambience_bed'))
        stack.enter_context(patch('core.ambience.beds', side_effect=sound_lib.SoundError(reason)))
        stack.enter_context(patch('core.delivery.sound_plan', side_effect=ReachedMix))
        record = stack.enter_context(patch('core.diag.record'))
        with pytest.raises(ReachedMix):
            delivery.render(p, 1, str(tmp_path), music_path=None, durations=[2],
                            settings=dict(delivery.DEFAULTS), render_size=(320,180))
    assert record.call_count == 1
    args = record.call_args.args
    assert args[2] == 'warn' and reason in args[3] and args[4] == 'ambience_audio'


def test_ambience_failure_shows_the_existing_render_warning():
    import sqlite3
    import json
    from types import SimpleNamespace
    from dashboard.steps import step5
    conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE outputs(id,project_id,kind,manifest)')
    reason = 'hãy chép về máy: G:/Kho/pop.wav'
    conn.execute('INSERT INTO outputs VALUES(1,1,?,?)', ('final', json.dumps({'ambience': {'error':reason}})))
    with patch.object(step5, '_note'), patch.object(step5.st, 'warning') as warn:
        step5.loudness_line(SimpleNamespace(conn=conn), 1)
    conn.close()
    assert reason in warn.call_args.args[0]


def test_same_basename_and_parallel(tmp_path):
    a, b = tmp_path / 'a' / 'pop.wav', tmp_path / 'b' / 'pop.wav'
    a.parent.mkdir(); b.parent.mkdir(); a.write_bytes(b'aaa'); b.write_bytes(b'bbb')
    cache = tmp_path / 'cache'
    with ThreadPoolExecutor(4) as pool:
        paths = list(pool.map(lambda _: sound_lib.local_audio(str(a), str(cache)), range(8)))
    assert len(set(paths)) == 1
    other = sound_lib.local_audio(str(b), str(cache))
    assert other != paths[0] and Path(other).read_bytes() == b'bbb'
    assert not list((tmp_path / 'ai-video-audio-cache').rglob('*.part*'))


def test_partial_copy_and_missing_are_explicit(tmp_path):
    src = tmp_path / 'G-pop.wav'; src.write_bytes(b'abc')
    cache = tmp_path / 'cache'
    def partial(a, b):
        Path(b).write_bytes(b'a')
        raise PermissionError('Drive offline')
    with patch('core.sound_lib.shutil.copyfile', side_effect=partial):
        with pytest.raises(sound_lib.SoundError, match='chép về máy') as exc:
            sound_lib.local_audio(str(src), str(cache))
    assert str(src) in str(exc.value)
    assert not [p for p in (tmp_path / 'ai-video-audio-cache').rglob('*') if p.is_file()]
    with pytest.raises(sound_lib.SoundError, match='chép về máy'):
        sound_lib.local_audio(str(tmp_path / 'missing.wav'), str(cache))


def test_bad_cache_and_source_changed_during_copy(tmp_path):
    src = tmp_path / 'pop.wav'; src.write_bytes(b'abc')
    cache = tmp_path / 'cache'
    local = sound_lib.local_audio(str(src), str(cache)); Path(local).write_bytes(b'x')
    assert Path(sound_lib.local_audio(str(src), str(cache))).read_bytes() == b'abc'
    real = sound_lib.shutil.copyfile
    def mutate(a, b):
        real(a, b); src.write_bytes(b'changed')
    src.write_bytes(b'new')
    with patch('core.sound_lib.shutil.copyfile', side_effect=mutate):
        with pytest.raises(sound_lib.SoundError, match='chép về máy'):
            sound_lib.local_audio(str(src), str(cache))


def test_bed_passes_local_file_to_ffmpeg(tmp_path):
    src = tmp_path / 'drive.wav'; src.write_bytes(b'fake')
    out = tmp_path / 'project' / 'bed.wav'; out.parent.mkdir()
    with patch('core.ffmpeg_studio.run') as run:
        ambience._bed(str(src), 2, str(out), 'ffmpeg')
    cmd = run.call_args.args[0]
    local = cmd[cmd.index('-i') + 1]
    assert local != str(src) and Path(local).read_bytes() == b'fake'


def test_reject_url_without_io(tmp_path):
    with patch('core.sound_lib.os.stat', side_effect=AssertionError('URL read')):
        with pytest.raises(sound_lib.SoundError, match='chép về máy'):
            sound_lib.local_audio('https://example.test/pop.wav', str(tmp_path))


def test_mtime_only_refresh_and_local_cache_limit(tmp_path, monkeypatch):
    src = tmp_path / 'pop.wav'; src.write_bytes(b'old')
    first = sound_lib.local_audio(str(src), str(tmp_path / 'project'))
    info = src.stat(); src.write_bytes(b'new')
    os.utime(src, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
    second = sound_lib.local_audio(str(src), str(tmp_path / 'project'))
    assert first != second and Path(second).read_bytes() == b'new'
    monkeypatch.setattr(sound_lib, 'LOCAL_AUDIO_MAX_FILES', 2)
    src.write_bytes(b'other')
    with pytest.raises(sound_lib.SoundError, match='cache tạm âm thanh đầy'):
        sound_lib.local_audio(str(src), str(tmp_path / 'project'))
    assert Path(first).read_bytes() == b'old'


def test_ffmpeg_really_cuts_cached_audio(tmp_path):
    import wave
    import struct
    import math
    try:
        ff = ffmpeg_studio.find_ffmpeg()
    except ffmpeg_studio.FFmpegNotFound:
        pytest.skip('Máy thiếu ffmpeg')
    src = tmp_path / 'drive.wav'
    with wave.open(str(src), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
        wav.writeframes(b''.join(struct.pack('<h', int(2000 * math.sin(i * 440 * 2 * math.pi / 48000))) for i in range(48000)))
    out = tmp_path / 'project' / 'bed.wav'; out.parent.mkdir()
    ambience._bed(str(src), 1.5, str(out), ff)
    assert ffmpeg_studio.probe_duration(str(out)) == pytest.approx(1.5, abs=0.05)
