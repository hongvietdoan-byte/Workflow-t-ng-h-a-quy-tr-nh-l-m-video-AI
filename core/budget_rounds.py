"""Đợt ngân sách có lịch sử + mức dùng theo NGÀY (S14.6 — Gói K, docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 6b ý 7, 6c).

  * Một ĐỢT = khoảng thời gian [started_at, ended_at) của sổ chi, với một mức dự tính (USD tổng + Claude). Mức dự tính chỉ để CẢNH BÁO
    (thanh 💵 vàng ≥ money_policy.WARN_AT, đỏ ≥ DANGER_AT), không chặn.
  * "Bắt đầu đợt mới" (chỉ Owner, lý do bắt buộc): đặt lại mốc + mức dự tính của thanh đợt thử và thanh Claude qua
    money_reset.set_planned (KHÔNG viết lại logic đặt lại), đóng đợt đang mở với tóm tắt (đã chi theo loại ảnh/video/âm thanh/Claude,
    số lượt, theo dự án) rồi mở đợt mới. Sổ chi không bị xóa / sửa.
  * Chưa có đợt nào → mốc hiện tại của đợt thử (budget.get()["since"]) được coi là đợt first_name(mốc) khi hiển thị; lần mở đợt đầu tiên
    lưu nó thành một đợt đã đóng.
  * Mức dùng theo ngày: mỗi ngày (giờ Việt Nam) cộng tiền theo loại; dòng chưa có giá → ước tính DƯ bằng money_policy (ghi rõ), nhà
    cung cấp giả lập (mock…) không tính — cùng quy ước với budget.spent."""
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from . import auth, budget, cost, money_policy, money_reset

VN = timedelta(hours=7)                     # sổ chi ghi giờ UTC; ngày hiển thị theo giờ Việt Nam
_FMT = "%Y-%m-%d %H:%M:%S"
FIRST_NO_BASE = "Từ đầu sổ chi"


def first_name(since: Optional[str]) -> str:
    """Tên đợt đầu tiên (chưa từng mở đợt): theo NGÀY mốc thật của đợt thử (giờ VN), vd. "Đợt từ 30/09/2026"."""
    if not since:
        return FIRST_NO_BASE
    try:
        return "Đợt từ " + (datetime.strptime(str(since)[:19], _FMT) + VN).strftime("%d/%m/%Y")
    except ValueError:
        return f"Đợt từ {since}"


KINDS = ("image", "video", "audio", "llm")
KIND_LABEL = {"image": "Ảnh", "video": "Video", "audio": "Âm thanh", "llm": "Claude"}

TABLE = ("CREATE TABLE IF NOT EXISTS budget_rounds (id INTEGER PRIMARY KEY, name TEXT NOT NULL, started_at TEXT, ended_at TEXT,"
         " planned_usd REAL, planned_llm_usd REAL, summary_json TEXT, opened_by TEXT, closed_by TEXT, reason TEXT, close_reason TEXT)")


def ensure(conn) -> None:
    """Bảng đợt + chỉ mục thời gian của sổ chi (idempotent; db._migrate cũng tạo)."""
    conn.execute(TABLE)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_at ON usage_events(at)")


def _row(r) -> Dict:
    d = dict(r)
    try:
        d["summary"] = json.loads(d.get("summary_json") or "null")
    except ValueError:
        d["summary"] = None
    return d


def _virtual_first(conn) -> Dict:
    b = budget.get(conn)
    return {"id": None, "name": first_name(b.get("since")), "started_at": b.get("since"), "ended_at": None,
            "planned_usd": float(b["usd"]) if b.get("enabled") else None, "planned_llm_usd": float(b.get("llm_usd") or 0) or None,
            "summary": None, "opened_by": None, "closed_by": None, "reason": None, "virtual": True}


def current(conn) -> Dict:
    """Đợt đang mở; chưa có đợt nào thì đợt ảo first_name(mốc) (mốc = mốc hiện tại của đợt thử, id None)."""
    ensure(conn)
    r = conn.execute("SELECT * FROM budget_rounds WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    return _row(r) if r else _virtual_first(conn)


def history(conn) -> List[Dict]:
    """Mọi đợt, mới nhất trước (kể cả đợt ảo first_name(mốc) khi chưa có đợt đang mở)."""
    ensure(conn)
    rows = [_row(r) for r in conn.execute("SELECT * FROM budget_rounds ORDER BY id DESC")]
    return rows or [_virtual_first(conn)]


def window(rnd: Dict) -> Tuple[Optional[str], Optional[str]]:
    return rnd.get("started_at"), rnd.get("ended_at")


# ---- giá một dòng sổ chi ---------------------------------------------------------------------------------------------------------------
def _missing_name(r) -> str:
    return f"{r['model']}:{r['tier']}" if r["kind"] == "video" else str(r["model"])


def price(pricing: Dict, r, cache: Optional[Dict] = None) -> Tuple[Optional[float], bool]:
    """(usd, ước-tính?) của một dòng sổ chi: giá bảng (budget.row_usd); thiếu giá → ước tính DƯ của money_policy (usd None khi không
    có giá nào cùng loại để ước tính)."""
    exact = budget.row_usd(pricing, r)
    if exact is not None:
        return exact, False
    key = (r["kind"], r["model"], r["tier"], r["quantity"])
    if cache is not None and key in cache:
        return cache[key], True
    if r["kind"] == "llm":
        usd, _ = money_policy.token_price(pricing, r["model"], r["tier"], r["quantity"])
    elif r["kind"] == "video":
        usd = money_policy.estimate("video", r["model"], r["tier"], r["quantity"], pricing)["usd"]
    else:
        usd = money_policy.estimate(r["kind"], r["model"], None, r["quantity"] or 1, pricing)["usd"]
    if cache is not None:
        cache[key] = usd
    return usd, True


def _rows(conn, since=None, until=None, project_id=None, extra: str = "", args: tuple = ()):
    ensure(conn)
    q = ("SELECT u.id, u.at, u.project_id, u.kind, u.provider, u.model, u.tier, u.quantity, u.unit, u.stage FROM usage_events u"
         " WHERE u.provider NOT LIKE 'mock%'")
    a: list = []
    if since:
        q += " AND u.at >= ?"
        a.append(since)
    if until:
        q += " AND u.at < ?"
        a.append(until)
    if project_id is not None:
        q += " AND u.project_id = ?"
        a.append(int(project_id))
    return conn.execute(q + extra + " ORDER BY u.at, u.id", tuple(a) + tuple(args)).fetchall()


def _empty() -> Dict:
    return {k: {"usd": 0.0, "est_usd": 0.0, "n": 0, "none_n": 0} for k in KINDS}


def _add(acc: Dict, r, usd: Optional[float], est: bool, unpriced: set, none: Optional[Dict] = None) -> float:
    """Cộng một dòng. Thiếu giá: có ước tính dư → `unpriced` + est_usd; KHÔNG ước tính được (usd None) → `none` {tên: số lượt} +
    slot["none_n"], không cộng đồng nào (không bao giờ giả là $0)."""
    k = r["kind"] if r["kind"] in KINDS else "video"
    slot = acc[k]
    if k in ("image", "audio"):
        n = int(r["quantity"] or 1)
    elif k == "llm":
        n = 1 if r["tier"] == "input" else 0          # một lần gọi Claude = dòng 'input' của nó (+ output / cache …)
    else:
        n = 1
    slot["n"] += n
    if est and usd is None:
        slot["none_n"] += n
        if none is not None:
            none[_missing_name(r)] = none.get(_missing_name(r), 0) + n
        return 0.0
    if est:
        unpriced.add(_missing_name(r))
        slot["est_usd"] += usd or 0.0
    else:
        slot["usd"] += usd or 0.0
    return usd or 0.0


def _round(acc: Dict) -> None:
    for k in KINDS:
        acc[k]["usd"] = round(acc[k]["usd"], 4)
        acc[k]["est_usd"] = round(acc[k]["est_usd"], 4)


def summarize(conn, since: Optional[str], until: Optional[str], pricing: Optional[Dict] = None) -> Dict:
    """Tóm tắt một khoảng sổ chi: {started_at, ended_at, by_kind{kind: usd, est_usd, n}, total_usd (gồm phần ước tính), est_usd,
    unpriced[], events, by_project{"pid": usd}}."""
    pricing = pricing if pricing is not None else cost.load_pricing()
    acc, unpriced, by_project, cache, none = _empty(), set(), {}, {}, {}
    rows = _rows(conn, since, until)
    for r in rows:
        usd, est = price(pricing, r, cache)
        v = _add(acc, r, usd, est, unpriced, none)
        key = str(r["project_id"]) if r["project_id"] is not None else "-"
        by_project[key] = round(by_project.get(key, 0.0) + v, 4)
    _round(acc)
    est_total = sum(acc[k]["est_usd"] for k in KINDS)
    return {"started_at": since, "ended_at": until, "by_kind": acc, "total_usd": round(sum(acc[k]["usd"] for k in KINDS) + est_total, 4),
            "est_usd": round(est_total, 4), "unpriced": sorted(unpriced), "events": len(rows), "by_project": by_project,
            "no_estimate": sorted(none), "no_estimate_counts": none, "no_estimate_n": sum(none.values())}


# ---- mức dùng theo ngày ---------------------------------------------------------------------------------------------------------------
def _local(at: str) -> datetime:
    return datetime.strptime(str(at)[:19], _FMT) + VN


def daily(conn, since: Optional[str] = None, until: Optional[str] = None, project_id: Optional[int] = None,
          pricing: Optional[Dict] = None) -> List[Dict]:
    """Mỗi ngày (giờ VN, mới nhất trước): {day, image/video/audio/llm{usd, est_usd, n}, total_usd (gồm ước tính), est_usd, unpriced[],
    events}. Lọc theo khoảng [since, until) (giờ UTC như sổ chi) và dự án."""
    pricing = pricing if pricing is not None else cost.load_pricing()
    days: Dict[str, Dict] = {}
    cache: Dict = {}
    for r in _rows(conn, since, until, project_id):
        day = _local(r["at"]).strftime("%Y-%m-%d")
        d = days.setdefault(day, {"day": day, **_empty(), "_unpriced": set(), "no_estimate_counts": {}, "events": 0, "chat_usd": 0.0})
        usd, est = price(pricing, r, cache)
        _add(d, r, usd, est, d["_unpriced"], d["no_estimate_counts"])
        d["events"] += 1
        if r["stage"] == "script_chat":
            d["chat_usd"] += usd or 0.0
    out = []
    for day in sorted(days, reverse=True):
        d = days[day]
        _round(d)
        d["unpriced"] = sorted(d.pop("_unpriced"))
        d["no_estimate"] = sorted(d["no_estimate_counts"])
        d["no_estimate_n"] = sum(d["no_estimate_counts"].values())
        d["est_usd"] = round(sum(d[k]["est_usd"] for k in KINDS), 4)
        d["total_usd"] = round(sum(d[k]["usd"] for k in KINDS) + d["est_usd"], 4)
        out.append(d)
    return out


def unpriced_note(d: Dict) -> str:
    """'' hoặc hai nhóm cho một ngày / một đợt: "chưa có giá: … — ước tính dư ≈ $… (đã cộng vào tổng)" và "chưa có giá — không ước
    tính được: tên (N lượt)" (nhóm sau không có số tiền nào, không cộng vào tổng)."""
    parts = []
    if d.get("unpriced"):
        parts.append(f"chưa có giá: {', '.join(d['unpriced'])} — ước tính dư ≈ ${float(d.get('est_usd') or 0):.2f} (đã cộng vào tổng)")
    counts = d.get("no_estimate_counts") or {}
    if counts:
        parts.append("chưa có giá — không ước tính được: " + ", ".join(f"{k} ({v} lượt)" for k, v in sorted(counts.items()))
                     + " — không tính vào tổng")
    return "; ".join(parts)


def day_bounds(day: str) -> Tuple[str, str]:
    """[đầu, cuối) của một ngày giờ VN, ở giờ UTC như sổ chi."""
    start = datetime.strptime(day, "%Y-%m-%d") - VN
    return start.strftime(_FMT), (start + timedelta(days=1)).strftime(_FMT)


def day_detail(conn, day: str, project_id: Optional[int] = None, since: Optional[str] = None, until: Optional[str] = None,
               pricing: Optional[Dict] = None) -> List[Dict]:
    """Từng dòng sổ chi của một ngày (giờ VN), cũng lọc theo đợt [since, until) + dự án: {time, project, stage, provider, model, tier,
    quantity, unit, kind, usd, estimated}."""
    pricing = pricing if pricing is not None else cost.load_pricing()
    lo, hi = day_bounds(day)
    lo = max(lo, since) if since else lo
    hi = min(hi, until) if until else hi
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM projects")}
    out, cache = [], {}
    for r in _rows(conn, lo, hi, project_id):
        usd, est = price(pricing, r, cache)
        pid = r["project_id"]
        out.append({"time": _local(r["at"]).strftime("%H:%M:%S"), "project": f"#{pid} {names.get(pid, '(đã xóa)')}" if pid else "-",
                    "stage": "chat Kịch bản" if r["stage"] == "script_chat" else (r["stage"] or ""), "provider": r["provider"], "model": r["model"], "tier": r["tier"],
                    "quantity": r["quantity"], "unit": r["unit"], "kind": r["kind"],
                    "usd": None if usd is None else round(usd, 4), "estimated": est})
    return out


def projects_in(conn, since: Optional[str] = None, until: Optional[str] = None) -> List[Tuple[int, str]]:
    """Dự án có dòng sổ chi trong khoảng (cho bộ lọc)."""
    ids = {r["project_id"] for r in _rows(conn, since, until) if r["project_id"] is not None}
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM projects")}
    return [(i, names.get(i, "(đã xóa)")) for i in sorted(ids)]


# ---- mở đợt mới -------------------------------------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(timezone.utc).strftime(_FMT)


class BarsNotReset(RuntimeError):
    """Đợt đã đóng / mở xong (ghi trọn) nhưng một số thanh tiền chưa đặt lại được — câu lỗi nói thanh nào + cách sửa."""


def reset_targets(conn) -> Dict:
    """Những thanh có thể đặt lại cùng đợt mới (người dùng 04/10 mục 6c "reset các mốc trần hiện tại"):
    {"projects": {pid: mức dự tính hiện tại (0 khi chưa có)} của các dự án còn tồn tại đang có ngân sách,
     "users": [e-mail] của người trong 👥 Nhóm (còn hoạt động)}."""
    from . import project_budget
    alive = {r["id"] for r in conn.execute("SELECT id FROM projects")}
    projects = {}
    for (key,) in conn.execute("SELECT key FROM app_settings WHERE key LIKE 'project_budget:%'").fetchall():
        try:
            pid = int(str(key).split(":", 1)[1])
        except ValueError:
            continue
        if pid in alive and project_budget.get(conn, pid):
            projects[pid] = float(project_budget.planned(conn, pid) or 0.0)
    try:
        users = [str(r[0]).strip().lower() for r in conn.execute("SELECT email FROM users WHERE COALESCE(active, 1)=1 ORDER BY email")]
    except Exception:  # noqa: BLE001 - no users table in an old database
        users = []
    return {"projects": dict(sorted(projects.items())), "users": [u for u in users if u]}


def bars_text(planned_usd: float, planned_llm_usd: float, projects: Optional[Dict] = None, users: Optional[List[str]] = None) -> str:
    """Đúng những thanh sẽ được đặt lại (cho câu hỏi xác nhận)."""
    parts = [f"Đợt thử (mức dự tính ${float(planned_usd):.2f})", f"Claude API (${float(planned_llm_usd):.2f})"]
    parts += [f"dự án #{pid} (${float(v):.2f})" for pid, v in sorted((projects or {}).items())]
    if users:
        parts.append("thanh theo người: " + ", ".join(users))
    return "; ".join(parts)


def start_new(conn, actor, name: str, planned_usd: float, planned_llm_usd: float, reason: str,
              pricing: Optional[Dict] = None, projects: Optional[Dict] = None, users: Optional[List[str]] = None) -> Dict:
    """Đóng đợt hiện tại (lưu tóm tắt) + mở đợt mới `name` với mức dự tính (USD tổng, Claude) — chỉ Owner, lý do bắt buộc.

    Thứ tự (rà soát độc lập 04/10): kiểm đầu vào + tính tóm tắt TRƯỚC (lỗi → không ghi gì); ghi đóng + mở đợt trong MỘT giao dịch
    (lỗi → rollback, thanh tiền chưa đổi); CHỈ SAU ĐÓ đặt lại thanh qua money_reset (set_planned trial / claude, `projects`
    {pid: mức dự tính} → set_planned('project'), `users` [e-mail] → reset 'user'). Thanh nào lỗi → BarsNotReset nói rõ + cách sửa
    (đợt đã ghi trọn). Mốc đợt mới = mốc thanh đợt thử sau khi đặt lại. Trả {"closed", "opened", "bars"}."""
    from . import project_budget
    if money_reset._get(actor, "role") != "owner":
        raise auth.AuthError("Chỉ Owner được mở đợt ngân sách mới")
    why = str(reason or "").strip()
    if not why:
        raise ValueError("mở đợt mới phải có lý do")
    title = str(name or "").strip()
    if not title:
        raise ValueError("đợt mới phải có tên")
    usd, llm = float(planned_usd), float(planned_llm_usd)
    if usd < 0 or llm < 0:
        raise ValueError("mức dự tính phải ≥ 0")
    plans = {int(k): float(v) for k, v in (projects or {}).items()}
    for pid, v in plans.items():
        if v < 0:
            raise ValueError(f"mức dự tính dự án #{pid} phải ≥ 0")
        if not project_budget.get(conn, pid):
            raise ValueError(f"dự án #{pid} chưa có ngân sách — không đặt lại được thanh dự án")
    mails = [str(m).strip().lower() for m in (users or []) if str(m or "").strip()]
    ensure(conn)
    who = str(money_reset._get(actor, "email") or "?")
    old = current(conn)
    start = _now()
    summary = summarize(conn, old.get("started_at"), start, pricing)          # lỗi ở đây → chưa ghi gì
    blob = json.dumps(summary, ensure_ascii=False)
    try:
        if old.get("id"):
            conn.execute("UPDATE budget_rounds SET ended_at=?, summary_json=?, closed_by=?, close_reason=? WHERE id=?",
                         (start, blob, who, why, old["id"]))
            closed_id = old["id"]
        else:
            closed_id = conn.execute("INSERT INTO budget_rounds (name, started_at, ended_at, planned_usd, planned_llm_usd, summary_json,"
                                     " opened_by, closed_by, reason, close_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                     (old["name"], old.get("started_at"), start, old.get("planned_usd"), old.get("planned_llm_usd"),
                                      blob, None, who, None, why)).lastrowid
        new_id = conn.execute("INSERT INTO budget_rounds (name, started_at, planned_usd, planned_llm_usd, opened_by, reason)"
                              " VALUES (?,?,?,?,?,?)", (title, start, usd, llm, who, why)).lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    auth.audit(conn, who, "budget_round", f"đóng #{closed_id} mở #{new_id} '{title}' — {bars_text(usd, llm, plans, mails)} — {why}")
    done, failed = [], []

    def bar(label: str, fn) -> None:
        try:
            fn()
            done.append(label)
        except Exception as e:  # noqa: BLE001 - collected and said below
            failed.append(f"{label}: {e}")
    bar("trial", lambda: money_reset.set_planned(conn, actor, "trial", usd, why))
    bar("claude", lambda: money_reset.set_planned(conn, actor, "claude", llm, why))
    for pid, v in sorted(plans.items()):
        bar(f"project:{pid}", lambda pid=pid, v=v: money_reset.set_planned(conn, actor, "project", v, why, project_id=pid))
    for mail in mails:
        bar(f"user:{mail}", lambda mail=mail: money_reset.reset(conn, actor, ["user"], why, email=mail))
    if "trial" in done:                          # mốc đợt = mốc thanh đợt thử (set_planned lấy giờ của nó, có thể sau `start` 1 giây)
        since = budget.get(conn)["since"] or start
        if since != start:
            summary["ended_at"] = since
            conn.execute("UPDATE budget_rounds SET ended_at=?, summary_json=? WHERE id=?",
                         (since, json.dumps(summary, ensure_ascii=False), closed_id))
            conn.execute("UPDATE budget_rounds SET started_at=? WHERE id=?", (since, new_id))
            conn.commit()
    if failed:
        raise BarsNotReset(f"Đã đóng đợt «{old['name']}» và mở đợt «{title}», nhưng CHƯA đặt lại được: " + "; ".join(failed)
                           + ". Cách sửa: đặt lại tay các thanh đó — đợt thử / Claude / dự án: 💵 → ↺ Đặt lại thanh tiền; "
                           "theo người: 👥 Nhóm → ↺ Đặt lại.")
    get = lambda i: _row(conn.execute("SELECT * FROM budget_rounds WHERE id=?", (i,)).fetchone())  # noqa: E731
    return {"closed": get(closed_id), "opened": get(new_id), "bars": done}


def trial_name(at: Optional[datetime] = None) -> str:
    """Tên tự đặt cho đợt mở từ nút "▶ Bắt đầu đợt thử": "Đợt thử 05/10 14:30" (giờ máy)."""
    return "Đợt thử " + (at or datetime.now()).strftime("%d/%m %H:%M")


def start_trial(conn, actor, usd: float, reason: str, image_cap: Optional[int] = None, audio_cap: Optional[int] = None,
                name: Optional[str] = None, pricing: Optional[Dict] = None) -> Dict:
    """S14.2: nút "▶ Bắt đầu đợt thử" (⚙ → Đợt thử & Claude, khóa `budget_start`) từng chỉ dời mốc thanh đợt thử (budget.restart) mà
    KHÔNG mở đợt ngân sách → bảng 📅 theo đợt lệch với thanh. Giờ nó đi qua start_new: chỉ Owner, lý do bắt buộc, đóng đợt hiện tại
    (lưu tóm tắt) và mở đợt mới với mức dự tính `usd` (Claude giữ mức đang đặt); thanh đợt thử và thanh Claude đếm lại từ bây giờ.
    Trần số ảnh / âm thanh chỉ lưu SAU khi mở đợt được (lỗi → không đổi gì). Trả kết quả của start_new."""
    from . import budget
    out = start_new(conn, actor, name or trial_name(), usd, float(budget.get(conn).get("llm_usd") or 0.0), reason, pricing=pricing)
    caps = {k: int(v) for k, v in (("image_cap", image_cap), ("audio_cap", audio_cap)) if v is not None}
    if caps:
        budget.save(conn, **caps)
    return out


DEFAULT_RESET_WHY = "Owner đặt lại thanh tiền từ nút"


def reset_two(conn, actor, reason: Optional[str] = None, pricing: Optional[Dict] = None) -> Dict:
    """S14.39: MỘT nút "↺ Đặt lại 2 thanh về 0": thanh Đợt thử bắt đầu ĐỢT ngân sách mới (đóng đợt cũ + lưu tóm tắt), thanh Claude API
    đặt lại mốc đếm; hai mức dự tính hiện có được giữ. Đi qua start_new (cùng nhật ký audit + "Đặt lại lần cuối"); sổ chi giữ nguyên,
    không xóa gì. Chỉ Owner; lý do mặc định DEFAULT_RESET_WHY (không bắt nhập)."""
    cur = budget.get(conn)
    return start_new(conn, actor, trial_name(), float(cur.get("usd") or 0.0), float(cur.get("llm_usd") or 0.0),
                     str(reason or "").strip() or DEFAULT_RESET_WHY, pricing=pricing)
