"""Hard spending limit for the test runs (kế hoạch v3, GĐ5): the person set "≤ $50 for testing".

Before a paid job is sent, the money already recorded in `usage_events` (every project, from the moment the limit was started)
plus the price of that job must stay under the limit — otherwise the job is left queued and the reason is shown. Prices come
from data/pricing.json (estimates until measured). Deepix pictures have no price yet, so they are counted instead (a cap on
the number of pictures). Simulated providers (mock) never count.

Settings live in the `app_settings` table (key 'budget'): {"usd": 50, "since": time or null, "image_cap": 80, "enabled": false}.
The limit is OFF until a test round is started (`restart`, ⚙ → Ngân sách thử), so normal production work is never blocked.
BUDGET_USD / BUDGET_IMAGE_CAP set the defaults.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from . import cost

KEY = "budget"


def _now() -> str:
    """Same text format as usage_events.at (SQLite datetime('now'), UTC) so the two compare as text."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def defaults() -> Dict:
    return {"usd": float(os.environ.get("BUDGET_USD", "50")), "since": None,
            "image_cap": int(os.environ.get("BUDGET_IMAGE_CAP", "80")), "enabled": False}


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


def spent(conn, pricing: Optional[Dict] = None, since: Optional[str] = None) -> Dict:
    """{"usd", "images", "unknown": [model:tier without a price]} of real (non-mock) submissions since `since`."""
    pricing = pricing or cost.load_pricing()
    rows = conn.execute("SELECT * FROM usage_events WHERE provider NOT LIKE 'mock%'" + (" AND at >= ?" if since else ""),
                        (since,) if since else ()).fetchall()
    usd, images, unknown = 0.0, 0, set()
    for r in rows:
        if r["kind"] == "image":
            images += int(r["quantity"] or 1)
            price = cost._number(pricing.get("per_image", {}).get(r["model"]))
            usd += (price or 0) * (r["quantity"] or 1)
        elif r["kind"] == "audio":
            price = cost._number(pricing.get("per_audio", {}).get(r["model"]))
            usd += (price or 0) * (r["quantity"] or 1)
            if price is None:
                unknown.add(r["model"])
        else:
            price = cost.clip_price(pricing, r["model"], r["tier"], r["quantity"])
            if price is None:
                unknown.add(f"{r['model']}:{r['tier']}")
            usd += price or 0
    return {"usd": round(usd, 2), "images": images, "unknown": sorted(unknown)}


def status(conn) -> Dict:
    b = get(conn)
    s = spent(conn, since=b["since"])
    return {**b, "spent": s["usd"], "images": s["images"], "unknown": s["unknown"],
            "left": round(b["usd"] - s["usd"], 2)}


def check_video(conn, provider_name: str, model: str, tier: str, seconds: float) -> Optional[str]:
    """A reason not to send this clip (it would pass the limit), else None."""
    if provider_name.startswith("mock"):
        return None
    b = get(conn)
    if not b["enabled"]:
        return None
    price = cost.clip_price(cost.load_pricing(), model, tier, seconds) or 0.0
    s = spent(conn, since=b["since"])
    if s["usd"] + price > b["usd"] + 1e-9:
        return (f"vượt trần ngân sách thử: đã chi ≈ ${s['usd']:.2f}, clip này ≈ ${price:.2f}, trần ${b['usd']:.0f} "
                "— nâng trần hoặc bắt đầu đợt mới trong ⚙ → Ngân sách thử")
    return None


def check_image(conn, provider_name: str) -> Optional[str]:
    if provider_name.startswith("mock"):
        return None
    b = get(conn)
    if not b["enabled"]:
        return None
    s = spent(conn, since=b["since"])
    if s["images"] + 1 > b["image_cap"]:
        return f"đã gen {s['images']} ảnh trong đợt thử (trần {b['image_cap']} ảnh) — nâng trần trong ⚙ → Ngân sách thử"
    return None
