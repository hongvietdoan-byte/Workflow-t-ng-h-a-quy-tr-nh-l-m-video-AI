"""Chỉnh gói ảnh theo shot; chưa nối runner/Dashboard. Không có đường gọi trả tiền.

Ghi UPDATE riêng có CAS trên nguyên văn scenes.data, giữ khóa _user_locked.
Đường dẫn chỉ lấy từ Kho hoặc index nền đúng shot; apply không đọc CSDL và
chỉ đọc nội dung ảnh để xác minh SHA. who do caller đã xác thực cung cấp.

save()/undo() bắt buộc base_refs là list gói ảnh gốc thực tế, kể cả gói rỗng.
Fingerprint cảnh dùng IMAGE_KEYS/IMAGE_SHOT_KEYS và khóa chọn ảnh; chỉnh đã lưu
bằng tập khóa cũ có thể stale, cần tải lại gói rồi lưu/duyệt lại; không migration tự động.
"""
import copy
import hashlib
import json
import os
from datetime import datetime, timezone

from . import features
from .sent_package import sha256_of


class OverrideError(ValueError):
    pass


def _on():
    return features.on('package_overrides')


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _scene(conn, sid):
    row = conn.execute('SELECT project_id,data FROM scenes WHERE id=?', (sid,)).fetchone()
    if row is None:
        raise OverrideError('Không tìm thấy shot; tải lại trước khi chỉnh gói.')
    return row[0], row[1], json.loads(row[1] or '{}')


def _scene_hash(data):
    """Dấu cảnh theo tập khóa hiện tại; dấu phiên bản cũ được coi stale để duyệt lại."""
    from .lineage import IMAGE_KEYS, IMAGE_SHOT_KEYS
    keys = set(IMAGE_KEYS + IMAGE_SHOT_KEYS) | {
        'characters', 'outfit', 'outfits', 'outfit_image_ids', 'plate', 'plate_key',
        'plate_path', 'aspect', 'aspect_ratio', 'location_id'}
    return _hash({k: v for k, v in data.items() if k in keys})


def load(conn, scene_id):
    if not _on():
        return None
    _, _, data = _scene(conn, scene_id)
    result = copy.deepcopy(data.get('package_overrides'))
    if result:
        result['stale'] = (result['base_scene_revision'] != _scene_hash(data)
                           or result.get('scene_id') != scene_id)
    return result


def _root(conn, data_dir):
    if data_dir:
        if not os.path.isabs(os.fspath(data_dir)):
            raise OverrideError('Thư mục dữ liệu phải là đường dẫn tuyệt đối.')
        return os.fspath(data_dir)
    filename = conn.execute('PRAGMA database_list').fetchone()[2]
    return os.path.dirname(filename) if filename else None


def _resolve(conn, pid, sid, edit, root):
    allowed = {'op', 'source_kind', 'asset_image_id', 'plate_key', 'content_sha',
               'role', 'look', 'project_id', 'scene_id', 'wearer', 'character'}
    if not isinstance(edit, dict) or set(edit) - allowed:
        raise OverrideError('Chỉnh gói chứa trường không hợp lệ; không nhận đường dẫn nhập tay.')
    if edit.get('op') not in ('exclude', 'add', 'pin') or not edit.get('role'):
        raise OverrideError('Cần thao tác bỏ/thêm/ghim và vai trò ảnh.')
    e = copy.deepcopy(edit)
    wearer = e.get('wearer') or e.get('character')
    if any(k in e and (not isinstance(e[k], str) or not e[k].strip()) for k in ('wearer', 'character')):
        raise OverrideError('Tên nhân vật mặc phải là chuỗi không rỗng.')
    if e.get('wearer') and e.get('character') and e['wearer'] != e['character']:
        raise OverrideError('wearer và character phải cùng nhân vật.')
    if wearer and (e['role'] != 'outfit' or e.get('source_kind') != 'kho'):
        raise OverrideError('Nhân vật mặc chỉ áp dụng cho ảnh OUTFIT từ Kho.')
    if wearer:
        _, _, scene = _scene(conn, sid)
        if wearer not in (scene.get('characters') or []):
            raise OverrideError('Nhân vật mặc không có trong shot hiện tại.')
    if e.get('source_kind') == 'kho':
        from . import assets, looks
        row = conn.execute('SELECT i.path,i.sha256,a.name,a.project_id,a.kind,i.status,i.look,a.id FROM asset_images i '
                           'JOIN assets a ON a.id=i.asset_id WHERE i.id=?', (e.get('asset_image_id'),)).fetchone()
        if row is None or row[3] not in (None, pid):
            raise OverrideError('Ảnh Kho không tồn tại hoặc thuộc dự án khác.')
        if row[5] not in assets.USABLE:
            raise OverrideError('Ảnh Kho chưa được phép dùng hoặc đã bỏ khỏi Kho.')
        if not conn.execute('SELECT 1 FROM project_assets WHERE project_id=? AND asset_id=?', (pid, row[7])).fetchone():
            raise OverrideError('Tài nguyên Kho chưa được chọn cho dự án.')
        project = conn.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone()
        want_look = looks.asset_look(project)
        if (want_look and row[6] != want_look) or (e.get('look') not in (None, 'default') and e['look'] != row[6]):
            raise OverrideError('Look ảnh Kho không khớp dự án hoặc lựa chọn.')
        path, stored_sha, label = row[:3]
        roles = {'character': {'character', 'front_standard', 'design_sheet', 'related'},
                 'outfit': {'outfit', 'outfit_object', 'front_standard', 'design_sheet', 'related'}, 'location': {'location', 'landmark'},
                 'weapon': {'object'}, 'prop': {'object'}, 'pet': {'object'}}
        if e['role'] not in roles.get(row[4], set()):
            raise OverrideError('Vai trò ảnh không khớp loại tài nguyên Kho.')
        if stored_sha and stored_sha != e.get('content_sha'):
            raise OverrideError('SHA ảnh Kho đã đổi; tải lại gói.')
    elif e.get('source_kind') == 'shot_3d':
        from . import location_pack, place_refs
        if e.get('project_id') != pid or e.get('scene_id') != sid or not root:
            raise OverrideError('Nền 3D phải thuộc đúng dự án/shot và có thư mục dữ liệu.')
        rec = location_pack.index(root, pid).get(str(sid)) or {}
        pick = rec if rec.get('key') == e.get('plate_key') else rec.get('wide') or {}
        if pick.get('key') != e.get('plate_key'):
            raise OverrideError('Nền 3D không thuộc máy của shot hiện tại.')
        path = pick.get('path') or pick.get('plate')
        stored_sha = None
        label = (rec.get('place') or 'the place') if pick is rec else f"{place_refs.WIDE_LABEL} ({rec.get('place') or 'the place'})"
        expected_role = place_refs.ROLE if pick is rec else place_refs.WIDE_ROLE
        if e['role'] != expected_role:
            raise OverrideError('Vai trò nền không khớp ảnh máy shot/ảnh toàn.')
    else:
        raise OverrideError('Nguồn ảnh phải là Kho hoặc nền 3D đúng shot.')
    if not path:
        raise OverrideError('Ảnh không có đường dẫn nguồn.')
    if not os.path.isabs(path):
        if not root:
            raise OverrideError('Không có thư mục gốc để đọc ảnh; không dùng thư mục đang chạy.')
        path = os.path.abspath(os.path.join(root, path))
        if os.path.commonpath([path, os.path.abspath(root)]) != os.path.abspath(root):
            raise OverrideError('Ảnh vượt thư mục dữ liệu.')
    try:
        actual = sha256_of(path)
    except OSError as exc:
        raise OverrideError('Không đọc được ảnh; tải lại gói.') from exc
    if actual != e.get('content_sha'):
        raise OverrideError('SHA nội dung ảnh đã đổi; tải lại gói.')
    e['_ref'] = {'path': path, 'label': wearer or label, 'role': e['role']}
    if e.get('plate_key'):
        e['_ref']['plate_key'] = e['plate_key']
    return e


def save(conn, scene_id, edits, who, reason, expected_revision, *, data_dir=None, base_refs=None):
    if not _on():
        raise OverrideError('Cờ Gói gửi kèm đang tắt.')
    if not isinstance(who, str) or not who.strip() or not isinstance(reason, str) or not reason.strip():
        raise OverrideError('Cần người chỉnh và lý do.')
    if not isinstance(edits, list):
        raise OverrideError('Danh sách chỉnh gói không hợp lệ.')
    if not isinstance(base_refs, list):
        raise OverrideError('Cần base_refs là gói ảnh gốc thực tế; tải lại gói trước khi chỉnh.')
    pid, raw, data = _scene(conn, scene_id)
    before = data.get('package_overrides')
    current = (before or {}).get('revision', 0)
    if expected_revision != current:
        raise OverrideError(f'revision đã đổi ({current}); tải lại, không ghi đè.')
    resolved = [_resolve(conn, pid, scene_id, e, _root(conn, data_dir)) for e in edits]
    for e in resolved:
        if e['op'] != 'pin' or e['role'] != 'outfit':
            continue
        slots = [r for r in base_refs if r.get('role') == 'outfit']
        wearer = e.get('wearer') or e.get('character')
        if not wearer:
            labels = {r.get('label') for r in slots}
            if len(labels) > 1:
                raise OverrideError('Gói có nhiều nhân vật mặc OUTFIT; cần wearer/character rõ ràng.')
            wearer = next(iter(labels), None)
            if not wearer:
                raise OverrideError('Ghim OUTFIT cần wearer/character khi gói chưa có ảnh trang phục.')
        if wearer not in (data.get('characters') or []):
            raise OverrideError('Nhân vật mặc không có trong shot hiện tại.')
        e['wearer'] = wearer
        e['_ref']['label'] = wearer
    now = datetime.now(timezone.utc).isoformat()
    after = {'schema_version': 1, 'revision': current + 1, 'project_id': pid,
             'scene_id': scene_id, 'base_scene_revision': _scene_hash(data),
             'base_package_hash': _hash(base_refs),
             'edits': resolved, 'updated_by': who, 'updated_at': now, 'reason': reason}
    data['package_overrides'] = after
    data['_user_locked'] = sorted(set(data.get('_user_locked') or []) | {'package_overrides'})
    # Một savepoint bảo vệ audit + cảnh, kể cả caller đang trong transaction khác.
    conn.execute('SAVEPOINT package_override_write')
    try:
        changed = conn.execute('UPDATE scenes SET data=? WHERE id=? AND data IS ?',
                               (json.dumps(data, ensure_ascii=False), scene_id, raw)).rowcount
        if changed != 1:
            raise OverrideError('revision cảnh đã đổi; tải lại trước khi chỉnh gói.')
        detail = {'project_id': pid, 'story_scene': data.get('story_scene'), 'shot_no': data.get('shot_no'),
                  'scene_id': scene_id, 'revision': current + 1, 'before': before, 'after': after,
                  'before_hash': _hash(before), 'after_hash': _hash(after)}
        conn.execute('INSERT INTO audit_log(at,email,action,detail) VALUES(?,?,?,?)',
                     (now, who, 'package_override', json.dumps(detail, ensure_ascii=False)))
        conn.execute('RELEASE package_override_write')
    except Exception:
        conn.execute('ROLLBACK TO package_override_write')
        conn.execute('RELEASE package_override_write')
        raise
    return current + 1


def apply(refs, overrides):
    if not _on() or not overrides:
        return refs, []
    out, warnings = copy.deepcopy(refs), []
    if overrides.get('stale') or overrides.get('base_package_hash') != _hash(refs):
        return out, [{'severity': 'yellow', 'code': 'override_stale', 'message': 'Shot đã đổi; duyệt lại chỉnh gói.'}]
    for e in overrides.get('edits') or []:
        ref = e.get('_ref') or {}
        try:
            valid = sha256_of(ref['path']) == e['content_sha']
        except (OSError, KeyError):
            valid = False
        if not valid:
            warnings.append({'severity': 'yellow', 'code': 'override_image_changed',
                             'message': 'Ảnh chỉnh gói mất hoặc SHA đã đổi; tải lại và duyệt lại.'})
            continue
        matches = []
        for i, r in enumerate(out):
            if r.get('role') != e['role']:
                continue
            if (e.get('wearer') or e.get('character')) and r.get('label') != ref.get('label'):
                continue
            if e.get('plate_key') and r.get('plate_key') != e['plate_key']:
                continue
            try:
                if sha256_of(r['path']) == e['content_sha']:
                    matches.append(i)
            except (OSError, KeyError):
                if not any(w['code'] == 'ref_unreadable' for w in warnings):
                    warnings.append({'severity': 'yellow', 'code': 'ref_unreadable', 'message': 'Ảnh gói gốc không đọc được.'})
        if e['op'] == 'exclude':
            out = [r for i, r in enumerate(out) if i not in matches]
            if not matches:
                warnings.append({'severity': 'yellow', 'code': 'override_not_found', 'message': 'Ảnh cần bỏ không còn trong gói.'})
        elif e['op'] == 'pin':
            # Thay lựa chọn cùng người/vai trò; không để hai look đánh nhau.
            slots = [i for i, r in enumerate(out) if r.get('role') == ref['role']
                     and (e['source_kind'] == 'shot_3d' or r.get('label') == ref['label'])]
            if slots:
                target = next((i for i in matches if i in slots), slots[0])
                out[target] = {**out[target], **copy.deepcopy(ref)}
                # Ảnh góc phụ cùng người vẫn cần giữ để khóa nhận dạng.
                if ref['role'] not in ('character', 'front_standard', 'design_sheet', 'related'):
                    out = [r for i, r in enumerate(out) if i not in slots or i == target]
            else:
                out.append(copy.deepcopy(ref))
        elif not matches:
            out.append(copy.deepcopy(ref))
    return out, warnings


def check(conn, data_dir, pid, scene_id, refs):
    if not _on():
        return []
    from . import location_pack, place_refs, scene_storyboard
    actual_pid, _, data = _scene(conn, scene_id)
    if actual_pid != pid:
        raise OverrideError('Shot không thuộc dự án yêu cầu.')
    root = _root(conn, data_dir)
    if not root:
        raise OverrideError('Cần thư mục dữ liệu tuyệt đối để kiểm gói.')
    errors = []
    current = load(conn, scene_id)
    if current and (current.get('stale') or current.get('scene_id') != scene_id):
        errors.append({'severity': 'yellow', 'code': 'override_stale', 'message': 'Shot đã replan; duyệt lại chỉnh gói.'})
    rec = location_pack.index(root, pid).get(str(scene_id))
    problem = place_refs.package_problem(refs, rec)
    if problem:
        errors.append({'severity': 'red', 'code': 'plate_package_mixed', 'message': problem})
    for name in scene_storyboard.cast_missing(conn, pid, data, refs):
        errors.append({'severity': 'red', 'code': 'cast_missing', 'message': f'Thiếu ảnh mẫu {name} trong gói gửi kèm.'})
    return errors


def undo(conn, scene_id, to_revision, who, *, data_dir=None, base_refs=None):
    if not _on():
        raise OverrideError('Cờ Gói gửi kèm đang tắt.')
    if not isinstance(base_refs, list):
        raise OverrideError('Cần base_refs là gói ảnh gốc thực tế; tải lại gói trước khi chỉnh.')
    pid, _, data = _scene(conn, scene_id)
    current = data.get('package_overrides') or {}
    target = None
    for row in conn.execute("SELECT detail FROM audit_log WHERE action='package_override' ORDER BY id DESC"):
        item = json.loads(row[0])
        same_shot = (item.get('project_id') == pid and
                     ((data.get('shot_no') is not None and item.get('story_scene') == data.get('story_scene')
                       and item.get('shot_no') == data.get('shot_no'))
                      or (data.get('shot_no') is None and item.get('scene_id') == scene_id)))
        if same_shot and item.get('revision') == to_revision:
            target = item['after']
            break
    if target is None:
        raise OverrideError('Không có revision hoàn tác của shot này.')
    edits = [{k: v for k, v in e.items() if k != '_ref'} for e in target['edits']]
    for e in edits:
        if e.get('source_kind') == 'shot_3d':
            e['project_id'], e['scene_id'] = pid, scene_id
    return save(conn, scene_id, edits, who, f'Hoàn tác về revision {to_revision}', current.get('revision', 0),
                data_dir=data_dir, base_refs=base_refs)
