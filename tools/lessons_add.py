"""KLD-21 (08/10) — nạp bài học TỔNG KẾT DỰ ÁN từ một bảng markdown vào bảng `lessons` (trạng thái 'proposed', độ tin "1 dự án").

  py tools/lessons_add.py --db data/manifest.sqlite --from docs/TONG_HOP_3_LUOT_KHUNG_LONG_DO.md --section 6 --source project_review:22
        CHẠY THỬ (mặc định): in bài nào sẽ vào / bỏ qua / đã có — KHÔNG ghi (mở CSDL chỉ đọc)
  ... --yes   ghi thật: sao lưu CSDL trước (<thư mục CSDL>/backup/manifest.before_lessons_add_<giờ>.sqlite), rồi ghi qua
              core.lessons.add_project_review

Bảng cần các cột: #, Nhóm, Tiêu đề, Bối cảnh, Phát hiện, Nguồn. Nhóm phải là nhóm của core.knowledge.GROUPS (director / motion / qc);
nhóm khác ("(code)", "(quy trình)", "(tổng)") là việc code / quy trình, không phải bài học cho prompt → bỏ qua và in ra.
Chống trùng: khóa project_review:<dự án>:<mã L#> — nạp lại không thêm dòng. Bài học chỉ tới prompt khi người duyệt ở tab Bài học.
"""
import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import knowledge, lessons  # noqa: E402

COLUMNS = {"#": "ref", "nhóm": "group", "tiêu đề": "title", "bối cảnh": "context", "phát hiện": "finding", "nguồn": "origin"}
SOURCE = re.compile(r"^project_review:(\d+)$")


def _cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_section(text: str, section: str) -> list:
    """Rows of the first table with the columns above inside the '## <section>.' part of the document."""
    lines, inside, out, head = text.splitlines(), False, [], None
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = re.match(rf"##\s+{re.escape(section)}[.\s]", line) is not None
            continue
        if not inside or not line.strip().startswith("|"):
            if head and out:
                break                                       # the table ended
            continue
        cells = _cells(line)
        if head is None:
            names = [c.lower() for c in cells]
            if all(k in names for k in COLUMNS):
                head = [COLUMNS.get(n) for n in names]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue                                        # |---|---|
        out.append({k: v for k, v in zip(head, cells) if k})
    if head is None:
        raise ValueError(f"không thấy bảng có cột {', '.join(COLUMNS)} trong mục {section}")
    return out


def plan(rows: list) -> dict:
    ok, skipped = [], []
    for r in rows:
        group = r.get("group", "").strip().strip("`").lower()
        if group in knowledge.GROUPS and r.get("title") and r.get("finding"):
            ok.append(dict(r, group=group))
        else:
            skipped.append(dict(r, why=f"nhóm '{r.get('group')}' không phải {'/'.join(knowledge.GROUPS)} (việc code / quy trình)"
                                if group not in knowledge.GROUPS else "thiếu tiêu đề / phát hiện"))
    return {"ok": ok, "skipped": skipped}


def _backup(db: str) -> str:
    folder = os.path.join(os.path.dirname(db), "backup")
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, f"manifest.before_lessons_add_{datetime.now():%Y%m%d_%H%M%S}.sqlite")
    src, dst = sqlite3.connect(db), sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "manifest.sqlite"))
    ap.add_argument("--from", dest="src", required=True, help="tệp markdown có bảng bài học")
    ap.add_argument("--section", required=True, help="số mục (vd 6)")
    ap.add_argument("--source", required=True, help="project_review:<mã dự án>")
    ap.add_argument("--dry-run", action="store_true", help="(mặc định) chỉ in, không ghi")
    ap.add_argument("--yes", action="store_true", help="ghi thật (sao lưu CSDL trước)")
    a = ap.parse_args(argv)
    m = SOURCE.match(a.source)
    if not m:
        print("--source phải có dạng project_review:<mã dự án> (vd project_review:22)", file=sys.stderr)
        return 2
    pid = int(m.group(1))
    db = os.path.abspath(a.db)
    if not os.path.exists(db):
        print(f"Không thấy CSDL {db}", file=sys.stderr)
        return 2
    try:
        rows = parse_section(open(a.src, encoding="utf-8").read(), a.section)
    except (OSError, ValueError) as e:
        print(f"Không đọc được bảng: {e}", file=sys.stderr)
        return 2
    p = plan(rows)
    write = a.yes and not a.dry_run
    doc = os.path.relpath(os.path.abspath(a.src), ROOT) if os.path.splitdrive(os.path.abspath(a.src))[0] == os.path.splitdrive(ROOT)[0] \
        else os.path.abspath(a.src)
    print(("GHI THẬT" if write else "CHẠY THỬ (không ghi; thêm --yes để ghi)") + f" · {db} · nguồn {a.source} · {len(rows)} dòng bảng")
    if write:
        from core.db import connect
        print(f"Đã sao lưu: {_backup(db)}")
        conn = connect(db)
    else:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        have = {r[0] for r in conn.execute("SELECT key FROM lessons")} if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lessons'").fetchone() else set()
        new, by = 0, {}
        for r in p["ok"]:
            key = f"{lessons.PROJECT_REVIEW}:{pid}:{r['ref']}"
            if key in have:
                print(f"  = {r['ref']:4} [{r['group']}] đã có ({key}) — bỏ qua")
                continue
            if write:
                lessons.add_project_review(conn, r["group"], r["ref"], r["title"], r["finding"], project_id=pid,
                                           context=r.get("context", ""), origin=r.get("origin", ""), doc=doc)
            new += 1
            by[r["group"]] = by.get(r["group"], 0) + 1
            print(f"  + {r['ref']:4} [{r['group']}] {r['title']}")
        for r in p["skipped"]:
            print(f"  - {r.get('ref', '?'):4} bỏ qua: {r['why']} — {r.get('title', '')}")
        print(f"{'Đã ghi' if write else 'Sẽ ghi'} {new} bài (trạng thái proposed, độ tin 1 dự án) · theo nhóm: "
              + ", ".join(f"{g} {n}" for g, n in sorted(by.items())) + f" · bỏ qua {len(p['skipped'])}"
              + ("" if write else " · người duyệt ở tab Bài học sau khi ghi"))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
