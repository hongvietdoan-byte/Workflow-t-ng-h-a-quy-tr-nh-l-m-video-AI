"""V3.1 M1.2 (A1 + A15, docs/DANH_GIA_P33_LOI_GAP_PHAI_2026-10-20.md + V2.1 §15.5): a result was written straight into its final name,
so a reader (QC layer 0, the Dashboard) could open a half-written file — and `download_error` PermissionError WinError 32 (the file held by
another process) left the job for the next round. The provider now writes a TEMPORARY file next to the final one (same folder, same
extension: ffmpeg/PIL read the type from it) and `os.replace` puts it in place in one step: nobody ever sees a half file. Replacing a file
another process holds open (Windows) is tried again a few times before the error goes up (the runner keeps the job running, said).

Same content, same final path, same returned path as before — only the moment the file appears changes (not behind a flag: a safety fix).
A provider that writes somewhere else than the path it was given keeps the old behaviour (its own path is returned, the temp is cleaned)."""
import glob
import os
import time
import uuid
from typing import Callable

REPLACE_TRIES = 6
REPLACE_WAIT_S = 0.5
STALE_PART_S = 3600                      # a temp left by a process that died mid-download is removed after this


def part_path(target: str) -> str:
    root, ext = os.path.splitext(target)
    return f"{root}.part-{os.getpid()}-{uuid.uuid4().hex[:8]}{ext}"


def _remove(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _clean_stale_parts(target: str, now: float) -> None:
    """Temps older than STALE_PART_S in the target's folder (any result: a job another process finished never comes back here)."""
    for old in glob.glob(os.path.join(glob.escape(os.path.dirname(target) or "."), "*.part-*")):
        try:
            if now - os.path.getmtime(old) > STALE_PART_S:
                os.remove(old)
        except OSError:
            pass


def replace(src: str, dest: str, tries: int = REPLACE_TRIES, wait_s: float = REPLACE_WAIT_S,
            sleep: Callable[[float], None] = time.sleep) -> None:
    """os.replace, tried again while the destination is held by another process (WinError 32 → PermissionError)."""
    for attempt in range(tries):
        try:
            os.replace(src, dest)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            sleep(wait_s)


def download(provider, external_id: str, target: str, sleep: Callable[[float], None] = time.sleep) -> str:
    """provider.download into a temp file, then moved onto `target` in one step. Returns the final path. Raises what the provider
    raises (the temp is removed)."""
    folder = os.path.dirname(target)
    if folder:
        os.makedirs(folder, exist_ok=True)
    _clean_stale_parts(target, time.time())
    tmp = part_path(target)
    try:
        got = provider.download(external_id, tmp)
    except BaseException:
        _remove(tmp)
        raise
    if not got or os.path.normcase(os.path.abspath(got)) != os.path.normcase(os.path.abspath(tmp)):
        _remove(tmp)                     # the provider wrote elsewhere: its own path, as before
        return got
    try:
        replace(tmp, target, sleep=sleep)
    except BaseException:
        _remove(tmp)
        raise
    return target


def write(target: str, make: Callable[[str], bool]) -> bool:
    """C-T12 (cloud-C 20/10): the same one-step appearance for a file the pipeline MAKES (ffmpeg cut of a group clip / a shot's trim):
    `make(tmp)` writes a temp next to `target` and says whether it worked; then os.replace. False (target untouched, temp removed) when
    `make` said no or wrote nothing. Raises what `make` raises (temp removed)."""
    tmp = part_path(target)
    try:
        ok = make(tmp) and os.path.exists(tmp)
        if ok:
            replace(tmp, target)
        return bool(ok)
    finally:
        _remove(tmp)


def copy(src: str, target: str) -> None:
    """shutil.copyfile into `target` in one step (a fallback 'keep the whole clip' copy is never seen half-written either)."""
    import shutil
    write(target, lambda tmp: shutil.copyfile(src, tmp) is not None)
