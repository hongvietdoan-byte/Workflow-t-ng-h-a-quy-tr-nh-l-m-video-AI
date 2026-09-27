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
from .memo import forget_json, read_json
from .pipeline import Pipeline

DEFAULT_PRICING_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pricing.json")


def load_pricing(path: Optional[str] = None) -> Dict:
    """The price table. A file that cannot be read or parsed is NOT silently an empty table: the result carries `_error` (Vietnamese),
    core.budget refuses every paid send while it is there and the dashboard shows it (luật 1)."""
    path = path or os.environ.get("PIPELINE_PRICING") or DEFAULT_PRICING_PATH
    error = None
    try:
        data = read_json(path)             # cached by file mtime (core.memo, a copy each call); a broken file raises, never cached
        if not isinstance(data, dict):
            raise ValueError("gốc JSON không phải object")
    except OSError as e:
        data, error = {}, f"không đọc được bảng giá {os.path.basename(path)} ({type(e).__name__})"
    except ValueError as e:
        data, error = {}, f"bảng giá {os.path.basename(path)} hỏng (JSON sai: {str(e)[:120]})"
    if error:
        data["_error"] = error
    data.setdefault("currency", "credits")
    data.setdefault("confirm_batch_at", 10)
    for key in ("per_image", "per_video_second", "per_video_clip", "per_audio"):
        if not isinstance(data.get(key), dict):
            if key in data:
                data["_error"] = data.get("_error") or f"bảng giá: mục '{key}' phải là object"
            data[key] = {}
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


def pending_end_frames(pipeline: Pipeline, project_id: int) -> int:
    """K1 end frames a run would draw (feature end_frames): one per shot that changes state (end_state, per-shot mode, not continuing
    into the next shot) and has no end frame waiting / ready yet. 0 when the feature is off."""
    from . import end_frames
    if not end_frames.enabled():
        return 0
    proj = pipeline.project(project_id)
    mode = proj["shot_mode"] if "shot_mode" in proj.keys() else None
    n = 0
    for s in pipeline.conn.execute("SELECT id, data FROM scenes WHERE project_id=?", (project_id,)).fetchall():
        if not end_frames.needed(json.loads(s["data"] or "{}"), mode):
            continue
        row = end_frames.current(pipeline.conn, s["id"])
        if row is None or row["state"] not in ("queued", "running", "ready"):
            n += 1
    return n


def estimate_images(pipeline: Pipeline, project_id: int, pricing: Dict, model: str) -> Dict:
    """Pictures a run would pay for: the shots' start pictures plus the K1 end frames (feature end_frames)."""
    ends = pending_end_frames(pipeline, project_id)
    from . import scene_establish
    wide = scene_establish.pending(pipeline.conn, project_id, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "projects"))
    n = pending_image_units(pipeline, project_id) + ends + wide
    price = _number(pricing["per_image"].get(model))
    max_retry = pipeline.project(project_id)["max_retry_count"]
    result = {"kind": "image", "items": n, "seconds": 0, "unit_price": price, "known": price is not None,
              "currency": pricing["currency"], "max_retry": max_retry, "end_frames": ends, "establishing": wide}
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


def clip_estimate(conn, scene_id: int, pricing: Optional[Dict] = None) -> Optional[float]:
    """M8: USD of sending this one shot's clip again (its model/tier/length; a remade shot of a multi-shot group goes alone).
    None when the model has no price."""
    from . import model_router, shots
    from .adapters.clipai import effective_duration, resolve_model
    from .providers import ProviderError
    pricing = pricing or load_pricing()
    choice = model_router.scene_choice(conn, scene_id)
    try:
        canonical, family = resolve_model(choice["model"])
    except ProviderError:
        return None
    tier = os.environ.get("CLIPAI_KLING_MODE", "pro") if family == "omni" else (
        choice.get("resolution") or (model_router.load_profiles()["models"].get(choice["model"]) or {}).get("tier") or "720p")
    mp = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=?", (scene_id,)).fetchone()
    seconds = (mp["duration_sec"] if mp and mp["duration_sec"] else None) or shots.planned_seconds(conn, scene_id) or 5
    return clip_price(pricing, canonical, tier, effective_duration(canonical, family, seconds))


def price_tag(usd: Optional[float], count: int = 1) -> str:
    """Text for a paid button: ' · ≈ $0.40' (or 'chưa có giá') — M8: the price is shown before the click."""
    if count <= 0:
        return ""
    return f" · ≈ {usd:.2f} USD" if usd is not None else " · chưa có giá"   # no "$": Streamlit labels read it as math


# ---- Claude (batch buttons, the automatic run) ------------------------------------------------------------------------------
# Tokens of ONE call per stage (usage_events.stage) when the ledger has no call of that stage yet: (input, output). Pictures count in
# the input (~w*h/750 tokens each at the 1024 px edge ≈ 1,400). Rough on purpose — replaced by the measured average after the first calls.
LLM_STAGE_TOKENS = {"director": (25000, 18000), "motion": (9000, 4000), "qc": (6000, 900), "style": (9000, 1500),
                    "video_analysis": (14000, 2500), "setcheck": (8000, 1200), "clipcheck": (10000, 1200),
                    "asset_vision": (6000, 900), "research": (25000, 1500)}
IMAGE_TOKENS = 1400


def llm_model() -> str:
    from .llm_runner import DEFAULT_MODEL
    return os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL


def llm_call_usd(conn, stage: str, pricing: Optional[Dict] = None, images: int = 0, ledger_stage: Optional[str] = None) -> Optional[float]:
    """USD of ONE Claude call of this kind: the measured average of that stage's recorded calls (usage_events, kind llm) when there
    are some, else LLM_STAGE_TOKENS + `images` pictures. None when the model has no price in per_million_tokens."""
    from . import budget
    pricing = pricing or load_pricing()
    model = llm_model()
    stage_key = ledger_stage or stage
    inp = out = None
    if conn is not None:
        try:
            row = conn.execute("SELECT COUNT(CASE WHEN tier='input' THEN 1 END) n, SUM(CASE WHEN tier='input' THEN quantity END) i,"
                               " SUM(CASE WHEN tier='output' THEN quantity END) o, SUM(CASE WHEN tier IN ('cache_read','cache_write')"
                               " THEN quantity END) c FROM usage_events WHERE kind='llm' AND stage=? AND provider NOT LIKE 'mock%'",
                               (stage_key,)).fetchone()
            if row and row["n"]:
                inp = ((row["i"] or 0) + (row["c"] or 0)) / row["n"]
                out = (row["o"] or 0) / row["n"]
        except Exception:  # noqa: BLE001 - an old ledger without the stage column: use the table
            inp = out = None
    if inp is None:
        base_in, base_out = LLM_STAGE_TOKENS.get(stage, (6000, 1500))
        inp, out = base_in + images * IMAGE_TOKENS, base_out
    a, b = budget.token_price(pricing, model, "input", inp), budget.token_price(pricing, model, "output", out)
    return None if a is None or b is None else a + b


def llm_estimate(conn, stage: str, calls: int, pricing: Optional[Dict] = None, images: int = 0,
                 ledger_stage: Optional[str] = None) -> Optional[float]:
    """USD of `calls` Claude calls of one kind (see llm_call_usd), None when unpriced; 0 calls = 0."""
    if calls <= 0:
        return 0.0
    one = llm_call_usd(conn, stage, pricing, images, ledger_stage)
    return None if one is None else one * calls


def llm_tag(usd: Optional[float], calls: int = 1) -> str:
    """Text for a Claude button: ' · Claude ≈ 0.05 USD' (luật chi phí: the estimate is shown before the click)."""
    if calls <= 0:
        return ""
    return f" · Claude ≈ {usd:.2f} USD" if usd is not None else " · Claude: chưa có giá"


def estimate_run(pipeline: Pipeline, project_id: int, pricing: Optional[Dict] = None) -> Dict:
    """What the automatic run will pay for, before the start button: pictures (+ end frames), clips (each shot's model, lip-sync
    shots on Seedance included), Claude (Director, QC, motion) — base and worst case with the retries. Unknown prices are listed,
    never counted as 0. {"images", "videos", "llm", "total", "max", "unknown": [...], "counts": {...}}"""
    from . import image_models, model_router
    pricing = pricing or load_pricing()
    conn = pipeline.conn
    proj = pipeline.project(project_id)
    unknown = []
    n_scenes = conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (project_id,)).fetchone()[0]
    img_model = image_models.of_project(proj)
    img = estimate_images(pipeline, project_id, pricing, img_model)
    if img["items"] == 0 and n_scenes and not conn.execute("SELECT 1 FROM jobs WHERE project_id=? AND type='image_gen'",
                                                            (project_id,)).fetchone():
        img["items"] = n_scenes + img.get("end_frames", 0)          # before the Director: one picture per scene at least
    img_usd = None if img["unit_price"] is None else img["unit_price"] * img["items"]
    if img_usd is None and img["items"]:
        unknown.append(f"ảnh {img_model}")
    rows = model_router.plan(conn, project_id, pricing)
    made = {r["scene_id"] for r in conn.execute("SELECT scene_id FROM jobs WHERE project_id=? AND type='video_gen' AND state IN"
                                                " ('succeeded','approved','running','queued','pending_review')", (project_id,))}
    todo = [r for r in rows if r["scene_id"] not in made]
    vid_usd = 0.0
    for r in todo:
        if r["cost"] is None:
            unknown.append(f"clip {r['model']}")
        else:
            vid_usd += r["cost"]
    from . import lipsync
    if lipsync.enabled() and lipsync.post_available():   # post lip sync (sync.so) of the finished clips; "generate" shots are in the
        for r in todo:                                   # clip price already (they go to Seedance with the voice)
            data = json.loads(conn.execute("SELECT data FROM scenes WHERE id=?", (r["scene_id"],)).fetchone()["data"] or "{}")
            if lipsync.method_for(data) == "post":
                price = clip_price(pricing, os.environ.get("SYNC_MODEL", "lipsync-2-pro"), "post", r["billed_seconds"])
                if price is None:
                    unknown.append("khớp môi sau")
                else:
                    vid_usd += price
    llm_calls = {"director": 0 if conn.execute("SELECT 1 FROM characters WHERE project_id=? AND TRIM(description)!=''",
                                               (project_id,)).fetchone() else 1,
                 "qc": img["items"] + len(todo), "motion": 1 if todo else 0}
    llm_usd = 0.0
    for stage, calls in llm_calls.items():
        one = llm_estimate(conn, stage, calls, pricing, images=2 if stage == "qc" else 0)
        if one is None:
            unknown.append(f"Claude {llm_model()}")
        else:
            llm_usd += one
    retry = int(proj["max_retry_count"] or 0)
    auto_cap = min(retry, 2)                           # automatic retries per picture/clip (pipeline.AUTO_RETRY_CAP)
    base = (img_usd or 0.0) + vid_usd + llm_usd
    worst = (img_usd or 0.0) * (1 + auto_cap) + vid_usd * (1 + auto_cap) + llm_usd * (1 + auto_cap)
    return {"images": img_usd, "videos": round(vid_usd, 2), "llm": round(llm_usd, 2), "total": round(base, 2), "max": round(worst, 2),
            "unknown": sorted(set(unknown)), "counts": {"images": img["items"], "end_frames": img.get("end_frames", 0),
                                                        "clips": len(todo), "seconds": sum(r["billed_seconds"] for r in todo)}}


def format_run_estimate(est: Dict) -> str:
    c = est["counts"]
    text = (f"≈ {est['total']:.2f} USD (tối đa ≈ {est['max']:.2f} nếu mọi ảnh/clip phải tự gen lại 2 lần): {c['images']} ảnh"
            + (f" (gồm {c['end_frames']} khung cuối)" if c.get("end_frames") else "")
            + f" ≈ {(est['images'] or 0):.2f} · {c['clips']} clip / {c['seconds']:.0f} giây ≈ {est['videos']:.2f} · Claude ≈ {est['llm']:.2f}")
    if est["unknown"]:
        text += " — CHƯA có giá (không tính, sẽ bị trần từ chối khi đợt thử bật): " + ", ".join(est["unknown"])
    return text


def format_estimate(est: Dict) -> str:
    unit = "ảnh" if est["kind"] == "image" else "clip"
    head = f"{est['items']} {unit}" + (f" (gồm {est['end_frames']} khung cuối)" if est.get("end_frames") else "")
    if est["kind"] == "video":
        head += f" · {est['seconds']:.0f} giây · {est['model']} ({est['tier']})"
    if not est["known"]:
        return head + " — chưa có giá trong data/pricing.json nên chưa tính được chi phí"
    return (f"{head} → ước tính {est['min']:.1f} {est['currency']} "
            f"(tối đa {est['max']:.1f} nếu mọi mục phải làm lại đủ {est['max_retry']} lần)")


def save_pricing(pricing: Dict, path: Optional[str] = None) -> None:
    """Write the price table back (keeps every key; used by the dashboard price editor)."""
    path = path or os.environ.get("PIPELINE_PRICING") or DEFAULT_PRICING_PATH
    pricing = {k: v for k, v in pricing.items() if k != "_error"}     # the read error is not part of the table
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pricing, f, ensure_ascii=False, indent=2)
        f.write("\n")
    forget_json(path)


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
                 quantity: float, unit: str, project_id: Optional[int] = None, stage: Optional[str] = None) -> None:
    """One billed-looking submission. Job-based usage (image/video) derives the project from the job;
    audio has no job, so pass `project_id`. `stage`: what a Claude call was for (director, qc, motion, asset_vision…)."""
    if project_id is None and job_id is not None:
        row = conn.execute("SELECT project_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        project_id = row["project_id"] if row else None
    conn.execute("INSERT INTO usage_events (job_id, project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                 " VALUES (?,?,?,?,?,?,?,?,datetime('now'),?)",
                 (job_id, project_id, kind, provider, model, tier, quantity, unit, stage))
    conn.commit()


def cancel_usage(conn: sqlite3.Connection, job_id: int) -> int:
    """Take a submission back out of the ledger: the provider never created the task (ClipAI 'not created'), so nothing was
    billed. Returns how many rows were removed."""
    cur = conn.execute("DELETE FROM usage_events WHERE job_id=? AND kind IN ('image','video')", (job_id,))
    conn.commit()
    return cur.rowcount


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
        elif r["kind"] == "llm":            # Claude tokens (trial 2026-09-27: priced as a clip → "chưa có giá: claude-sonnet-5")
            from .budget import token_price
            cost = token_price(pricing, r["model"], r["tier"], r["quantity"])
        else:
            cost = clip_price(pricing, r["model"], r["tier"], r["quantity"])
        if cost is None:
            unknown.add(f"{r['model']}:{r['tier']}" if r["kind"] == "video" else r["model"])
        else:
            total += cost
    return {"images": images, "audios": audios, "clips": len(clips), "seconds": seconds, "credits": total,
            "unknown_prices": sorted(unknown), "currency": pricing["currency"],
            "mock": sum(1 for r in rows if r["provider"].startswith("mock")), "events": len(rows)}
