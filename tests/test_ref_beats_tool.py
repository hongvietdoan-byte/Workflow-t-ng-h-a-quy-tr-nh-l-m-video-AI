import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core import ffmpeg_studio as ff
from core.shot_lessons import ref_beats_path, ref_coverage, framing_amplitude
from tools import ref_beats as tool


@pytest.fixture(autouse=True)
def enable_tool(monkeypatch):
    monkeypatch.setattr(tool.features, 'on', lambda name: name == 'ref_beats_tool')


def filled():
    return {'nhip': [{'ten': 'dang_tay', 'tu_s': 0, 'den_s': 1,
                      'mo_ta': 'Dang tay', 'tu_khoa': ['dang tay'], 'bien_do': 'toan_than'}],
            'chi_tiet': [{'ten': 'nuoc_mat', 'mo_ta': 'Nước mắt', 'tu_khoa': ['nước mắt']}]}


def test_unfilled_template_still_warns():
    # Rà tích hợp Đợt 6: mẫu rỗng ghi đúng <video>.beats.json không được làm mất VÀNG "ref chưa ghi nhịp" ở đường chạy thật
    issues = ref_coverage(tool.template(5.0), {'image_prompt': 'x'})
    assert len(issues) == 1 and 'chưa điền' in issues[0]['msg']
    half = filled()
    half['chi_tiet'].append({'ten': 'khoi', 'mo_ta': 'Khói', 'tu_khoa': []})
    assert 'chưa điền' in ref_coverage(half, {'action': 'dang tay nước mắt'})[0]['msg']
    assert 'chưa điền' in ref_coverage({'nhip': [], 'chi_tiet': []}, {})[0]['msg']


def test_filled_compatible():
    doc = filled()
    tool.validate(doc, 1)
    assert len(ref_coverage(doc, {})) == 2
    assert framing_amplitude({'size': 'CU'}, doc=doc)
    with pytest.raises(ValueError):
        tool.validate(tool.template(1), 1)


@pytest.mark.parametrize('change', ['nan', 'negative', 'past_end', 'order', 'duplicate', 'words', 'empty'])
def test_invalid(change):
    doc = filled()
    if change == 'nan': doc['nhip'][0]['den_s'] = float('nan')
    if change == 'negative': doc['nhip'][0]['tu_s'] = -1
    if change == 'past_end': doc['nhip'][0]['den_s'] = 2
    if change == 'order': doc['nhip'][0]['tu_s'] = 1
    if change == 'duplicate': doc['chi_tiet'][0]['ten'] = 'dang_tay'
    if change == 'words': doc['nhip'][0]['tu_khoa'] = 'dang tay'
    if change == 'empty': doc['nhip'] = []
    with pytest.raises(ValueError): tool.validate(doc, 1)


def test_failure_preserves_outputs(tmp_path, monkeypatch):
    video = tmp_path / 'ref.mp4'
    video.write_bytes(b'bad')
    beats, jpg = Path(ref_beats_path(str(video))), video.with_suffix('.beats.jpg')
    for p in (beats, jpg): p.write_bytes(b'old')
    with pytest.raises(FileExistsError): tool.generate(video)
    monkeypatch.setattr(tool, 'duration_of', lambda *a, **k: 1)
    monkeypatch.setattr(ff, 'find_ffmpeg', lambda: 'ffmpeg')
    monkeypatch.setattr(tool, 'extract_frames', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('failed')))
    with pytest.raises(RuntimeError): tool.generate(video, force=True)
    assert beats.read_bytes() == jpg.read_bytes() == b'old'


def test_missing_and_url_fail_closed(tmp_path):
    assert tool.main([str(tmp_path / 'missing.mp4'), '--check']) == 1
    with pytest.raises(ValueError): tool.local_video('https://example.com/ref.mp4')


@pytest.mark.parametrize('force', [False, True])
def test_publish_failure_rolls_back_pair(tmp_path, monkeypatch, force):
    from PIL import Image
    video = tmp_path / 'ref.mp4'
    video.write_bytes(b'video')
    targets = [video.with_suffix('.beats.jpg'), Path(ref_beats_path(str(video)))]
    if force:
        for target in targets: target.write_bytes(b'old')
    monkeypatch.setattr(tool, 'duration_of', lambda *a: 1)
    monkeypatch.setattr(ff, 'find_ffmpeg', lambda: 'ffmpeg')
    def extract(video, folder, duration): Image.new('RGB', (64, 48), 'red').save(folder / 'frame_0001.jpg')
    monkeypatch.setattr(tool, 'extract_frames', extract)
    operation = 'replace' if force else 'link'
    original = getattr(tool.os, operation)
    def fail_second(source, target):
        if Path(source).name == 'beats.json': raise OSError('publish failed')
        return original(source, target)
    monkeypatch.setattr(tool.os, operation, fail_second)
    with pytest.raises(OSError): tool.generate(video, force)
    if force:
        assert all(p.read_bytes() == b'old' for p in targets)
    else:
        assert all(not p.exists() for p in targets)
    assert not list(tmp_path.glob('.ref-beats-*'))


def test_real_video_and_cli_from_other_directory(tmp_path):
    try: exe = ff.find_ffmpeg()
    except ff.FFmpegNotFound: pytest.skip('Thiếu ffmpeg')
    video = tmp_path / 'video có dấu.mp4'
    ff.run([exe, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x48:r=10:d=1', str(video)])
    tool.generate(video)
    from PIL import Image
    with Image.open(video.with_suffix('.beats.jpg')) as image:
        assert image.height > 48
        # Vùng chữ mốc giờ có điểm sáng, khác nền đen.
        assert image.crop((0, image.height - 24, image.width, image.height)).getbbox()
    beats = Path(ref_beats_path(str(video)))
    assert 'tu_khoa' in json.loads(beats.read_text(encoding='utf-8'))['nhip'][0]
    beats.write_text(json.dumps(filled(), ensure_ascii=False), encoding='utf-8')
    script = Path(tool.__file__).resolve()
    result = subprocess.run([sys.executable, str(script), str(video), '--check'], cwd=tmp_path,
                            capture_output=True, text=True, encoding='utf-8',
                            env={**os.environ, 'FEATURE_REF_BEATS_TOOL': '1', **_CP1252,
                                 'FEATURE_SETTINGS_FILE': str(tmp_path / 'feature_settings.json')})
    assert result.returncode == 0, result.stderr
    assert not ref_coverage(json.loads(beats.read_text(encoding='utf-8')), {'action': 'dang tay nước mắt'})

@pytest.mark.parametrize('amplitude', ['nua_tren', 'mat'])
def test_standard_amplitude(amplitude):
    doc = filled()
    doc['nhip'][0]['bien_do'] = amplitude
    tool.validate(doc, 1)

@pytest.mark.parametrize('field', ['tu_s', 'den_s', 'duration'])
@pytest.mark.parametrize('value', [10**400, True])
def test_invalid_numeric_no_overflow(field, value):
    doc = filled()
    duration = 1
    if field == 'duration': duration = value
    else: doc['nhip'][0][field] = value
    with pytest.raises(ValueError): tool.validate(doc, duration)

def test_sheet_limits():
    assert tool.sheet_size(48, 240, 600) == (240, 31680)
    with pytest.raises(ValueError): tool.sheet_size(240, 960, 600)
    with pytest.raises(ValueError): tool.sheet_size(240, 240, 601)

def test_extract_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(ff, 'find_ffmpeg', lambda: 'ffmpeg')
    def timeout(cmd, **kwargs):
        assert kwargs['timeout'] == 60
        assert cmd[cmd.index('-frames:v') + 1] == '3'
        assert 'force_original_aspect_ratio=decrease' in cmd[cmd.index('-vf') + 1]
        raise subprocess.TimeoutExpired(cmd, kwargs['timeout'])
    monkeypatch.setattr(tool.subprocess, 'run', timeout)
    with pytest.raises(subprocess.TimeoutExpired): tool.extract_frames(tmp_path / 'v.mp4', tmp_path, 1)

def test_off_no_action(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool.features, 'on', lambda name: False)
    def forbidden(*a, **k): raise AssertionError('Không được đọc nguồn khi cờ tắt')
    monkeypatch.setattr(tool, 'local_video', forbidden)
    with pytest.raises(ValueError, match='FEATURE_REF_BEATS_TOOL=1'): tool.generate(tmp_path / 'v.mp4')
    assert tool.main([str(tmp_path / 'v.mp4'), '--check']) == 1
    assert 'FEATURE_REF_BEATS_TOOL=1' in capsys.readouterr().err

@pytest.mark.parametrize('force', [False, True])
def test_output_directory_guard(tmp_path, monkeypatch, force):
    video = tmp_path / 'ref.mp4'
    video.write_bytes(b'video')
    video.with_suffix('.beats.jpg').mkdir()
    def forbidden(*a): raise AssertionError('Không chạy ffmpeg khi đầu ra là thư mục')
    monkeypatch.setattr(tool, 'duration_of', forbidden)
    with pytest.raises(ValueError, match='thư mục'): tool.generate(video, force)

@pytest.mark.parametrize('mode', ['extra_frames', 'timeout'])
def test_resource_failure_preserves_pair(tmp_path, monkeypatch, mode):
    from PIL import Image
    video = tmp_path / 'ref.mp4'
    video.write_bytes(b'video')
    outputs = [video.with_suffix('.beats.jpg'), Path(ref_beats_path(str(video)))]
    for path in outputs: path.write_bytes(b'old')
    monkeypatch.setattr(tool, 'duration_of', lambda *a: 1)
    def extract(video, folder, duration):
        if mode == 'timeout': raise subprocess.TimeoutExpired('ffmpeg', 60)
        for index in range(3): Image.new('RGB', (16, 16)).save(folder / f'frame_{index:04d}.jpg')
    monkeypatch.setattr(tool, 'extract_frames', extract)
    with pytest.raises((ValueError, subprocess.TimeoutExpired)): tool.generate(video, force=True)
    assert all(path.read_bytes() == b'old' for path in outputs)
    assert not list(tmp_path.glob('.ref-beats-*'))

def test_huge_integer_check_returns_clear_error(tmp_path, monkeypatch, capsys):
    video = tmp_path / 'ref.mp4'
    video.write_bytes(b'video')
    doc = filled()
    doc['nhip'][0]['den_s'] = 10**400
    Path(ref_beats_path(str(video))).write_text(json.dumps(doc), encoding='utf-8')
    monkeypatch.setattr(tool, 'duration_of', lambda *a: 1)
    assert tool.main([str(video), '--check']) == 1
    assert 'Mốc giờ phải là số hữu hạn' in capsys.readouterr().err

def test_unknown_amplitude_rejected():
    doc = filled()
    doc['nhip'][0]['bien_do'] = 'cuc_bo'
    with pytest.raises(ValueError, match='bien_do'): tool.validate(doc, 1)

def test_real_portrait_bounded(tmp_path):
    try: exe = ff.find_ffmpeg()
    except ff.FFmpegNotFound: pytest.skip('Thiếu ffmpeg')
    video = tmp_path / 'portrait.mp4'
    ff.run([exe, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x256:r=10:d=1', str(video)])
    tool.generate(video)
    from PIL import Image
    with Image.open(video.with_suffix('.beats.jpg')) as sheet:
        assert sheet.width <= 480 and sheet.height <= 264

# 13/10: a Windows console piped in cp1252 (no PYTHONUTF8) made the Vietnamese lines fail — the CLI must print UTF-8 anyway
_CP1252 = {'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0'}


def test_default_flag_off_cli_before_source_access(tmp_path):
    assert tool.features.FEATURES['ref_beats_tool']['verified'] is False
    script = Path(tool.__file__).resolve()
    env = {**os.environ, 'FEATURE_REF_BEATS_TOOL': '0', **_CP1252, 'FEATURE_SETTINGS_FILE': str(tmp_path / 'settings.json')}
    result = subprocess.run([sys.executable, str(script), str(tmp_path / 'missing.mp4')],
                            capture_output=True, text=True, encoding='utf-8', env=env)
    assert result.returncode == 1
    assert 'FEATURE_REF_BEATS_TOOL=1' in result.stderr
    assert not list(tmp_path.glob('*.beats.*'))
