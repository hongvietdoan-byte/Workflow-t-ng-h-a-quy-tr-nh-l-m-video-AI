"""Tạo dải ảnh 0,5 giây và mẫu nhịp ref để người duyệt điền (không gọi API)."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import ffmpeg_studio as ff
from core import features
from core.shot_lessons import ref_beats_path


def require_enabled():
    if not features.on('ref_beats_tool'):
        raise ValueError('Công cụ nhịp ref đang TẮT; bật FEATURE_REF_BEATS_TOOL=1 để dùng CLI.')


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def sheet_size(width, height, count):
    # 600 khung tối đa; không cấp phát ảnh vượt khoảng 120 MB RGB.
    if not 0 < count <= 600 or not 0 < width <= 240 or not 0 < height <= 240:
        raise ValueError('Số khung hoặc kích thước khung vượt giới hạn dải ảnh.')
    cols = min(5, count)
    size = cols * width, math.ceil(count / cols) * (height + 24)
    if max(size) > 65500 or size[0] * size[1] > 40_000_000:
        raise ValueError('Dải ảnh vượt giới hạn JPG/pixel; hãy cắt ref ngắn hơn.')
    return size


def extract_frames(video, folder, duration):
    # Một khung dư để phát hiện metadata ngắn hơn phần video thực.
    limit = math.ceil(duration * 2)
    cmd = [ff.find_ffmpeg(), '-y', '-v', 'error', '-protocol_whitelist', 'file', '-i', str(video),
           '-vf', 'fps=2:start_time=0,scale=240:240:force_original_aspect_ratio=decrease:force_divisible_by=2',
           '-frames:v', str(limit + 1), '-q:v', '3', str(folder / 'frame_%04d.jpg')]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    if proc.returncode:
        raise ff.FFmpegError(proc.stderr[-2000:])


def template(duration):
    """Ô chữ rỗng có chủ ý: mẫu chưa duyệt luôn bị --check từ chối."""
    return {'nhip': [{'ten': '', 'tu_s': 0, 'den_s': duration, 'mo_ta': '',
                      'tu_khoa': [], 'bien_do': ''}], 'chi_tiet': [],
            '_huong_dan': 'Xem dải ảnh, chia nhịp và điền tên/mô tả/từ khóa. '
                          'bien_do: toan_than, nua_tren hoặc mat; chi_tiet: [{ten, mo_ta, tu_khoa}].'}


def validate(doc, duration):
    """Kiểm tệp đã điền, tránh nhịp thiếu từ khóa lọt qua ref_coverage."""
    if not finite_number(duration) or duration <= 0:
        raise ValueError('Không đo được thời lượng video hợp lệ.')
    if not isinstance(doc, dict) or not isinstance(doc.get('nhip'), list) or not doc['nhip']:
        raise ValueError('nhip phải là danh sách có ít nhất một nhịp đã điền.')
    if not isinstance(doc.get('chi_tiet'), list):
        raise ValueError('chi_tiet phải là danh sách (có thể rỗng).')
    names, end = set(), 0
    for kind in ('nhip', 'chi_tiet'):
        for item in doc[kind]:
            if not isinstance(item, dict):
                raise ValueError(f'{kind}: mỗi mục phải là object.')
            for key in ('ten', 'mo_ta'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f'{kind}: thiếu {key}.')
            name = item['ten'].strip().casefold()
            if name in names:
                raise ValueError(f'Tên nhịp/chi tiết trùng: {item["ten"]}.')
            names.add(name)
            words = item.get('tu_khoa')
            if not isinstance(words, list) or not words or any(not isinstance(w, str) or not w.strip() for w in words):
                raise ValueError(f'{item["ten"]}: tu_khoa cần danh sách chữ không rỗng.')
            if kind == 'nhip':
                start, stop = item.get('tu_s'), item.get('den_s')
                if any(not finite_number(t) for t in (start, stop)):
                    raise ValueError('Mốc giờ phải là số hữu hạn.')
                if not 0 <= end <= start < stop <= duration + 0.001:
                    raise ValueError('Nhịp sai thứ tự, chồng lấn hoặc vượt thời lượng video.')
                end = stop
                if item.get('bien_do') not in ('toan_than', 'nua_tren', 'mat'):
                    raise ValueError('bien_do phải là toan_than, nua_tren hoặc mat.')


def local_video(value):
    if '://' in str(value):
        raise ValueError('Chỉ nhận video là tệp cục bộ, không nhận URL.')
    path = Path(value).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Video phải là tệp cục bộ.')
    return path


def duration_of(video):
    # probe_duration chung không giới hạn protocol; ref không tin cậy cần chặn mạng cả lúc đo.
    proc = subprocess.run([ff.find_ffmpeg(), '-hide_banner', '-protocol_whitelist', 'file', '-i', str(video)],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
    match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', proc.stderr or '')
    duration = (int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])) if match else None
    if duration is None or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Không đo được thời lượng video; kiểm ffmpeg và tệp nguồn.')
    return duration


def generate(video, force=False):
    require_enabled()
    from PIL import Image, ImageDraw
    video = local_video(video)
    targets = [video.with_suffix('.beats.jpg'), Path(ref_beats_path(str(video)))]
    if video in targets:
        raise ValueError('Đường dẫn đầu ra trùng video nguồn.')
    if any(p.exists() and not p.is_file() for p in targets):
        raise ValueError('Đầu ra đang là thư mục hoặc không phải tệp; không ghi đè.')
    if any(p.exists() for p in targets) and not force:
        raise FileExistsError('Dải ảnh hoặc tệp nhịp đã có; dùng --force để tạo lại cả hai.')
    duration = duration_of(video)
    # Giới hạn kích thước dải ảnh, báo rõ thay vì âm thầm cắt bớt khung.
    if duration > 300:
        raise ValueError('Video quá 300 giây; hãy cắt đoạn ref trước khi tạo dải ảnh.')
    with tempfile.TemporaryDirectory(prefix='.ref-beats-', dir=video.parent) as folder:
        temp = Path(folder)
        # protocol_whitelist chặn playlist/nguồn lồng tham chiếu mạng.
        extract_frames(video, temp, duration)
        frames = sorted(temp.glob('frame_*.jpg'))
        if not frames:
            raise ValueError('Không trích được khung hình video.')
        if len(frames) > math.ceil(duration * 2):
            raise ValueError('Số khung thực vượt thời lượng đã đo; kiểm hoặc cắt lại video ref.')
        with Image.open(frames[0]) as first:
            width, height = first.size
        cols = min(5, len(frames))
        sheet = Image.new('RGB', sheet_size(width, height, len(frames)), 'black')
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(frames):
            x, y = index % cols * width, index // cols * (height + 24)
            with Image.open(frame) as image:
                sheet.paste(image, (x, y))
            seconds = index * 0.5
            draw.text((x + 5, y + height + 5), f'{int(seconds // 60):02d}:{seconds % 60:04.1f}', fill='white')
        sheet.save(temp / 'sheet.jpg', quality=90)
        (temp / 'beats.json').write_text(json.dumps(template(duration), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        staged = [temp / 'sheet.jpg', temp / 'beats.json']
        # Sao lưu trong thư mục tạm trước publish; lỗi đầu ra thứ hai phục hồi cả cặp.
        backups, published = {}, []
        try:
            for target in targets:
                if target.exists():
                    if not target.is_file():
                        raise ValueError(f'Đầu ra không phải tệp: {target}')
                    if not force:
                        raise FileExistsError(f'Tệp vừa được tạo: {target}')
                    backup = temp / (target.name + '.backup')
                    os.replace(target, backup)
                    backups[target] = backup
            for source, target in zip(staged, targets):
                if force:
                    os.replace(source, target)
                else:
                    # Link tạo tên nguyên tử và không ghi đè file xuất hiện đồng thời.
                    os.link(source, target)
                published.append(target)
        except Exception:
            for target in published:
                target.unlink()
            for target, backup in backups.items():
                os.replace(backup, target)
            raise
    return targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', help='Video cục bộ; đầu ra cạnh video (.beats.jpg, .beats.json)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--force', action='store_true', help='Tạo lại cả dải ảnh và mẫu nhịp')
    group.add_argument('--check', action='store_true', help='Chỉ kiểm tệp nhịp đã điền, không ghi đầu ra')
    args = parser.parse_args(argv)
    try:
        require_enabled()
        video = local_video(args.video)
        if args.check:
            path = Path(ref_beats_path(str(video)))
            validate(json.loads(path.read_text(encoding='utf-8')), duration_of(video))
            print(f'Tệp nhịp hợp lệ: {path}')
        else:
            outputs = generate(video, args.force)
            print(f'Đã tạo {outputs[0]} và mẫu {outputs[1]}; điền mẫu rồi chạy --check.')
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired, ff.FFmpegError, ff.FFmpegNotFound) as exc:
        print(f'Lỗi: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
