"""Hard spending limit for the test runs (kế hoạch v3, GĐ5): the person set "≤ $50 for testing".

Before a paid job is sent, the money already recorded in `usage_events` (every project, from the moment the limit was started)
plus the price of that job must stay under the limit — otherwise the job is left queued and the reason is shown. Prices come
from data/pricing.json (estimates until measured). Deepix pictures have a provisional price (per_image) and a count cap; audio has
no price, so only its count is capped. A job whose model has no price is refused while the limit is on (it would count as $0), and a
broken price table refuses every paid job. Simulated providers (mock) never count.

Settings live in the `app_settings` table (key 'budget'): {"usd": 50, "since": time or null, "image_cap": 80, "enabled": false,
"llm_usd": 5, "llm_since": time or null}.
The limit is OFF until a test round is started (`restart`, ⚙ → Ngân sách thử), so normal production work is never blocked.
BUDGET_USD / BUDGET_IMAGE_CAP set the defaults.

Claude API (usage kind 'llm', tokens priced per million from pricing.json `per_million_tokens`) counts in the test round's total and
has its own cap `llm_usd` (CLAUDE_BUDGET_USD, default $5 = the money loaded on the Anthropic account), always on: when it is used up
the next Claude call is refused with a clear note (`check_llm`). `llm_since` restarts the count after the person tops up.
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
             extra_check=None) -> Tuple[Optional[str], Optional[int]]:
    """Check the Claude cap with this call's worst case + every call in flight (all processes) and hold the money in ONE write
    transaction. `extra_check(conn)` → a reason (the project budget) is checked inside the same transaction. (reason, hold id)."""
    _holds_table(conn)
    conn.execute("BEGIN IMMEDIATE")
    try:
        reason = check_llm(conn, usd + held(conn))
        if not reason and extra_check is not None:
            reason = extra_check(conn)
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
            key = (db, since, cnt, last, pf)
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
    return (f"{service_of(provider_name)} báo HẾT TIỀN lúc {h['at']} ({h['message'][:120]}) — đã dừng mọi lượt gửi tới dịch vụ này; "
            "nạp tiền rồi mở lại trong ⚙ → 💵 Ngân sách")


def check_llm(conn, next_usd: float = 0.0) -> Optional[str]:
    """A reason not to call the Claude API now, else None: its money is used up, or this call (`next_usd`, its worst case) would cross
    the cap — the cap is never crossed, not just reached (trial #8 2026-09-28: 5.54 / 5.50). llm_usd <= 0 switches the cap off."""
    stop = halted(conn, "anthropic")
    if stop:
        return stop
    b = get(conn)
    if b["llm_usd"] <= 0:
        return None
    used = llm_spent(conn)
    if used >= b["llm_usd"] - 1e-9 or used + next_usd > b["llm_usd"] + 1e-9:
        return (f"Hết ngân sách Claude API: đã dùng ≈ ${used:.2f} / ${b['llm_usd']:.2f}"
                + (f" (lời gọi này có thể tốn tới ≈ ${next_usd:.2f})" if next_usd else "")
                + " — nạp thêm tiền trên Anthropic Console rồi cập nhật trong ⚙ → 💵 Ngân sách thử")
    return None


def pricing_problem(pricing: Optional[Dict] = None) -> Optional[str]:
    """Why no paid job may be sent because of the price table itself (broken / unreadable file), else None."""
    pricing = pricing if pricing is not None else cost.load_pricing()
    if pricing.get("_error"):
        return (f"{pricing['_error']} — không gửi job trả tiền khi chưa đọc được giá (sửa data/pricing.json hoặc ⚙ → 💲 Bảng giá)")
    return None


def _no_price(what: str) -> str:
    return (f"{what} chưa có giá trong data/pricing.json — trần ngân sách thử không tính được nên KHÔNG gửi (giống trần Claude); "
            "thêm giá ở ⚙ → 💲 Bảng giá, chọn model khác, hoặc tắt đợt thử")


def check_video(conn, provider_name: str, model: str, tier: str, seconds: float) -> Optional[str]:
    """A reason not to send this clip (it would pass the limit, its model/tier has no price while the limit is on, or the price table
    is broken), else None. A clip without a price used to count as $0 and pass the cap."""
    if provider_name.startswith("mock"):
        return None
    stop = halted(conn, provider_name)          # Data Pack P5: the service said it is out of money
    if stop:
        return stop
    pricing = cost.load_pricing()
    broken = pricing_problem(pricing)
    if broken:
        return broken
    b = get(conn)
    if not b["enabled"]:
        return None
    price = cost.clip_price(pricing, model, tier, seconds)
    if price is None:
        return _no_price(f"clip {model}:{tier}")
    s = spent(conn, pricing, since=b["since"])
    if s["usd"] + price > b["usd"] + 1e-9:
        return (f"vượt trần ngân sách thử: đã chi ≈ ${s['usd']:.2f}, clip này ≈ ${price:.2f}, trần ${b['usd']:.0f} "
                "— nâng trần hoặc bắt đầu đợt mới trong ⚙ → Ngân sách thử")
    return None


def check_audio(conn, provider_name: str) -> Optional[str]:
    """C12: TTS / music / sound effects have no price in pricing.json, so the money cap cannot see them — the count is capped instead
    (and the reason says so). A broken price table refuses them too."""
    if provider_name.startswith("mock"):
        return None
    stop = halted(conn, provider_name)          # Data Pack P5: the service said it is out of money
    if stop:
        return stop
    broken = pricing_problem()
    if broken:
        return broken
    b = get(conn)
    if not b["enabled"]:
        return None
    n = spent(conn, since=b["since"])["audios"]
    if n + 1 > b["audio_cap"]:
        return (f"đã tạo {n} âm thanh trong đợt thử (trần {b['audio_cap']} lượt — âm thanh chưa có giá nên trần tính theo SỐ LƯỢT, "
                "không vào tổng USD) — nâng trần trong ⚙ → Ngân sách thử")
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
    """A reason not to send `count` more pictures (default one): the count cap, and — now that data/pricing.json has per_image prices
    (provisional) — the USD cap too; a picture model without a price is refused while the limit is on (it would count as $0).
    `count` > 1: a set sent together (core.costume's 2 pictures, S14.1) is checked whole before the first one goes."""
    if provider_name.startswith("mock"):
        return None
    stop = halted(conn, provider_name)          # Data Pack P5: the service said it is out of money
    if stop:
        return stop
    pricing = cost.load_pricing()
    broken = pricing_problem(pricing)
    if broken:
        return broken
    b = get(conn)
    if not b["enabled"]:
        return None
    s = spent(conn, pricing, since=b["since"])
    if s["images"] + count > b["image_cap"]:
        return f"đã gen {s['images']} ảnh trong đợt thử (trần {b['image_cap']} ảnh) — nâng trần trong ⚙ → Ngân sách thử"
    price = cost._number(pricing.get("per_image", {}).get(model)) if model else None
    if price is None:
        return _no_price(f"ảnh model {model or '(không rõ model)'}")
    if s["usd"] + price * count > b["usd"] + 1e-9:
        return (f"vượt trần ngân sách thử: đã chi ≈ ${s['usd']:.2f}, ảnh này ≈ ${price * count:.3f}, trần ${b['usd']:.0f} "
                "— nâng trần hoặc bắt đầu đợt mới trong ⚙ → Ngân sách thử")
    return None
