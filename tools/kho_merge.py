"""Gộp hai mục Kho trùng nhau (S14.43B, 06/10/2026) — 0 USD, mặc định CHẠY THỬ (chỉ in kế hoạch); thêm --yes mới ghi.

    py tools/kho_merge.py --keep 303 --merge 414                 chạy thử: in ảnh nào chuyển, file nào dời, tên/alias/hồ sơ, bảng nào đổi
    py tools/kho_merge.py --keep 303 --merge 414 --yes           làm thật (tự sao lưu CSDL trước, một giao dịch)
    py tools/kho_merge.py --find-duplicates [--game FF]          liệt kê các cặp nghi trùng (KHÔNG tự gộp)

Chạy từ worktree: thêm --db D:/AI-Video-Pipeline/data/manifest.sqlite (ảnh luôn ở <thư mục CSDL>/assets, không theo thư mục đang chạy).

Luật gộp (mục giữ = --keep, mục bỏ = --merge):
  - cùng game + cùng loại, nếu không → từ chối; tổng ảnh (trừ thùng rác) ≤ 6, nếu không → từ chối; chưa đổi gì;
  - tên: giữ tên mục giữ; chỉ chuẩn hóa cách viết danh xưng 'Mr.Waggor' → 'Mr. Waggor' (cùng name_key nên tra tên cũ vẫn khớp;
    --keep-name để giữ nguyên);
  - tên gọi khác: hợp nhất cả hai + tên mục bỏ, bỏ trùng (so bằng assets.name_key) và bỏ cái trùng tên chính;
  - hồ sơ chuẩn: mục giữ chưa có → lấy của mục bỏ; cả hai có mà khác nhau → từ chối (người chọn một trước);
  - mô tả: giữ cả hai, mục giữ trước;
  - ảnh: MỌI dòng của mục bỏ (giữ nguyên status) chuyển sang mục giữ; file dời data/assets/<bỏ>/* → data/assets/<giữ>/<số mới>
    (không đè file có sẵn); đường dẫn lưu vẫn dạng tương đối 'data/assets/…';
  - liên kết: project_assets / project_assets_declined (dự án đã có mục giữ → bỏ dòng thừa), characters.ref_asset_id, meshy_tasks…
    (mọi bảng có cột asset_id / ref_asset_id trừ asset_images và seedance_subject_pictures — mã chủ thể ClipAI);
  - xóa mục bỏ; ghi audit_log 'kho_merge'. Lỗi giữa chừng → hoàn tác CSDL + dời file về chỗ cũ."""
import argparse
import datetime
import json
import os
import re
import shutil
import sqlite3
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core import assets  # noqa: E402

SKIP_TABLES = {"asset_images", "seedance_subject_pictures", "sqlite_sequence"}
LINK_COLUMNS = ("asset_id", "ref_asset_id")
PAIR_TABLES = {"project_assets", "project_assets_declined"}          # (project_id, asset_id) primary key: a project keeps one row
_TITLE = re.compile(r"\b(Mr|Mrs|Ms|Dr|St)\.(?=[^\s.])")


class MergeError(Exception):
    """Refused before anything changed — the message says why and what to do."""


def display_name(name: str) -> str:
    """'Mr.Waggor' -> 'Mr. Waggor' (only a title before a name; same name_key, so every lookup still matches)."""
    return _TITLE.sub(r"\1. ", name)


def _row(conn, aid: int) -> Optional[Dict]:
    r = conn.execute("SELECT * FROM assets WHERE id=?", (aid,)).fetchone()
    return dict(r) if r else None


def _link_tables(conn) -> List[tuple]:
    out = []
    for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        if t in SKIP_TABLES:
            continue
        cols = {c[1] for c in conn.execute(f'PRAGMA table_info("{t}")')}
        out += [(t, c) for c in LINK_COLUMNS if c in cols]
    return out


def _profile(raw: Optional[str]):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _check_folder(db: str) -> str:
    """The library folder that belongs to this database, or MergeError when the code would write the pictures elsewhere."""
    expected = os.path.join(os.path.dirname(os.path.abspath(db)), "assets")
    folder = assets.root()
    if os.path.normcase(os.path.abspath(folder)) != os.path.normcase(expected):
        raise MergeError(f"Thư mục ảnh Kho đang dùng ({folder}) KHÔNG nằm cạnh CSDL {db} (phải là {expected}) — bỏ ASSET_DIR / đặt "
                         "PIPELINE_DB đúng rồi chạy lại. Chưa đổi gì.")
    return folder


def make_plan(conn, keep: int, merge: int, db: str, keep_name: bool = False) -> Dict:
    """Everything the merge would do, without changing anything. MergeError when it must not run."""
    if keep == merge:
        raise MergeError("--keep và --merge phải là hai mục khác nhau")
    k, m = _row(conn, keep), _row(conn, merge)
    if m is None:
        raise MergeError(f"Không có mục #{merge} (đã gộp rồi?) — không làm gì.")
    if k is None:
        raise MergeError(f"Không có mục giữ #{keep} — không làm gì.")
    if (k["game"], k["kind"]) != (m["game"], m["kind"]):
        raise MergeError(f"Khác game/loại: #{keep} {k['game']}/{k['kind']} ≠ #{merge} {m['game']}/{m['kind']} — không gộp.")
    folder = _check_folder(db)
    kp, mp = _profile(k.get("profile")), _profile(m.get("profile"))
    if kp and mp and kp != mp:
        raise MergeError(f"Cả #{keep} và #{merge} đều có hồ sơ chuẩn và khác nhau — mở 📋 Hồ sơ chuẩn, giữ một bản rồi gộp lại. Chưa đổi gì.")
    profile_action = "lấy của mục bỏ" if (mp and not kp) else ("giữ của mục giữ" if kp else "không có")
    imgs = [dict(r) for r in conn.execute("SELECT id, path, status, sort FROM asset_images WHERE asset_id=? ORDER BY sort, id", (merge,))]
    have = assets._count(conn, keep)
    taking = sum(1 for i in imgs if i["status"] != "removed")
    if have + taking > assets.MAX_IMAGES_PER_ASSET:
        raise MergeError(f"#{keep} có {have} ảnh + #{merge} {taking} ảnh > {assets.MAX_IMAGES_PER_ASSET} — bớt ảnh trước. Chưa đổi gì.")
    kfolder = os.path.join(folder, str(keep))
    taken = assets._held_paths(conn, keep)
    moves, n = [], have
    for img in imgs:
        n += 1
        ext = os.path.splitext(img["path"])[1]
        while os.path.exists(os.path.join(kfolder, f"{n}{ext}")) or assets._path_key(os.path.join(kfolder, f"{n}{ext}")) in taken:
            n += 1
        dst = os.path.join(kfolder, f"{n}{ext}")
        taken.add(assets._path_key(dst))
        src = assets.resolve(img["path"])
        moves.append({"id": img["id"], "status": img["status"], "old_path": img["path"], "src": src if src and os.path.isfile(src) else None,
                      "dst": dst, "stored": assets.stored_path(dst), "sort": n})
    new_name = k["name"] if keep_name else display_name(k["name"])
    names, seen = [], {assets.name_key(new_name)}
    for x in assets._all_names("", k["aliases"]) + [k["name"]] + assets._all_names(m["name"], m["aliases"]):
        key = assets.name_key(x)
        if key and key not in seen:
            seen.add(key)
            names.append(x)
    kd, md = (k["description"] or "").strip(), (m["description"] or "").strip()
    description = kd if (not md or md in kd) else (f"{kd}\n\n{md}" if kd else md)
    links = []
    for t, c in _link_tables(conn):
        total = conn.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}"=?', (merge,)).fetchone()[0]
        dropped = 0
        if t in PAIR_TABLES and total:
            dropped = conn.execute(f'SELECT COUNT(*) FROM "{t}" a WHERE a."{c}"=? AND EXISTS (SELECT 1 FROM "{t}" b'
                                   f' WHERE b.project_id=a.project_id AND b."{c}"=?)', (merge, keep)).fetchone()[0]
        links.append({"table": t, "column": c, "rows": total, "dropped": dropped})
    leftovers = []
    mfolder = assets.asset_folder(merge)
    if mfolder and os.path.isdir(mfolder):
        same = lambda p: os.path.normcase(os.path.realpath(p))  # noqa: E731 - 8.3 short names (HONGVI~1) vs long names
        planned = {same(mv["src"]) for mv in moves if mv["src"]}
        leftovers = [f for f in sorted(os.listdir(mfolder)) if same(os.path.join(mfolder, f)) not in planned]
    return {"keep": k, "merge": m, "name": new_name, "aliases": ", ".join(names), "description": description,
            "profile_action": profile_action, "profile": m["profile"] if profile_action == "lấy của mục bỏ" else None,
            "moves": moves, "links": links, "merge_folder": mfolder, "leftovers": leftovers, "db": os.path.abspath(db)}


def plan_text(plan: Dict) -> str:
    k, m = plan["keep"], plan["merge"]
    out = [f"Gộp #{m['id']} “{m['name']}” → #{k['id']} “{k['name']}” ({k['game']}/{k['kind']})",
           f"  tên: “{k['name']}”" + (f" → “{plan['name']}” (chuẩn hóa cách viết danh xưng; cùng name_key)" if plan["name"] != k["name"]
                                       else " (giữ nguyên)"),
           f"  tên gọi khác: {plan['aliases'] or '(không)'}",
           f"  hồ sơ chuẩn: {plan['profile_action']}",
           f"  mô tả: giữ cả hai (mục giữ trước) — {len(plan['description'])} ký tự",
           f"  ảnh chuyển ({len(plan['moves'])}):"]
    for mv in plan["moves"]:
        src = os.path.relpath(mv["src"], os.path.dirname(os.path.dirname(plan["db"]))) if mv["src"] else "(file mất — chỉ dời hàng)"
        out.append(f"    ảnh #{mv['id']} [{mv['status']}] {src} → {mv['stored']} (sort {mv['sort']})")
    out.append("  bảng liên kết:")
    for ln in plan["links"]:
        out.append(f"    {ln['table']}.{ln['column']}: {ln['rows']} dòng dời"
                   + (f" ({ln['dropped']} dòng bỏ vì dự án đã có mục giữ)" if ln["dropped"] else ""))
    out.append(f"  asset_images: {len(plan['moves'])} dòng đổi asset_id; assets: 1 dòng sửa (#{k['id']}), 1 dòng xóa (#{m['id']}); "
               "audit_log: +1")
    if plan["leftovers"]:
        out.append(f"  ⚠ thư mục {plan['merge_folder']} còn file không thuộc hàng nào: {', '.join(plan['leftovers'])} — giữ lại, không xóa")
    return "\n".join(out)


def _backup_path(db: str, keep: int, merge: int) -> str:
    folder = os.path.join(os.path.dirname(os.path.abspath(db)), "backup")
    base = os.path.join(folder, f"manifest.before_kho_merge_{datetime.date.today().isoformat()}_{keep}_{merge}")
    path, n = base + ".sqlite", 1
    while os.path.exists(path):
        n += 1
        path = f"{base}_{n}.sqlite"
    return path


def _write_audit(conn, plan: Dict) -> None:
    k, m = plan["keep"], plan["merge"]
    conn.execute("INSERT INTO audit_log (at, email, action, detail) VALUES (datetime('now'), ?, 'kho_merge', ?)",
                 ("tools/kho_merge.py", f"#{m['id']} “{m['name']}” → #{k['id']} “{plan['name']}”: {len(plan['moves'])} ảnh, "
                                        + ", ".join(f"{x['table']}.{x['column']}={x['rows']}" for x in plan["links"] if x["rows"])))


def apply(conn, plan: Dict, db: str) -> Dict:
    """Do the plan: back up the database, move the files, change every table in ONE transaction. Any error: the transaction is rolled
    back and the files are moved back, then the error is raised again."""
    keep, merge = plan["keep"]["id"], plan["merge"]["id"]
    conn.commit()
    backup = _backup_path(db, keep, merge)
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    dst = sqlite3.connect(backup)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    moved = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        for mv in plan["moves"]:
            if mv["src"]:
                if os.path.exists(mv["dst"]):
                    raise MergeError(f"{mv['dst']} đã có file (ai đó vừa thêm ảnh?) — chạy thử lại.")
                os.makedirs(os.path.dirname(mv["dst"]), exist_ok=True)
                shutil.move(mv["src"], mv["dst"])
                moved.append((mv["src"], mv["dst"]))
            conn.execute("UPDATE asset_images SET asset_id=?, path=?, sort=? WHERE id=? AND asset_id=?",
                         (keep, mv["stored"], mv["sort"], mv["id"], merge))
        for ln in plan["links"]:
            t, c = ln["table"], ln["column"]
            if t in PAIR_TABLES:
                conn.execute(f'DELETE FROM "{t}" WHERE "{c}"=? AND project_id IN (SELECT project_id FROM "{t}" WHERE "{c}"=?)', (merge, keep))
            conn.execute(f'UPDATE "{t}" SET "{c}"=? WHERE "{c}"=?', (keep, merge))
        conn.execute("UPDATE assets SET name=?, aliases=?, description=? WHERE id=?", (plan["name"], plan["aliases"], plan["description"], keep))
        if plan["profile"]:
            conn.execute("UPDATE assets SET profile=? WHERE id=?", (plan["profile"], keep))
        left = conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (merge,)).fetchone()[0]
        if left:
            raise MergeError(f"Còn {left} ảnh của #{merge} chưa chuyển (vừa có ảnh mới?) — đã hoàn tác, chạy thử lại.")
        conn.execute("DELETE FROM assets WHERE id=?", (merge,))
        _write_audit(conn, plan)
        conn.commit()
    except BaseException:
        conn.rollback()
        for src, dst_ in reversed(moved):
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dst_, src)
            except OSError as e:                      # said, never silent: the database is back, this file is not
                print(f"⚠ KHÔNG dời lại được {dst_} → {src}: {e} — dời tay (CSDL đã hoàn tác; sao lưu: {backup})", file=sys.stderr)
        raise
    folder = plan["merge_folder"]
    removed_folder = False
    if folder and os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)
        removed_folder = True
    return {"backup": backup, "moved_files": len(moved), "rows": len(plan["moves"]), "removed_folder": removed_folder,
            "leftovers": plan["leftovers"]}


def duplicates_text(conn, game: Optional[str]) -> str:
    pairs = assets.find_duplicates(conn, game)
    if not pairs:
        return "Không thấy cặp nghi trùng."
    count = lambda aid: conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=? AND status IS NOT 'removed'", (aid,)).fetchone()[0]  # noqa: E731
    out = [f"{len(pairs)} cặp nghi trùng (cùng game + loại, chung name_key qua tên / tên gọi khác) — KHÔNG tự gộp:"]
    for p in pairs:
        a, b = p["a"], p["b"]
        scope = lambda r: "dùng chung" if r["project_id"] is None else f"dự án {r['project_id']}"  # noqa: E731
        out.append(f"  {a['game']}/{a['kind']}: #{a['id']} “{a['name']}” ({count(a['id'])} ảnh, {scope(a)}) ~ #{b['id']} “{b['name']}” "
                   f"({count(b['id'])} ảnh, {scope(b)}) — chung: {', '.join(p['keys'])}")
        out.append(f"      gộp thử: py tools/kho_merge.py --keep {a['id']} --merge {b['id']}")
    return "\n".join(out)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB") or os.path.join(assets.REPO, "data", "manifest.sqlite"))
    ap.add_argument("--keep", type=int)
    ap.add_argument("--merge", type=int)
    ap.add_argument("--yes", action="store_true", help="làm thật (mặc định chỉ chạy thử)")
    ap.add_argument("--keep-name", action="store_true", help="không chuẩn hóa cách viết tên mục giữ")
    ap.add_argument("--find-duplicates", action="store_true")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    db = os.path.abspath(a.db)
    if not os.path.isfile(db):
        print(f"Không thấy CSDL {db}", file=sys.stderr)
        return 2
    os.environ["PIPELINE_DB"] = db                  # pictures next to THIS database, whatever the working folder
    os.environ.pop("ASSET_DIR", None)
    from core.db import connect
    conn = connect(db)
    try:
        if a.find_duplicates:
            print(duplicates_text(conn, a.game))
            return 0
        if a.keep is None or a.merge is None:
            ap.error("cần --keep và --merge (hoặc --find-duplicates)")
        try:
            plan = make_plan(conn, a.keep, a.merge, db, keep_name=a.keep_name)
        except MergeError as e:
            print(f"KHÔNG GỘP: {e}")
            return 1
        print(plan_text(plan))
        if not a.yes:
            print("\nCHẠY THỬ — chưa đổi gì. Thêm --yes để làm thật (tự sao lưu CSDL trước).")
            return 0
        rep = apply(conn, plan, db)
        print(f"\nĐÃ GỘP. Sao lưu CSDL: {rep['backup']}; dời {rep['moved_files']} file, {rep['rows']} dòng ảnh; "
              f"thư mục cũ {'đã xóa (rỗng)' if rep['removed_folder'] else 'còn giữ'}.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
