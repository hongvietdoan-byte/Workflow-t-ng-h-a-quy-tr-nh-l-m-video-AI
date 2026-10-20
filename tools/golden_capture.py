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


def capture(*, db, project, shot, flags_file, ref_root, purpose):
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
                         "sent_package_raw": raw, "sent_package_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(), "refs": refs})
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
    args = parser.parse_args(argv)
    try:
        result = capture(db=args.db, project=args.project, shot=args.shot, flags_file=args.flags_file,
                         ref_root=args.ref_root, purpose=args.purpose)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
    except GoldenError as exc:
        parser.exit(2, str(exc) + "\n")
    except (OSError, ValueError, sqlite3.Error):
        # CLI không xuất exception chứa nội dung JSON/đường dẫn nhạy cảm.
        parser.exit(2, "Chụp thất bại: kiểm schema, trường bắt buộc, flags và đầu ra chưa tồn tại; dùng API để xem mã lỗi đã lược bỏ.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
