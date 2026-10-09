"""Thống kê 3 lượt làm Khủng Long Đỏ (#22) — CHỈ ĐỌC (0 USD): tiền theo khâu/model, số ảnh/clip theo trạng thái, cảnh báo diag, điểm QC.

    py tools/kld_round_stats.py <manifest.sqlite> [project_id=22] [--md out.md]

Mốc lượt (UTC, giờ máy = UTC+7): video giao lượt 1 lúc 02:38, lượt 2 lúc 07:25, lượt 3 lúc 13:13 ngày 07/10. Dữ liệu từ 06/10 tới mốc lượt 1
là lượt 1; sau mốc đó tới mốc lượt 2 là lượt 2; còn lại là lượt 3.
"""
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import budget_rounds, cost  # noqa: E402
from core.timestamps import utc_key  # noqa: E402

ROUNDS = [("Lượt 1 (thử)", "0000", "2026-10-07T02:38"),
          ("Lượt 2 (thử)", "2026-10-07T02:38", "2026-10-07T07:25"),
          ("Lượt 3 (chất lượng cao)", "2026-10-07T07:25", "9999")]


def _norm(ts: str) -> str:
    """KLD-30: usage_events.at ('… 02:38:05') and jobs.created_at ('…T02:38:05+00:00') → one UTC form before comparing."""
    return utc_key(ts)


def rnd_of(ts: str) -> int:
    ts = _norm(ts)
    for i, (_, a, b) in enumerate(ROUNDS):
        if _norm(a) <= ts < _norm(b):
            return i
    return len(ROUNDS) - 1


def main(db: str, pid: int) -> str:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    pricing = cost.load_pricing()
    out = [f"# Thống kê 3 lượt dự án #{pid} (chỉ đọc, CSDL `{os.path.basename(db)}`)\n"]
    # --- tiền ---
    usd = defaultdict(lambda: defaultdict(float))
    est = defaultdict(float)
    cnt = defaultdict(lambda: defaultdict(float))
    cache: dict = {}
    for r in c.execute("SELECT * FROM usage_events WHERE project_id=? AND provider NOT LIKE 'mock%' ORDER BY at", (pid,)):
        i = rnd_of(r["at"])
        v, is_est = budget_rounds.price(pricing, r, cache)
        key = (r["kind"], r["model"] + (":" + r["tier"] if r["kind"] == "video" else ""))
        usd[i][key] += v or 0
        if is_est:
            est[i] += v or 0
        if r["kind"] == "llm":
            cnt[i][key] += 1 if r["tier"] == "input" else 0
        else:
            cnt[i][key] += r["quantity"] or 1
    out.append("## 1. Tiền theo lượt và model (USD, giá bảng; phần ước tính dư ghi riêng)\n")
    out.append("| Lượt | Loại | Model | Số lượng (ảnh / giây / lần gọi) | USD |\n|---|---|---|---|---|")
    for i, (name, _, _) in enumerate(ROUNDS):
        for key in sorted(usd[i], key=lambda k: -usd[i][k]):
            out.append(f"| {name} | {key[0]} | {key[1]} | {cnt[i][key]:g} | {usd[i][key]:.2f} |")
        out.append(f"| **{name}** | | **cộng** | | **{sum(usd[i].values()):.2f}** (trong đó ước tính {est[i]:.2f}) |")
    out.append("")
    # --- job ảnh / video theo trạng thái ---
    jobs = defaultdict(lambda: defaultdict(int))
    reasons = defaultdict(lambda: defaultdict(int))
    for r in c.execute("SELECT type,state,retry_reason,created_at,model FROM jobs WHERE project_id=? AND type IN ('image_gen','video_gen')", (pid,)):
        i = rnd_of(r["created_at"])
        jobs[i][(r["type"], r["state"])] += 1
        if r["state"] not in ("approved",) and r["retry_reason"]:
            reasons[(r["type"], r["retry_reason"][:60])][i] += 1
    out.append("## 2. Số lượt gen theo trạng thái (job tạo trong khoảng của lượt)\n")
    states = sorted({k[1] for i in jobs for k in jobs[i]})
    out.append("| Lượt | Loại | " + " | ".join(states) + " | Tổng |\n|---|---|" + "---|" * (len(states) + 1))
    for i, (name, _, _) in enumerate(ROUNDS):
        for t in ("image_gen", "video_gen"):
            row = [jobs[i][(t, s)] for s in states]
            out.append(f"| {name} | {t} | " + " | ".join(map(str, row)) + f" | {sum(row)} |")
    out.append("")
    out.append("## 3. Lý do loại / gen lại (job không duyệt, có `retry_reason`)\n")
    out.append("| Loại | Lý do | " + " | ".join(n for n, _, _ in ROUNDS) + " |\n|---|---|---|---|---|")
    for (t, rs), d in sorted(reasons.items(), key=lambda kv: -sum(kv[1].values()))[:30]:
        out.append(f"| {t} | {rs} | " + " | ".join(str(d[i]) for i in range(3)) + " |")
    out.append("")
    # --- diag ---
    dg = defaultdict(lambda: defaultdict(int))
    for r in c.execute("SELECT stage,code,severity,at,count FROM diag_events WHERE project_id=?", (pid,)):
        dg[(r["stage"], r["code"], r["severity"])][rnd_of(r["at"])] += r["count"] or 1
    out.append("## 4. Cảnh báo `diag_events` theo loại (tổng số lần)\n")
    out.append("| Khâu | Mã | Mức | " + " | ".join(n for n, _, _ in ROUNDS) + " |\n|---|---|---|---|---|---|")
    for k, d in sorted(dg.items(), key=lambda kv: -sum(kv[1].values())):
        out.append(f"| {k[0]} | {k[1]} | {k[2]} | " + " | ".join(str(d[i]) for i in range(3)) + " |")
    out.append("")
    # --- QC ---
    q = defaultdict(lambda: defaultdict(list))
    for r in c.execute("SELECT q.criterion,q.score,q.auto_decision,j.created_at,j.type FROM qc_results q JOIN jobs j ON j.id=q.job_id WHERE j.project_id=?", (pid,)):
        if r["score"] is not None:
            q[(r["type"], r["criterion"])][rnd_of(r["created_at"])].append(r["score"])
    out.append("## 5. Điểm QC trung bình theo tiêu chí (số mẫu trong ngoặc)\n")
    out.append("| Loại | Tiêu chí | " + " | ".join(n for n, _, _ in ROUNDS) + " |\n|---|---|---|---|---|")
    for k, d in sorted(q.items()):
        cells = [f"{sum(d[i]) / len(d[i]):.2f} ({len(d[i])})" if d[i] else "—" for i in range(3)]
        out.append(f"| {k[0]} | {k[1]} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    if md and md in a:
        a.remove(md)
    text = main(a[0], int(a[1]) if len(a) > 1 else 22)
    if md:
        with open(md, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
