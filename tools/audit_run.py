"""Tiền và lỗi dồn ở bước nào — báo cáo từ cơ sở dữ liệu thật, CHỈ ĐỌC.

    py tools/audit_run.py                                  (các dự án có job gen thật, CSDL mặc định)
    py tools/audit_run.py --db D:/AI-Video-Pipeline/data/manifest.sqlite --project 12 13 14
    py tools/audit_run.py --since "2026-09-23"

Mở CSDL ở chế độ `mode=ro` (không migrate, không ghi gì). Giá lấy từ data/pricing.json (ước tính, giống sổ chi của Dashboard).
Kết quả in ra màn hình và lưu vào data/bao_cao_chi_phi_loi.md — không có đường dẫn file, khóa API hay email; gửi file đó vào chat.
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import budget, cost  # noqa: E402  (chỉ dùng hàm tính giá, không đụng CSDL)

LOW = 0.7   # điểm tiêu chí dưới mức này = "lỗi" khi thống kê


# ---- đọc ------------------------------------------------------------------------------------------------------------
def open_ro(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        sys.exit(f"Không thấy CSDL: {path}")
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def columns(conn, table: str) -> set:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def has_table(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def col(row, key, default=None):
    return row[key] if key in row.keys() else default


def load_floors() -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "qc_checklist.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for key in ("criteria", "video_criteria"):
        for c in data.get(key) or []:
            if isinstance(c.get("hard_floor"), (int, float)):
                out[c["key"]] = float(c["hard_floor"])
    return out


# ---- phân loại ------------------------------------------------------------------------------------------------------
FIRST, QC, SETCHECK, STALE, TECH, USER, RESTART, GROUP = (
    "Lần đầu", "QC loại → tự gen lại", "QC đồng bộ cả bộ → gen lại", "Đầu vào đổi → làm lại", "Lỗi kỹ thuật/nhà cung cấp → thử lại",
    "Người loại / bấm gen lại", "Bắt đầu lại sau khi hết lượt", "Phần của nhóm multi-shot (không tính tiền riêng)")
CAUSE_ORDER = [FIRST, QC, SETCHECK, STALE, TECH, USER, RESTART, GROUP]


class Data:
    def __init__(self, conn, pid: int):
        self.conn, self.pid = conn, pid
        jc = columns(conn, "jobs")
        self.jobs = {r["id"]: r for r in conn.execute("SELECT * FROM jobs WHERE project_id=? ORDER BY id", (pid,))}
        self.scene = {r["id"]: r for r in conn.execute("SELECT * FROM scenes WHERE project_id=? ORDER BY idx", (pid,))}
        self.reviews = defaultdict(list)
        self.events = defaultdict(list)
        self.qc = defaultdict(dict)
        self.usage = defaultdict(list)
        ids = tuple(self.jobs) or (-1,)
        marks = ",".join("?" * len(ids))
        for r in conn.execute(f"SELECT * FROM review_log WHERE job_id IN ({marks}) ORDER BY id", ids):
            self.reviews[r["job_id"]].append(r)
        for r in conn.execute(f"SELECT * FROM job_events WHERE job_id IN ({marks}) ORDER BY id", ids):
            self.events[r["job_id"]].append(r)
        for r in conn.execute(f"SELECT * FROM qc_results WHERE job_id IN ({marks}) ORDER BY id", ids):
            self.qc[r["job_id"]][r["criterion"]] = r["score"]
        ucols = columns(conn, "usage_events")
        where = "project_id=?" if "project_id" in ucols else f"job_id IN ({marks})"
        args = (pid,) if "project_id" in ucols else ids
        self.llm = []
        self.audio = []
        for r in conn.execute(f"SELECT * FROM usage_events WHERE {where} AND provider NOT LIKE 'mock%' ORDER BY id", args):
            if r["kind"] == "llm":
                self.llm.append(r)
            elif r["kind"] == "audio":
                self.audio.append(r)
            elif r["job_id"] is not None:
                self.usage[r["job_id"]].append(r)
        self.has_leader = "group_leader" in jc
        self.moderation = set()
        if has_table(conn, "content_moderation_failures"):
            self.moderation = {r["job_id"] for r in conn.execute(
                f"SELECT job_id FROM content_moderation_failures WHERE job_id IN ({marks})", ids)}

    def shot_label(self, scene_id) -> str:
        s = self.scene.get(scene_id)
        if s is None:
            return "?"
        d = json.loads(s["data"] or "{}")
        return f"S{s['idx']:02d}" + (f"·{d['shot_no']}" if d.get("shot_no") else "")

    def last_review(self, job_id):
        rows = self.reviews.get(job_id) or []
        return rows[-1] if rows else None

    def failed_before(self, job_id) -> bool:
        return any(e["to_state"] == "failed" for e in self.events.get(job_id, []))

    def fail_note(self, job_id) -> str:
        notes = [e["note"] for e in self.events.get(job_id, []) if e["to_state"] == "failed" and e["note"]]
        return notes[-1] if notes else ""

    def is_follower(self, j) -> bool:
        return bool(self.has_leader and col(j, "group_leader") and col(j, "group_leader") != j["id"])

    def cause(self, j) -> str:
        if self.is_follower(j):
            return GROUP
        reason = j["retry_reason"] or ""
        if reason.startswith("Đồng bộ cả bộ"):
            return SETCHECK
        if reason.startswith("Nội dung cảnh đã đổi"):
            return STALE
        parent = self.jobs.get(j["parent_job_id"]) if j["parent_job_id"] else None
        if parent is not None:
            rv = self.last_review(parent["id"])
            note = (rv["note"] if rv is not None else "") or ""   # 2026-09-26: the Vietnamese note stays in the review log only
            if note.startswith("Đồng bộ cả bộ"):                   # (retry_reason carries just the English fix for the model)
                return SETCHECK
            if note.startswith(("Nội dung cảnh đã đổi", "làm lại vì")):
                return STALE
            if self.failed_before(parent["id"]) and parent["state"] in ("cancelled", "retryable", "failed"):
                return TECH
            if rv is not None and rv["decision"] == "reject":
                return QC if rv["reviewer_type"] == "ai_agent" else USER
            return USER
        earlier = [x for x in self.jobs.values() if x["scene_id"] == j["scene_id"] and x["type"] == j["type"] and x["id"] < j["id"]
                   and not self.is_follower(x)]
        if not earlier:
            return FIRST
        prev = earlier[-1]
        rv = self.last_review(prev["id"])
        if rv is not None and (rv["note"] or "").startswith("làm lại vì"):
            return STALE
        if prev["escalated"]:
            return RESTART
        return USER

    def price(self, j, pricing) -> tuple:
        """(usd | None, seconds, images, [model:tier chưa có giá])"""
        usd, secs, imgs, unknown = 0.0, 0.0, 0, []
        for u in self.usage.get(j["id"], []):
            if u["kind"] == "video":
                p = cost.clip_price(pricing, u["model"], u["tier"], u["quantity"])
                secs += u["quantity"] or 0
                if p is None:
                    unknown.append(f"{u['model']}:{u['tier']}")
                usd += p or 0
            elif u["kind"] == "image":
                imgs += int(u["quantity"] or 1)
                p = cost._number(pricing.get("per_image", {}).get(u["model"]))
                if p is None:
                    unknown.append(u["model"])
                usd += (p or 0) * (u["quantity"] or 1)
        return usd, secs, imgs, unknown

    def in_cut(self, j) -> bool:
        """Clip mà bản ghép dùng (core.final_cut.collect_clips): job video mới nhất (không tính đã hủy) của shot, trạng thái
        succeeded/approved."""
        latest = [x for x in self.jobs.values() if x["scene_id"] == j["scene_id"] and x["type"] == "video_gen" and x["state"] != "cancelled"]
        return bool(latest) and latest[-1]["id"] == j["id"] and j["state"] in ("succeeded", "approved")

    def used(self, j) -> bool:
        """Kết quả của lần gửi này có nằm trong bản cuối không (video: được bản ghép dùng; ảnh: được duyệt / làm khung đầu video)."""
        if j["type"] == "video_gen":
            if self.in_cut(j):
                return True
            return self.has_leader and any(col(x, "group_leader") == j["id"] and self.in_cut(x) for x in self.jobs.values())
        if j["state"] == "approved":
            return True
        if "source_job_id" in j.keys():
            return any(col(x, "source_job_id") == j["id"] and self.usage.get(x["id"]) for x in self.jobs.values()
                       if x["type"] == "video_gen")
        return False

    def qc_rejected(self, job_id) -> bool:
        return any(r["reviewer_type"] == "ai_agent" and r["decision"] == "reject" for r in self.reviews.get(job_id, []))

    def submitted(self, j) -> bool:
        return bool(self.usage.get(j["id"])) or bool(j["external_id"] and not self.is_follower(j))


VISIBLE = 0.6     # điểm tiêu chí bố cục/tỉ lệ dưới mức này = lỗi người xem ảnh thấy ngay (sai cỡ cảnh, người tí hon, sai bối cảnh)


def image_flags(d, image_id, floors) -> list:
    """Lỗi nhìn thấy trên ẢNH khung đầu (trước khi có video): dưới mức sàn, bố cục/tỉ lệ/bối cảnh rất thấp, hoặc về sau ảnh bị chính
    người/QC đồng bộ loại (tức là ảnh sai mà vẫn đã làm video)."""
    if not image_id or image_id not in d.jobs:
        return []
    sc = d.qc.get(image_id, {})
    out = [f"{k} {v:.2f} < sàn" for k, v in sc.items() if k in floors and v < floors[k]]
    out += [f"{k} {v:.2f}" for k, v in sc.items() if k in ("composition", "set_match", "scale") and v < VISIBLE]
    later = [r for r in d.reviews.get(image_id, []) if r["decision"] == "reject" and r["reviewer_type"] == "user"]
    if later:
        out.append("ảnh bị loại sau đó: " + short(later[-1]["note"], 60))
    return out


def group_gaps(d, j) -> list:
    """Nhóm multi-shot: nhân vật của các shot sau không có trong shot đầu nhóm (ảnh duy nhất Kling nhận) — thấy được nếu
    storyboard hiện nhóm + danh sách nhân vật."""
    if not d.has_leader:
        return []
    lead = set(json.loads((d.scene.get(j["scene_id"]) or {"data": "{}"})["data"] or "{}").get("characters") or [])
    missing = set()
    for x in d.jobs.values():
        if col(x, "group_leader") == j["id"] and x["id"] != j["id"]:
            chars = json.loads((d.scene.get(x["scene_id"]) or {"data": "{}"})["data"] or "{}").get("characters") or []
            missing |= {c for c in chars if c not in lead}
    return sorted(missing)


def storyboard_gate(d, pricing, floors) -> str:
    rows, total, flagged_usd, flagged_unused, n_flag = [], 0.0, 0.0, 0.0, 0
    for j in d.jobs.values():
        if j["type"] != "video_gen" or not d.usage.get(j["id"]):
            continue
        usd = d.price(j, pricing)[0]
        total += usd
        flags = image_flags(d, col(j, "source_job_id"), floors)
        gaps = group_gaps(d, j)
        if gaps:
            flags.append("nhóm thiếu " + ", ".join(gaps) + " trong ảnh đầu")
        if flags:
            n_flag += 1
            flagged_usd += usd
            flagged_unused += 0 if d.used(j) else usd
            rows.append((d.shot_label(j["scene_id"]), j["id"], usd, d.used(j), "; ".join(flags)))
    head = (f"Video đã chi tiền: {money(total)}. Gửi từ ảnh/nhóm có lỗi **nhìn thấy trước khi gen video**: **{n_flag} lần, "
            f"{money(flagged_usd)} ({pct(flagged_usd, total)})**, trong đó không vào bản cuối: {money(flagged_unused)}.")
    if not rows:
        return head
    lines = [head, "", "| Shot | Job | Tiền | Vào bản cuối | Lỗi thấy trên ảnh/nhóm |", "|---|---|---|---|---|"]
    for label, jid, usd, used, why in rows[:25]:
        lines.append(f"| {label} | {jid} | {money(usd)} | {'có' if used else 'không'} | {short(why, 150)} |")
    return "\n".join(lines)


def overall(scores: dict):
    return sum(scores.values()) / len(scores) if scores else None


def money(x) -> str:
    return "—" if x is None else f"${x:,.2f}".replace(",", " ")


def pct(a, b) -> str:
    return "—" if not b else f"{100 * a / b:.0f}%"


def short(text, n=140) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


# ---- báo cáo một dự án ------------------------------------------------------------------------------------------------
def report_project(conn, pid: int, pricing: dict, floors: dict) -> tuple:
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    d = Data(conn, pid)
    out = []
    w = out.append
    w(f"## Dự án #{pid} — {proj['name']}")
    settings = [f"chế độ `{proj['operating_mode']}`", f"ngưỡng {proj['qc_auto_pass_threshold']}", f"max_retry {proj['max_retry_count']}"]
    for key, label in (("shot_mode", "shot_mode"), ("style_profile", "phong cách"), ("test_quality", "thử rẻ"), ("qc_policy", "QC"),
                       ("autopilot_gates", "cổng"), ("autopilot_state", "tự động")):
        if col(proj, key) not in (None, "", 0):
            settings.append(f"{label} `{short(col(proj, key), 80)}`")
    w("Thiết lập: " + " · ".join(settings))
    w(f"Số shot/cảnh: {len(d.scene)} · job ảnh: {sum(1 for j in d.jobs.values() if j['type'] == 'image_gen')}"
      f" · job video: {sum(1 for j in d.jobs.values() if j['type'] == 'video_gen')}")
    w("")

    # 1. tiền theo nguyên nhân
    agg = {t: defaultdict(lambda: {"n": 0, "usd": 0.0, "sec": 0.0, "used": 0, "used_usd": 0.0}) for t in ("video_gen", "image_gen")}
    unknown = set()
    per_scene = defaultdict(lambda: {"img": 0, "vid": 0, "usd": 0.0, "wasted": 0.0, "causes": Counter()})
    totals = {"usd": 0.0, "wasted": 0.0}
    for j in d.jobs.values():
        if j["type"] not in agg:
            continue
        c = d.cause(j)
        usd, secs, imgs, unk = d.price(j, pricing)
        unknown.update(unk)
        if c != GROUP and not d.submitted(j):
            continue            # chưa từng gửi (bị hủy/đang chờ): không tốn tiền
        a = agg[j["type"]][c]
        a["n"] += 1
        a["usd"] += usd
        a["sec"] += secs
        ok = d.used(j)
        if ok:
            a["used"] += 1
            a["used_usd"] += usd
        s = per_scene[j["scene_id"]]
        s["img" if j["type"] == "image_gen" else "vid"] += 0 if c == GROUP else 1
        s["usd"] += usd
        s["wasted"] += 0 if ok else usd
        if c not in (FIRST, GROUP):
            s["causes"][c] += 1
        totals["usd"] += usd
        totals["wasted"] += 0 if ok else usd

    llm_usd, llm_tok, llm_stage = 0.0, Counter(), Counter()
    for u in d.llm:
        usd = budget.token_price(pricing, u["model"], u["tier"], u["quantity"]) or 0
        llm_usd += usd
        llm_tok[u["tier"]] += u["quantity"] or 0
        llm_stage[(u["stage"] if "stage" in u.keys() else None) or "chưa gắn nhãn"] += usd

    w("### 1. Tiền dồn vào đâu")
    w(f"Tổng đã ghi sổ: **video + ảnh {money(totals['usd'])}**, trong đó **không nằm trong bản cuối: {money(totals['wasted'])}"
      f" ({pct(totals['wasted'], totals['usd'])})** · Claude API: {money(llm_usd)} "
      f"({int(llm_tok['input']):,} token vào / {int(llm_tok['output']):,} token ra"
      + (": " + ", ".join(f"{k} {money(v)}" for k, v in llm_stage.most_common()) if llm_stage else "") + ")"
      f" · âm thanh: {len(d.audio)} lượt")
    if unknown:
        w(f"_Chưa có giá (tính $0): {', '.join(sorted(unknown))}_")
    w("")
    for t, label in (("video_gen", "Video"), ("image_gen", "Ảnh")):
        rows = agg[t]
        if not rows:
            continue
        n_all = sum(r["n"] for c, r in rows.items() if c != GROUP)
        usd_all = sum(r["usd"] for r in rows.values())
        w(f"**{label}** — lý do tạo mỗi lần gửi:")
        w("")
        w("| Lý do | Số lần gửi | % | Giây | Tiền | % tiền | Kết quả được dùng |")
        w("|---|---|---|---|---|---|---|")
        for c in CAUSE_ORDER:
            if c in rows:
                r = rows[c]
                w(f"| {c} | {r['n']} | {pct(r['n'], n_all) if c != GROUP else '—'} | {r['sec']:.0f} | {money(r['usd'])} |"
                  f" {pct(r['usd'], usd_all)} | {r['used']}/{r['n']} |")
        w("")

    # 2. gen lại video: đầu vào có đổi không, điểm có lên không
    w("### 2. Gen lại video có hiệu quả không")
    same, changed, better, worse, pairs = 0, 0, 0, 0, []
    for j in d.jobs.values():
        if j["type"] != "video_gen" or not j["parent_job_id"] or d.cause(j) != QC:
            continue
        parent = d.jobs.get(j["parent_job_id"])
        same_input = (col(j, "input_hash") and col(j, "input_hash") == col(parent, "input_hash")
                      and col(j, "source_job_id") == col(parent, "source_job_id"))
        same += bool(same_input)
        changed += not same_input
        a, b = overall(d.qc.get(parent["id"], {})), overall(d.qc.get(j["id"], {}))
        if a is not None and b is not None:
            better += b > a + 0.02
            worse += b < a - 0.02
            pairs.append((d.shot_label(j["scene_id"]), a, b, bool(same_input)))
    total_retry = same + changed
    w(f"Lần gen lại video do QC loại: **{total_retry}** — gửi lại **đầu vào y hệt** (cùng ảnh + cùng motion prompt): **{same}**"
      f" ({pct(same, total_retry)}). Có điểm trước/sau: {len(pairs)} cặp → điểm lên {better}, xuống {worse},"
      f" gần như không đổi {len(pairs) - better - worse}.")
    if pairs:
        w("")
        w("| Shot | QC lần trước | QC lần sau | Đầu vào y hệt |")
        w("|---|---|---|---|")
        for label, a, b, s in pairs[:20]:
            w(f"| {label} | {a:.2f} | {b:.2f} | {'có' if s else 'không'} |")
    w("")

    # 3. lỗi dồn ở tiêu chí nào
    # 2b. cổng storyboard: video gửi từ ảnh có lỗi NHÌN THẤY ĐƯỢC trước khi chi tiền video
    w("### 2b. Nếu có cổng duyệt storyboard: video nào lẽ ra bị chặn từ ảnh")
    w(storyboard_gate(d, pricing, floors))
    w("")

    w("### 3. QC: tiêu chí nào kéo trượt")
    for t, label in (("image_gen", "Ảnh"), ("video_gen", "Video")):
        scored = [(j, d.qc[j["id"]]) for j in d.jobs.values() if j["type"] == t and d.qc.get(j["id"])]
        if not scored:
            continue
        crit = defaultdict(list)
        for _, sc in scored:
            for k, v in sc.items():
                crit[k].append(v)
        rejected = [(j, sc) for j, sc in scored if d.qc_rejected(j["id"])]
        culprit = Counter(min(sc, key=sc.get) for _, sc in rejected)
        kept = sum(1 for j, _ in rejected if any(r["reviewer_type"] == "user" and r["decision"] == "approve" for r in d.reviews[j["id"]]))
        w(f"**{label}** — {len(scored)} lần chấm, QC loại {len(rejected)} ({pct(len(rejected), len(scored))}), sau đó người giữ lại {kept}:")
        w("")
        w(f"| Tiêu chí | Điểm TB | < {LOW} | Dưới mức sàn | Là tiêu chí thấp nhất ở lần bị loại |")
        w("|---|---|---|---|---|")
        for k, vals in sorted(crit.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
            fl = floors.get(k)
            under = sum(1 for v in vals if fl is not None and v < fl)
            w(f"| {k} | {sum(vals) / len(vals):.2f} | {sum(1 for v in vals if v < LOW)}/{len(vals)} |"
              f" {f'{under} (sàn {fl})' if fl is not None else 'không có sàn'} | {culprit.get(k, 0)} |")
        w("")
        notes = Counter(short(r["note"], 160) for j, _ in rejected for r in d.reviews[j["id"]]
                        if r["reviewer_type"] == "ai_agent" and r["decision"] == "reject")
        if notes:
            w(f"Ví dụ lý do QC loại ({label.lower()}):")
            for n, _ in notes.most_common(6):
                w(f"- {n}")
            w("")

    # 4. người vs QC
    user_keep = sum(1 for j in d.jobs.values() for r in d.reviews[j["id"]] if r["reviewer_type"] == "user" and r["decision"] == "approve"
                    and any(x["reviewer_type"] == "ai_agent" and x["decision"] == "reject" for x in d.reviews[j["id"]]))
    user_reject_ai_ok = sum(1 for j in d.jobs.values() for r in d.reviews[j["id"]] if r["reviewer_type"] == "user" and r["decision"] == "reject"
                            and any(x["reviewer_type"] == "ai_agent" and x["decision"] == "approve" for x in d.reviews[j["id"]]))
    user_any = sum(1 for j in d.jobs.values() if any(r["reviewer_type"] == "user" for r in d.reviews[j["id"]]))
    w("### 4. Người và QC có đồng ý không")
    w(f"Job có người duyệt/loại: {user_any} · người **giữ** kết quả QC đã loại: {user_keep} · người **loại** kết quả QC đã duyệt"
      f" (gồm cả QC đồng bộ/đầu vào đổi chạy dưới tên người): {user_reject_ai_ok}")
    w("")

    # 5. lỗi kỹ thuật / nhà cung cấp
    fails = Counter()
    for j in d.jobs.values():
        if d.failed_before(j["id"]):
            code = short(d.fail_note(j["id"]).split(":")[0], 40) or "?"
            fails[("ảnh" if j["type"] == "image_gen" else "video", code, j["id"] in d.moderation)] += 1
    w("### 5. Lỗi kỹ thuật / nhà cung cấp")
    if fails:
        w("| Loại | Mã lỗi | Risk control | Số job |")
        w("|---|---|---|---|")
        for (kind, code, mod), n in fails.most_common(12):
            w(f"| {kind} | {code} | {'có' if mod else ''} | {n} |")
    else:
        w("Không có job thất bại.")
    auto_retry = sum(1 for j in d.jobs.values() if "autopilot: thử lại" in (j["retry_reason"] or ""))
    lost = [j for j in d.jobs.values() if j["type"] == "video_gen" and d.usage.get(j["id"]) and "not_found" in d.fail_note(j["id"])]
    lost_usd = sum(d.price(j, pricing)[0] for j in lost)
    w("")
    w(f"Autopilot tự thử lại sau lỗi: **{auto_retry}** lần · video đã gửi (có ghi sổ) rồi bị đánh `not_found`:"
      f" **{len(lost)}** ({money(lost_usd)} — nguy cơ trả 2 lần nếu task cũ vẫn chạy xong)")
    w("")

    # 6. shot tốn nhất
    w("### 6. Shot tốn nhất")
    w("| Shot | Ảnh gửi | Video gửi | Tiền | Tiền không dùng | Lý do làm lại |")
    w("|---|---|---|---|---|---|")
    for sid, s in sorted(per_scene.items(), key=lambda kv: -kv[1]["usd"])[:12]:
        w(f"| {d.shot_label(sid)} | {s['img']} | {s['vid']} | {money(s['usd'])} | {money(s['wasted'])} |"
          f" {', '.join(f'{k} ×{v}' for k, v in s['causes'].most_common()) or '—'} |")
    w("")

    # 7. câu vá trong prompt ảnh gen lại
    from core.runner import model_fix                     # a plain resend's note never reaches the prompt (not a "câu sửa")
    patched = [j for j in d.jobs.values() if j["type"] == "image_gen" and model_fix(j["retry_reason"])]
    noisy = [j for j in patched if "QC " in j["retry_reason"] or any(ch in j["retry_reason"] for ch in "ảắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữự")]
    w("### 7. Câu sửa đưa vào prompt ảnh gen lại")
    w(f"Ảnh gen lại có câu sửa: {len(patched)} · câu sửa chứa điểm số hoặc tiếng Việt (đi thẳng vào prompt Deepix): {len(noisy)}")
    for j in noisy[:3]:
        w(f"- {d.shot_label(j['scene_id'])}: “{short(j['retry_reason'], 180)}”")
    w("")

    # 8. chẩn đoán
    if has_table(conn, "diag_events"):
        rows = conn.execute("SELECT stage, severity, code, SUM(count) n, MAX(message) m FROM diag_events WHERE project_id=?"
                            " GROUP BY stage, severity, code ORDER BY n DESC LIMIT 12", (pid,)).fetchall()
        if rows:
            w("### 8. Sự kiện chẩn đoán (diag)")
            w("| Bước | Mức | Mã | Số lần | Ví dụ |")
            w("|---|---|---|---|---|")
            for r in rows:
                w(f"| {r['stage']} | {r['severity']} | {r['code'] or ''} | {r['n']} | {short(r['m'], 110)} |")
            w("")
    return "\n".join(out), totals["usd"], totals["wasted"], llm_usd


def pick_projects(conn, since) -> list:
    sql = ("SELECT DISTINCT j.project_id FROM usage_events u JOIN jobs j ON j.id=u.job_id WHERE u.provider NOT LIKE 'mock%'"
           + (" AND u.at >= ?" if since else "") + " ORDER BY j.project_id")
    return [r[0] for r in conn.execute(sql, (since,) if since else ())]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--project", type=int, nargs="*", help="id dự án (mặc định: mọi dự án có job gen thật)")
    ap.add_argument("--since", help="chỉ chọn dự án có job gen thật từ thời điểm này (YYYY-MM-DD)")
    ap.add_argument("--out", default=os.path.join("data", "bao_cao_chi_phi_loi.md"))
    args = ap.parse_args()
    conn = open_ro(args.db)
    pricing, floors = cost.load_pricing(), load_floors()
    pids = args.project or pick_projects(conn, args.since)
    if not pids:
        sys.exit("Không có dự án nào có job gen thật (usage_events không phải mock).")
    parts, summary = [], []
    for pid in pids:
        if conn.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone() is None:
            print(f"(bỏ qua #{pid}: không có)")
            continue
        text, usd, wasted, llm = report_project(conn, pid, pricing, floors)
        name = conn.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()[0]
        summary.append((pid, name, usd, wasted, llm))
        parts.append(text)
    head = [f"# Báo cáo tiền & lỗi theo bước — {datetime.now():%Y-%m-%d %H:%M}",
            "_Tạo bởi `tools/audit_run.py` (CSDL mở chỉ đọc; giá = ước tính trong data/pricing.json)._", "",
            "| Dự án | Video + ảnh | Không dùng | % | Claude API |", "|---|---|---|---|---|"]
    for pid, name, usd, wasted, llm in summary:
        head.append(f"| #{pid} {short(name, 40)} | {money(usd)} | {money(wasted)} | {pct(wasted, usd)} | {money(llm)} |")
    t_usd, t_w = sum(s[2] for s in summary), sum(s[3] for s in summary)
    head.append(f"| **Tổng** | **{money(t_usd)}** | **{money(t_w)}** | **{pct(t_w, t_usd)}** | {money(sum(s[4] for s in summary))} |")
    text = "\n".join(head) + "\n\n" + "\n\n".join(parts) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"(đã lưu: {args.out})")


if __name__ == "__main__":
    main()
