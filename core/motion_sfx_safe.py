"""Guard I/O và thay manifest chỉ cho caller SFX theo nhịp, không gọi API."""
import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
import uuid
from pathlib import Path

MAX_CLIPS = 128
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_READ_SECONDS = 20
MAX_MANIFEST_BYTES = 4 * 1024 * 1024


def local_file(value, *, scope=None):
    """Từ chối đường dẫn không tin cậy trước mở; không theo symlink/junction."""
    if not isinstance(value, str) or not value or not os.path.isabs(value) or '://' in value or value.startswith(('\\\\', '//')):
        raise ValueError('Nguồn phải là đường dẫn file cục bộ tuyệt đối.')
    path = Path(os.path.abspath(value))
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('Nguồn không được qua symlink/junction.')
    if scope is not None:
        root = os.path.realpath(scope)
        if os.path.commonpath([root, os.path.realpath(path)]) != root:
            raise ValueError('Clip nằm ngoài thư mục dự án được phép.')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
        raise ValueError('Nguồn phải là file thường và nằm trong trần dung lượng.')
    return str(path), info


def signature_payload(p, data_dir, pid, transition, fade, *, strong):
    from . import sfx_plan
    rows = [dict(r) for r in p.conn.execute(
        'SELECT s.id, s.idx, s.data, m.motion_prompt FROM scenes s LEFT JOIN motion_prompts m ON m.scene_id=s.id WHERE s.project_id=? ORDER BY s.idx, s.id', (pid,))]
    sounds = sfx_plan.catalog(p.conn)
    collected = final_clips(p, data_dir, pid)
    if len(collected) > MAX_CLIPS:
        raise ValueError('Quá trần số clip cho gợi ý SFX theo nhịp.')
    scope = os.path.join(os.path.abspath(data_dir), str(pid))
    checked, total = [], 0
    for clip in collected:
        path, info = local_file(clip['path'], scope=scope) if clip.get('path') else (None, None)
        if path:
            allowed = [os.path.join(scope, *parts) for parts in (('videos',), ('trash', 'videos'), ('assets',), ('takes',))]
            if (Path(path).suffix.lower() not in ('.mp4', '.mov', '.webm', '.mkv')
                    or not any(os.path.commonpath([root, path]) == root for root in allowed)):
                raise ValueError('Nguồn clip không thuộc thư mục video/take/assets được phép.')
        total += info.st_size if info else 0
        checked.append((clip, path, info))
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Tổng clip vượt trần dung lượng kiểm SFX theo nhịp.')
    clips, deadline = [], time.monotonic() + MAX_READ_SECONDS
    for clip, path, before in checked:
        digest = None
        if strong and path:
            hashed, count = hashlib.sha256(), 0
            with open(path, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                    raise ValueError('Clip đổi trước khi đọc; lập lại gợi ý.')
                while True:
                    if time.monotonic() > deadline:
                        raise ValueError('Kiểm clip vượt trần thời gian; chưa áp hiệu ứng.')
                    block = stream.read(min(1024 * 1024, MAX_FILE_BYTES - count + 1))
                    if not block:
                        break
                    count += len(block)
                    if count > before.st_size or count > MAX_FILE_BYTES:
                        raise ValueError('Clip đổi dung lượng trong lúc kiểm.')
                    hashed.update(block)
            _, after = local_file(path, scope=scope)
            if count != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError('Clip đổi trong lúc kiểm; lập lại gợi ý.')
            digest = hashed.hexdigest()
        clips.append(dict(metadata=dict(clip, path=path), sha256=digest,
                          size=before.st_size if before else None, mtime=before.st_mtime_ns if before else None))
    payload = json.dumps([pid, transition, fade, rows, clips, sounds], sort_keys=True, ensure_ascii=False, allow_nan=False)
    if strong:
        cheap_clips = [dict(clip, sha256=None) for clip in clips]
        cheap_payload = json.dumps([pid, transition, fade, rows, cheap_clips, sounds], sort_keys=True, ensure_ascii=False, allow_nan=False)
        cheap_hash = hashlib.sha256(cheap_payload.encode('utf-8')).hexdigest()
        if cheap_hash != signature_payload(p, data_dir, pid, transition, fade, strong=False):
            raise ValueError('Metadata/nguồn clip đổi trong lúc băm; lập lại gợi ý.')
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def source_digest(path, deadline):
    path, before = local_file(path)
    hashed, count = hashlib.sha256(), 0
    with open(path, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise ValueError('Nguồn âm đổi trước khi đọc.')
        while True:
            if time.monotonic() > deadline:
                raise ValueError('Kiểm âm vượt trần thời gian.')
            block = stream.read(min(1024 * 1024, MAX_FILE_BYTES - count + 1))
            if not block:
                break
            count += len(block)
            if count > before.st_size or count > MAX_FILE_BYTES:
                raise ValueError('Nguồn âm đổi dung lượng.')
            hashed.update(block)
    _, after = local_file(path)
    if count != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Nguồn âm đổi trong lúc đọc.')
    return hashed.hexdigest()


def final_clips(p, data_dir, pid):
    from . import final_cut
    return final_cut.collect_clips(p, data_dir, pid)


def manifest_bytes(path):
    if not path.exists():
        return None
    local_file(str(path))
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError('Manifest âm vượt trần dung lượng.')
    with path.open('rb') as stream:
        content = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(content) > MAX_MANIFEST_BYTES:
        raise ValueError('Manifest âm vượt trần dung lượng.')
    return content


def validate_entries(entries, directory):
    if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
        raise ValueError('Manifest âm không hợp lệ; giữ nguyên mix cũ.')
    for entry in entries:
        for key in ('file', 'fit_file'):
            name = entry.get(key)
            if name is None:
                continue
            if not isinstance(name, str) or not name or name != os.path.basename(name) or '/' in name or '\\' in name or ':' in name or name in ('.', '..'):
                raise ValueError('Manifest âm có đường dẫn không hợp lệ.')
            path = Path(directory) / name
            if path.exists() or path.is_symlink():
                local_file(str(path), scope=str(directory))


def atomic_apply(module, p, data_dir, pid, chosen, scenes, *, verify=None):
    """Stage toàn bộ; giữ âm cũ tới replace manifest. Lock chỉ phối hợp caller mới."""
    project = Path(os.path.abspath(data_dir)) / str(pid)
    directory = project / 'audio_assets'
    # Thư mục cha cũng phải không bị đổi hướng qua symlink/junction.
    for part in (directory, *directory.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise module.SfxPlanError('Thư mục âm không được qua symlink/junction.')
    directory.mkdir(parents=True, exist_ok=True)
    manifest, installed = directory / 'assets.json', []
    lock = directory / '.motion_sfx.lock'
    locked = False
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        locked = True
        original = manifest_bytes(manifest)
        entries = json.loads(original) if original is not None else []
        validate_entries(entries, directory)
        # Những âm mới đã chọn phải vẫn là nguồn Kho cục bộ, không phải link.
        if len(chosen) > MAX_CLIPS:
            raise ValueError('Số âm chọn vượt trần staging.')
        total_sources, sources = 0, []
        trusted_ids = {row['id'] for row in module.catalog(p.conn)}
        for cue in chosen:
            if cue['id'] not in trusted_ids:
                raise ValueError('Âm không còn trong catalog Kho đáng tin.')
            source = module.sound_lib.get(p.conn, cue['id'])
            if source is None:
                raise ValueError('Âm Kho đã mất; chưa áp hiệu ứng.')
            registered = p.conn.execute('SELECT path FROM sound_sources WHERE id=?', (source.get('source_id'),)).fetchone()
            if registered is None or not isinstance(registered['path'], str) or not os.path.isabs(registered['path']):
                raise ValueError('Nguồn âm chưa thuộc thư mục Kho cục bộ được đăng ký.')
            path, info = local_file(source['path'], scope=registered['path'])
            total_sources += info.st_size
            sources.append(path)
        if total_sources > MAX_TOTAL_BYTES:
            raise ValueError('Âm chọn vượt trần dung lượng staging.')
        deadline = time.monotonic() + MAX_READ_SECONDS
        digests = [source_digest(path, deadline) for path in sources]
        with tempfile.TemporaryDirectory(prefix='.motion-sfx-', dir=str(project)) as stage:
            stage_path = Path(stage)
            (stage_path / 'assets.json').write_bytes(original or b'[]')
            added = module.apply(p, data_dir, pid, chosen, scenes, _directory=stage)
            staged = json.loads(manifest_bytes(stage_path / 'assets.json'))
            validate_entries(staged, stage)
            effects = [e for e in staged if str(e.get('label', '')).startswith(module.LABEL_PREFIX)]
            if added != len(chosen) or len(effects) != len(chosen):
                raise ValueError('Nguồn âm thiếu trong lúc stage; giữ mix cũ.')
            deadline = time.monotonic() + MAX_READ_SECONDS
            for effect, digest, source in zip(effects, digests, sources):
                if (source_digest(str(stage_path / effect['file']), deadline) != digest
                        or source_digest(source, deadline) != digest):
                    raise ValueError('Âm Kho đổi trong lúc sao chép; giữ mix cũ.')
            # Legacy apply giữ manual rows, tạo file chỉ cho cue mới.
            for entry in staged:
                if not str(entry.get('label', '')).startswith(module.LABEL_PREFIX):
                    continue
                source = stage_path / entry['file']
                local_file(str(source), scope=stage)
                name = 'motion_' + uuid.uuid4().hex + source.suffix
                target = directory / name
                # Chưa sửa manifest và không ghi đè bất kỳ file cũ nào.
                with target.open('xb'):
                    pass
                installed.append(target)
                shutil.copyfile(str(source), str(target))
                entry['file'] = name
            validate_entries(staged, directory)
            candidate = stage_path / 'assets.commit.json'
            candidate.write_text(json.dumps(staged, ensure_ascii=False, indent=1), encoding='utf-8')
            if verify is not None:
                verify()
            if manifest_bytes(manifest) != original:
                raise ValueError('Mix âm đã đổi ở phiên khác; chưa áp hiệu ứng.')
            os.replace(str(candidate), str(manifest))
            installed.clear()
            return added
    except (OSError, ValueError, KeyError, TypeError):
        raise module.SfxPlanError('Không thể áp SFX theo nhịp an toàn; mix cũ được giữ. Hãy kiểm nguồn âm và lập lại gợi ý.') from None
    finally:
        for path in installed:
            try:
                path.unlink()
            except OSError:
                pass
        if locked:
            try:
                lock.unlink(missing_ok=True)
            except OSError:
                pass
