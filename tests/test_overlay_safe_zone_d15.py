from PIL import Image
from core import delivery, end_popup, features, overlay_safe_zone
import json
import pytest


def test_off_preserves_pixels_but_warns(monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '0')
    image = Image.new('RGBA', (108, 192))
    image.paste('white', (0, 0, 80, 20))
    out, note = overlay_safe_zone.place(image, 'tiktok')
    assert out.tobytes() == image.tobytes()
    assert note['muc'] == 'vang' and note['suggested'] == [15, 16, 93, 140]


def test_on_fits_oversized_overlay(monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    image = Image.new('RGBA', (108, 192), 'white')
    out, note = overlay_safe_zone.place(image, 'chung')
    x, y, right, bottom = out.getbbox()
    assert x >= 7 and y >= 29 and right <= 88 and bottom <= 122
    assert note['muc'] == 'vang' and note['adjusted'] is True


def test_ai_label_inside_selected_box(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    path = delivery.ai_label_picture(360, 640, 'AI', str(tmp_path / 'ai.png'), platform='chung')
    with Image.open(path) as image:
        x, y, right, bottom = image.getbbox()
        assert x >= 22 and y >= 96 and right <= 295 and bottom <= 409


def test_flag_opt_in():
    assert 'overlay_safe_zone' in features.OPT_IN_ONLY
    assert not features.FEATURES['overlay_safe_zone']['verified']


def test_popup_all_animation_frames_fit(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    icon = tmp_path / 'icon.png'
    Image.new('RGBA', (80, 180), 'white').save(icon)
    count = end_popup.frames([{'path': str(icon), 'label': 'HÀNH ĐỘNG'}], 'SẮP RA MẮT',
                             (360, 640), 1., str(tmp_path), {'shade': False, 'platform': 'chung'})
    safe = overlay_safe_zone.bounds((360, 640), 'chung')
    for k in range(count):
        with Image.open(tmp_path / f'p_{k:04d}.png') as image:
            rect = image.getbbox()
            if rect:
                assert rect[0] >= safe[0] and rect[1] >= safe[1]
                assert rect[2] <= safe[2] and rect[3] <= safe[3]


def test_no_popup_hash_unchanged_when_flag_changes(monkeypatch):
    class Project:
        conn = None
    monkeypatch.setattr('core.shot_popup.fingerprint', lambda *_: None)
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '0')
    off = delivery._render_hash(Project(), 1, delivery.DEFAULTS)
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    assert delivery._render_hash(Project(), 1, delivery.DEFAULTS) == off


def test_flag_registered_in_area():
    from pathlib import Path
    areas = json.loads((Path(__file__).parents[1] / 'devsys/areas.json').read_text(encoding='utf8'))
    assert 'overlay_safe_zone' in next(a for a in areas['areas'] if a['id'] == 'step5')['flags']


@pytest.mark.parametrize('kind', ['ai', 'card'])
def test_on_retains_long_content_before_fitting(kind, tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    original = overlay_safe_zone.place
    captured = []
    def capture(image, *args, **kwargs):
        captured.append(image.copy())
        return original(image, *args, **kwargs)
    monkeypatch.setattr(overlay_safe_zone, 'place', capture)
    path = str(tmp_path / 'long.png')
    if kind == 'ai':
        delivery.ai_label_picture(360, 640, 'W' * 300, path)
    else:
        delivery.card_picture(360, 640, {'title': 'W' * 300, 'subtitle': 'second line'}, path)
    # Glyphs must be drawn completely BEFORE fitting, not recovered from a clipped 360px canvas.
    assert captured[0].getbbox()[2] - captured[0].getbbox()[0] > 3000
    with Image.open(path) as result:
        assert result.size == (360, 640)


@pytest.mark.parametrize('kind', ['ai', 'card'])
def test_on_retains_many_lines_before_fitting(kind, tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    original = overlay_safe_zone.place
    boxes = []
    def capture(image, *args, **kwargs):
        boxes.append(image.getbbox())
        return original(image, *args, **kwargs)
    monkeypatch.setattr(overlay_safe_zone, 'place', capture)
    path = str(tmp_path / 'lines.png')
    text = '\n'.join(['Line W'] * 100)
    if kind == 'ai':
        delivery.ai_label_picture(360, 640, text, path)
    else:
        delivery.card_picture(360, 640, {'title': text}, path)
    assert boxes[0][3] - boxes[0][1] > 1200
    with Image.open(path) as result:
        assert result.size == (360, 640)


@pytest.mark.parametrize('on', ['0', '1'])
def test_export_crop_reports_adjustments(on, tmp_path, monkeypatch):
    from core.db import connect
    from core.pipeline import Pipeline
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', on)
    p = Pipeline(connect())
    pid = p.create_project('fake')
    source = tmp_path / 'final.mp4'
    source.write_bytes(b'fake')
    final = delivery.record(p, pid, 'final', str(source), None, {})
    label = delivery.record(p, pid, 'ailabel', str(source), final, {'text': 'AI'})
    monkeypatch.setattr(delivery, '_require_output_sources', lambda *_: None)
    monkeypatch.setattr(delivery.ffmpeg_studio, 'probe_size', lambda *_: (360, 640))
    def write(video, output, *args, **kwargs):
        from pathlib import Path
        Path(output).write_bytes(b'fake export')
        return {'path': output}
    monkeypatch.setattr(delivery.ffmpeg_studio, 'resize_to_size', write)
    monkeypatch.setattr(delivery.ffmpeg_studio, 'overlay_still', lambda video, png, output: write(video, output)['path'])
    result = delivery.export_layer(p, pid, str(tmp_path), {'w': 360, 'h': 360, 'fit': 'crop'}, label)
    manifest = json.loads(p.conn.execute('SELECT manifest FROM outputs WHERE id=?', (result['output_id'],)).fetchone()[0])
    assert manifest['safe_zone'][0]['muc'] == 'vang'
    assert manifest['safe_zone'][0]['adjusted'] is (on == '1')
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='overlay_safe_zone'").fetchone()[0] > 0


def test_popup_overshoot_keeps_complete_headline(tmp_path, monkeypatch):
    monkeypatch.setenv('FEATURE_OVERLAY_SAFE_ZONE', '1')
    monkeypatch.setattr(end_popup, '_text_block', lambda *_: Image.new('RGBA', (345, 80), 'white'))
    monkeypatch.setattr(end_popup, '_scale', lambda *_: 1.15)
    original = overlay_safe_zone.place
    widths = []
    def capture(image, *args, **kwargs):
        bbox = image.getbbox()
        widths.append(bbox[2] - bbox[0])
        return original(image, *args, **kwargs)
    monkeypatch.setattr(overlay_safe_zone, 'place', capture)
    end_popup.frames([], 'headline', (360, 640), .05, str(tmp_path), {'shade': False})
    assert widths == [int(345 * 1.15)]
