"""W14 — Lấy lại clip đã trả tiền mà Dashboard đánh hỏng (not_found / lỗi hỏi trạng thái) + xem lý do ClipAI từ chối.

    py tools/recover_clips.py                         (chỉ xem: tra mọi job video đã gửi nhưng không thành công)
    py tools/recover_clips.py --download              (tải clip ClipAI đã làm xong về data/projects/<id>/recovered/)
    py tools/recover_clips.py --project 3 --pages 30  (một dự án; quét tối đa 30 trang × 50 task mỗi loại model)

KHÔNG gửi job mới (không tốn tiền), KHÔNG ghi vào CSDL (mở chỉ đọc). Chỉ đọc danh sách `video-list` của ClipAI và tải file
video đã có. Clip tải về nằm ở thư mục `recovered/` riêng — không lẫn vào thư mục `videos/` mà bản ghép tự lấy; xem rồi tự chọn.
Cần CLIPAI_TOKEN như khi chạy Dashboard. Báo cáo lưu vào data/khoi_phuc_clip.md (không có token, không có đường dẫn cá nhân).
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.adapters.clipai import PATH_LIST, TASK_TYPE, ClipAIVideoProvider  # noqa: E402
from core.providers import ProviderError  # noqa: E402

STATUS = {0: "đã gửi", 1: "đang xử lý", 2: "XONG", 3: "thất bại", 4: "chờ"}
PAGE_SIZE = 50
_SKIP_KEYS = ("url", "token", "cover", "image", "thumb", "prompt", "content", "file")   # không in link / prompt dài / dữ liệu ảnh


def open_ro(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        sys.exit(f"Không thấy CSDL: {path}")
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def targets(conn, projects=None, job_ids=None) -> list:
    """Job video đã gửi tới ClipAI (có external_id) mà Dashboard không nhận được clip: thất bại / đã hủy sau thất bại.
    Một nhóm multi-shot chung một task → gộp theo external_id (lấy job trưởng nhóm)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
    leader = "AND (j.group_leader IS NULL OR j.group_leader = j.id)" if "group_leader" in cols else ""
    sql = ("SELECT j.*, s.idx, s.data AS scene_data, p.name AS project_name FROM jobs j JOIN scenes s ON s.id=j.scene_id"
           " JOIN projects p ON p.id=j.project_id WHERE j.type='video_gen' AND j.external_id IS NOT NULL AND j.external_id != ''"
           f" AND j.result_path IS NULL {leader}")
    args = []
    if job_ids:
        sql += f" AND j.id IN ({','.join('?' * len(job_ids))})"
        args += list(job_ids)
    else:
        sql += " AND EXISTS (SELECT 1 FROM job_events e WHERE e.job_id=j.id AND e.to_state='failed')"
    if projects:
        sql += f" AND j.project_id IN ({','.join('?' * len(projects))})"
        args += list(projects)
    rows, seen = [], set()
    for r in conn.execute(sql + " ORDER BY j.project_id, j.id", args):
        if r["external_id"] in seen:
            continue
        seen.add(r["external_id"])
        rows.append(r)
    return rows


def fail_note(conn, job_id) -> str:
    row = conn.execute("SELECT note FROM job_events WHERE job_id=? AND to_state='failed' AND note IS NOT NULL ORDER BY id DESC LIMIT 1",
                       (job_id,)).fetchone()
    return row["note"] if row else ""


def paid(conn, job_id) -> bool:
    return conn.execute("SELECT 1 FROM usage_events WHERE job_id=? AND kind='video' AND provider NOT LIKE 'mock%'", (job_id,)).fetchone() \
        is not None


def shot_has_clip(conn, scene_id) -> bool:
    """Shot này hiện đã có clip dùng được (bản ghép lấy clip mới nhất succeeded/approved)."""
    row = conn.execute("SELECT state FROM jobs WHERE scene_id=? AND type='video_gen' AND state!='cancelled' ORDER BY id DESC LIMIT 1",
                       (scene_id,)).fetchone()
    return bool(row and row["state"] in ("succeeded", "approved"))


def _get(provider, query, tries: int = 6):
    """video-list, chờ và hỏi lại khi bị giới hạn tốc độ (code 1130 'Too many requests')."""
    for n in range(tries):
        try:
            return provider.client.get(PATH_LIST, query)
        except ProviderError as e:
            if e.transient or "1130" in str(e) or "too many" in str(e).lower():
                time.sleep(min(8 * (n + 1), 30))
                continue
            raise
    raise ProviderError("ClipAI vẫn báo quá nhiều yêu cầu sau nhiều lần chờ", code="rate_limited")


def scan(provider, wanted: set, max_pages: int, pause: float = 1.5, log=print, stats=None) -> dict:
    """{task_id: task} cho các task_id cần tìm, quét lần lượt các trang của cả hai loại model (Omni, Seedance).
    stats[family] = {pages, tasks, oldest, newest, ended}: đã quét bao xa (để biết task "không thấy" là do danh sách hết hay do
    chưa quét tới)."""
    found = {}
    stats = stats if stats is not None else {}
    for family, task_type in TASK_TYPE.items():
        need = {t for t in wanted if t.startswith(family + ":")}
        if not need:
            continue
        ids = {t.split(":", 1)[1] for t in need}
        st = stats.setdefault(family, {"pages": 0, "tasks": 0, "oldest": None, "newest": None, "ended": False})
        for page in range(1, max_pages + 1):
            data = _get(provider, {"page": page, "pageSize": PAGE_SIZE, "task_type": task_type, "order_by_desc": 1})
            rows = (data or {}).get("data") or []
            st["pages"], st["tasks"] = page, st["tasks"] + len(rows)
            times = [int(t["created_at"]) for t in rows if str(t.get("created_at") or "").isdigit()]
            if times:
                st["oldest"] = min([x for x in (st["oldest"], min(times)) if x is not None])
                st["newest"] = max([x for x in (st["newest"], max(times)) if x is not None])
            st["ended"] = len(rows) < PAGE_SIZE
            for t in rows:
                tid = str(t.get("task_id"))
                if tid in ids:
                    found[f"{family}:{tid}"] = t
            log(f"  {family} trang {page}: {len(rows)} task, đã tìm thấy {sum(1 for k in found if k.startswith(family))}/{len(ids)}")
            if len(rows) < PAGE_SIZE or all(f"{family}:{i}" in found for i in ids):
                break
            time.sleep(pause)
    return found


def details(task: dict) -> str:
    """Mọi trường ngắn của task (lý do lỗi, thời gian, model...) trừ link, prompt, dữ liệu ảnh."""
    parts = []
    for k, v in task.items():
        if any(s in k.lower() for s in _SKIP_KEYS) or isinstance(v, (dict, list)) or v in (None, ""):
            continue
        parts.append(f"{k}={str(v)[:300]}")
    return "; ".join(parts)


def _day(ts) -> str:
    return "?" if not ts else datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d %H:%M")


def recover(conn, provider, data_dir: str, projects=None, job_ids=None, max_pages: int = 20, download: bool = False,
            pause: float = 1.5, log=print) -> dict:
    rows = targets(conn, projects, job_ids)
    if not rows:
        return {"rows": [], "text": "Không có job video nào đã gửi tới ClipAI mà bị đánh hỏng."}
    log(f"Tra {len(rows)} task trên ClipAI...")
    stats = {}
    found = scan(provider, {r["external_id"] for r in rows}, max_pages, pause, log, stats)
    out, lines = [], []
    for r in rows:
        task = found.get(r["external_id"])
        status = None if task is None else task.get("task_status")
        try:
            status = int(status) if status is not None else None
        except (TypeError, ValueError):
            pass
        scene = json.loads(r["scene_data"] or "{}")
        label = f"S{r['idx']:02d}" + (f"·{scene['shot_no']}" if scene.get("shot_no") else "")
        item = {"job": r["id"], "project": r["project_id"], "shot": label, "model": r["model"] if "model" in r.keys() else None,
                "paid": paid(conn, r["id"]), "dashboard": fail_note(conn, r["id"]), "clipai": STATUS.get(status, "không thấy"
                if task is None else str(status)), "reason": (task or {}).get("task_status_msg") or "", "details": details(task or {}),
                "has_clip_now": shot_has_clip(conn, r["scene_id"]), "group": r["external_id"] in {x["external_id"] for x in conn.execute(
                    "SELECT external_id FROM jobs WHERE group_leader IS NOT NULL AND group_leader != id")} if "group_leader" in r.keys() else False,
                "file": None, "cost": (task or {}).get("cost"), "sent_at": r["created_at"]}
        if download and status == 2 and task.get("video_url"):
            dest = os.path.join(data_dir, str(r["project_id"]), "recovered", f"job_{r['id']}_{label.replace('·', '_')}.mp4")
            if os.path.exists(dest):
                item["file"] = dest
            else:
                try:
                    item["file"] = provider.client.download(task["video_url"], dest)
                except ProviderError as e:
                    item["file"] = f"lỗi tải: {e}"
        out.append(item)
    ok = [i for i in out if i["clipai"] == "XONG"]
    head = [f"# Khôi phục clip ClipAI — {datetime.now():%Y-%m-%d %H:%M}",
            "_`tools/recover_clips.py`: chỉ đọc CSDL + danh sách ClipAI, không gửi job mới (không tốn tiền)._", "",
            f"Tra {len(out)} task · **ClipAI đã làm XONG: {len(ok)}** (Dashboard tưởng hỏng — đã trả tiền mà chưa lấy clip)"
            f" · thất bại thật: {sum(1 for i in out if i['clipai'] == 'thất bại')} · không thấy trong {max_pages} trang: "
            f"{sum(1 for i in out if i['clipai'] == 'không thấy')}", "",
            "Đã quét: " + " · ".join(
                f"{fam} {st['pages']} trang / {st['tasks']} task, từ {_day(st['oldest'])} đến {_day(st['newest'])}"
                + (" — **đã hết danh sách**" if st["ended"] else " — chưa hết (tăng --pages để quét sâu hơn)")
                for fam, st in stats.items()), "",
            "| Dự án | Shot | Job | Gửi lúc (UTC) | Model | Đã ghi sổ | Dashboard ghi | ClipAI | `cost` ClipAI | Shot đã có clip khác | Clip tải về |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i in out:
        f = i["file"]
        shown = "—" if not f else (os.path.relpath(f, data_dir) if os.path.exists(f) else f)
        head.append(f"| #{i['project']} | {i['shot']}{' (cả nhóm multi-shot)' if i['group'] else ''} | {i['job']} | {str(i['sent_at'])[:16]} |"
                    f" {i['model'] or ''} | {'có' if i['paid'] else 'không'} | {i['dashboard'][:70]} | **{i['clipai']}** |"
                    f" {'' if i['cost'] is None else i['cost']} | {'có' if i['has_clip_now'] else 'không'} | {shown} |")
    failed = [i for i in out if i["clipai"] == "thất bại"]
    if failed:
        head += ["", "## Lý do ClipAI báo thất bại (nguyên văn)"]
        for i in failed:
            head.append(f"- #{i['project']} {i['shot']} (job {i['job']}): **{i['reason'] or '(ClipAI không ghi lý do)'}**")
            if i["details"]:
                head.append(f"  - các trường khác: {i['details']}")
    lines = head + ["", "Clip tải về nằm trong `data/projects/<dự án>/recovered/` — xem rồi chép vào thư mục `videos/` "
                        "(đặt tên theo số shot, ví dụ `05.mp4`) nếu muốn dùng; công cụ không tự thay clip nào."]
    return {"rows": out, "text": "\n".join(lines) + "\n"}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--data", default=os.environ.get("PIPELINE_DATA", os.path.join("data", "projects")))
    ap.add_argument("--project", type=int, nargs="*")
    ap.add_argument("--job", type=int, nargs="*", help="tra đúng các job này (kể cả job không bị đánh hỏng)")
    ap.add_argument("--pages", type=int, default=20, help="số trang tối đa mỗi loại model (50 task/trang)")
    ap.add_argument("--download", action="store_true", help="tải clip ClipAI đã làm xong về thư mục recovered/")
    ap.add_argument("--out", default=os.path.join("data", "khoi_phuc_clip.md"))
    args = ap.parse_args()
    from core.adapters.check import load_dashboard_env
    load_dashboard_env()
    try:
        provider = ClipAIVideoProvider.from_env()
    except ProviderError as e:
        sys.exit(f"Không kết nối được ClipAI: {e}")
    res = recover(open_ro(args.db), provider, args.data, args.project, args.job, args.pages, args.download)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(res["text"])
    print(res["text"])
    print(f"(đã lưu: {args.out})")


if __name__ == "__main__":
    main()
