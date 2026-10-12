import json
import sqlite3
import subprocess
import math
import array
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from core import shot_popup, end_popup, features, ffmpeg_studio, delivery, access, final_cut


def connection(spec):
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE scenes(id INTEGER, project_id INTEGER, idx INTEGER, data TEXT)')
    c.execute('INSERT INTO scenes VALUES(1,1,20,?)', (json.dumps({'post_popup': spec}),))
    return c


def test_timeline_uses_measured_trimmed_clips_and_fade():
    c = connection({'asset_id': 432, 'at': 'end', 'seconds': 1.5, 'pop_sound': False})
    rows = [{'scene_id': 2, 'path': 'group_cut_19.mp4'}, {'scene_id': 1, 'path': 'trim20.mp4'}]
    with patch('core.ffmpeg_studio.probe_duration', side_effect=[3, 2]):
        plan = shot_popup.plan(c, 1, rows, ['a', 'b'], 'crossfade', .5)
    assert plan[0]['start_s'] == 3.0
    assert plan[0]['seconds'] == 1.5
    assert plan[0]['end_s'] == 4.5


def test_lost_shot_and_invalid_spec_are_yellow():
    c = connection({'asset_id': 432, 'seconds': 1.5})
    assert shot_popup.plan(c, 1, [], [], 'cut', .5)[0]['muc'] == 'vang'
    c.execute('UPDATE scenes SET data=?', (json.dumps({'post_popup': {'seconds': float('nan')}}),))
    with patch('core.ffmpeg_studio.probe_duration', return_value=2):
        assert shot_popup.plan(c, 1, [{'scene_id': 1, 'path': 'x'}], ['x'], 'cut', .5)[0]['muc'] == 'vang'


def test_green_key_only_connected_background():
    im = Image.new('RGBA', (20, 20), 'lime')
    for x in range(4, 16):
        for y in range(4, 16):
            im.putpixel((x, y), (255, 0, 0, 255))
    im.putpixel((10, 10), (0, 255, 0, 255))
    keyed = end_popup.remove_green_background(im)
    assert keyed.getpixel((0, 0))[3] == 0
    assert keyed.getpixel((10, 10))[3] == 255


def test_off_does_not_probe_or_modify(tmp_path):
    c = connection({'asset_id': 432})
    with patch('core.features.on', return_value=False), patch('core.ffmpeg_studio.probe_duration', side_effect=AssertionError):
        assert shot_popup.apply(c, 1, 'film', [], [], {}, 'tiktok') == []


def test_relative_asset_and_sound_resolve_outside_cwd(tmp_path, monkeypatch):
    icon = tmp_path / 'icon.png'
    sound = tmp_path / 'pop.wav'
    icon.write_bytes(b'image')
    sound.write_bytes(b'sound')
    monkeypatch.chdir(tmp_path.parent)
    cfg = {'items': [{'asset_id': 432}], 'local_root': str(tmp_path), 'sound': 'pop.wav'}
    c = sqlite3.connect(':memory:')
    c.execute('CREATE TABLE asset_images(asset_id, path, sort, id, status)')
    c.execute("INSERT INTO asset_images VALUES(432,'icon.png',0,1,'approved')")
    assert end_popup.resolve(c, cfg)[0]['path'] == str(icon)
    assert end_popup.pop_sound(None, cfg) == str(sound)


def test_tall_icon_frames_stay_inside_common_safe_box(tmp_path):
    icon = tmp_path / 'tall.png'
    Image.new('RGBA', (20, 400), (255, 0, 0, 255)).save(icon)
    box = {'left': .06, 'right': .18, 'top': .15, 'bottom': .36}
    count = end_popup.frames([{'path': str(icon), 'label': ''}], '', (320, 480), .5, str(tmp_path),
                             {'safe_box': box, 'shade': False})
    for k in range(count):
        with Image.open(tmp_path / f'p_{k:04d}.png') as im:
            bounds = im.getbbox()
        if bounds:
            assert bounds[0] >= 19 and bounds[2] <= 262
            assert bounds[1] >= 72 and bounds[3] <= 307


def test_missing_icon_warning_keeps_video(tmp_path):
    video = tmp_path / 'video.mp4'
    video.write_bytes(b'original')
    c = connection({'asset_id': 432, 'seconds': 1.5, 'pop_sound': False})
    with patch('core.features.on', return_value=True), patch('core.ffmpeg_studio.probe_duration', return_value=2), \
         patch('core.end_popup.resolve', side_effect=ValueError('không có ảnh')):
        report = shot_popup.apply(c, 1, str(video), [{'scene_id': 1, 'path': str(video)}], [str(video)],
                                  {'transition': 'cut', 'fade': .5}, 'tiktok')
    assert report[0]['muc'] == 'vang'
    assert 'không có ảnh' in report[0]['reasons'][0]
    assert video.read_bytes() == b'original'


def test_opt_in_only(monkeypatch):
    assert 'shot_popup' in features.OPT_IN_ONLY
    monkeypatch.delenv('FEATURE_SHOT_POPUP', raising=False)
    assert features.on('shot_popup') is False


def test_unauthorized_save_does_not_write():
    c = connection({'asset_id': 432})
    before = c.execute('SELECT data FROM scenes').fetchone()[0]
    with patch('core.access.need_edit', side_effect=access.AccessDenied('không được sửa')):
        with pytest.raises(access.AccessDenied):
            shot_popup.save(SimpleNamespace(conn=c), 1, 1, None)
    assert c.execute('SELECT data FROM scenes').fetchone()[0] == before
    with pytest.raises(ValueError):
        shot_popup.save(SimpleNamespace(conn=c), 2, 1, None)


def test_fingerprint_changes_with_image_spec_and_flag(tmp_path):
    c = connection({'asset_id': 432, 'seconds': 1.5, 'pop_sound': False})
    image = tmp_path / 'icon.png'
    image.write_bytes(b'first')
    p = SimpleNamespace(conn=c)
    with patch('core.features.on', return_value=True), patch('core.end_popup.resolve', return_value=[{'path': str(image)}]), \
         patch('core.subtitles.get_settings', return_value={'platform': 'tiktok'}):
        first = delivery._render_hash(p, 1, delivery.DEFAULTS)
        image.write_bytes(b'changed')
        assert delivery._render_hash(p, 1, delivery.DEFAULTS) != first
        with patch('core.features.on', return_value=False):
            assert delivery._render_hash(p, 1, delivery.DEFAULTS) == delivery.render_hash(delivery.DEFAULTS)


def test_real_render_popup_timing_sound_safe_box_and_green(tmp_path):
    ff = ffmpeg_studio.find_ffmpeg()
    a, b, video = [str(tmp_path / name) for name in ('group_cut20.mp4', 'trim21.mp4', 'film.mp4')]
    for path in (a, b):
        ffmpeg_studio.run([ff, '-y', '-f', 'lavfi', '-i', 'color=c=black:s=320x480:r=24:d=2',
                           *ffmpeg_studio._ENCODE, '-an', path])
    sound = str(tmp_path / 'pop.wav')
    ffmpeg_studio.run([ff, '-y', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=0.15', sound])
    icon = tmp_path / 'icon.png'
    im = Image.new('RGBA', (64, 64), 'lime')
    for x in range(10, 54):
        for y in range(10, 54):
            im.putpixel((x, y), (255, 0, 0, 255))
    im.save(icon)
    c = connection({'asset_id': 432, 'at': 'end', 'seconds': .5, 'pop_sound': sound, 'remove_green': True})
    rows = [{'scene_id': 1, 'path': a}, {'scene_id': 2, 'path': b}]
    settings = {'transition': 'crossfade', 'fade': .25}
    ffmpeg_studio.render_final([a, b], video, [2, 2], 'crossfade', .25, keep_audio=False, size=(320, 480))
    with patch('core.features.on', return_value=True), \
         patch('core.end_popup.resolve', return_value=[{'path': str(icon), 'label': '', 'remove_green': True}]):
        report = shot_popup.apply(c, 1, video, rows, [a, b], settings, 'tiktok', [2, 2])
    assert report[0]['muc'] == 'xanh'
    assert report[0]['render']['pops_s'] == [1.5]
    assert report[0]['render']['held_s'] == 0
    assert abs(ffmpeg_studio.probe_duration(video) - 3.75) < .08
    def pixels(t):
        raw = subprocess.check_output([ff, '-v', 'error', '-ss', str(t), '-i', video, '-frames:v', '1',
                                       '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        return Image.frombytes('RGB', (320, 480), raw)
    for t in (1.0, 2.3, 3.5):
        assert max(pixels(t).getextrema()[0]) < 12
    frame = pixels(1.9)
    red = [(x, y) for y in range(480) for x in range(320)
           if frame.getpixel((x, y))[0] > 100 and frame.getpixel((x, y))[1] < 60]
    assert red
    assert all(43 <= x < 277 and 38 <= y < 351 for x, y in red)
    assert max(frame.getextrema()[1]) < 60  # nền xanh thật đã mất sau ffmpeg
    raw = subprocess.check_output([ff, '-v', 'error', '-i', video, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'])
    samples = array.array('f', raw)
    def rms(start, end):
        values = samples[int(start * 48000):int(end * 48000)]
        return math.sqrt(sum(v*v for v in values) / len(values))
    assert rms(1.51, 1.62) > .01
    assert rms(1.1, 1.3) < .001
    assert rms(2.1, 2.3) < .001


def test_draft_passes_its_actual_scene_rows(tmp_path):
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(':memory:'))
    pid = p.create_project('Popup nháp', aspect='9:16')
    sid = p.create_scene(pid, 20, 'Quét sạch đội')
    video = tmp_path / 'group_cut20.mp4'
    video.write_bytes(b'local fixture')
    p.conn.execute('UPDATE scenes SET data=? WHERE id=?', (json.dumps({'post_popup': {'asset_id': 432}}), sid))
    p.conn.commit()
    with patch('core.takes.used', return_value={'state': 'pending_review', 'result_path': str(video)}), \
         patch('core.ffmpeg_studio.probe_duration', return_value=2), patch('core.ffmpeg_studio.probe_size', return_value=(320, 480)), \
         patch('core.ffmpeg_studio.render_final'), patch('core.features.on', return_value=True), \
         patch('core.shot_popup.apply', return_value=[{'idx': 20, 'muc': 'xanh'}]) as popup:
        res = final_cut.draft_preview(p, str(tmp_path), pid)
    assert popup.call_args.args[3] == [{'scene_id': sid, 'idx': 20, 'path': str(video)}]
    assert res['manifest']['shot_popup'][0]['idx'] == 20


@pytest.mark.parametrize('bad', [r'\\server\share\pop.wav', '//server/share/pop.wav', 'https://host/pop.wav', r'\\?\C:\pop.wav', 'NUL', r'C:\temp\CON.wav', r'C:\pop.wav:stream', [], 123])
def test_untrusted_sound_rejected_before_io(bad):
    with patch('core.end_popup.os.path.exists', side_effect=AssertionError('IO')):
        with pytest.raises(ValueError):
            end_popup.pop_sound(None, {'sound': bad, 'local_root': shot_popup.LOCAL_ROOT})


def test_missing_sound_cleans_work(tmp_path):
    work = tmp_path / 'work'
    work.mkdir()
    with patch('core.end_popup.resolve', return_value=[{'path': 'local.png', 'label': ''}]), \
         patch('core.ffmpeg_studio.probe_size', return_value=(320,480)), \
         patch('core.ffmpeg_studio.probe_duration', return_value=2), \
         patch('core.end_popup.tempfile.mkdtemp', return_value=str(work)), \
         patch('core.end_popup.pop_sound', side_effect=ValueError('thiếu tiếng')):
        with pytest.raises(ValueError):
            end_popup.apply(None, 'video', 'output', {'hold': False, 'seconds': 1, 'start_s': 1})
    assert not work.exists()


@pytest.mark.parametrize('bad', [[], 3, {'asset_id': True}, {'asset_id': 432, 'seconds': float('nan')}, {'asset_id':432,'pop_sound': []}])
def test_save_invalid_spec_keeps_scene(bad):
    c = connection({'asset_id':432})
    before = c.execute('SELECT data FROM scenes').fetchone()[0]
    with patch('core.access.need_edit'):
        with pytest.raises(ValueError):
            shot_popup.save(SimpleNamespace(conn=c),1,1,bad)
    assert c.execute('SELECT data FROM scenes').fetchone()[0] == before


def test_delivery_yellow_popup_keeps_manifest_and_diag():
    from tests.test_delivery_resolution import DeliveryEntryTests
    case = DeliveryEntryTests()
    case.setUp()
    try:
        with patch('core.ffmpeg_studio.probe_size', return_value=(720,1280)), \
             patch('core.ffmpeg_studio.probe_duration', return_value=2), \
             patch('core.ffmpeg_studio.render_final'), patch('core.features.on', return_value=False), \
             patch('core.shot_popup.apply', return_value=[{'idx':2,'muc':'vang','reasons':['ảnh mất']}]), \
             patch('core.ffmpeg_studio.needs_upscale', return_value=False), \
             patch('core.delivery._loudness', return_value=None):
            result = delivery.render(case.p,case.pid,case.data,None,render_size=(320,480))
        row = case.p.conn.execute('SELECT manifest FROM outputs WHERE id=?',(result['output_id'],)).fetchone()
        assert json.loads(row[0])['shot_popup'][0]['muc'] == 'vang'
        assert case.p.conn.execute("SELECT count(*) FROM diag_events WHERE code='shot_popup_warning'").fetchone()[0] == 1
    finally:
        case.doCleanups()


@pytest.mark.parametrize('raw', ['[]', 'null', '3'])
def test_malformed_scene_warning_and_save_no_write(raw):
    c = connection({'asset_id':432})
    c.execute('UPDATE scenes SET data=?',(raw,))
    with pytest.raises(ValueError):
        shot_popup.scene_data(raw)
    with patch('core.access.need_edit'):
        with pytest.raises(ValueError):
            shot_popup.save(SimpleNamespace(conn=c),1,1,None)
    assert c.execute('SELECT data FROM scenes').fetchone()[0] == raw
    assert shot_popup.plan(c,1,[],[],'cut',1)[0]['muc'] == 'vang'


@pytest.mark.parametrize('bad', ['https://host/clip.mp4', r'\\server\clip.mp4', r'\\?\C:\clip.mp4'])
def test_remote_timeline_never_probes(bad):
    c = connection({'asset_id':432})
    with patch('core.ffmpeg_studio.probe_duration',side_effect=AssertionError('probe')):
        assert shot_popup.plan(c,1,[{'scene_id':1,'path':bad}],[bad],'cut',1)[0]['muc'] == 'vang'


@pytest.mark.parametrize('bad', ['https://host/icon.png', r'\\server\icon.png', r'\\?\C:\icon.png'])
def test_asset_and_fingerprint_reject_before_io(bad):
    c = connection({'asset_id':432,'pop_sound':False})
    c.execute('CREATE TABLE asset_images(asset_id, path, sort, id, status)')
    c.execute("INSERT INTO asset_images VALUES(432,?,0,1,'approved')",(bad,))
    with patch('core.assets.get',side_effect=AssertionError('unguarded assets')), \
         patch('core.end_popup.os.path.exists',side_effect=AssertionError('IO')), \
         patch('builtins.open',side_effect=AssertionError('hash IO')), \
         patch('core.features.on',return_value=True), \
         patch('core.subtitles.get_settings',return_value={'platform':'tiktok'}):
        with pytest.raises(ValueError) as err:
            end_popup.resolve(c,{'items':[{'asset_id':432}],'local_root':shot_popup.LOCAL_ROOT})
        assert bad not in str(err.value)
        assert shot_popup.fingerprint(SimpleNamespace(conn=c),1)['items'][0]['content'] is None


@pytest.mark.parametrize('mode', ['start', 'renderer'])
def test_failure_cleans_work_and_staged_keeps_source(tmp_path, mode):
    c=connection({'asset_id':432,'pop_sound':False})
    source=tmp_path/'video.mp4'; source.write_bytes(b'original')
    work=tmp_path/'work'; work.mkdir()
    def fail_run(cmd):
        Path(cmd[-1]).write_bytes(b'partial')
        raise RuntimeError('renderer lỗi')
    from pathlib import Path
    with patch('core.features.on',return_value=True), \
         patch('core.ffmpeg_studio.probe_duration',return_value=2), \
         patch('core.ffmpeg_studio.probe_size',return_value=(320,480)), \
         patch('core.end_popup.resolve',return_value=[{'path':'icon','label':''}]), \
         patch('core.end_popup.tempfile.mkdtemp',return_value=str(work)), \
         patch('core.end_popup.frames'), patch('core.ffmpeg_studio.run',side_effect=fail_run):
        if mode == 'start':
            with pytest.raises(ValueError):
                end_popup.apply(c,str(source),str(source)+'.shot_popup.mp4',
                                {'hold':False,'start_s':3,'seconds':1,'sound':False})
        else:
            result=shot_popup.apply(c,1,str(source),[{'scene_id':1,'path':str(source)}],[str(source)],
                                    {'transition':'cut','fade':1},'tiktok')
            assert result[0]['muc']=='vang'
    assert source.read_bytes()==b'original'
    assert not work.exists()
    assert not Path(str(source)+'.shot_popup.mp4').exists()


@pytest.mark.parametrize('raw', ['[]', 'null', '3'])
def test_panel_malformed_json_shows_warning(raw):
    from contextlib import nullcontext
    from unittest.mock import Mock
    from dashboard.steps import step5
    c=connection({'asset_id':432})
    c.execute('UPDATE scenes SET data=?',(raw,))
    ui=SimpleNamespace(expander=lambda *a,**k:nullcontext(), caption=Mock(),warning=Mock(),
                       selectbox=lambda *a,**k:0)
    with patch.object(step5,'st',ui),patch('core.features.on',return_value=True), \
         patch.object(step5.C,'read_only',return_value=False),patch('core.assets.project_assets',return_value=[]):
        step5.shot_popup_panel(SimpleNamespace(conn=c),1)
    assert 'dữ liệu shot' in ui.warning.call_args.args[0]


def test_local_asset_keeps_approved_selector_and_skips_missing(tmp_path):
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE asset_images(asset_id,path,sort,id,status)')
    good=tmp_path/'good.png'; good.write_bytes(b'local')
    for i,(path,status) in enumerate([('rejected.png','rejected'),('pending.png','pending'),('missing.png','approved'),('good.png','claude_ok')]):
        c.execute('INSERT INTO asset_images VALUES(432,?,?,?,?)',(path,i,i,status))
    with patch('core.assets.get',side_effect=AssertionError('unguarded lookup')):
        assert end_popup.resolve(c,{'items':[{'asset_id':432}],'local_root':str(tmp_path)})[0]['path']==str(good)


@pytest.mark.parametrize('bad', ['https://host/video.mp4', r'\\server\video.mp4', r'\\?\C:\video.mp4', [], 123])
def test_output_video_rejected_before_any_io(bad):
    c=connection({'asset_id':432,'pop_sound':False})
    with patch('core.features.on',return_value=True), \
         patch('core.end_popup.os.path.exists',side_effect=AssertionError('exists')), \
         patch('core.ffmpeg_studio.probe_duration',side_effect=AssertionError('probe')), \
         patch('core.ffmpeg_studio.run',side_effect=AssertionError('run')):
        report=shot_popup.apply(c,1,bad,[{'scene_id':1,'path':'local.mp4'}],['local.mp4'],
                                {'transition':'cut','fade':1},'tiktok')
    assert report[0]['muc']=='vang'
    assert str(bad) not in report[0]['reasons'][0]


def test_relative_output_video_is_normalized_before_replace_and_cleanup(tmp_path, monkeypatch):
    from pathlib import Path
    c=connection({'asset_id':432,'pop_sound':False})
    monkeypatch.setattr(shot_popup,'LOCAL_ROOT',str(tmp_path))
    monkeypatch.chdir(tmp_path.parent)
    source=tmp_path/'video.mp4'; source.write_bytes(b'original')
    def render(conn,video,staged,cfg):
        assert video==str(source)
        assert staged==str(source)+'.shot_popup.mp4'
        Path(staged).write_bytes(b'popup')
        return {}
    with patch('core.features.on',return_value=True), \
         patch('core.ffmpeg_studio.probe_duration',return_value=2), \
         patch('core.end_popup.apply',side_effect=render):
        report=shot_popup.apply(c,1,'video.mp4',[{'scene_id':1,'path':'local.mp4'}],['local.mp4'],
                                {'transition':'cut','fade':1},'tiktok')
    assert report[0]['muc']=='xanh'
    assert source.read_bytes()==b'popup'
    assert not Path(str(source)+'.shot_popup.mp4').exists()
