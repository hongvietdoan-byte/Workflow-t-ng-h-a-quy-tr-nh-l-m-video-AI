"""Spending of the test runs (kế hoạch v3, GĐ5): the person set "≤ $50 for testing".

Chính sách tiền 04/10 (S14.16, core.money_policy — THAY "trần cứng" 28/09): the trial's money / count caps, a model without a price and
the Claude cap are PLANNED AMOUNTS that WARN (warn_image / warn_video / warn_audio / warn_llm: a sentence with the money spent, the
planned amount, this send's estimate, the % over, the model without a price) — the send goes. The check_* functions now refuse only
when a service said it is out of credit (halt → halted, reopened by a person). Prices come from data/pricing.json; a missing price is
estimated high (money_policy.estimate). Simulated providers (mock) never count.

Settings live in the `app_settings` table (key 'budget'): {"usd": 50, "since": time or null, "image_cap": 80, "enabled": false,
"llm_usd": 5, "llm_since": time or null}.
The trial round is OFF until it is started (`restart`, ⚙ → Ngân sách thử). BUDGET_USD / BUDGET_IMAGE_CAP set the defaults.

Claude API (usage kind 'llm', tokens priced per million from pricing.json `per_million_tokens`) counts in the test round's total and
has its own planned amount `llm_usd` (CLAUDE_BUDGET_USD, default $5 = the money loaded on the Anthropic account): past it every call
warns (`warn_llm`). `llm_since` restarts the count after the person tops up.
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Tuple, Dict, Optional

from . import cost

KEY = "budget"
SPEND_LOCK = threading.RLock()
"""Held from "check the limit" to "record the spend" (runner.submit_pending): without it two projects' threads could both see room
for one more clip just under the cap and both send it (the check and the ledger write are separate steps)."""


def _now() -> str:
    """Same text format as usage_events.at (SQLite datetime('now'), UTC) so the two compare as text."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def defaults() -> Dict:
    return {"usd": float(os.environ.get("BUDGET_USD", "50")), "since": None,
            "image_cap": int(os.environ.get("BUDGET_IMAGE_CAP", "80")), "enabled": False,
            "audio_cap": int(os.environ.get("BUDGET_AUDIO_CAP", "300")),        # C12: audio has no price yet -> capped by count
            "llm_usd": float(os.environ.get("CLAUDE_BUDGET_USD", "5")), "llm_since": None,
            "out_of_credit": {}}                       # Data Pack P5: {service: {"at", "message"}} — halted until reopened


def get(conn) -> Dict:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (KEY,)).fetchone()
    try:
        saved = json.loads(row["value"]) if row else {}
    except ValueError:
        saved = {}
    return {**defaults(), **{k: v for k, v in saved.items() if k in defaults()}}


def save(conn, **fields) -> Dict:
    data = {**get(conn), **{k: v for k, v in fields.items() if k in defaults()}}
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (KEY, json.dumps(data)))
    conn.commit()
    return data


def restart(conn, usd: Optional[float] = None) -> Dict:
    """Start a test round: the limit is switched on and counts what is spent from now on."""
    return save(conn, since=_now(), enabled=True, **({"usd": float(usd)} if usd is not None else {}))


def stop(conn) -> Dict:
    return save(conn, enabled=False)


def token_price(pricing: Dict, model: str, tier: str, tokens: float) -> Optional[float]:
    """USD of `tokens` Claude API tokens (tier 'input' or 'output'), None when the model has no price. Tier 'web_search': `tokens`
    is a number of searches, priced by pricing["per_web_search"] (the same for every model)."""
    if tier == "web_search":
        unit = cost._number(pricing.get("per_web_search"))
        return None if unit is None else unit * float(tokens or 0)
    prices = pricing.get("per_million_tokens") or {}
    table = prices.get(model)
    if table is None:           # a dated/suffixed id (claude-sonnet-5-20260101) takes the price of its longest known prefix
        known = [k for k in prices if not k.startswith("_") and model.startswith(k + "-")]
        table = prices[max(known, key=len)] if known else None
    table = table if isinstance(table, dict) else {}
    unit = cost._number(table.get(tier))
    if unit is None and tier in ("cache_write", "cache_read"):          # C2: priced from the input price (Anthropic: x1.25 / x0.1)
        base = cost._number(table.get("input"))
        unit = None if base is None else base * {"cache_write": 1.25, "cache_read": 0.1}[tier]
    return None if unit is None else unit * float(tokens or 0) / 1_000_000


def row_usd(pricing: Dict, r) -> Optional[float]:
    """USD of one usage_events row (None = no price for it)."""
    if r["kind"] == "llm":
        return token_price(pricing, r["model"], r["tier"], r["quantity"])
    if r["kind"] == "image":
        p = cost._number(pricing.get("per_image", {}).get(r["model"]))
        return None if p is None else p * (r["quantity"] or 1)
    if r["kind"] == "audio":
        p = cost._number(pricing.get("per_audio", {}).get(r["model"]))
        return None if p is None else p * (r["quantity"] or 1)
    return cost.clip_price(pricing, r["model"], r["tier"], r["quantity"])


# ---- money held by Claude calls in flight (review 2026-09-28: the dashboard and a command-line tool are two processes; a hold kept in
# memory was not seen by the other, both could pass the cap at the same moment). Holds live in the database; a hold older than
# HOLD_MINUTES is a call whose process died — ignored.
HOLD_MINUTES = 30


def _holds_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS llm_holds (id INTEGER PRIMARY KEY, at TEXT NOT NULL, project_id INTEGER, stage TEXT,"
                 " usd REAL NOT NULL)")


def held(conn, project_id: Optional[int] = None, stage: Optional[str] = None) -> float:
    _holds_table(conn)
    q = "SELECT COALESCE(SUM(usd), 0) FROM llm_holds WHERE at >= datetime('now', ?)"
    args = [f"-{HOLD_MINUTES} minutes"]
    if project_id is not None:
        q += " AND project_id=?"
        args.append(project_id)
    if stage is not None:
        q += " AND stage=?"
        args.append(stage)
    return float(conn.execute(q, args).fetchone()[0] or 0)


def hold_llm(conn, usd: float, project_id: Optional[int] = None, stage: Optional[str] = None,
             extra_check=None, warnings: Optional[list] = None, extra_warn=None) -> Tuple[Optional[str], Optional[int]]:
    """Check the Claude money with this call's worst case + every call in flight (all processes) and hold the money in ONE write
    transaction. (reason, hold id): reason = a real stop only (Anthropic out of credit, or `extra_check(conn)`). S14.16: the Claude cap
    and `extra_warn(conn)` (the project budget) only add a warning text to `warnings` — the call goes."""
    _holds_table(conn)
    conn.execute("BEGIN IMMEDIATE")
    try:
        reason = check_llm(conn, usd + held(conn))
        if not reason and extra_check is not None:
            reason = extra_check(conn)
        if not reason and warnings is not None:
            for w in (warn_llm(conn, usd + held(conn)), extra_warn(conn) if extra_warn is not None else None):
                if w:
                    warnings.append(w)
        hid = None
        if not reason:
            hid = conn.execute("INSERT INTO llm_holds (at, project_id, stage, usd) VALUES (datetime('now'),?,?,?)",
                               (project_id, stage, float(usd))).lastrowid
        conn.execute("COMMIT")
        return reason, hid
    except Exception:
        conn.execute("ROLLBACK")
        raise


def release_hold(conn, hold_id: Optional[int]) -> None:
    if hold_id:
        _holds_table(conn)
        conn.execute("DELETE FROM llm_holds WHERE id=?", (hold_id,))
        conn.commit()


_SPENT_CACHE: Dict = {}


def spent(conn, pricing: Optional[Dict] = None, since: Optional[str] = None) -> Dict:
    """{"usd", "images", "unknown": [model:tier without a price], "llm_usd"} of real (non-mock) submissions since `since`
    ("usd" includes the Claude API part).
    The ledger only grows, so with the default price list the answer is remembered until a row is added (the top bar asked 6 times on every
    redraw and each ask went through every row; 02/10)."""
    key = None
    if pricing is None:
        try:
            db = next((r[2] for r in conn.execute("PRAGMA database_list") if r[1] == "main"), "")
            cnt, last = conn.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM usage_events").fetchone()
            pp = os.environ.get("PIPELINE_PRICING") or cost.DEFAULT_PRICING_PATH
            pf = os.path.getmtime(pp) if os.path.exists(pp) else 0
            key = (db or f"memory:{id(conn)}", since, cnt, last, pf)   # two in-memory databases must not share an answer
            if key in _SPENT_CACHE:
                return dict(_SPENT_CACHE[key])
        except Exception:  # noqa: BLE001 - no cache is always correct
            key = None
    out = _spent(conn, pricing or cost.load_pricing(), since)
    if key is not None:
        if len(_SPENT_CACHE) > 50:
            _SPENT_CACHE.clear()
        _SPENT_CACHE[key] = dict(out)
    return out


def _spent(conn, pricing: Dict, since: Optional[str]) -> Dict:
    rows = conn.execute("SELECT * FROM usage_events WHERE provider NOT LIKE 'mock%'" + (" AND at >= ?" if since else ""),
                        (since,) if since else ()).fetchall()
    usd, images, unknown, llm, audios = 0.0, 0, set(), 0.0, 0
    for r in rows:
        if r["kind"] == "llm":
            price = token_price(pricing, r["model"], r["tier"], r["quantity"])
            if price is None:
                unknown.add(r["model"])
            llm += price or 0
            usd += price or 0
        elif r["kind"] == "image":
            images += int(r["quantity"] or 1)
            price = cost._number(pricing.get("per_image", {}).get(r["model"]))
            usd += (price or 0) * (r["quantity"] or 1)
            if price is None:
                unknown.add(r["model"])
        elif r["kind"] == "audio":
            audios += int(r["quantity"] or 1)
            price = cost._number(pricing.get("per_audio", {}).get(r["model"]))
            usd += (price or 0) * (r["quantity"] or 1)
            if price is None:
                unknown.add(r["model"])
        else:
            price = cost.clip_price(pricing, r["model"], r["tier"], r["quantity"])
            if price is None:
                unknown.add(f"{r['model']}:{r['tier']}")
            usd += price or 0
    return {"usd": round(usd, 2), "images": images, "unknown": sorted(unknown), "llm_usd": round(llm, 4), "audios": audios}


def status(conn) -> Dict:
    b = get(conn)
    s = spent(conn, since=b["since"])
    llm = llm_spent(conn)
    return {**b, "spent": s["usd"], "images": s["images"], "audios": s["audios"], "unknown": s["unknown"],
            "left": round(b["usd"] - s["usd"], 2), "llm_spent": llm, "llm_left": round(b["llm_usd"] - llm, 4)}


def llm_spent(conn) -> float:
    """Claude API money used since the Claude count started (llm_since; every recorded call when never set)."""
    return spent(conn, since=get(conn)["llm_since"])["llm_usd"]


def restart_llm(conn, usd: float) -> Dict:
    """The person loaded money on the Anthropic account: count from now against the new amount."""
    return save(conn, llm_usd=float(usd), llm_since=_now())


HALT_KEY = "out_of_credit"


def service_of(provider_name: str) -> str:
    n = str(provider_name or "").lower()
    return "clipai" if "clipai" in n else "deepix" if "deepix" in n else "anthropic" if n in ("anthropic", "claude", "llm") else n


def halt(conn, provider_name: str, message: str) -> None:
    """Data Pack P5: a service said it is out of money — every later send to it is refused (with this reason) until a person reopens it
    (nạp tiền → ⚙ Ngân sách → mở lại). Money already spent stays spent; nothing is retried in a loop."""
    halts = dict(get(conn).get(HALT_KEY) or {})
    halts[service_of(provider_name)] = {"at": _now(), "message": str(message)[:300]}
    save(conn, **{HALT_KEY: halts})


def reopen(conn, provider_name: str) -> None:
    halts = dict(get(conn).get(HALT_KEY) or {})
    halts.pop(service_of(provider_name), None)
    save(conn, **{HALT_KEY: halts})


def halted(conn, provider_name: str) -> Optional[str]:
    h = (get(conn).get(HALT_KEY) or {}).get(service_of(provider_name))
    if not h:
        return None
    try:                                   # S14.16: a real stop says the numbers too (money spent / planned amount)
        b = get(conn)
        llm = service_of(provider_name) == "anthropic"
        used = llm_spent(conn) if llm else spent(conn, since=b["since"] if b["enabled"] else None)["usd"]
        plan = b["llm_usd"] if llm else (b["usd"] if b["enabled"] else None)
        nums = f"; đã chi ≈ ${used:.2f}" + (f", mức dự tính ${plan:.2f}" if plan else "")
    except Exception:  # noqa: BLE001 - the stop itself must still be said
        nums = ""
    return (f"⛔ CHẶN: {service_of(provider_name)} báo HẾT TIỀN lúc {h['at']} ({h['message'][:120]}){nums} — đã dừng mọi lượt gửi tới "
            "dịch vụ này; cách mở: nạp tiền rồi mở lại trong ⚙ → 💵 Ngân sách")


def check_llm(conn, next_usd: float = 0.0) -> Optional[str]:
    """A reason the Claude API must NOT be called now, else None. Chính sách tiền 04/10 (S14.16, core.money_policy): only a real stop —
    Anthropic said it is out of credit (halt). The Claude cap (llm_usd) is a planned amount that WARNS (warn_llm), it never refuses."""
    return halted(conn, "anthropic")


def warn_llm(conn, next_usd: float = 0.0) -> Optional[str]:
    """A warning with numbers when the Claude money used (+ this call's worst case `next_usd`) passes the planned amount llm_usd, else
    None. llm_usd <= 0 = no planned amount. The call still goes (S14.16)."""
    from . import money_policy
    b = get(conn)
    if b["llm_usd"] <= 0:
        return None
    used = llm_spent(conn)
    if not money_policy.over(used, b["llm_usd"], next_usd):
        return None
    return money_policy.warning_text("Claude API", used, b["llm_usd"], next_usd or None,
                                     extra="nạp thêm tiền trên Anthropic Console / đặt lại mức ở ⚙ → 💵 Ngân sách")


def pricing_problem(pricing: Optional[Dict] = None) -> Optional[str]:
    """Why no paid job may be sent because of the price table itself (broken / unreadable file), else None."""
    pricing = pricing if pricing is not None else cost.load_pricing()
    if pricing.get("_error"):
        return (f"{pricing['_error']} — không gửi job trả tiền khi chưa đọc được giá (sửa data/pricing.json hoặc ⚙ → 💲 Bảng giá)")
    return None


def _trial_warning(conn, pricing: Dict, what: str, usd: Optional[float], est: Dict) -> Optional[str]:
    """The trial round's money warning for one send priced `usd` (an over-estimate when the table has no price: est["missing"])."""
    from . import money_policy
    b = get(conn)
    if not b["enabled"]:
        return None
    s = spent(conn, pricing, since=b["since"])
    missing = [est["missing"]] if est.get("missing") else []
    if usd is None or missing or money_policy.over(s["usd"], b["usd"], usd):
        return money_policy.warning_text(f"đợt thử — {what}", s["usd"], b["usd"], usd, missing + list(s["unknown"]),
                                         extra=est.get("note") or "")
    return None


def _hard(conn, provider_name: str) -> Optional[str]:
    """The only refusal left for a paid send (S14.16): the service said it is out of money. Simulated providers never stop."""
    if str(provider_name or "").startswith("mock"):
        return None
    return halted(conn, provider_name)


def check_video(conn, provider_name: str, model: str, tier: str, seconds: float) -> Optional[str]:
    """A reason NOT to send this clip, else None. Chính sách tiền 04/10 (S14.16): only a service out of credit refuses; the trial cap,
    a model/tier without a price and a broken price table only warn (warn_video)."""
    return _hard(conn, provider_name)


def warn_video(conn, provider_name: str, model: str, tier: str, seconds: float) -> Optional[str]:
    """Warning with numbers for this clip (trial cap passed, no price → estimated high, broken price table), else None."""
    from . import money_policy
    if str(provider_name or "").startswith("mock"):
        return None
    pricing = cost.load_pricing()
    broken = pricing_problem(pricing)
    if broken:
        return f"⚠ {broken} — giá ước tính có thể sai, VẪN GỬI"
    est = money_policy.estimate("video", model, tier, seconds, pricing)
    return _trial_warning(conn, pricing, f"clip {model}:{tier}", est["usd"], est)


def check_audio(conn, provider_name: str) -> Optional[str]:
    """A reason NOT to send one audio job, else None: only a service out of credit (S14.16). The trial's count cap warns (warn_audio)."""
    return _hard(conn, provider_name)


def warn_audio(conn, provider_name: str) -> Optional[str]:
    """C12: TTS / music / sound effects have no price, so the trial counts them — past its count the send WARNS (and goes)."""
    if str(provider_name or "").startswith("mock"):
        return None
    broken = pricing_problem()
    if broken:
        return f"⚠ {broken} — VẪN GỬI"
    b = get(conn)
    if not b["enabled"]:
        return None
    n = spent(conn, since=b["since"])["audios"]
    if n + 1 > b["audio_cap"]:
        return (f"⚠ đợt thử: đã tạo {n} âm thanh, mức dự tính {b['audio_cap']} lượt (âm thanh chưa có giá USD nên tính theo SỐ LƯỢT), "
                f"lượt này là lượt {n + 1} — VẪN GỬI (trần chỉ để cảnh báo; đặt lại ở ⚙ → Ngân sách thử)")
    return None


def audio_tag(conn, count: int = 1) -> str:
    """Text for an audio button (music / SFX / voice): audio has no USD price, so the button says how many sends it costs and where
    the trial's count cap stands (luật chi phí: shown before the click)."""
    if count <= 0:
        return ""
    b = get(conn)
    if not b["enabled"]:
        return f" · {count} lượt âm thanh (chưa có giá USD)"
    used = spent(conn, since=b["since"])["audios"]
    return f" · {count} lượt âm thanh (chưa có giá USD; đợt thử {used}/{b['audio_cap']} lượt)"


def check_image(conn, provider_name: str, model: Optional[str] = None, count: int = 1) -> Optional[str]:
    """A reason NOT to send `count` more pictures, else None: only a service out of credit (S14.16). The trial's count and money caps
    and a picture model without a price only warn (warn_image)."""
    return _hard(conn, provider_name)


def warn_image(conn, provider_name: str, model: Optional[str] = None, count: int = 1) -> Optional[str]:
    """Warning with numbers for `count` pictures sent together (core.costume's 2 pictures are checked whole): the trial's count cap,
    the trial's money (a model without a price is estimated high — core.money_policy), a broken price table. None = nothing to say."""
    from . import money_policy
    if str(provider_name or "").startswith("mock"):
        return None
    pricing = cost.load_pricing()
    broken = pricing_problem(pricing)
    if broken:
        return f"⚠ {broken} — giá ước tính có thể sai, VẪN GỬI"
    b = get(conn)
    if not b["enabled"]:
        return None
    s = spent(conn, pricing, since=b["since"])
    count_note = f"đã gen {s['images']} ảnh, mức dự tính {b['image_cap']} ảnh" if s["images"] + count > b["image_cap"] else ""
    est = money_policy.estimate("image", model, None, count, pricing)
    what = f"{'ảnh này' if count == 1 else f'{count} ảnh'} ({model or 'không rõ model'})"
    money = _trial_warning(conn, pricing, what, est["usd"], est)
    if money:
        return money + (f"; {count_note}" if count_note else "")
    if count_note:
        return f"⚠ đợt thử: {count_note} — VẪN GỬI (trần chỉ để cảnh báo; đặt lại ở ⚙ → Ngân sách thử)"
    return None
