"""Đ20 M1.9a: chụp sổ gói gửi ngoại tuyến; chưa phải replay đường gửi."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
from urllib.parse import urlsplit


class GoldenError(ValueError):
    """Đầu vào thiếu hoặc chưa đủ an toàn để lưu fixture."""


def head_sha():
    # Không kế thừa môi trường máy chính, không nạp provider/config ứng dụng.
    git = Path("C:/Program Files/Git/cmd/git.exe")
    if not git.is_file():
        raise GoldenError("Không tìm thấy Git; chưa chụp được HEAD SHA")
    result = subprocess.run([str(git), "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                            env={"SYSTEMROOT": "C:/Windows"}, capture_output=True, check=True, text=True)
    value = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise GoldenError("HEAD SHA không hợp lệ")
    return value


def compare_compat(expected: bytes, actual: bytes):
    """So byte do caller cung cấp; không chứng nhận replay/correctness."""
    if not isinstance(expected, bytes) or not isinstance(actual, bytes):
        raise GoldenError("COMPAT cần hai chuỗi bytes")
    if expected != actual:
        raise GoldenError("COMPAT lệch byte; chưa đạt tương thích")


def _safe(value):
    # Từ chối cả bản chụp; không xuất giá trị hay tên trường đáng ngờ trong lỗi.
    if isinstance(value, dict):
        for key, item in value.items():
            low = str(key).lower().replace("-", "_")
            if low in ("key", "auth", "headers") or any(w in low for w in
                    ("token", "secret", "password", "credential", "authorization", "cookie", "api_key", "apikey")):
                raise GoldenError("Gói chứa trường nhạy cảm; cần bản xuất đã lược bỏ trước khi chụp")
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise GoldenError("Gói chứa số không hữu hạn; cần JSON hợp lệ trước khi chụp")
    elif isinstance(value, str) and value.lower().startswith(("http://", "https://")):
        url = urlsplit(value)
        if "?" in value or "#" in value or url.username is not None or url.password is not None:
            raise GoldenError("URL có credential/query/fragment; cần bản xuất đã lược bỏ trước khi chụp")


def _ref(ref, root):
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        raise GoldenError("refs thiếu path")
    result = dict(ref)
    result["captured_sha256"] = None
    path = ref["path"]
    if path.startswith(("http://", "https://")):
        status = "remote_not_fetched"
    elif "://" in path or path.startswith(("\\\\", "//")):
        status = "outside_scope"
    else:
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            status = "outside_scope"
        elif not candidate.is_file():
            status = "missing"
        else:
            try:
                with candidate.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError:
                status = "unreadable"
            else:
                result["captured_sha256"] = digest
                status = "missing_stored_hash" if not ref.get("sha256") else ("match" if digest == ref["sha256"] else "mismatch")
    result["hash_status"] = status
    return result


def capture(*, db, project, shot, flags_file, ref_root, purpose, input_snapshots_file=None):
    db, root = Path(db).resolve(), Path(ref_root).resolve()
    if not db.is_file() or not root.is_dir():
        raise GoldenError("Cần --db tồn tại và --ref-root là thư mục rõ ràng")
    if purpose not in ("compat", "correctness"):
        raise GoldenError("purpose cần compat hoặc correctness")
    flags = json.loads(Path(flags_file).read_text(encoding="utf-8-sig"))
    if not isinstance(flags, dict) or not all(isinstance(k, str) and type(v) is bool for k, v in flags.items()):
        raise GoldenError("flags phải là JSON object tên cờ → boolean (không đọc môi trường)")
    if purpose == "compat" and any(flags.values()):
        raise GoldenError("COMPAT yêu cầu các cờ thử nghiệm khai trong file đều TẮT")
    inputs = {}
    if input_snapshots_file is not None:
        inputs = json.loads(Path(input_snapshots_file).read_text(encoding="utf-8-sig"))
        if not isinstance(inputs, dict):
            raise GoldenError("input snapshots cần object job id → snapshot trước lắp gói")
        _safe(inputs)
    warnings, jobs = [], []
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN")  # Một snapshot đọc nhất quán cho mọi SELECT.
        schema = {key: conn.execute(f"PRAGMA {key}").fetchone()[0] for key in ("user_version", "schema_version")}
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        required = {"id", "project_id", "scene_id", "type", "state", "model", "quality_tier", "sent_package"}
        missing = required - columns
        if missing:
            raise GoldenError("jobs thiếu trường: " + ", ".join(sorted(missing)))
        running = conn.execute("SELECT count(*) FROM jobs WHERE project_id=? AND state IN ('running','submitted','polling','sending')", (project,)).fetchone()[0]
        if running:
            warnings.append("Dự án có job đang chạy; nên dùng snapshot CSDL + ref nhất quán trước khi chụp")
        rows = conn.execute("SELECT id,type,state,model,quality_tier,sent_package FROM jobs WHERE project_id=? AND scene_id=? AND type IN ('image_gen','video_gen') ORDER BY id", (project, shot)).fetchall()
        if not rows:
            raise GoldenError("Không có jobs ảnh/video cho project + shot chỉ định")
        for row in rows:
            raw = row["sent_package"]
            try:
                package = json.loads(raw)
            except (TypeError, ValueError):
                raise GoldenError(f"job {row['id']}: thiếu/hỏng sent_package") from None
            if not isinstance(package, dict):
                raise GoldenError(f"job {row['id']}: sent_package cần object")
            for name in ("v", "prompt", "provider", "model", "refs"):
                if name not in package:
                    raise GoldenError(f"job {row['id']}: sent_package thiếu {name}")
            if not isinstance(package["refs"], list):
                raise GoldenError("refs cần list giữ nguyên thứ tự")
            if not isinstance(package["prompt"], str) or not package["provider"] or not package["model"]:
                raise GoldenError("prompt/provider/model thiếu giá trị")
            _safe(package)
            refs = [_ref(ref, root) for ref in package["refs"]]
            for index, ref in enumerate(refs):
                if ref["hash_status"] != "match":
                    warnings.append(f"job {row['id']} refs[{index}]: {ref['hash_status']}")
            if row["quality_tier"] is None:
                warnings.append(f"job {row['id']}: thiếu quality_tier (NULL), không suy đoán")
            jobs.append({"id": row["id"], "type": row["type"], "state": row["state"], "model": row["model"],
                         "tier": row["quality_tier"], "provider": package["provider"], "prompt": package["prompt"],
                         "sent_package_raw": raw, "sent_package_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "refs": refs, "input_snapshot": inputs.get(str(row["id"]))})
    return {"fixture_version": 1, "purpose": purpose, "head_sha": head_sha(), "flags": flags,
            "flags_provenance": "explicit_file_unverified_at_send", "schema": schema, "project": project, "scene_id": shot,
            "jobs": jobs, "warnings": warnings, "replay_status": "OPEN", "correctness_status": "OPEN"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("db", "flags-file", "ref-root", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("project", "shot"):
        parser.add_argument("--" + name, required=True, type=int)
    parser.add_argument("--purpose", required=True, choices=("compat", "correctness"))
    parser.add_argument("--input-snapshots-file", type=Path, help="JSON job id → args/kwargs trước lắp gói; không suy ngược từ sent_package")
    args = parser.parse_args(argv)
    try:
        result = capture(db=args.db, project=args.project, shot=args.shot, flags_file=args.flags_file,
                         ref_root=args.ref_root, purpose=args.purpose, input_snapshots_file=args.input_snapshots_file)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    except GoldenError as exc:
        parser.exit(2, str(exc) + "\n")
    except (OSError, ValueError, sqlite3.Error):
        # CLI không xuất exception chứa nội dung JSON/đường dẫn nhạy cảm.
        parser.exit(2, "Chụp thất bại: kiểm schema, trường bắt buộc, flags và đầu ra chưa tồn tại; dùng API để xem mã lỗi đã lược bỏ.\n")
    return 0


def replay_builder(snapshot, *, ref_root):
    """Replay biên lắp sổ gửi từ input trước lắp gói; không chạy prepare/send/poll.

    Snapshot độc lập chứa args/kwargs/meta, bytes ref nằm trong ref_root; baseline
    chỉ dùng ở comparator bên ngoài, không bao giờ làm đầu vào builder.
    """
    import datetime
    import os
    import socket
    from unittest.mock import patch
    required = {"kind", "args", "kwargs", "sent_kwargs", "job", "meta", "external_id", "at", "provider", "files", "flags"}
    if not isinstance(snapshot, dict) or required - snapshot.keys():
        raise GoldenError("snapshot thiếu trường bắt buộc trước lắp gói")
    _safe(snapshot)
    if snapshot["kind"] not in ("image", "video") or snapshot["provider"] not in ("fake", "clipai", "deepix"):
        raise GoldenError("Replay cần tên provider trong whitelist và loại image/video")
    if not isinstance(snapshot["flags"], dict) or any(type(v) is not bool for v in snapshot["flags"].values()) or any(snapshot["flags"].get(k) is not False for k in snapshot.get("experimental_flags", snapshot["flags"])):
        raise GoldenError("COMPAT replay cần cờ TẮT explicit")
    root = Path(ref_root).resolve()
    for name, digest in snapshot["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise GoldenError("snapshot ref thiếu/sai hash/ngoài phạm vi")
    # Mọi đường dẫn ref trong input phải được đóng băng và kiểm hash trước đọc.
    from_names = {"image_path", "references", "image_references", "reference_video", "last_frame", "reference_only", "reference_audio"}
    def check_ref(item):
        if isinstance(item, list):
            for value in item:
                check_ref(value)
        else:
            name = item.get("path") or item.get("file") or item.get("url") if isinstance(item, dict) else item
            if name and name not in snapshot["files"]:
                raise GoldenError("snapshot ref chưa đóng băng")
    args = snapshot["args"]
    if snapshot["kind"] == "image" and len(args) > 1:
        check_ref(args[1])
    if snapshot["kind"] == "video" and args:
        check_ref(args[0])
    if snapshot["kind"] == "video":
        for index in (7, 8):
            if len(args) > index:
                check_ref(args[index])
    for mapping in (snapshot["kwargs"], snapshot["sent_kwargs"]):
        for key in from_names & mapping.keys():
            check_ref(mapping[key])
        if mapping.get("_from_sample"):
            raise GoldenError("snapshot nâng nháp cần snapshot CSDL riêng; chưa hỗ trợ")
    moment = datetime.datetime.fromisoformat(snapshot["at"])
    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return moment
    def forbidden(*args, **kwargs):
        raise GoldenError("Replay cấm mạng/provider/subprocess")
    class FakeProvider:
        name = snapshot["provider"]
        submit = staticmethod(forbidden)
        submit_final_from_sample = staticmethod(forbidden)
    # Thay object env trước import ứng dụng; không khởi tạo registry/credential/client.
    with patch.object(os, "environ", {}), patch.object(socket, "socket", forbidden), patch.object(socket, "create_connection", forbidden), patch.object(subprocess, "Popen", forbidden):
        from core import runner, sent_package, features
        cls = runner.ImageRunner if snapshot["kind"] == "image" else runner.VideoRunner
        instance = object.__new__(cls)
        instance.provider = FakeProvider()
        instance._sent = {snapshot["job"]["id"]: snapshot["meta"]}
        instance._pregen_fingerprints = {snapshot["job"]["id"]: snapshot.get("pregen_fingerprint")}
        previous = Path.cwd()
        try:
            os.chdir(root)
            with patch.object(features, "on", side_effect=lambda name: snapshot["flags"].get(name, False)), patch.object(features, "active", side_effect=lambda name: snapshot["flags"].get(name, False)), patch.object(sent_package, "ROOT", str(root)), patch.object(sent_package.datetime, "datetime", FrozenDateTime):
                raw, warnings = instance._build_package(snapshot["job"], args, snapshot["kwargs"], snapshot["sent_kwargs"], snapshot["external_id"])
        finally:
            os.chdir(previous)
    if raw is None or warnings:
        raise GoldenError("Replay builder thiếu input hoặc không lắp được gói")
    return raw.encode("utf-8")


def check_correctness(actual, expectations):
    """Tiêu chí do người viết ca khai riêng; COMPAT xanh không suy ra đúng."""
    body = json.loads(actual)
    failures = []
    if any(text not in (body.get("prompt") or "") for text in expectations.get("prompt_contains", [])):
        failures.append("prompt_contains")
    if "ref_roles" in expectations and [r["role"] for r in body["refs"]] != expectations["ref_roles"]:
        failures.append("ref_roles")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
