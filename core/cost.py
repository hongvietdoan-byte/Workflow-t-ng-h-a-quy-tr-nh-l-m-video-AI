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
    for key in ("per_image", "per_video_second", "per_video_clip", "per_audio"):
        data.setdefault(key, {})
    return data


def _number(value) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def video_unit_price(pricing: Dict, model: str, tier: str) -> Dict:
    """Return {'per_second': x|None, 'per_clip': y|None} for a model/tier."""
    key = f"{model}:{tier}"
    return {"per_second": _number(pricing["per_video_second"].get(key)),
            "per_clip": _number(pricing["per_video_clip"].get(key))}


def clip_price(pricing: Dict, model: str, tier: str, seconds: float) -> Optional[float]:
    """Price of ONE clip. Lookup order (first found wins):
    1. per_video_clip["model:tier:<N>s"] - exact setup price as shown on the Clip AI web page,
    2. per_video_clip["model:tier"]      - flat price per clip,
    3. per_video_second["model:tier"] x seconds."""
    exact = _number(pricing["per_video_clip"].get(f"{model}:{tier}:{int(round(seconds))}s"))
    if exact is not None:
        return exact
    price = video_unit_price(pricing, model, tier)
    if price["per_clip"] is not None:
        return price["per_clip"]
    if price["per_second"] is not None:
        return price["per_second"] * seconds
    return None


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
    from .shots import needs_own_image
    fresh = [r["id"] for r in pipeline.conn.execute(
        "SELECT id FROM scenes WHERE project_id=? AND state='ready' AND id NOT IN"
        " (SELECT scene_id FROM jobs WHERE type='image_gen' AND state NOT IN ('rejected','cancelled'))", (project_id,))]
    return queued + sum(1 for sid in fresh if needs_own_image(pipeline.conn, sid))   # v3 multi-shot: one picture per group


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
    seconds, clips, durations = 0.0, 0, []
    live = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state NOT IN ('cancelled','rejected')",
        (project_id,))}
    queued = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state='queued'", (project_id,))}
    for row in ready_for_video(pipeline, project_id):
        if row["scene_id"] in queued or row["scene_id"] not in live:
            seconds += clamp(row["duration_sec"])
            durations.append(clamp(row["duration_sec"]))
            clips += 1
    return {"clips": clips, "seconds": seconds, "durations": durations}


def estimate_videos(pipeline: Pipeline, project_id: int, pricing: Dict, model: str, tier: str, clamp) -> Dict:
    pending = pending_video_seconds(pipeline, project_id, clamp)
    price = video_unit_price(pricing, model, tier)
    max_retry = pipeline.project(project_id)["max_retry_count"]
    prices = [clip_price(pricing, model, tier, d) for d in pending["durations"]]
    base = None if any(x is None for x in prices) else sum(prices)
    result = {"kind": "video", "items": pending["clips"], "seconds": pending["seconds"], "model": model, "tier": tier,
              "unit_price": price, "known": base is not None or pending["clips"] == 0,
              "currency": pricing["currency"], "max_retry": max_retry}
    result.update(_range(base if base is not None else (0.0 if pending["clips"] == 0 else None), max_retry))
    return result


def estimate_videos_by_scene(pipeline: Pipeline, project_id: int, pricing: Dict) -> Dict:
    """Like estimate_videos, but every scene priced with ITS model (v2: model chosen per scene, core.model_router)."""
    from . import model_router
    from .adapters.clipai import effective_duration, resolve_model
    from .providers import ProviderError
    conn = pipeline.conn
    live = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state NOT IN ('cancelled','rejected')", (project_id,))}
    queued = {r["scene_id"] for r in conn.execute(
        "SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state='queued'", (project_id,))}
    kling_tier = os.environ.get("CLIPAI_KLING_MODE", "pro")
    profiles = model_router.load_profiles()["models"]
    items, seconds, base, models = 0, 0.0, 0.0, {}
    for row in ready_for_video(pipeline, project_id):
        if not (row["scene_id"] in queued or row["scene_id"] not in live):
            continue
        choice = model_router.scene_choice(conn, row["scene_id"])
        try:
            canonical, family = resolve_model(choice["model"])
        except ProviderError:
            base = None
            continue
        tier = kling_tier if family == "omni" else (choice.get("resolution") or (profiles.get(choice["model"]) or {}).get("tier") or "720p")
        sec = effective_duration(canonical, family, row["duration_sec"])
        price = clip_price(pricing, canonical, tier, sec)
        items += 1
        seconds += sec
        models[choice["model"]] = models.get(choice["model"], 0) + 1
        base = None if base is None or price is None else base + price
    max_retry = pipeline.project(project_id)["max_retry_count"]
    result = {"kind": "video", "items": items, "seconds": seconds, "model": ", ".join(f"{m}×{n}" for m, n in models.items()) or "-",
              "tier": "theo cảnh", "unit_price": None, "known": base is not None or items == 0, "currency": pricing["currency"],
              "max_retry": max_retry}
    result.update(_range(base if base is not None else (0.0 if items == 0 else None), max_retry))
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


def save_pricing(pricing: Dict, path: Optional[str] = None) -> None:
    """Write the price table back (keeps every key; used by the dashboard price editor)."""
    path = path or os.environ.get("PIPELINE_PRICING") or DEFAULT_PRICING_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pricing, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---- price table <-> editable rows (dashboard price editor) -------------------------
PRICE_KINDS = {
    "per_image": "Ảnh — giá mỗi ảnh (khóa: tên model)",
    "per_video_clip": "Video — giá mỗi clip (khóa: model:mức:Ns, vd kling-v3-omni:pro:5s)",
    "per_video_second": "Video — giá mỗi giây (khóa: model:mức)",
    "per_audio": "Âm thanh — giá mỗi lần tạo (khóa: model)",
}
SUGGESTED_CLIP_KEYS = [f"{m}:{t}:{s}s" for m, tiers in (
    ("kling-v3-omni", ("std", "pro")), ("dreamina-seedance-2-0-260128", ("720p", "1080p")),
    ("dreamina-seedance-2-5-260628", ("720p",))) for t in tiers for s in (5, 10)]


def pricing_to_rows(pricing: Dict, suggest: bool = True) -> List[Dict]:
    """Flat rows [{kind, key, price}] for a table editor; suggested empty clip rows help the first fill."""
    rows = [{"kind": kind, "key": key, "price": _number(value)}
            for kind in PRICE_KINDS for key, value in pricing.get(kind, {}).items()]
    if suggest:
        have = {(r["kind"], r["key"]) for r in rows}
        rows += [{"kind": "per_video_clip", "key": k, "price": None} for k in SUGGESTED_CLIP_KEYS
                 if ("per_video_clip", k) not in have]
    return rows


def rows_to_pricing(rows: List[Dict], base: Dict) -> Dict:
    """Validate the edited rows and rebuild the price table (keeps currency, confirm_batch_at and notes)."""
    result = {k: v for k, v in base.items() if k not in PRICE_KINDS}
    for kind in PRICE_KINDS:
        result[kind] = {}
    for i, row in enumerate(rows, start=1):
        kind, key, price = row.get("kind"), (row.get("key") or "").strip(), row.get("price")
        if kind is None and not key and price in (None, ""):
            continue  # blank line added by the editor
        if kind not in PRICE_KINDS:
            raise ValueError(f"dòng {i}: chưa chọn loại giá")
        if not key:
            raise ValueError(f"dòng {i}: thiếu khóa")
        if price in (None, "") or (isinstance(price, float) and price != price):
            result[kind][key] = None
            continue
        number = _number(price)
        if number is None or number < 0:
            raise ValueError(f"dòng {i} ({key}): giá phải là số không âm")
        result[kind][key] = number
    return result


# ---- ledger ---------------------------------------------------------------
def record_usage(conn: sqlite3.Connection, job_id: Optional[int], kind: str, provider: str, model: str, tier: str,
                 quantity: float, unit: str, project_id: Optional[int] = None) -> None:
    """One billed-looking submission. Job-based usage (image/video) derives the project from the job;
    audio has no job, so pass `project_id`."""
    if project_id is None and job_id is not None:
        row = conn.execute("SELECT project_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        project_id = row["project_id"] if row else None
    conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at)"
                 " VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                 (job_id, project_id, kind, provider, model, tier, quantity, unit))
    conn.commit()


def spend_summary(conn: sqlite3.Connection, project_id: int, pricing: Dict) -> Dict:
    """Recorded submissions (each may be billed) priced with the declared prices."""
    rows = conn.execute("SELECT * FROM usage_events WHERE project_id=?", (project_id,)).fetchall()
    images = sum(1 for r in rows if r["kind"] == "image")
    audios = sum(1 for r in rows if r["kind"] == "audio")
    clips = [r for r in rows if r["kind"] == "video"]
    seconds = sum(r["quantity"] for r in clips)
    total, unknown = 0.0, set()
    for r in rows:
        if r["provider"].startswith("mock"):
            continue
        if r["kind"] == "image":
            price = _number(pricing["per_image"].get(r["model"]))
            cost = None if price is None else price * r["quantity"]
        elif r["kind"] == "audio":
            price = _number(pricing.get("per_audio", {}).get(r["model"]))
            cost = None if price is None else price * r["quantity"]
        else:
            cost = clip_price(pricing, r["model"], r["tier"], r["quantity"])
        if cost is None:
            unknown.add(f"{r['model']}:{r['tier']}" if r["kind"] == "video" else r["model"])
        else:
            total += cost
    return {"images": images, "audios": audios, "clips": len(clips), "seconds": seconds, "credits": total,
            "unknown_prices": sorted(unknown), "currency": pricing["currency"],
            "mock": sum(1 for r in rows if r["provider"].startswith("mock")), "events": len(rows)}
