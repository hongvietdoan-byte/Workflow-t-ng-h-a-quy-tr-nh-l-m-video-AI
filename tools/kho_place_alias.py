"""Đề xuất bí danh tiếng Anh cho địa điểm FF trong Kho; mặc định chỉ đọc, 0 USD.

Nguồn đề xuất là tên/bí danh tiếng Anh đã có trên một mục địa điểm FF khớp
chính xác sau chuẩn hoá dấu. Không dịch, không gọi mạng/API, không mở CSDL ghi.
`--lam-that` chỉ áp dụng các đề xuất duy nhất sau khi sao lưu manifest bằng
`tools/don_rac.py sao-luu`; cần chạy từ repo chính và chỉ định CSDL rõ ràng.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from core import assets
from core.seedance_refs import has_vietnamese


ROOT = Path(__file__).resolve().parents[1]
_ALIAS_SPLIT = re.compile(r"[,;|]")
_BACKUP_ENV_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONUTF8", "PYTHONIOENCODING")


def _aliases(asset: dict) -> list[str]:
    return [value.strip() for value in _ALIAS_SPLIT.split(str(asset.get("aliases") or "")) if value.strip()]


def _names(asset: dict) -> list[str]:
    return [name for name in [str(asset.get("name") or "").strip(), *_aliases(asset)] if name]


def _has_english_name(asset: dict) -> bool:
    return any(not has_vietnamese(name) for name in _names(asset))


def _english_candidates(asset: dict) -> set[str]:
    """Tên Anh đã tồn tại; không tự dịch hay bỏ dấu tên Việt để tạo alias."""
    return {name for name in _names(asset) if not has_vietnamese(name)}


def _candidate_for(target: dict, locations: list[dict]) -> tuple[str | None, str]:
    target_keys = {assets.fold(name) for name in _names(target) if assets.fold(name)}
    candidates: set[str] = set()
    for source in locations:
        if source["id"] == target["id"]:
            continue
        source_keys = {assets.fold(name) for name in _names(source) if assets.fold(name)}
        if not target_keys.intersection(source_keys):
            continue
        candidates.update(_english_candidates(source))

    own_keys = {assets.fold(name) for name in _names(target)}
    candidates = {name for name in candidates if assets.fold(name) not in own_keys}
    if len(candidates) == 1:
        return next(iter(candidates)), "mục Kho FF trùng tên"
    if len(candidates) > 1:
        return None, "nhiều nguồn tiếng Anh khớp; cần duyệt thủ công"
    return None, "không có nguồn tiếng Anh khớp chính xác"


def scan_locations(conn) -> list[dict]:
    """Liệt kê địa điểm FF thiếu bí danh Anh và đề xuất từ catalog cục bộ."""
    locations = assets.list_assets(conn, game="FF", kind="location")
    missing = [item for item in locations if not _has_english_name(item)]
    result = []
    for item in missing:
        suggestion, source = _candidate_for(item, locations)
        result.append({
            "id": item["id"],
            "name": item["name"],
            "aliases": item.get("aliases") or "",
            "suggested_alias": suggestion,
            "source": source,
        })
    return result


def open_readonly(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """Mở CSDL có sẵn ở mode=ro; không tạo file, migrate hoặc ghi."""
    db = Path(path).expanduser().resolve(strict=True)
    if not db.is_file():
        raise ValueError("Đường dẫn CSDL không phải tệp thường.")
    conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _manifest_path(path: str | os.PathLike[str]) -> Path:
    db = Path(path).expanduser().resolve(strict=True)
    expected = (ROOT / "data" / "manifest.sqlite").resolve()
    if os.path.normcase(str(db)) != os.path.normcase(str(expected)):
        raise ValueError("Chỉ cho phép --lam-that với data/manifest.sqlite của repo đang chạy.")
    return db


def backup_database(path: str | os.PathLike[str]) -> None:
    """Gọi quy trình sao lưu hiện có; lỗi sao lưu sẽ chặn hoàn toàn bước ghi."""
    db = _manifest_path(path)
    command = [
        sys.executable,
        str(ROOT / "tools" / "don_rac.py"),
        "--goc", str(ROOT),
        "sao-luu", str(db),
        "--loai", "a2f-place-alias",
        "--lam-that",
    ]
    env = {key: os.environ[key] for key in _BACKUP_ENV_KEYS if os.environ.get(key)}
    result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True, env=env)
    if result.returncode:
        raise RuntimeError("Sao lưu manifest thất bại; đã dừng trước khi ghi bí danh.")


def write_proposals(
    path: str | os.PathLike[str],
    proposals: Iterable[dict],
    *,
    backup=backup_database,
) -> int:
    """Ghi các đề xuất duy nhất trong một transaction sau khi sao lưu thành công."""
    db = _manifest_path(path)
    rows = [row for row in proposals if row.get("suggested_alias")]
    if not rows:
        return 0

    backup(db)
    conn = sqlite3.connect(str(db), timeout=5)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        catalog = [dict(row) for row in conn.execute(
            "SELECT id, game, kind, name, aliases FROM assets WHERE game='FF' AND kind='location'"
        )]
        current_by_id = {row["id"]: row for row in catalog}
        for item in rows:
            alias = str(item["suggested_alias"]).strip()
            if not alias or has_vietnamese(alias):
                raise ValueError("Đề xuất không phải tên Anh; transaction đã huỷ.")
            old_aliases = str(item.get("aliases") or "").strip()
            current = current_by_id.get(item["id"])
            if (current is None or current["name"] != item["name"]
                    or str(current["aliases"] or "").strip() != old_aliases):
                raise RuntimeError(f"Mục Kho #{item['id']} đã đổi hoặc không còn; transaction đã huỷ.")
            verified, _source = _candidate_for(current, catalog)
            if verified != alias:
                raise RuntimeError(f"Bí danh cho mục Kho #{item['id']} không còn là đề xuất duy nhất; transaction đã huỷ.")
            next_aliases = f"{old_aliases}, {alias}" if old_aliases else alias
            cursor = conn.execute(
                "UPDATE assets SET aliases=? WHERE id=? AND game='FF' AND kind='location' "
                "AND name=? AND COALESCE(aliases,'')=?",
                (next_aliases, item["id"], item["name"], old_aliases),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Mục Kho #{item['id']} đã đổi hoặc không còn; transaction đã huỷ.")
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _print_report(rows: list[dict], *, approvals: dict[int, str] | None = None) -> None:
    if approvals is None:
        print("CX23-A2F-ALIAS · CHẾ ĐỘ CHỈ ĐỌC · chưa ghi · không gọi mạng/API")
    else:
        approved = ", ".join(f"{asset_id}={alias}" for asset_id, alias in approvals.items())
        print(f"CX23-A2F-ALIAS · CHẾ ĐỘ GHI · chỉ áp dụng ID và bí danh đã duyệt: {approved}")
    if not rows:
        print("Không có địa điểm FF nào đang thiếu bí danh tiếng Anh.")
        return
    for row in rows:
        proposal = row["suggested_alias"] or "—"
        print(f"#{row['id']} | {row['name']} | đề xuất: {proposal} | nguồn: {row['source']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Liệt kê địa điểm FF thiếu bí danh Anh; mặc định chỉ in, không ghi.")
    parser.add_argument("--db", required=True, help="đường dẫn CSDL hiện có; không tự chọn data/manifest.sqlite")
    parser.add_argument("--lam-that", action="store_true", help="cho phép ghi sau khi xác nhận đúng ID và bí danh đã xem")
    parser.add_argument("--duyet", action="append", dest="approvals", metavar="ID=BI_DANH",
                        help="cặp ID và bí danh chính xác đã xem trong bản xem trước; có thể lặp lại")
    args = parser.parse_args(argv)
    approvals: dict[int, str] = {}
    for value in args.approvals or []:
        raw_id, separator, alias = value.partition("=")
        try:
            asset_id = int(raw_id)
        except ValueError:
            parser.error("--duyet phải có dạng ID=BI_DANH, ví dụ --duyet '12=Clock Tower'.")
        if not separator or asset_id <= 0 or not alias.strip() or alias != alias.strip():
            parser.error("--duyet phải có ID dương và bí danh chính xác, không rỗng hoặc thừa khoảng trắng.")
        if asset_id in approvals:
            parser.error("Mỗi ID chỉ được duyệt một lần.")
        approvals[asset_id] = alias
    if args.lam_that and not approvals:
        parser.error("--lam-that cần ít nhất một --duyet ID=BI_DANH đã xem trong bản xem trước.")
    if not args.lam_that and approvals:
        parser.error("--duyet chỉ dùng cùng --lam-that sau khi đã xem bản đề xuất.")
    try:
        with open_readonly(args.db) as conn:
            rows = scan_locations(conn)
        approved_rows = None
        if args.lam_that:
            proposals = {row["id"]: row for row in rows if row.get("suggested_alias")}
            if any(
                asset_id not in proposals or proposals[asset_id]["suggested_alias"] != alias
                for asset_id, alias in approvals.items()
            ):
                print("Đề xuất không còn khớp chính xác ID và bí danh đã duyệt; không ghi gì.", file=sys.stderr)
                return 2
            approved_rows = [proposals[asset_id] for asset_id in approvals]
        _print_report(rows, approvals=approvals if args.lam_that else None)
        if approved_rows is not None:
            count = write_proposals(args.db, approved_rows)
            print(f"Đã ghi {count} bí danh đã duyệt sau khi sao lưu manifest.")
        return 0
    except (OSError, sqlite3.Error, RuntimeError, ValueError) as exc:
        print(f"Lỗi an toàn khi xử lý bí danh Kho: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
