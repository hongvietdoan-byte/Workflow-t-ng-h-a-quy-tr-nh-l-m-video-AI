"""Popup cuối từng shot trên timeline bản dựng thật; xử lý cục bộ, 0 USD."""
import json
import math
import os
import hashlib

from . import end_popup, features, ffmpeg_studio, subtitles

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError('popup phải là đối tượng cấu hình')
    aid = spec.get('asset_id')
    if isinstance(aid, bool) or not isinstance(aid, int) or aid <= 0:
        raise ValueError('mã ảnh Kho phải là số nguyên dương')
    if spec.get('at', 'end') != 'end':
        raise ValueError('popup cần vị trí cuối shot')
    seconds = spec.get('seconds', 1.5)
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0 < seconds <= 8:
        raise ValueError('giây popup phải > 0 và ≤ 8')
    sound = spec.get('pop_sound')
    if sound is not None and sound is not True and sound is not False:
        end_popup.local_path(sound, LOCAL_ROOT)
    if 'remove_green' in spec and not isinstance(spec['remove_green'], bool):
        raise ValueError('tách nền xanh phải là bật hoặc tắt')
    return float(seconds)


def scene_data(raw):
    data = json.loads(raw or '{}')
    if not isinstance(data, dict):
        raise ValueError('dữ liệu shot phải là đối tượng')
    return data


def save(p, project_id, scene_id, spec):
    from . import access
    access.need_edit(p, project_id, 'lưu popup theo shot')
    row = p.conn.execute('SELECT data FROM scenes WHERE id=? AND project_id=?', (scene_id, project_id)).fetchone()
    if row is None:
        raise ValueError('shot không thuộc dự án')
    data = scene_data(row['data'])
    if spec is None:
        data.pop('post_popup', None)
    else:
        validate(spec)
        data['post_popup'] = spec
    with p.conn:
        p.conn.execute('UPDATE scenes SET data=? WHERE id=? AND project_id=?',
                       (json.dumps(data, ensure_ascii=False), scene_id, project_id))


def fingerprint(p, project_id):
    """Cờ TẮT giữ hash cũ; bật: theo dõi cấu hình, nội dung ảnh/tiếng pop và nền tảng."""
    if not features.on('shot_popup'):
        return None
    items = []
    def digest(path):
        if path is None:
            return None
        try:
            with open(end_popup.local_path(path, LOCAL_ROOT), 'rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest()
        except (OSError, TypeError):
            return None
    for row in p.conn.execute('SELECT id, data FROM scenes WHERE project_id=? ORDER BY idx', (project_id,)):
        try:
            spec = json.loads(row['data'] or '{}').get('post_popup')
            if not spec:
                continue
            validate(spec)
            sound_spec = spec.get('pop_sound')
            cfg = {'items': [{'asset_id': spec.get('asset_id')}], 'sound': None if sound_spec is True else sound_spec,
                   'local_root': LOCAL_ROOT}
            try:
                image = end_popup.resolve(p.conn, cfg)[0]['path']
                sound = end_popup.pop_sound(p.conn, cfg)
                content = [digest(image), digest(sound)]
            except Exception:
                content = None
            items.append({'scene_id': row['id'], 'spec': spec, 'content': content})
        except (ValueError, TypeError, AttributeError):
            items.append({'scene_id': row['id'], 'invalid': row['data']})
    return {'enabled': True, 'items': items, 'platform': subtitles.get_settings(p, project_id)['platform']}


def plan(conn, project_id, rows, paths, transition, fade, durations=None):
    usable = [r for r in rows if r.get('path')]
    overlap = float(fade) if transition in ffmpeg_studio.OVERLAP_STYLES else 0.0
    clock, timeline = 0.0, {}
    unknown = False
    for i, (row, path) in enumerate(zip(usable, paths)):
        try:
            seconds = ffmpeg_studio.probe_duration(end_popup.local_path(path, LOCAL_ROOT))
        except ValueError:
            seconds = None
        # xfade dùng offsets durations; cut nối toàn bộ tệp. Shot cuối giữ đuôi tệp thật.
        if overlap and durations is not None and i < len(paths) - 1 and seconds:
            seconds = min(seconds, float(durations[i]))
        if not seconds or not math.isfinite(seconds) or seconds <= 0:
            unknown = True
        start = clock - (overlap if i else 0)
        if not unknown:
            timeline.setdefault(row.get('scene_id'), []).append((start, start + seconds, seconds))
            clock = start + seconds
    out = []
    for row in conn.execute('SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx', (project_id,)):
        try:
            data = scene_data(row['data'])
            if not isinstance(data, dict):
                raise ValueError('dữ liệu shot phải là đối tượng')
        except (ValueError, TypeError) as exc:
            out.append({'scene_id': row['id'], 'idx': row['idx'], 'muc': 'vang', 'reasons': [f'không đọc được dữ liệu shot: {exc}']})
            continue
        if 'post_popup' not in data:
            continue
        spec = data['post_popup']
        if spec is None or spec is False:
            continue
        entry = {'scene_id': row['id'], 'idx': row['idx']}
        try:
            times = timeline.get(row['id'], [])
            if len(times) != 1:
                raise ValueError('shot không có trong bản dựng hoặc chưa đo được timeline/shot bị lặp')
            seconds = validate(spec)
            start, end, duration = times[0]
            seconds = min(seconds, duration)
            cfg = {'items': [{'asset_id': spec['asset_id'], 'label': '', 'remove_green': spec.get('remove_green') is True}],
                   'headline': '', 'hold': False, 'shade': False, 'seconds': seconds, 'start_s': end - seconds,
                   'sound': None if spec.get('pop_sound') is True else spec.get('pop_sound'), 'local_root': LOCAL_ROOT}
            entry.update(muc='xanh', start_s=end - seconds, end_s=end, seconds=seconds, cfg=cfg)
        except (TypeError, ValueError) as exc:
            entry.update(muc='vang', reasons=[str(exc)])
        out.append(entry)
    return out


def apply(conn, project_id, video, rows, paths, settings, platform, durations=None):
    if not features.on('shot_popup'):
        return []
    try:
        video = end_popup.local_path(video, LOCAL_ROOT)
    except ValueError as exc:
        result = plan(conn, project_id, [], [], 'cut', 0)
        for entry in result:
            entry.update(muc='vang', reasons=[f'không ghép được popup: {exc}'])
        return result
    result = plan(conn, project_id, rows, paths, settings['transition'], settings['fade'], durations)
    for entry in result:
        if entry['muc'] == 'vang':
            continue
        staged = video + '.shot_popup.mp4'
        cfg = entry.pop('cfg')
        cfg['safe_box'] = subtitles.safe_box(platform)
        try:
            entry['render'] = end_popup.apply(conn, video, staged, cfg)
            os.replace(staged, video)
            note = entry['render'].get('sound_note')
            if note:
                entry.update(muc='vang', reasons=[note])
        except Exception as exc:  # giữ bản dựng còn lại, báo VÀNG qua người gọi
            entry.update(muc='vang', reasons=[f'không ghép được popup: {str(exc)[:200]}'])
        finally:
            if os.path.exists(staged):
                os.remove(staged)
    return result
