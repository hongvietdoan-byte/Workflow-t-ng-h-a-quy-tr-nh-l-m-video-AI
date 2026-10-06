"""S14.46 — cất bài học / lỗi đã ghi / ca kinh nghiệm thuộc chủ đề đã bỏ (phông xanh, sync.so, 5 cờ S14.9…) để chúng không vào prompt.

  py tools/lessons_retire.py                      CHẠY THỬ (mặc định): in danh sách ứng viên, KHÔNG đổi gì (mở CSDL chỉ đọc)
  py tools/lessons_retire.py --yes                cất: sao lưu CSDL trước (data/backup/manifest.before_lessons_retire_<ngày>.sqlite),
                                                  một giao dịch, ghi danh sách + lý do ra docs/BAI_HOC_DA_CAT_<ngày>.md
  py tools/lessons_retire.py --yes --keep mistakes:7 --keep experience_cases:12   cất trừ các dòng giữ lại
  py tools/lessons_retire.py --restore mistakes:96,experience_cases:143   khôi phục từng dòng (hoặc --restore all)
  py tools/lessons_retire.py --list-retired       các dòng đang cất

"Cất" = điền retired_at / retired_why, dòng vẫn ở bảng của nó (không xóa: các nguồn nhập lại theo khóa sẽ không chép lại nó). Chủ đề
và từ khóa: core/retired_topics.py (+ data/retired_topics.json sửa tay). CSDL: --db, mặc định PIPELINE_DB hoặc <repo>/data/manifest.sqlite
(đường dẫn tuyệt đối, không phụ thuộc thư mục đang đứng).
"""
import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import retired_topics  # noqa: E402

LABEL = {"mistakes": "lỗi đã ghi (mistakes)", "lessons": "bài học (lessons)", "experience_cases": "ca kinh nghiệm (experience_cases)"}
CONTEXT = {"mistakes": "source || ':' || ref_id || ' · dự án ' || coalesce(project_id,'?') || ' · ' || stage",
           "lessons": "group_name || ' · ' || state || ' · ' || key",
           "experience_cases": "key || ' · dự án ' || coalesce(project_id,'?') || ' · ' || coalesce(stage,'') || ' · ' || coalesce(outcome,'')"}
REF = re.compile(r"^(mistakes|lessons|experience_cases):(\d+)$")


def default_db() -> str:
    return os.path.abspath(os.environ.get("PIPELINE_DB") or os.path.join(ROOT, "data", "manifest.sqlite"))


def _tables(conn) -> list:
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return [t for t in retired_topics.TABLES if t in have]


def candidates(conn, keep=frozenset()) -> list:
    """Rows not retired yet whose text names a retired topic: [{table, id, context, text, topics}]."""
    out = []
    for table in _tables(conn):
        where = " WHERE retired_at IS NULL" if retired_topics.has_columns(conn, table) else ""
        sql = f"SELECT id, {CONTEXT[table]} AS ctx, {retired_topics.TABLES[table]} AS txt FROM {table}{where} ORDER BY id"
        for rid, ctx, txt in conn.execute(sql).fetchall():
            hits = retired_topics.matches(txt or "")
            if hits and f"{table}:{rid}" not in keep:
                out.append({"table": table, "id": rid, "context": ctx or "", "text": txt or "", "topics": hits})
    return out


def _why(topics) -> str:
    return "; ".join(f"{t}: {retired_topics.why(t)}" for t in topics)


def print_list(rows, title) -> None:
    print(title)
    if not rows:
        print("  (không có)")
        return
    summary = {}
    for r in rows:
        for t in r["topics"]:
            summary[(r["table"], t)] = summary.get((r["table"], t), 0) + 1
    for (table, topic), n in sorted(summary.items()):
        print(f"  {LABEL[table]} · {topic}: {n}")
    print()
    for r in rows:
        snippet = re.sub(r"\s+", " ", r["text"])[:110]
        print(f"  [{r['table']}:{r['id']}] {','.join(r['topics'])} | {r['context']} | {snippet}")


def knowledge_report() -> None:
    """Knowledge documents naming a retired topic: the person's uploads / distilled playbook (flagged, never cut automatically) and the
    built-in files (informational: repo documents, changed by hand when they are wrong)."""
    from core import knowledge
    print("\nTài liệu kiến thức nhắc chủ đề đã bỏ:")
    any_hit = False
    for group in knowledge.GROUPS:
        for f in knowledge.retired_in_docs(group):
            any_hit = True
            print(f"  [người dùng · {group}] {f['title']} ({f['file']}): {', '.join(f['topics'])} — sửa/tắt tay hoặc chắt lọc lại (tốn tiền)")
    for base in ("knowledge", "prompts"):
        for dirpath, _, files in os.walk(os.path.join(ROOT, base)):
            for name in files:
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        hits = retired_topics.matches(line)
                        if hits:
                            any_hit = True
                            print(f"  [có sẵn, chỉ báo] {os.path.relpath(path, ROOT)}:{n} {','.join(hits)} | {line.strip()[:100]}")
    if not any_hit:
        print("  (không có)")


def backup(db: str, backup_dir: str) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    stem = f"manifest.before_lessons_retire_{datetime.now():%Y-%m-%d}"
    path = os.path.join(backup_dir, stem + ".sqlite")
    if os.path.exists(path):
        path = os.path.join(backup_dir, f"{stem}_{datetime.now():%H%M%S}.sqlite")
    src = sqlite3.connect(db)
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
        dst.execute("PRAGMA journal_mode = DELETE")     # one self-contained file (the source is WAL: no -wal / -shm beside the copy)
    finally:
        dst.close()
        src.close()
    check = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit(f"Bản sao lưu {path} không toàn vẹn — dừng, chưa cất gì.")
    finally:
        check.close()
    return path


def _sync_lessons(conn, groups) -> None:
    if not groups:
        return
    from core import lessons
    conn.row_factory = sqlite3.Row
    for g in sorted(groups):
        try:
            lessons.sync_knowledge(conn, g)
            print(f"  đã viết lại tài liệu bài học của bước '{g}'")
        except Exception as e:  # noqa: BLE001 - the retirement itself is done; say what is left
            print(f"  CHƯA viết lại được tài liệu bài học của bước '{g}': {e} — mở tab Bài học rồi duyệt lại một bài để ghi lại")


def retire(db: str, rows, backup_dir: str, docs_dir: str) -> None:
    saved = backup(db, backup_dir)
    print(f"Đã sao lưu: {saved}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db, timeout=60)
    groups = set()
    try:
        conn.execute("BEGIN IMMEDIATE")
        retired_topics.ensure_columns(conn)
        done = 0
        for r in rows:
            cur = conn.execute(f"UPDATE {r['table']} SET retired_at=?, retired_why=? WHERE id=? AND retired_at IS NULL",
                               (now, f"S14.46 · {_why(r['topics'])}", r["id"]))
            done += cur.rowcount
            if r["table"] == "lessons" and cur.rowcount:
                groups.add(conn.execute("SELECT group_name FROM lessons WHERE id=?", (r["id"],)).fetchone()[0])
        if done != len(rows):
            raise RuntimeError(f"chỉ cất được {done}/{len(rows)} dòng (dòng đổi trong lúc chạy?)")
        conn.commit()
    except BaseException:
        conn.rollback()
        conn.close()
        print("Lỗi — đã hoàn tác, CSDL như trước khi chạy (bản sao lưu vẫn giữ).")
        raise
    print(f"Đã cất {done} dòng (retired_at = {now}).")
    _sync_lessons(conn, groups)
    conn.close()
    path = write_doc(rows, docs_dir, saved, now, db)
    print(f"Danh sách + lý do: {path}")


def write_doc(rows, docs_dir: str, saved: str, now: str, db: str) -> str:
    os.makedirs(docs_dir, exist_ok=True)
    day = now[:10]
    path = os.path.join(docs_dir, f"BAI_HOC_DA_CAT_{day}.md")
    if os.path.exists(path):
        path = os.path.join(docs_dir, f"BAI_HOC_DA_CAT_{day}_{now[11:].replace(':', '')}.md")
    topics = {}
    for r in rows:
        for t in r["topics"]:
            topics.setdefault(t, []).append(r)
    lines = [f"# Bài học / kinh nghiệm đã cất — {day} (S14.46)", "",
             "Người dùng 06/10: \"bài học nào không dùng đến cũng nên loại bỏ, tránh gây nhầm lẫn cho Đạo diễn\". Các dòng dưới đây "
             "thuộc tính năng đã bỏ nên KHÔNG còn đưa vào prompt. Không xóa: dòng vẫn ở bảng của nó, có `retired_at` / `retired_why`.", "",
             f"- Lúc cất: {now} · số dòng: {len(rows)}",
             f"- CSDL: `{os.path.basename(db)}` · bản sao lưu trước khi cất: `{os.path.basename(saved)}` (thư mục `data/backup/`)",
             "- Khôi phục một dòng: `py tools/lessons_retire.py --restore mistakes:<id>` (nhiều dòng cách nhau dấu phẩy; tất cả: `--restore all`). "
             "Dòng khôi phục mà vẫn khớp chủ đề đã bỏ thì bộ lọc lúc đọc (core/retired_topics.py) vẫn chặn — muốn dùng lại phải bỏ chủ đề "
             "đó (data/retired_topics.json: `{\"<chủ đề>\": null}`).", "",
             "## Theo chủ đề", ""]
    for t, items in sorted(topics.items()):
        lines.append(f"- **{t}** ({len(items)}): {retired_topics.why(t)}")
    lines += ["", "## Từng dòng", "", "| Bảng:id | Ngữ cảnh | Chủ đề | Nội dung |", "|---|---|---|---|"]
    for r in rows:
        text = re.sub(r"\s+", " ", r["text"]).replace("|", "/")[:300]
        lines.append(f"| {r['table']}:{r['id']} | {r['context'].replace('|', '/')} | {', '.join(r['topics'])} | {text} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def restore(db: str, spec: str) -> None:
    conn = sqlite3.connect(db, timeout=60)
    groups = set()
    try:
        conn.execute("BEGIN IMMEDIATE")
        retired_topics.ensure_columns(conn)
        n = 0
        if spec.strip() == "all":
            for table in _tables(conn):
                if table == "lessons":
                    groups |= {g for (g,) in conn.execute("SELECT DISTINCT group_name FROM lessons WHERE retired_at IS NOT NULL")}
                n += conn.execute(f"UPDATE {table} SET retired_at=NULL, retired_why=NULL WHERE retired_at IS NOT NULL").rowcount
        else:
            for ref in [x.strip() for x in spec.split(",") if x.strip()]:
                m = REF.match(ref)
                if not m:
                    raise SystemExit(f"'{ref}' không đúng dạng bảng:id (bảng ∈ {', '.join(retired_topics.TABLES)})")
                table, rid = m.group(1), int(m.group(2))
                got = conn.execute(f"UPDATE {table} SET retired_at=NULL, retired_why=NULL WHERE id=? AND retired_at IS NOT NULL",
                                   (rid,)).rowcount
                if not got:
                    print(f"  {ref}: không có dòng đang cất với id này — bỏ qua")
                elif table == "lessons":
                    groups.add(conn.execute("SELECT group_name FROM lessons WHERE id=?", (rid,)).fetchone()[0])
                n += got
        conn.commit()
    except BaseException:
        conn.rollback()
        conn.close()
        raise
    print(f"Đã khôi phục {n} dòng.")
    print("Lưu ý: dòng vẫn khớp chủ đề đã bỏ thì bộ lọc lúc đọc vẫn không đưa vào prompt (core/retired_topics.py).")
    _sync_lessons(conn, groups)
    conn.close()


def list_retired(conn) -> None:
    print("Các dòng đang cất:")
    any_row = False
    for table in _tables(conn):
        if not retired_topics.has_columns(conn, table):
            continue
        for rid, ctx, txt, at, why in conn.execute(f"SELECT id, {CONTEXT[table]}, {retired_topics.TABLES[table]}, retired_at, retired_why "
                                                   f"FROM {table} WHERE retired_at IS NOT NULL ORDER BY id"):
            any_row = True
            print(f"  [{table}:{rid}] {at} | {why} | {ctx} | {re.sub(r'\s+', ' ', txt or '')[:90]}")
    if not any_row:
        print("  (không có)")


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=default_db())
    ap.add_argument("--yes", action="store_true", help="cất thật (mặc định chỉ chạy thử)")
    ap.add_argument("--keep", action="append", default=[], help="bảng:id giữ lại, không cất (lặp được)")
    ap.add_argument("--restore", help="bảng:id[,bảng:id…] hoặc all")
    ap.add_argument("--list-retired", action="store_true")
    ap.add_argument("--backup-dir", help="mặc định <thư mục CSDL>/backup")
    ap.add_argument("--docs-dir", default=os.path.join(ROOT, "docs"))
    a = ap.parse_args(argv)
    db = os.path.abspath(a.db)
    if not os.path.isfile(db):
        print(f"Không thấy CSDL: {db}")
        return 2
    for k in a.keep:
        if not REF.match(k):
            print(f"--keep '{k}' không đúng dạng bảng:id (bảng ∈ {', '.join(retired_topics.TABLES)})")
            return 2
    err = retired_topics.file_error()
    if err:
        print(f"CẢNH BÁO: không đọc được danh sách chủ đề sửa tay ({err}) — dùng danh sách có sẵn")
    print(f"CSDL: {db}")
    if a.restore:
        restore(db, a.restore)
        return 0
    ro = sqlite3.connect(f"file:{db.replace(os.sep, '/')}?mode=ro", uri=True)
    try:
        if a.list_retired:
            list_retired(ro)
            return 0
        rows = candidates(ro, set(a.keep))
    finally:
        ro.close()
    print("Chủ đề đã bỏ: " + ", ".join(sorted(retired_topics.topics())))
    if a.keep:
        print("Giữ lại (--keep): " + ", ".join(a.keep))
    if not a.yes:
        print_list(rows, f"\nCHẠY THỬ — {len(rows)} ứng viên (chưa đổi gì; thêm --yes để cất):")
        knowledge_report()
        return 0
    print_list(rows, f"\nCẤT {len(rows)} dòng:")
    if rows:
        retire(db, rows, a.backup_dir or os.path.join(os.path.dirname(db), "backup"), a.docs_dir)
    else:
        print("Không có gì để cất.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
