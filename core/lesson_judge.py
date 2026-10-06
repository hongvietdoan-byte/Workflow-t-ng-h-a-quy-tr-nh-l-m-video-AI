"""S14.24 (KE_HOACH_BO_NAO_PROMPT_TU_HOC Đợt 5): agent chấm bài học — CHẾ ĐỘ BÓNG.

Agent chấm MỌI bài học và ghi điểm vào `lesson_reviews` (reviewer_type 'ai_agent'); người vẫn bấm Duyệt/Bỏ như cũ. Module này KHÔNG
đổi bảng `lessons`, KHÔNG ghi knowledge, KHÔNG gọi `lessons.decide` — chỉ đọc qua hàm công khai của core/lessons.py và core/knowledge.py.
Sau cờ `lesson_judge` (TẮT mặc định). Bật tự duyệt là việc sau, khi `agreement()` đạt chỉ tiêu (≥ 10 cặp, đồng thuận ≥ 90 %,
agent-lỏng-quá = 0).

Nguyên tắc devsys: AI ghi KHOẢN TRỪ + bằng chứng, CODE tính điểm (SEVERITY_FRACTION giống devsys/scores.py); thứ code tự đếm được
(bằng chứng, trùng key, nguồn web) không hỏi AI.
  facts()        số đo do code tính cho một bài học
  build_prompt() lời gọi Claude (chỉ các tiêu chí AI chấm)
  normalize()    câu trả lời → điểm 0–1; trường thiếu / enum sai → JudgeError (không đoán)
  verdict()      8 van về tay người + van 'chủ đề đã bỏ' (S14.46) → approve | reject | needs_human
  judge() / judge_all()  chạy bóng, ghi lesson_reviews; estimate() trước khi bấm; MockJudge cho test/cloud
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from . import diag

STAGE = "lesson_judge"
AUTO_PASS_DEFAULT = 0.85          # mượn QC ảnh (projects.qc_auto_pass_threshold) — chưa có cơ sở riêng: đo ở chế độ bóng rồi chỉnh
GREY_ZONE = 0.05
PRESETS = {
    "chat": {"label": "Chặt", "threshold": 0.90, "quota_week": 2},
    "can_bang": {"label": "Cân bằng", "threshold": 0.85, "quota_week": 3},
    "thoang": {"label": "Thoáng", "threshold": 0.78, "quota_week": 5},
}
SEVERITY_FRACTION = {"chan": 0.35, "lon": 0.12, "nho": 0.04}    # = devsys/scores.SEVERITY_FRACTION (một bảng cho hai hệ)
CHAN_CAP = 60.0                   # ≥ 1 khoản chặn → tổng ≤ 60 (dưới mọi ngưỡng, luôn về người)
CRITERIA = {"bang_chung": 25, "cu_the": 25, "khong_mau_thuan": 20, "khong_trung": 15, "do_rong": 10, "an_toan": 5}
AI_CRITERIA = ("cu_the", "khong_mau_thuan", "khong_trung", "do_rong", "an_toan")
CODE_CRITERIA = ("bang_chung",)   # khong_trung / an_toan: code trừ phần đếm được (trùng key, nguồn web) + AI trừ phần ý
FLOORS = {"cu_the": 0.60, "do_rong": 0.50}
MAX_AUTO_LESSONS = 12             # trần mềm mỗi nhóm
SOFT_DOC_CHARS = 8_000            # trần mềm tài liệu bài học (trần cứng lessons.MAX_DOC_CHARS… để còn đường lùi)
DOCS_PROMPT_CHARS = 12_000        # tài liệu gửi kèm để soát mâu thuẫn: cắt ở đây, và nói ra là đã cắt
TRUST_PAIRS, TRUST_AGREEMENT = 10, 0.90
# S14.46: tính năng đã bỏ — bài học về chúng coi là KHÔNG dùng. Dùng chung danh sách chủ đề của core/retired_topics (một nguồn, sửa
# một chỗ; so nguyên dấu, có biên từ, có danh sách 'keep' cho lỗi vẫn còn xảy ra như "ghép lộ").
VALVE_TEXT = {
    "research": "nguồn web (research) — UI hứa chỉ là đề xuất, agent không chấm thay người",
    "san_cung": "trượt sàn cứng hoặc có khoản chặn",
    "vung_xam": "điểm sát ngưỡng (± 0,05)",
    "khong_goi_duoc_claude": "không gọi được Claude",
    "tra_loi_hong": "câu trả lời của Claude không đúng dạng",
    "mau_thuan": "mâu thuẫn tài liệu đang bật / bài học đã duyệt",
    "tran_tai_lieu": "vượt trần tài liệu bài học — người quyết gộp/cắt",
    "loi_dong_bo": "lỗi khi đồng bộ knowledge",
    "quota": "hết quota tự duyệt trong 7 ngày",
    "key_la": "key ngoài tập tag — agent không được sinh key mới",
    "chu_de_da_bo": "chủ đề tính năng đã bỏ (S14.46) — coi là không dùng",
}


class JudgeError(ValueError):
    """Câu trả lời của agent không dùng được (thiếu trường, enum sai, không phải JSON) — nói rõ, không đoán."""


class JudgeOff(RuntimeError):
    """Cờ `lesson_judge` đang tắt: không chấm, không gọi Claude."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def retired_topics(text: str) -> List[str]:
    from . import retired_topics as _retired
    return _retired.matches(text or "")


def body_hash(lesson: Dict) -> str:
    return hashlib.sha256(f"{lesson.get('title')}\n{lesson.get('body')}".encode("utf-8")).hexdigest()[:16]


# ---- 1. số đo do code tính ------------------------------------------------------------------------------------------------
def _known_tags() -> set:
    from . import lessons
    return set(lessons.TAGS) | set(lessons.RISK_TAGS)


def _docs_text(conn, lesson: Dict) -> str:
    """Tài liệu đang bật của nhóm (trừ tài liệu bài học tự sinh) + các bài học đã duyệt khác — thứ bài học không được chọi."""
    from . import knowledge, lessons
    parts = []
    try:
        for d in knowledge.user_docs(lesson["group_name"]):
            if d["enabled"] and d["title"] != lessons.DOC_TITLE:
                parts.append(f"## {d['title']}\n{knowledge.read_doc(lesson['group_name'], 'user', d['file']).strip()}")
    except (KeyError, OSError, ValueError) as e:
        diag.record(conn, "system", "warn", f"agent chấm bài học: không đọc được tài liệu nhóm {lesson['group_name']} ({e})",
                    code="lesson_judge_docs")
    for r in lessons.list_lessons(conn, "approved"):
        if r["group_name"] == lesson["group_name"] and r["id"] != lesson["id"]:
            parts.append(f"- {r['title']}: {r['body'].strip()}")
    return "\n\n".join(parts)


def facts(conn, lesson: Dict) -> Dict:
    from . import lessons
    try:
        ev = json.loads(lesson.get("evidence") or "{}")
    except ValueError:
        ev = {}
    examples = [e for e in (ev.get("examples") or []) if isinstance(e, str)]
    found = sum(1 for e in examples if conn.execute("SELECT 1 FROM mistakes WHERE text=? AND group_name=?",
                                                    (e, lesson["group_name"])).fetchone())
    key = lesson.get("key") or ""
    tag = key.split(":", 1)[1] if key.startswith("mistake:") else None
    approved = [r for r in lessons.list_lessons(conn, "approved") if r["group_name"] == lesson["group_name"]]
    dups = [r["id"] for r in approved if r["id"] != lesson["id"] and r["key"] == key]
    mine = [] if lesson.get("state") == "approved" else [lesson]
    doc_chars = sum(len(r["title"]) + len(r["body"]) + 8 for r in approved + mine)
    docs = _docs_text(conn, lesson)
    return {"lesson_id": lesson["id"], "source": lesson.get("source"), "group": lesson["group_name"], "key": key,
            "state": lesson.get("state"), "events": int(ev.get("events") or 0), "projects": int(ev.get("projects") or 0),
            "examples": len(examples), "examples_found": found,
            "key_known": lesson.get("source") != "mistakes" or tag in _known_tags(),
            "duplicates": dups, "retired": retired_topics(f"{lesson.get('title')} {lesson.get('body')}"),
            "approved_in_group": len([r for r in approved if r["id"] != lesson["id"]]), "doc_chars": doc_chars,
            "docs_text": docs[:DOCS_PROMPT_CHARS], "docs_cut": max(0, len(docs) - DOCS_PROMPT_CHARS)}


def _code_deductions(f: Dict) -> Dict[str, List[Dict]]:
    out = {k: [] for k in CRITERIA}
    if f["events"] < 3 or f["projects"] < 2:
        out["bang_chung"].append({"muc": "chan", "reason": f"chỉ {f['events']} lần / {f['projects']} dự án (cần ≥ 3 / ≥ 2)", "by": "code"})
    if f["examples"] and f["examples_found"] < f["examples"]:
        out["bang_chung"].append({"muc": "lon", "reason": f"{f['examples'] - f['examples_found']}/{f['examples']} ví dụ không có trong bảng mistakes",
                                  "by": "code"})
    if f["duplicates"]:
        out["khong_trung"].append({"muc": "lon", "reason": f"trùng key với bài đã duyệt {f['duplicates']} — đề nghị thay thế, không thêm",
                                   "by": "code"})
    if f["source"] == "research":
        out["an_toan"].append({"muc": "chan", "reason": "nội dung web chưa kiểm (source='research')", "by": "code"})
    return out


# ---- 2. lời gọi Claude ---------------------------------------------------------------------------------------------------
def build_prompt(lesson: Dict, f: Dict) -> str:
    docs = f["docs_text"] or "(không có tài liệu bổ sung / bài học đã duyệt nào)"
    cut = f"\n(… đã cắt {f['docs_cut']} ký tự cuối)" if f.get("docs_cut") else ""
    return (
        "Bạn là người chấm BÀI HỌC cho quy trình làm video AI. KHÔNG cho điểm số: chỉ ghi các KHOẢN TRỪ kèm bằng chứng; code tính điểm.\n"
        f"LESSON_ID: {lesson['id']}\n"
        f"## Bài học (nhóm {lesson['group_name']}, key {lesson.get('key')})\nTiêu đề: {lesson.get('title')}\nNội dung: {lesson.get('body')}\n\n"
        f"## Số đo do code tính (đừng trừ lại)\n- {f['events']} lần lỗi, {f['projects']} dự án; {f['examples_found']}/{f['examples']} ví dụ có thật\n"
        f"- trùng key bài đã duyệt: {f['duplicates'] or 'không'}\n\n"
        f"## Tài liệu đang bật + bài học đã duyệt cùng nhóm\n{docs}{cut}\n\n"
        "## Tiêu chí bạn chấm\n"
        "- cu_the (25): mệnh lệnh, nói rõ làm gì/cấm gì, kiểm được bằng mắt\n"
        "- khong_mau_thuan (20): không chọi tài liệu/bài học trên — evidence PHẢI là câu trích NGUYÊN VĂN từ mục trên\n"
        "- khong_trung (15): không lặp Ý của bài học đã duyệt\n"
        "- do_rong (10): không quá hẹp (đúng 1 cảnh), không quá rộng (khẩu hiệu)\n"
        "- an_toan (5): không ép đổi đầu vào ngoài cờ\n"
        "muc: chan | lon | nho. Khoản chan/lon BẮT BUỘC có 'sua' (cách sửa cụ thể) và 'evidence' (danh sách, không rỗng).\n"
        'Chỉ trả JSON: {"criteria": {"cu_the": {"deductions": [{"muc": "lon", "reason": "...", "evidence": ["..."], "sua": "..."}]}, '
        '"khong_mau_thuan": {"deductions": []}, "khong_trung": {"deductions": []}, "do_rong": {"deductions": []}, '
        '"an_toan": {"deductions": []}}, "summary": "một câu"}')


def _parse(raw) -> Dict:
    if isinstance(raw, dict):
        return raw
    text = str(raw or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise JudgeError("câu trả lời không có JSON")
    try:
        data = json.loads(m.group(0))
    except ValueError as e:
        raise JudgeError(f"JSON hỏng: {e}") from e
    if not isinstance(data, dict):
        raise JudgeError("JSON không phải object")
    return data


def normalize(raw, f: Dict) -> Dict:
    """Câu trả lời → {"criteria": {k: {"points", "max", "deductions"}}, "total" (0–100), "score" (0–1), "floors_failed", "chan"}."""
    data = _parse(raw)
    crit = data.get("criteria")
    problems = []
    if not isinstance(crit, dict):
        raise JudgeError("thiếu 'criteria'")
    extra = set(crit) - set(AI_CRITERIA)
    if extra:
        problems.append(f"tiêu chí không được chấm bằng AI: {sorted(extra)}")
    missing = [k for k in AI_CRITERIA if not isinstance(crit.get(k), dict) or not isinstance(crit[k].get("deductions"), list)]
    if missing:
        problems.append(f"thiếu tiêu chí: {missing}")
    if problems:
        raise JudgeError("; ".join(problems))
    deds = _code_deductions(f)
    for k in AI_CRITERIA:
        for i, d in enumerate(crit[k]["deductions"]):
            where = f"{k}[{i}]"
            if not isinstance(d, dict):
                problems.append(f"{where} không phải object")
                continue
            if d.get("muc") not in SEVERITY_FRACTION:
                problems.append(f"{where}.muc = '{d.get('muc')}' (phải chan/lon/nho)")
                continue
            if not str(d.get("reason") or "").strip():
                problems.append(f"{where} thiếu reason")
            ev = d.get("evidence")
            if d["muc"] in ("chan", "lon"):
                if not isinstance(ev, list) or not [e for e in ev if str(e).strip()]:
                    problems.append(f"{where} ({d['muc']}) thiếu evidence")
                if not str(d.get("sua") or "").strip():
                    problems.append(f"{where} ({d['muc']}) thiếu sua")
            item = {"muc": d["muc"], "reason": str(d.get("reason") or ""), "evidence": [str(e) for e in (ev or [])],
                    "sua": d.get("sua"), "by": "ai"}
            if k == "khong_mau_thuan" and item["muc"] == "chan" and not any(e and e in (f.get("docs_text") or "") for e in item["evidence"]):
                item["muc"] = "lon"
                item["note"] = "hạ chặn → lớn: không tìm thấy câu trích nguyên văn trong tài liệu gửi kèm"
            deds[k].append(item)
    if problems:
        raise JudgeError("; ".join(problems))
    out, total, chan = {}, 0.0, 0
    for k, mx in CRITERIA.items():
        lost = sum(mx * SEVERITY_FRACTION[d["muc"]] for d in deds[k])
        pts = round(max(0.0, mx - lost), 2)
        chan += sum(1 for d in deds[k] if d["muc"] == "chan")
        out[k] = {"points": pts, "max": mx, "deductions": deds[k]}
        total += pts
    if chan:
        total = min(total, CHAN_CAP)
    floors = [k for k, frac in FLOORS.items() if out[k]["points"] < frac * CRITERIA[k]]
    if any(d["muc"] == "chan" for d in deds["bang_chung"]):
        floors.insert(0, "bang_chung")
    if f.get("source") == "research":
        floors.append("an_toan")
    total = round(total, 1)
    return {"criteria": out, "total": total, "score": round(total / 100, 3), "floors_failed": floors, "chan": chan,
            "summary": str(data.get("summary") or "")}


# ---- 3. van về người ------------------------------------------------------------------------------------------------------
def verdict(result: Optional[Dict], f: Dict, threshold: float = AUTO_PASS_DEFAULT, approved_this_week: int = 0,
            quota_week: int = PRESETS["can_bang"]["quota_week"], no_claude: Optional[str] = None, bad_answer: Optional[str] = None,
            sync_error: Optional[str] = None) -> Dict:
    """Agent SẼ quyết gì (bóng: chỉ ghi lại). Mọi van → needs_human, trừ 'chủ đề đã bỏ' → reject (coi là không dùng)."""
    valves = []
    if f.get("retired"):
        return {"decision": "reject", "valves": ["chu_de_da_bo"], "why": f"{VALVE_TEXT['chu_de_da_bo']}: {', '.join(f['retired'])}"}
    if f.get("source") == "research":
        valves.append("research")
    if not f.get("key_known", True):
        valves.append("key_la")
    if no_claude:
        valves.append("khong_goi_duoc_claude")
    if bad_answer:
        valves.append("tra_loi_hong")
    if result is not None:
        if result["floors_failed"] or result["chan"]:
            valves.append("san_cung")
        km = result["criteria"]["khong_mau_thuan"]["deductions"]
        if any(d["muc"] in ("chan", "lon") for d in km):
            valves.append("mau_thuan")
    if f.get("doc_chars", 0) > SOFT_DOC_CHARS or f.get("approved_in_group", 0) >= MAX_AUTO_LESSONS:
        valves.append("tran_tai_lieu")
    if sync_error:
        valves.append("loi_dong_bo")
    if f.get("state") == "proposed" and approved_this_week >= quota_week:
        valves.append("quota")
    score = None if result is None else result["score"]
    if score is not None and abs(score - threshold) <= GREY_ZONE and "san_cung" not in valves:
        valves.append("vung_xam")
    if valves or score is None:
        return {"decision": "needs_human", "valves": valves, "why": "; ".join(VALVE_TEXT[v] for v in valves) or "chưa có điểm"}
    return {"decision": "approve" if score >= threshold else "reject", "valves": [], "why": f"điểm {score:.2f} so ngưỡng {threshold:.2f}"}


# ---- 4. chạy bóng ---------------------------------------------------------------------------------------------------------
def _enabled() -> bool:
    from . import features
    return features.on("lesson_judge")


def _approved_this_week(conn) -> int:
    since = (_now() - timedelta(days=7)).isoformat(timespec="seconds")
    return conn.execute("SELECT COUNT(*) FROM lesson_reviews r JOIN lessons l ON l.id=r.lesson_id WHERE r.reviewer_type='ai_agent'"
                        " AND r.decision='approve' AND l.state='proposed' AND r.decided_at>=?", (since,)).fetchone()[0]


def _record(conn, lesson: Dict, f: Dict, v: Dict, result: Optional[Dict], threshold: float, model: Optional[str], note: str) -> None:
    detail = {"shadow": True, "valves": v["valves"], "why": v["why"], "model": model, "body_hash": body_hash(lesson),
              "criteria": (result or {}).get("criteria") or {}, "total": (result or {}).get("total"),
              "summary": (result or {}).get("summary"),
              "facts": {k: f[k] for k in ("events", "projects", "examples", "examples_found", "duplicates", "retired", "doc_chars",
                                          "approved_in_group", "docs_cut")}}
    conn.execute("INSERT INTO lesson_reviews (lesson_id, reviewer_type, decision, score, threshold_at_time, detail, note, decided_at)"
                 " VALUES (?, 'ai_agent', ?, ?, ?, ?, ?, ?)",
                 (lesson["id"], v["decision"], None if result is None else result["score"], threshold,
                  json.dumps(detail, ensure_ascii=False), note, _now().isoformat(timespec="seconds")))
    conn.commit()


def judge(conn, lesson: Dict, client, threshold: float = AUTO_PASS_DEFAULT, quota_week: int = PRESETS["can_bang"]["quota_week"]) -> Dict:
    """Chấm một bài học (bóng). Trả {"decision", "valves", "score", "called"}. Không đổi bài học / knowledge."""
    from . import budget
    f = facts(conn, lesson)
    ctx = {"threshold": threshold, "approved_this_week": _approved_this_week(conn), "quota_week": quota_week}
    model = next((m for m in (getattr(client, "model", None), getattr(client, "name", None)) if isinstance(m, str)), None)
    called = 0
    if f["retired"] or f["source"] == "research":         # code đã đủ để quyết: không tốn lời gọi
        v = verdict(None, f, **ctx)
        _record(conn, lesson, f, v, None, threshold, model, "chế độ bóng — không gọi Claude")
        return {**v, "score": None, "called": 0}
    halt = budget.check_llm(conn) if client is not None else "chưa có Claude (thiếu khóa API)"
    if halt:
        diag.record(conn, "system", "warn", f"agent chấm bài học #{lesson['id']} không chạy: {halt} — bài học giữ nguyên, chờ người",
                    code="lesson_judge_no_claude")
        v = verdict(None, f, no_claude=halt, **ctx)
        _record(conn, lesson, f, v, None, threshold, model, f"chế độ bóng — {halt}")
        return {**v, "score": None, "called": 0}
    from .llm_runner import LlmError, tagged
    result, err = None, None
    for _ in range(2):                                    # một lần hỏi lại khi trả lời sai dạng (như devsys)
        called += 1
        try:
            with tagged(STAGE):
                reply = client.complete(build_prompt(lesson, f))
        except LlmError as e:
            why = str(e)
            diag.record(conn, "system", "warn", f"agent chấm bài học #{lesson['id']} không gọi được Claude: {why} — chờ người",
                        code="lesson_judge_no_claude")
            v = verdict(None, f, no_claude=why, **ctx)
            _record(conn, lesson, f, v, None, threshold, model, f"chế độ bóng — {why}")
            return {**v, "score": None, "called": called}
        try:
            result = normalize(reply.text, f)
            break
        except JudgeError as e:
            err = str(e)
    if result is None:
        diag.record(conn, "system", "warn", f"agent chấm bài học #{lesson['id']}: trả lời sai dạng 2 lần ({err}) — chờ người",
                    code="lesson_judge_bad_answer")
        v = verdict(None, f, bad_answer=err, **ctx)
    else:
        v = verdict(result, f, **ctx)
    _record(conn, lesson, f, v, result, threshold, model, "chế độ bóng" + (f" — {err}" if result is None else ""))
    return {**v, "score": None if result is None else result["score"], "called": called}


def judge_all(conn, client, states=("proposed", "approved", "rejected"), threshold: float = AUTO_PASS_DEFAULT) -> Dict:
    """Chấm mọi bài học chưa chấm (hoặc đã sửa chữ từ lần chấm trước). Bài đã duyệt/bỏ = bộ vàng miễn phí (đã có nhãn người).
    Cờ tắt → JudgeOff (không gọi gì)."""
    if not _enabled():
        raise JudgeOff("Cờ 'lesson_judge' đang tắt — bật ở 🧪 Tính năng thử để agent chấm bóng")
    from . import lessons
    done = {}
    for r in conn.execute("SELECT lesson_id, detail FROM lesson_reviews WHERE reviewer_type='ai_agent' ORDER BY id"):
        try:
            done[r["lesson_id"]] = json.loads(r["detail"] or "{}").get("body_hash")
        except ValueError:
            done[r["lesson_id"]] = None
    judged, calls, out = 0, 0, []
    for lesson in reversed(lessons.list_lessons(conn)):
        if lesson["state"] not in states or done.get(lesson["id"]) == body_hash(lesson):
            continue
        res = judge(conn, lesson, client, threshold=threshold)
        judged += 1
        calls += res["called"]
        out.append({"lesson_id": lesson["id"], **res})
    return {"judged": judged, "calls": calls, "results": out}


def pending_count(conn) -> int:
    """Số bài judge_all() sẽ gọi Claude (để ghi giá lên nút): chưa chấm / đã sửa chữ, không phải research / chủ đề đã bỏ."""
    from . import lessons
    done = {}
    for r in conn.execute("SELECT lesson_id, detail FROM lesson_reviews WHERE reviewer_type='ai_agent' ORDER BY id"):
        try:
            done[r["lesson_id"]] = json.loads(r["detail"] or "{}").get("body_hash")
        except ValueError:
            done[r["lesson_id"]] = None
    return sum(1 for l in lessons.list_lessons(conn) if done.get(l["id"]) != body_hash(l) and l.get("source") != "research"
               and not retired_topics(f"{l.get('title')} {l.get('body')}"))


def estimate(conn, calls: int) -> Dict:
    """Trước khi bấm: USD của `calls` lời gọi (sổ chi đo thật nếu có, không thì LLM_STAGE_TOKENS) + nhãn nút. Tối đa gấp đôi khi hỏi lại."""
    from . import cost
    usd = cost.llm_estimate(conn, STAGE, calls) if calls > 0 else 0.0
    return {"calls": calls, "usd": usd, "usd_max": None if usd is None else 2 * usd, "tag": cost.llm_button_tag(conn, STAGE, calls)}


def agreement(conn) -> Dict:
    """Agent ↔ người trên bài người đã duyệt/bỏ (state approved/rejected), lần chấm agent mới nhất; 'needs_human' không tính cặp."""
    rows = []
    for row in conn.execute(
        "SELECT l.*, r.decision AS ai, r.detail AS review_detail FROM lessons l JOIN lesson_reviews r ON r.id="
        "(SELECT MAX(id) FROM lesson_reviews WHERE lesson_id=l.id AND reviewer_type='ai_agent')"
        " WHERE l.state IN ('approved','rejected')"):
        try:
            detail = json.loads(row["review_detail"] or "{}")
        except ValueError:
            continue
        if isinstance(detail, dict) and detail.get("body_hash") == body_hash(dict(row)):
            rows.append(row)
    pairs = [(r["ai"] == "approve", r["state"] == "approved") for r in rows if r["ai"] in ("approve", "reject")]
    held = sum(1 for r in rows if r["ai"] == "needs_human")
    if not pairs:
        return {"pairs": 0, "agreement": None, "ai_too_lenient": 0, "ai_too_strict": 0, "needs_human": held, "ready": False}
    agree = sum(1 for a, b in pairs if a == b) / len(pairs)
    lenient = sum(1 for a, b in pairs if a and not b)
    return {"pairs": len(pairs), "agreement": agree, "ai_too_lenient": lenient, "ai_too_strict": sum(1 for a, b in pairs if not a and b),
            "needs_human": held, "ready": len(pairs) >= TRUST_PAIRS and agree >= TRUST_AGREEMENT and lenient == 0}


class MockJudge:
    """Giả lập tất định (test / cloud): không mạng, không sổ chi. Bài ngắn (< 60 ký tự) bị trừ 'cu_the' + 'do_rong' mức lớn."""
    name = "mock-lesson-judge"
    model = "mock"

    def complete(self, prompt: str, images=()):
        from .llm_runner import LlmReply
        body = (re.search(r"^Nội dung: (.*)$", prompt, re.M) or [None, ""])[1]
        crit = {k: {"deductions": []} for k in AI_CRITERIA}
        if len(body.strip()) < 60:
            crit["cu_the"]["deductions"].append({"muc": "lon", "reason": "chung chung (giả lập)", "evidence": [body[:60]],
                                                 "sua": "nêu rõ làm gì / cấm gì"})
            crit["do_rong"]["deductions"].append({"muc": "lon", "reason": "quá rộng (giả lập)", "evidence": [body[:60]],
                                                  "sua": "thu hẹp vào lỗi cụ thể"})
        return LlmReply(text=json.dumps({"criteria": crit, "summary": "giả lập — không phải đánh giá thật"}, ensure_ascii=False))
