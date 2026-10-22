"""Cue SFX cục bộ 0 USD; hoạt động toàn khung KHÔNG nhận diện động tác."""
import json
import math
import re

from . import features

BEATS = ('bat_dau', 'dinh', 'ket_thuc')
# Chỉ nhãn đã nghe từ catalog sfx_plan; tuyệt đối không chọn theo tên file.
LABELS = {
    'footstep': ('Walk, footsteps', 'Run'),
    'whoosh': ('Whoosh, swoosh, swish', 'Swoosh'),
    'impact': ('Thump, thud', 'Whack, thwack', 'Slap, smack', 'Impact'),
    'rustle': ('Rustle', 'Scrape', 'Rub'),
    'transform': ('Whoosh, swoosh, swish', 'Steam'),
    'hiccup': ('Hiccup',),
    'touch': ('Tap', 'Tick'),
    'noise': ('Static', 'White noise', 'Pink noise'),
}
ACTIONS = {
    'footstep': r'\b(?:walk(?:s|ing)?|run(?:s|ning)?|bước chân|đi bộ|chạy)\b',
    'whoosh': r'\b(?:vút|whoosh|swoosh|swish|lao)\b',
    'impact': r'\b(?:ngã|nga|fall(?:s|ing)?|fell|impact)\b',
    'rustle': r'\b(?:bò|trườn|truon|bám|crawl(?:s|ing)?|cling(?:s|ing)?|scrape)\b',
    'transform': r'\b(?:biến hình|bien_hinh|transform(?:s|ing)?|morph(?:s|ing)?)\b',
    'hiccup': r'\b(?:nấc|hiccup(?:s|ping)?)\b',
    'touch': r'\b(?:nhích|chạm|touch(?:es|ing)?|tap(?:s|ping)?|nudge(?:s|ing)?)\b',
    'noise': r'\b(?:glitch|nhiễu sóng|nhieu_song|nhấp nháy|nhap_nhay)\b',
}


def finite(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def action_text(value):
    """Không lấy lời thoại, tên người hay trường nhìn/che làm động tác."""
    from .assets import _without_spoken_lines
    if isinstance(value, dict):
        return ' '.join('crawl' if k == 'tu_the' and value[k] == 'bo' else action_text(value[k])
                        for k in ('action', 'hanh_dong', 'mo_ta', 'tu_the', 'cham_dat') if k in value)
    if isinstance(value, list):
        return ' '.join(action_text(v) for v in value)
    return _without_spoken_lines(value) if isinstance(value, str) else ''


def kinds(text):
    found = set()
    for clause in re.split(r'[.!?;\n]', text.lower().replace('_', ' ')):
        if re.search(r'\b(?:no|not|without|avoid|không|tránh|đừng)\b', clause):
            continue
        for kind, pattern in ACTIONS.items():
            if re.search(pattern.replace('_', ' '), clause):
                found.add(kind)
    return found


def activity(row, warnings):
    from . import clip_measure
    result = {'scene': row['idx'], 'frame_activity_peak_s': None,
              'semantic_action_measured': False}
    try:
        if not row.get('clip_path'):
            raise ValueError('thiếu clip')
        values, fps, same = clip_measure.motion_series(row['clip_path'])
        if (not finite(fps, True) or not isinstance(values, (list, tuple)) or not values
                or not isinstance(same, (list, tuple)) or len(values) != len(same)
                or any(not finite(v) for v in values)
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not -1 <= v <= 1 for v in same)):
            raise ValueError('dải đo thiếu hoặc không hợp lệ')
        peak = (max(range(len(values)), key=values.__getitem__) + 1) / fps
        if peak > row['length'] or max(values) <= .15:
            raise ValueError('clip tĩnh hoặc dải đo lệch thời lượng')
        result['frame_activity_peak_s'] = round(peak, 3)
    except Exception as ex:
        warnings.append(f"Shot {row['idx']}: không đo được hoạt động khung ({type(ex).__name__}); dùng BYĐ ước tính.")
    warnings.append(f"Shot {row['idx']}: VÀNG — mốc SFX ước tính theo BYĐ; hoạt động toàn khung có thể do máy quay, chưa chứng minh động tác/nhân vật.")
    return result


def plan(scenes, sounds, *, opted_in=False):
    """Trả proposal tương thích sfx_plan.apply; không gọi LLM, không sửa audio."""
    if not opted_in or not features.on('motion_sfx'):
        return None
    from . import post_fx
    warnings, requests, cues, unmet, measured = [], [], [], [], []
    valid = {}
    if not isinstance(scenes, (list, tuple)):
        scenes = []
        warnings.append('VÀNG — danh sách shot sai cấu trúc.')
    if not isinstance(sounds, (list, tuple)):
        sounds = []
        warnings.append('VÀNG — catalog âm sai cấu trúc.')
    for row in scenes:
        if not isinstance(row, dict) or row.get('idx') is None or not finite(row.get('start')) or not finite(row.get('length'), True):
            warnings.append('VÀNG — shot thiếu mốc bắt đầu/thời lượng hợp lệ; không sinh cue.')
            continue
        if not finite(row['start'] + row['length']):
            warnings.append('VÀNG — tổng mốc bắt đầu/thời lượng tràn số; không sinh cue.')
            continue
        if not isinstance(row['idx'], (int, str)) or isinstance(row['idx'], bool) or row['idx'] in valid:
            warnings.append('VÀNG — shot thiếu mã hợp lệ hoặc mã trùng; không sinh cue.')
            continue
        valid[row['idx']] = row
        measurement = activity(row, warnings)
        measured.append(measurement)
        camera = row.get('camera_move')
        locked_camera = isinstance(camera, str) and camera.strip().casefold() in ('static', 'locked', 'locked-off', 'none', 'tĩnh', 'cố định')
        peak = measurement['frame_activity_peak_s'] if locked_camera else None
        if not locked_camera:
            warnings.append(f"Shot {row['idx']}: VÀNG — máy chưa được xác nhận cố định; chia đều BYĐ, không dùng đỉnh toàn khung làm động tác.")
        from . import shot_intent                  # V3.1 M2.1: đọc BYĐ qua adapter
        byd = shot_intent.byd_of(row)
        entries = byd.get('hanh_dong') if byd is not None else None
        if not isinstance(entries, list) or not entries:
            warnings.append(f"Shot {row['idx']}: VÀNG — thiếu BYĐ hành động; chỉ gợi ý nhịp giữa shot.")
            entries = []
        prompt = row.get('motion_prompt')
        current_prompt = isinstance(prompt, str) and bool(prompt.strip())
        motion = action_text(prompt if current_prompt else row.get('motion_en') or row.get('motion') or row.get('action'))
        current = kinds(motion)
        emitted = set()
        for entry in entries:
            if not isinstance(entry, dict):
                warnings.append(f"Shot {row['idx']}: VÀNG — BYĐ hành động sai cấu trúc.")
                continue
            for i, beat in enumerate(BEATS):
                state = entry.get(beat)
                if not isinstance(state, dict):
                    warnings.append(f"Shot {row['idx']}: VÀNG — thiếu/sai BYĐ {beat}.")
                    continue
                text = action_text(state)
                matched = kinds(text)
                if current_prompt and matched - kinds(motion):
                    warnings.append(f"Shot {row['idx']}: VÀNG — BYĐ {beat} xung đột motion prompt hiện tại; bỏ loại âm chỉ còn trong BYĐ cũ.")
                    matched.intersection_update(kinds(motion))
                current.update(matched)
                if not matched and text and text.lower() not in ('dung', 'nam', 'ngoi', 'đứng', 'nằm', 'ngồi'):
                    unmet.append({'scene': row['idx'], 'request': text, 'reason': 'Bảng code chưa phủ; có thể đề xuất Claude sau báo giá trên UI.'})
                for kind in sorted(matched):
                    emitted.add(kind)
                    requests.append({'scene': row['idx'], 'kind': kind, 'at': round(row['start'] + (peak if i == 1 and peak is not None else i * row['length'] / 2), 2),
                                     'time_source': 'frame_activity' if i == 1 and peak is not None else 'uniform_byd',
                                     'estimated': True, 'source': f'byd.{beat}', 'actor': entry.get('ai')})
        for kind in sorted(kinds(motion) - emitted):
            requests.append({'scene': row['idx'], 'kind': kind, 'at': round(row['start'] + (peak if peak is not None else row['length'] / 2), 2),
                             'time_source': 'frame_activity' if peak is not None else 'uniform_byd',
                             'estimated': True, 'source': 'motion'})
        if motion and not kinds(motion):
            unmet.append({'scene': row['idx'], 'request': motion, 'reason': 'Bảng code chưa phủ; cần người duyệt, không tự gọi Claude.'})
        fx = row.get('post_fx')
        if fx is not None:
            check = post_fx.validate(fx, row['length'])
            if check['muc'] != 'xanh':
                warnings.extend(f"Shot {row['idx']}: VÀNG — {reason}" for reason in check['reasons'])
            else:
                current.add('noise')
                at = row['length'] - fx['thoi_luong_s'] if fx['vi_tri'] == 'cuoi' else 0
                requests.append({'scene': row['idx'], 'kind': 'noise', 'at': round(row['start'] + at, 2),
                                 'estimated': False, 'time_source': 'post_fx_spec', 'source': 'post_fx', 'filter': post_fx.filter_for(fx, row['length'])})
        sound = row.get('sound')
        stale = kinds(action_text(sound.get('sfx'))) - current if isinstance(sound, dict) else set()
        for kind in sorted(stale):
            warnings.append(f"Shot {row['idx']}: VÀNG — sound có thể lỗi thời ({kind}); không còn trong motion/BYĐ/post_fx.")
    by_label = {}
    for sound in sounds:
        if isinstance(sound, dict) and isinstance(sound.get('heard_label'), str):
            by_label.setdefault(sound['heard_label'].casefold(), sound)
    seen = set()
    for request in requests:
        sound = next((by_label[label.casefold()] for label in LABELS[request['kind']] if label.casefold() in by_label), None)
        if sound is None:
            unmet.append(dict(request, reason='Kho đã nghe chưa có âm đúng loại; không thay bằng âm khác.'))
            warnings.append(f"Shot {request['scene']}: VÀNG — thiếu âm {request['kind']} trong catalog đáng tin.")
            continue
        scene = valid[request['scene']]
        at = round(min(request['at'], scene['start'] + max(scene['length'] - .05, 0)), 2)
        key = (request['scene'], at, sound['id'])
        if key in seen:
            continue
        seen.add(key)
        # Clip kết thúc: giữ âm trong shot như adapter apply hiện có.
        cues.append(dict(request, at=at, anchor_idx=scene['idx'], offset=round(max(at - scene['start'], 0), 2),
                         id=sound['id'], name=sound['name'], folder=sound['category'], volume=.5,
                         reason='SFX theo nhịp ' + request['source'] + (' (ước tính; cần duyệt)' if request['estimated'] else ' (âm hậu kỳ)')))
    cues.sort(key=lambda c: c['at'])
    return {'summary': 'Gợi ý code 0 USD; chưa áp âm. Mốc động tác ước tính, cần người duyệt.',
            'cues': cues, 'requests': requests, 'unmet': unmet, 'warnings': warnings, 'measurements': measured}
