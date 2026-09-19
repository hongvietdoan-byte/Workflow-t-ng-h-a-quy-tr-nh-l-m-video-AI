"""Cost estimation and usage ledger.

Prices are NOT known to the code: they come from data/pricing.json (filled in by the owner after measuring
the balance on the Clip AI / Deepix websites). With missing prices the estimates still report counts and
seconds and say the price is unknown, instead of inventing a number.
"""
import json
import os
import sqlite3
from typing import Dict, List, Optional

from .llm_io import ready_for_video
from .pipeline import Pipeline

DEFAULT_PRICING_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pricing.json")


def load_pricing(path: Optional[str] = None) -> Dict:
    path = path or os.environ.get("PIPELINE_PRICING") or DEFAULT_PRICING_PATH
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data.setdefault("currency", "credits")
    data.setdefault("confirm_batch_at", 10)
    for key in ("per_image", "per_video_second", "per_video_clip"):
        data.setdefault(key, {})
    return data


def _number(value) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def video_unit_price(pricing: Dict, model: str, tier: str) -> Dict:
    """Return {'per_second': x|None, 'per_clip': y|None} for a model/tier."""
    key = f"{model}:{tier}"
    return {"per_second": _number(pricing["per_video_second"].get(key)),
            "per_clip": _number(pricing["per_video_clip"].get(key))}


def _cost(units: float, clips: int, price: Dict) -> Optional[float]:
    if price["per_clip"] is not None:
        return price["per_clip"] * clips
    if price["per_second"] is not None:
        return price["per_second"] * units
    return None


def _range(base: Optional[float], max_retry: int) -> Dict:
    if base is None:
        return {"min": None, "max": None}
    return {"min": base, "max": base * (1 + max_retry)}


# ---- images ---------------------------------------------------------------
def pending_image_units(pipeline: Pipeline, project_id: int) -> int:
    """Image jobs that a run would submit: queued jobs plus ready scenes that have no live image job yet."""
    queued = pipeline.conn.execute("SELECT COUNT(*) c FROM jobs WHERE project_id=? AND type='image_gen'"
                                   " AND state='queued'", (project_id,)).fetchone()["c"]
    fresh = pipeline.conn.execute(
        "SELECT COUNT(*) c FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN"
        " (SELECT scene_id FROM jobs WHERE type='image_gen' AND state NOT IN ('rejected','cancelled'))",
        (project_id,)).fetchone()["c"]
    return queued + fresh


def estimate_images(pipeline: Pipeline, project_id: int, pricing: Dict, model: str) -> Dict:
    n = pending_image_units(pipeline, project_id)
    price = _number(pricing["per_image"].get(model))
    max_retry = pipeline.project(project_id)["max_retry_count"]
    result = {"kind": "image", "items": n, "seconds": 0, "unit_price": price, "known": price is not None,
              "currency": pricing["currency"], "max_retry": max_retry}
    result.update(_range(None if price is None else price * n, max_retry))
    return result


# ---- videos ---------------------------------------------------------------
def pending_video_seconds(pipeline: Pipeline, project_id: int, clamp) -> Dict:
    """Clips/seconds a video run would submit: queued video jobs plus ready scenes without a live video job."""
    conn = pipeline.conn
    seconds, clips = 0.0, 0
    live = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state NOT IN ('cancelled','rejected')",
        (project_id,))}
    queued = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state='queued'", (project_id,))}
    for row in ready_for_video(pipeline, project_id):
        if row["scene_id"] in queued or row["scene_id"] not in live:
            seconds += clamp(row["duration_sec"])
            clips += 1
    return {"clips": clips, "seconds": seconds}


def estimate_videos(pipeline: Pipeline, project_id: int, pricing: Dict, model: str, tier: str, clamp) -> Dict:
    pending = pending_video_seconds(pipeline, project_id, clamp)
    price = video_unit_price(pricing, model, tier)
    max_retry = pipeline.project(project_id)["max_retry_count"]
    base = _cost(pending["seconds"], pending["clips"], price)
    result = {"kind": "video", "items": pending["clips"], "seconds": pending["seconds"], "model": model, "tier": tier,
              "unit_price": price, "known": base is not None or pending["clips"] == 0,
              "currency": pricing["currency"], "max_retry": max_retry}
    result.update(_range(base if base is not None else (0.0 if pending["clips"] == 0 else None), max_retry))
    return result


def format_estimate(est: Dict) -> str:
    unit = "ảnh" if est["kind"] == "image" else "clip"
    head = f"{est['items']} {unit}"
    if est["kind"] == "video":
        head += f" · {est['seconds']:.0f} giây · {est['model']} ({est['tier']})"
    if not est["known"]:
        return head + " — chưa có giá trong data/pricing.json nên chưa tính được chi phí"
    return (f"{head} → ước tính {est['min']:.1f} {est['currency']} "
            f"(tối đa {est['max']:.1f} nếu mọi mục phải làm lại đủ {est['max_retry']} lần)")


# ---- ledger ---------------------------------------------------------------
def record_usage(conn: sqlite3.Connection, job_id: int, kind: str, provider: str, model: str, tier: str,
                 quantity: float, unit: str) -> None:
    conn.execute("INSERT INTO usage_events (job_id, kind, provider, model, tier, quantity, unit, at)"
                 " VALUES (?,?,?,?,?,?,?,datetime('now'))", (job_id, kind, provider, model, tier, quantity, unit))
    conn.commit()


def spend_summary(conn: sqlite3.Connection, project_id: int, pricing: Dict) -> Dict:
    """Recorded submissions (each may be billed) priced with the declared prices."""
    rows = conn.execute("SELECT e.* FROM usage_events e JOIN jobs j ON j.id=e.job_id WHERE j.project_id=?",
                        (project_id,)).fetchall()
    images = sum(1 for r in rows if r["kind"] == "image")
    clips = [r for r in rows if r["kind"] == "video"]
    seconds = sum(r["quantity"] for r in clips)
    total, unknown = 0.0, set()
    for r in rows:
        if r["provider"].startswith("mock"):
            continue
        if r["kind"] == "image":
            price = _number(pricing["per_image"].get(r["model"]))
            cost = None if price is None else price * r["quantity"]
        else:
            cost = _cost(r["quantity"], 1, video_unit_price(pricing, r["model"], r["tier"]))
        if cost is None:
            unknown.add(f"{r['model']}:{r['tier']}" if r["kind"] == "video" else r["model"])
        else:
            total += cost
    return {"images": images, "clips": len(clips), "seconds": seconds, "credits": total,
            "unknown_prices": sorted(unknown), "currency": pricing["currency"]}
