import json
import os
import sqlite3
import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest
from core import ffmpeg_studio as f
from core import post_fx

SPEC = {'loai': 'nhieu_song', 'vi_tri': 'cuoi', 'thoi_luong_s': 0.5, 'cuong_do': 0.8}

def require_ffmpeg():
    try:
        return f.find_ffmpeg()
    except f.FFmpegNotFound:
        pytest.skip('ffmpeg not installed')

def require_filter(ffmpeg, name):
    listing = subprocess.check_output([ffmpeg, '-hide_banner', '-filters'], text=True, stderr=subprocess.STDOUT)
    if not any(name == field for line in listing.splitlines() for field in line.split()[1:2]):
        pytest.skip(f'ffmpeg thiếu filter {name} — chỉ bỏ ca dùng filter này')


@pytest.fixture
def real_ffmpeg():
    return require_ffmpeg()

def test_real_ffmpeg_missing_skips_only_real_tests():
    with mock.patch.object(f, 'find_ffmpeg', side_effect=f.FFmpegNotFound('missing')):
        with pytest.raises(pytest.skip.Exception):
            require_ffmpeg()

@pytest.mark.parametrize('key', ['thoi_luong_s', 'cuong_do'])
def test_huge_integer_is_yellow_and_next_shot_survives(tmp_path, key):
    p = pipeline({**SPEC, key: 10**1000})
    p.conn.execute('INSERT INTO scenes VALUES(2, ?)', (json.dumps({'post_fx': SPEC}),))
    for name in ('a.mp4', 'b.mp4'):
        (tmp_path / name).write_bytes(b'fake-source')
    paths = [str(tmp_path / 'a.mp4'), str(tmp_path / 'b.mp4')]
    def run(cmd):
        with open(cmd[-1], 'wb') as output:
            output.write(b'complete')
    with mock.patch('core.features.on', return_value=True), mock.patch.object(f, 'run', side_effect=run), mock.patch.object(f, 'find_ffmpeg', return_value='ffmpeg'):
        result = post_fx.apply(p, [{'path': paths[0], 'scene_id': 1}, {'path': paths[1], 'scene_id': 2}], paths, [2, 2], str(tmp_path))
    assert [r['muc'] for r in result] == ['vang', 'xanh']
    assert result[0]['reasons'] and paths[0] == str(tmp_path / 'a.mp4') and paths[1] != str(tmp_path / 'b.mp4')

@pytest.mark.parametrize('bad', [None, {}, {'loai': 'x'}, {**SPEC, 'cuong_do': float('nan')}, {**SPEC, 'thoi_luong_s': True}, {**SPEC, 'vi_tri': 'x'}])
def test_invalid_is_yellow(bad):
    result = post_fx.validate(bad, 2)
    assert result['muc'] == 'vang' and result['reasons']

@pytest.mark.parametrize('kind', ['nhieu_song', 'glitch', 'nhap_nhay'])
@pytest.mark.parametrize('position', ['dau', 'cuoi', 'ca_shot'])
def test_schema(kind, position):
    assert post_fx.validate({**SPEC, 'loai': kind, 'vi_tri': position}, 2)['muc'] == 'xanh'

def pipeline(spec):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE scenes(id INTEGER, data TEXT)')
    conn.execute('INSERT INTO scenes VALUES(1, ?)', (json.dumps({'post_fx': spec}),))
    return SimpleNamespace(conn=conn)

def test_disabled_does_not_read_or_render(tmp_path):
    paths = ['original.mp4']
    with mock.patch('core.features.on', return_value=False), mock.patch.object(f, 'run') as run:
        assert post_fx.apply(SimpleNamespace(conn=None), [{'path': paths[0], 'scene_id': 1}], paths, [2], str(tmp_path)) == []
        assert paths == ['original.mp4']
        run.assert_not_called()

def test_invalid_keeps_original(tmp_path):
    paths = ['original.mp4']
    with mock.patch('core.features.on', return_value=True), mock.patch.object(f, 'run') as run:
        result = post_fx.apply(pipeline({}), [{'path': paths[0], 'scene_id': 1}], paths, [2], str(tmp_path))
        assert result[0]['muc'] == 'vang' and result[0]['reasons']
        assert paths == ['original.mp4']
        run.assert_not_called()

@pytest.mark.parametrize('seconds', [float('nan'), float('inf'), -1, None])
def test_invalid_duration_is_yellow(seconds):
    assert post_fx.validate(SPEC, seconds)['muc'] == 'vang'

def test_ffmpeg_failure_isolated_and_partial_removed(tmp_path):
    p = pipeline(SPEC)
    p.conn.execute('INSERT INTO scenes VALUES(2, ?)', (json.dumps({'post_fx': SPEC}),))
    for name in ('a.mp4', 'b.mp4'):
        (tmp_path / name).write_bytes(b'fake-source')
    paths = [str(tmp_path / 'a.mp4'), str(tmp_path / 'b.mp4')]
    def run(cmd):
        with open(cmd[-1], 'wb') as output:
            output.write(b'partial')
        if 'a.mp4' == os.path.basename(cmd[cmd.index('-i') + 1]):
            raise f.FFmpegError('test failure')
    with mock.patch('core.features.on', return_value=True), mock.patch.object(f, 'run', side_effect=run), mock.patch.object(f, 'find_ffmpeg', return_value='ffmpeg'):
        result = post_fx.apply(p, [{'path': paths[0], 'scene_id': 1}, {'path': paths[1], 'scene_id': 2}], paths, [2, 2], str(tmp_path))
    assert [r['muc'] for r in result] == ['vang', 'xanh']
    assert paths[0] == str(tmp_path / 'a.mp4') and paths[1] != str(tmp_path / 'b.mp4')
    assert not list(tmp_path.glob('*.part-*'))

def test_delivery_records_warning_and_manifest_for_each_shot(tmp_path, real_ffmpeg):
    from core import delivery, final_cut
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(':memory:'))
    pid = p.create_project('post fx integration')
    for idx, spec in ((1, {}), (2, SPEC)):
        sid = p.create_scene(pid, idx, f's{idx}')
        p.conn.execute('UPDATE scenes SET data=? WHERE id=?', (json.dumps({'post_fx': spec}), sid))
        path = final_cut.clip_path(str(tmp_path), pid, idx)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run([f.find_ffmpeg(), '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=d=2:s=128x72:r=24', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', path], check=True)
    p.conn.commit()
    with mock.patch('core.features.on', side_effect=lambda name: name == 'post_fx_render'), mock.patch('core.formats.spec', return_value={'render': None}), mock.patch('core.delivery._loudness', return_value={}):
        res = delivery.render(p, pid, str(tmp_path), music_path=None, settings=delivery.get_settings(p, pid))
    man = json.loads(p.conn.execute('SELECT manifest FROM outputs WHERE id=?', (res['output_id'],)).fetchone()['manifest'])
    assert [r['muc'] for r in man['post_fx']] == ['vang', 'xanh']
    warnings = p.conn.execute("SELECT * FROM diag_events WHERE project_id=?", (pid,)).fetchall()
    assert any('post_fx_warning' in tuple(row) for row in warnings)
    assert os.path.exists(res['path']) and abs(res['seconds'] - 4) < 0.1

@pytest.mark.parametrize('kind', ['nhieu_song', 'glitch', 'nhap_nhay'])
def test_real_effect_duration_audio_and_disabled_bytes(tmp_path, kind, real_ffmpeg):
    ff = real_ffmpeg
    if kind == 'glitch':
        require_filter(ff, 'rgbashift')
    src = str(tmp_path / 'src.mp4')
    subprocess.run([ff, '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=d=2:s=128x72:r=24', '-f', 'lavfi', '-i', 'sine=d=2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', src], check=True)
    before = open(src, 'rb').read()
    p = pipeline({**SPEC, 'loai': kind})
    rows = [{'path': src, 'scene_id': 1, 'idx': 1}]
    paths = [src]
    with mock.patch('core.features.on', return_value=False):
        assert post_fx.apply(p, rows, paths, [2], str(tmp_path / 'out')) == []
    assert open(paths[0], 'rb').read() == before
    with mock.patch('core.features.on', return_value=True):
        result = post_fx.apply(p, rows, paths, [2], str(tmp_path / 'out'))
    assert result[0]['muc'] == 'xanh', result
    assert paths[0] != src and open(src, 'rb').read() == before
    assert abs(f.probe_duration(paths[0]) - f.probe_duration(src)) < 0.06
    assert f.has_audio(paths[0])
    control = str(tmp_path / 'control.mp4')
    disabled_filter = post_fx.filter_for({**SPEC, 'loai': kind}, 2)
    import re
    disabled_filter = re.sub(r"enable='[^']*'", "enable='0'", disabled_filter)
    subprocess.run([ff, '-loglevel', 'error', '-y', '-i', src, '-t', '2', '-map', '0:v:0', '-map', '0:a?',
                    '-vf', disabled_filter, *f._ENCODE, '-c:a', 'copy', control], check=True)
    def frame(path):
        return subprocess.check_output([ff, '-loglevel', 'error', '-ss', '1.75', '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    assert frame(src) != frame(paths[0])
    assert frame(control) != frame(paths[0])
