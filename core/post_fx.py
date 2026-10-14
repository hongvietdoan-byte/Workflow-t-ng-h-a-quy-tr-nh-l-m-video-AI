"""Hậu kỳ 0 USD: loai, vi_tri, thoi_luong_s > 0, cuong_do trong (0, 1]."""
import json
import math
import os
import hashlib

from . import features, ffmpeg_studio as f


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate(spec, seconds):
    reasons = []
    if not _finite_number(seconds) or seconds <= 0:
        return {'muc': 'vang', 'reasons': ['không đo được thời lượng clip hợp lệ']}
    if not isinstance(spec, dict):
        return {'muc': 'vang', 'reasons': ['post_fx cần đối tượng đủ loại, vị trí, thời lượng, cường độ']}
    if spec.get('loai') not in ('nhieu_song', 'glitch', 'nhap_nhay'):
        reasons.append('loai phải là nhieu_song, glitch hoặc nhap_nhay')
    if spec.get('vi_tri') not in ('dau', 'cuoi', 'ca_shot'):
        reasons.append('vi_tri phải là dau, cuoi hoặc ca_shot')
    for key, upper in (('thoi_luong_s', seconds), ('cuong_do', 1)):
        value = spec.get(key)
        if not _finite_number(value) or not 0 < value <= upper:
            reasons.append(f'{key} phải là số > 0 và ≤ {upper:g}')
    return {'muc': 'vang' if reasons else 'xanh', 'reasons': reasons}


def filter_for(spec, seconds):
    start = seconds - spec['thoi_luong_s'] if spec['vi_tri'] == 'cuoi' else 0
    end = seconds if spec['vi_tri'] == 'ca_shot' else start + spec['thoi_luong_s']
    enabled = f"between(t,{start:.6f},{end:.6f})"
    strength = spec['cuong_do']
    if spec['loai'] == 'nhieu_song':
        return f"noise=alls={max(1, round(80 * strength))}:allf=t+u:enable='{enabled}'"
    if spec['loai'] == 'glitch':
        shift = max(1, round(16 * strength))
        return (f"rgbashift=rh={shift}:bh={-shift}:enable='{enabled}',"
                f"noise=alls={max(1, round(30 * strength))}:allf=t:enable='{enabled}'")
    return f"eq=brightness='{strength:.6f}*if(lt(mod(t*8,1),0.5),0.6,-0.6)':eval=frame:enable='{enabled}'"



def _output_path(work_dir, sid, source, spec, seconds):
    """Tên ổn định theo shot + toàn bộ đầu vào; không tái dùng cache, luôn ghi atomic.

    SHA nội dung nguồn tránh nhầm khi thay clip cùng tên/kích thước/mtime.
    Khóa gồm độ dài, filter và encode để thay công thức không đè kết quả khác.
    """
    content = hashlib.sha256()
    with open(source, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            content.update(chunk)
    blob = {'version': 1, 'sha256': content.hexdigest(),
            'spec': spec, 'seconds': seconds, 'filter': filter_for(spec, seconds), 'encode': f._ENCODE}
    key = hashlib.sha256(json.dumps(blob, sort_keys=True, ensure_ascii=False,
                                   separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    return os.path.abspath(os.path.join(work_dir, f'post_fx_{int(sid)}_{key}.mp4'))


def fingerprint(p, project_id):
    """Đ13v1 mục 4: what the cut's post effects depend on — None when the flag is off or no shot asks for one (the render key stays
    the old one); else the hash of every shot's `post_fx` (by shot number) + the filter version."""
    if not features.on('post_fx_render'):
        return None
    items = []
    for row in p.conn.execute('SELECT idx, data FROM scenes WHERE project_id=? ORDER BY idx', (project_id,)):
        try:
            data = json.loads(row['data'] or '{}')
        except ValueError:
            continue
        if isinstance(data, dict) and 'post_fx' in data:
            items.append([row['idx'], data['post_fx']])
    if not items:
        return None
    blob = json.dumps({'version': 1, 'items': items}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


def apply(p, rows, paths, durations, work_dir):
    """Đổi paths tại chỗ, không ghi đè clip gốc. Kết quả cho manifest/diag."""
    if not features.on('post_fx_render'):
        return []
    result = []
    for i, (row, seconds) in enumerate(zip([r for r in rows if r.get('path')], durations)):
        sid = row.get('scene_id')
        if not sid:
            continue
        entry = {'idx': row.get('idx'), 'scene_id': sid}
        try:
            stored = p.conn.execute('SELECT data FROM scenes WHERE id=?', (sid,)).fetchone()
            if stored is None:
                raise ValueError('không tìm thấy shot trong CSDL')
            data = json.loads(stored['data'] or '{}')
            if not isinstance(data, dict):
                raise ValueError('dữ liệu shot phải là đối tượng JSON')
            if 'post_fx' not in data:
                continue
            spec = data['post_fx']
            checked = validate(spec, seconds)
            entry.update(checked)
            if checked['muc'] == 'vang':
                result.append(entry)
                continue
            os.makedirs(work_dir, exist_ok=True)
            dst = _output_path(work_dir, sid, paths[i], spec, seconds)
            with f.atomic_output(dst) as staged:
                f.run([f.find_ffmpeg(), '-y', '-i', os.path.abspath(paths[i]), '-t', str(seconds), '-map', '0:v:0', '-map', '0:a?',
                       '-vf', filter_for(spec, seconds), *f._ENCODE, '-c:a', 'copy', staged])
            paths[i] = dst
            entry.update({'path': dst, 'spec': spec})
        except (OSError, ValueError, TypeError, f.FFmpegError, f.FFmpegNotFound) as exc:
            entry.update({'muc': 'vang', 'reasons': [f'không áp được post_fx: {str(exc)[:200]}']})
        result.append(entry)
    return result
