"""Bổ sung chiều cao hồ sơ Kho CHUNG; không đoán số, không đổi liên kết dự án."""
import json
import math
import os

from . import access, assets, auth


def _profile(raw):
    def invalid_constant(value):
        raise ValueError('nonfinite JSON')
    try:
        value = json.loads(raw or '{}', parse_constant=invalid_constant)
    except (TypeError, ValueError):
        raise assets.AssetError('Hồ sơ Kho lỗi JSON; mở Kho để sửa hồ sơ trước, chưa ghi chiều cao.') from None
    if (not isinstance(value, dict) or type(value.get('schema_version', 1)) is not int
            or value.get('schema_version', 1) not in (1, 2)):
        raise assets.AssetError('Hồ sơ Kho sai cấu trúc; chưa ghi chiều cao.')
    return value


def _writer(conn, user):
    identity = access.user_of(user)
    if identity is None:
        if os.environ.get('DASHBOARD_AUTH', 'on').strip().lower() in ('off', '0', 'false', 'no'):
            return 'local'
        raise assets.AssetError('Cần đăng nhập để sửa chiều cao Kho chung.')
    rows = conn.execute('SELECT role,active,perms FROM users WHERE lower(trim(email))=?',
                        (identity.get('email'),)).fetchall()
    if len(rows) != 1 or rows[0]['active'] != 1:
        raise assets.AssetError('Danh tính không còn hoạt động; chưa sửa Kho.')
    try:
        perms = json.loads(rows[0]['perms'] or '[]')
    except (ValueError, TypeError):
        perms = []
    if not isinstance(perms, list) or not auth.can({'role': rows[0]['role'], 'perms': perms}, 'assets'):
        raise assets.AssetError('Cần quyền sửa Kho tài nguyên hiện tại.')
    return identity['email']


def save_height(conn, asset_id, height_m, *, user, confirmed, expected_profile_snapshot):
    """Ghi đúng một trường qua writer hiện có; snapshot từ lượt vẽ, không lấy lại để bỏ qua CAS."""
    if confirmed is not True:
        raise assets.AssetError('Cần xác nhận sửa Kho CHUNG, ảnh hưởng mọi dự án dùng hồ sơ này.')
    if isinstance(height_m, bool):
        raise assets.AssetError('Chiều cao cần là số mét từ 0,2 đến 30.')
    try:
        height = float(height_m)
    except (TypeError, ValueError, OverflowError):
        raise assets.AssetError('Chiều cao cần là số mét từ 0,2 đến 30.') from None
    if not math.isfinite(height) or not .2 <= height <= 30:
        raise assets.AssetError('Chiều cao cần là số mét hữu hạn từ 0,2 đến 30.')
    if conn.in_transaction:
        raise assets.AssetError('CSDL đang có thay đổi chưa kết thúc; đợi hoặc tải lại trước khi sửa chiều cao.')
    owned = True
    try:
        if owned:
            conn.execute('BEGIN IMMEDIATE')
        email = _writer(conn, user)
        row = conn.execute('SELECT kind,project_id,profile FROM assets WHERE id=?', (asset_id,)).fetchone()
        if row is None or row['kind'] not in ('character', 'pet') or row['project_id'] is not None:
            raise assets.AssetError('Chỉ bổ sung chiều cao nhân vật/thú tại Kho CHUNG.')
        raw = row['profile'] or ''
        if not isinstance(expected_profile_snapshot, str) or raw != expected_profile_snapshot:
            raise assets.AssetError('Hồ sơ đã đổi; tải lại trước khi lưu chiều cao.')
        profile = _profile(raw)
        result = assets.set_profile(conn, asset_id, {'height_m': height}, approved=bool(profile.get('approved')),
                                    actor={'kind': 'human', 'who': email}, expected_revision=profile.get('revision'),
                                    expected_profile_snapshot=raw)
        conn.commit()
        return result
    except Exception:
        if owned:
            conn.rollback()
        raise


def missing_heights(conn, project_id, shots):
    """Chỉ vai trong các shot của cảnh, dùng resolver canonical link/tên của audit."""
    from . import change_audit, speaker_lint
    entries, problems, seen = [], [], set()
    for shot in shots:
        row = conn.execute('SELECT data FROM scenes WHERE project_id=? AND idx=?', (project_id, shot)).fetchone()
        if row is None:
            continue
        try:
            data = json.loads(row['data'] or '{}')
            names = data.get('characters')
            if not isinstance(names, list):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            problems.append('Dữ liệu vai của shot sai cấu trúc; sửa đầu vào trước.')
            continue
        for name in names:
            if not isinstance(name, str) or speaker_lint.is_narrator(name):
                continue
            asset, error = change_audit._role_asset(conn, project_id, name)
            if error:
                problems.append(f'{name}: {error}')
                continue
            if not asset or asset['id'] in seen:
                continue
            seen.add(asset['id'])
            try:
                profile = _profile(asset.get('profile'))
            except assets.AssetError as error:
                problems.append(f'{name}: {error}')
                continue
            height = profile.get('height_m')
            if type(height) in (int, float) and math.isfinite(height) and .2 <= height <= 30:
                continue
            if asset.get('project_id') is not None:
                problems.append(f'{name}: hồ sơ riêng dự án; ô bổ sung này chỉ sửa Kho CHUNG.')
                continue
            entries.append({'id': asset['id'], 'name': asset['name'], 'snapshot': asset.get('profile') or ''})
    return entries, list(dict.fromkeys(problems))
