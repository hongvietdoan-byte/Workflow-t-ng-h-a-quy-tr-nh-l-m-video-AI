"""Director hai lượt (kế hoạch V4 GĐ5 — H2 + H7 of docs/KE_HOACH_2026-09-25.md), behind the feature `director_two_pass`.

Today one big Claude call writes the Character Bible, every scene AND every shot (core/llm_runner.run_director). For a shot project
(shots.mode) with the feature on, the work is split the way a film crew splits it:

- **Tầng A — Đạo diễn** (1 call, prompts/19): Bible + per scene the intent — `emotional_intent`, `beat`, the kept lines (verbatim, in
  order; drops only with ✂), `target_s`, `focus`, `peak`, scene `sound`, `dp_notes`, `editor_notes`. Director knowledge only.
- **Tầng B — Quay phim** (1 call per scene, prompts/20 + 17): the shots of ONE scene. The shared part (rules, DP book, Bible, all
  intents) sits before the cache mark: the first scene writes the cache alone, the others then run in parallel threads and read it at
  ~1/10 price. A scene whose answer breaks a rule is re-asked on its own (ask_json: once, with the error); the scenes that passed are
  kept (projects.director_intent_raw), so a second run only asks the failed scenes again (`resume`).
- **Đạo diễn duyệt** (code, no call): each scene's shots against its intent — every kept line verbatim in order (hard: re-asked), the
  seconds within the intent's frame, the focus character in frame, a hold shot after a strong moment, plus the acting / sound warnings.
  The result is stored in the plan (`review`) and shown at Bước 1. No extra Claude call is made for flagged scenes (optional in the plan,
  not built: the flags go to the person).

The merged answer has exactly the single-call shape (genre, characters, scenes[*].shots, tradeoffs, script_notes, dropped_lines…) and goes
through the very same `llm_io.validate_for_project` (shot normaliser, schema, `_check_lines`) and `store_scene_analysis` (locked /
hand-edited Bible entries, `_user_locked` shot fields, store_plan) — every later step works unchanged.
"""
from . import access
import copy
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import dialogue, diag, features, knowledge, llm_io, prompts, shots
from .llm_io import SchemaError
from .pipeline import Pipeline

FEATURE = "director_two_pass"
PARALLEL = max(1, int(os.environ.get("DIRECTOR_PARALLEL", "3") or 3))   # Tầng B calls at the same time (after the first one)
FRAME_TOL_S, FRAME_TOL_SHARE = 1.0, 0.15    # a scene's shots may run ±max(1 s, 15%) around the Director's target_s
TARGET_MAX = 180                            # seconds: one script scene of a short video is never longer
INTENT_KEYS = ("focus", "peak", "target_s", "dp_notes", "editor_notes", "sound")   # Tầng A only: kept under scene["intent"]
# estimate (rough, labelled as such): characters of answer per item, thinking billed as output (effort medium — the Director of a
# 58-s script ran past 32k output tokens on 2026-09-24 with ~12k tokens of written answer), one 900-px reference picture ≈ w*h/750
OUT_CHARS = {"shot": 900, "scene": 1500, "intent": 900, "character": 900, "task": 1500}
THINK = 2.0
IMG_TOKENS = 1100
# 08/10 (#24: ước tính 0,21 USD, thực chi 0,47): đo trên các lượt thật trong usage_events — approx_tokens (2,5 ký tự / token) đếm thiếu
# ~1,5 lần phần vào (#24 Tầng A 46.254 thật / 30.986 ước tính; phần chung Tầng B 56.750 / 37.160), phần ra Tầng A 4–8,7k (ước 2,9k),
# Tầng B 8–17,6k mỗi cảnh (ước 6,5k). Luật chi phí: ước tính tính DƯ → hệ số vào + sàn phần ra = mức lớn nhất đã đo.
INPUT_FACTOR = 1.6
MEASURE_CALLS = 40                          # the last N Director calls of the ledger used as the floor of the output guess


class TwoPassError(Exception):
    pass


def enabled(proj) -> bool:
    """Two passes only make sense when there are shots to split (a v2 project keeps the single call: nothing to hand to a DP)."""
    return features.on(FEATURE) and shots.mode(proj) is not None


def frame_of(scene: Dict) -> Tuple[float, float]:
    t = float(scene.get("target_s") or 0)
    tol = max(FRAME_TOL_S, t * FRAME_TOL_SHARE)
    return round(max(0.5, t - tol), 1), round(t + tol, 1)


def _spoken(lines) -> List[Tuple[str, str]]:
    return [(str(d.get("speaker") or "").strip().upper(), str(d.get("text") or "").strip()) for d in lines or []
            if isinstance(d, dict) and str(d.get("text") or "").strip()
            and not dialogue.is_non_speaker(str(d.get("speaker") or ""))]


def kept_lines(scene: Dict) -> List[Tuple[str, str]]:
    """(SPEAKER, line) the Director kept for this scene, in order (on-screen text rows excluded — they are never voiced)."""
    return _spoken(scene.get("dialogue"))


def shot_lines(shot_list) -> List[Tuple[str, str]]:
    return [x for s in shot_list or [] if isinstance(s, dict) for x in _spoken(s.get("dialogue"))]


# ---- Tầng A: validation ----------------------------------------------------------------------------------------------------------
def validate_intent(pipeline: Pipeline, project_id: int) -> Callable[[Any], Dict]:
    """The Tầng A answer. Reuses llm_io.validate_scene_analysis for the Bible, locks, scene fields and cast (a probe with the shot-only
    scene fields filled), then checks what only the intent has: every script scene once, `emotional_intent`, `target_s`, `focus`, the
    kept lines (script's own words, in the script's order, all of them unless ✂). Wrong → sent back to Claude once (ask_json)."""
    story = shots.story_scenes(pipeline, project_id)
    script = {s["idx"]: [(who, said) for who, said in dialogue.lines(s["text"])] for s in story}
    proj = pipeline.project(project_id)
    trim = bool("dialogue_trim" in proj.keys() and proj["dialogue_trim"])

    def check(data: Any) -> Dict:
        obj = llm_io._load(data)
        for sc in obj.get("scenes") or []:
            if isinstance(sc, dict):
                sc.pop("shots", None)                  # the Director does not split shots in this pass (the DP does)
        probe = copy.deepcopy(obj)
        for sc in probe.get("scenes") or []:
            if isinstance(sc, dict):
                sc.setdefault("shot", "")
                sc.setdefault("image_prompt", "")
                for key in INTENT_KEYS + ("duration_s",):     # a scene's seconds are `target_s` here (may pass 30 s)
                    sc.pop(key, None)
        llm_io.validate_scene_analysis(probe)
        names = {c["name"] for c in obj["characters"]}
        seen = [sc["idx"] for sc in obj["scenes"]]
        if story:
            want = [s["idx"] for s in story]
            unknown = [i for i in seen if i not in want]
            missing = [i for i in want if i not in seen]
            if unknown or missing or len(seen) != len(set(seen)):
                raise SchemaError("scenes: cần đúng mỗi cảnh kịch bản một lần (" + ", ".join(map(str, want)) + ")"
                                  + (f"; thiếu {missing}" if missing else "") + (f"; lạ {unknown}" if unknown else ""))
        for sc in obj["scenes"]:
            w = f"scenes[idx={sc['idx']}]"
            sc["beat"] = llm_io._clean_beat(sc.get("beat")) if "beat" in sc else None
            if sc["beat"] is None:
                sc.pop("beat")
            if not isinstance(sc.get("emotional_intent"), str) or not sc["emotional_intent"].strip():
                raise SchemaError(f"{w}.emotional_intent: bắt buộc — người xem phải cảm gì ở cảnh này")
            t = sc.get("target_s")
            if not isinstance(t, (int, float)) or isinstance(t, bool) or not 1 <= t <= TARGET_MAX:
                raise SchemaError(f"{w}.target_s: số giây của cảnh (1–{TARGET_MAX}), bắt buộc")
            focus = sc.get("focus")
            if focus not in (None, ""):
                if not isinstance(focus, str) or focus not in names:
                    raise SchemaError(f"{w}.focus: '{focus}' không có trong Character Bible")
            peak = sc.get("peak")
            if peak is not None and (not isinstance(peak, int) or isinstance(peak, bool) or not 1 <= peak <= 5):
                raise SchemaError(f"{w}.peak: số nguyên 1–5 hoặc bỏ trống")
            for key in ("dp_notes", "editor_notes"):
                if sc.get(key) is not None and not isinstance(sc.get(key), str):
                    raise SchemaError(f"{w}.{key}: cần chữ")
            if "sound" in sc:
                from . import sound_intent
                sound, _ = sound_intent.clean(sc.get("sound"))
                if sound:
                    sc["sound"] = sound
                else:
                    sc.pop("sound")
            if story:
                _check_kept(sc, script.get(sc["idx"]) or [], trim, w)
        for key in ("tradeoffs", "script_notes", "dropped_lines", "ip_risk_notes"):
            if obj.get(key) is not None and not isinstance(obj[key], list):
                raise SchemaError(f"root.{key}: cần danh sách")
        return obj
    return check


def _check_kept(sc: Dict, script_lines: List[Tuple[str, str]], trim: bool, where: str) -> None:
    """The kept lines are the script's own words, by the script's speaker, in the script's order (a subsequence); all of them without ✂."""
    from .voice_direction import clean as clean_delivery
    for d in sc.get("dialogue") or []:
        if isinstance(d, dict) and "delivery" in d:
            how, _ = clean_delivery(d.get("delivery"))
            if how:
                d["delivery"] = how
            else:
                d.pop("delivery")
    kept = kept_lines(sc)
    pos = 0
    norm_script = [(who.upper(), dialogue.norm(said)) for who, said in script_lines]
    for who, said in kept:
        n = dialogue.norm(said)
        at = next((k for k in range(pos, len(norm_script)) if norm_script[k][1] == n), None)
        if at is None:
            anywhere = any(t == n for _, t in norm_script)
            raise SchemaError(f"{where}.dialogue: " + (f"câu sai thứ tự so với kịch bản: “{said}”" if anywhere else
                                                       f"câu không có nguyên văn trong cảnh này của kịch bản (không thêm, không sửa chữ): “{said}”"))
        if norm_script[at][0] != who:
            raise SchemaError(f"{where}.dialogue: “{said}” là câu của {norm_script[at][0]}, không phải {who}")
        pos = at + 1
    if not trim and len(kept) != len(norm_script):
        have = {dialogue.norm(t) for _, t in kept}
        dropped = [said for _, said in script_lines if dialogue.norm(said) not in have]
        raise SchemaError(f"{where}.dialogue: thiếu câu thoại của kịch bản (không được bỏ): " + "; ".join(dropped[:3]))


# ---- Tầng B: validation of one scene ---------------------------------------------------------------------------------------------
def check_scene(scene: Dict, names) -> Callable[[Any], Dict]:
    """One scene's shots from the DP: the per-scene part of the normaliser (enum spellings, a spoken shot shorter than its line, 0,5 s
    silent shots, short wide shots — the film total is fitted later on the whole plan), the shot schema, and the lines: exactly the
    Director's kept lines, verbatim, same speaker, same order."""
    idx = scene["idx"]
    kept = kept_lines(scene)

    def check(data: Any) -> Dict:
        part = llm_io._load(data)
        if part.get("idx") not in (None, idx):
            raise SchemaError(f"idx: cần {idx} (chỉ chia shot Cảnh {idx})")
        if "shots" not in part and isinstance(part.get("scenes"), list) and len(part["scenes"]) == 1:
            part = dict(part["scenes"][0], tradeoffs=part.get("tradeoffs"))     # an answer in the single-call shape
        from .shot_normalize import normalize
        probe = {"scenes": [{"idx": idx, "shots": part.get("shots")}]}
        if isinstance(part.get("shots"), list):
            _, changes = normalize(probe, "", None, in_place=True)
        else:
            changes = []
        try:
            shots.validate(probe["scenes"][0]["shots"], f"scenes[idx={idx}].shots", names)
        except shots.ShotError as e:
            raise SchemaError(str(e)) from e
        got = shot_lines(probe["scenes"][0]["shots"])
        if [(w, dialogue.norm(t)) for w, t in got] != [(w, dialogue.norm(t)) for w, t in kept]:
            raise SchemaError(f"Cảnh {idx}: thoại trong shot phải đúng {len(kept)} câu Đạo diễn giữ, nguyên văn, đúng người nói, đúng thứ tự"
                              f" — nhận {len(got)} câu" + _first_mismatch(got, kept))
        trade = part.get("tradeoffs")
        if trade is not None and not isinstance(trade, list):
            raise SchemaError("tradeoffs: cần danh sách")
        return {"idx": idx, "shots": probe["scenes"][0]["shots"], "tradeoffs": [t for t in trade or [] if isinstance(t, dict)],
                "normalized": changes}
    return check


def _first_mismatch(got, kept) -> str:
    for k in range(max(len(got), len(kept))):
        a = got[k] if k < len(got) else None
        b = kept[k] if k < len(kept) else None
        if a is None or b is None or a[0] != b[0] or dialogue.norm(a[1]) != dialogue.norm(b[1]):
            return (f"; câu {k + 1}: cần “{b[0]}: {b[1]}”" if b else f"; câu {k + 1} thừa") + (f", nhận “{a[0]}: {a[1]}”" if a else "")
    return ""


# ---- merge + review ----------------------------------------------------------------------------------------------------------------
def merge(intent: Dict, parts: Dict[int, Dict]) -> Dict:
    """The single-call answer rebuilt from Tầng A + every Tầng B part: scene fields from the Director, `shots` from the DP, the
    Director's voice direction carried onto the DP's line when the DP left it out; Tầng A-only fields under scene["intent"]."""
    obj = {k: copy.deepcopy(v) for k, v in intent.items() if k != "scenes"}
    trade = [t for t in obj.get("tradeoffs") or [] if isinstance(t, dict)]
    changes = list(obj.get("normalized") or [])
    scenes = []
    for sc in intent["scenes"]:
        part = parts[sc["idx"]]
        s = {k: copy.deepcopy(v) for k, v in sc.items() if k not in INTENT_KEYS}
        s["intent"] = {k: copy.deepcopy(sc[k]) for k in INTENT_KEYS if k in sc}
        s["shots"] = copy.deepcopy(part["shots"])
        how = [d.get("delivery") for d in sc.get("dialogue") or [] if isinstance(d, dict) and str(d.get("text") or "").strip()
               and not dialogue.is_non_speaker(str(d.get("speaker") or ""))]
        k = 0
        for shot in s["shots"]:
            for d in shot.get("dialogue") or []:
                if not isinstance(d, dict) or dialogue.is_non_speaker(str(d.get("speaker") or "")):
                    continue
                if k < len(how) and how[k] and not d.get("delivery"):
                    d["delivery"] = copy.deepcopy(how[k])
                k += 1
        s.setdefault("shot", "theo danh sách shot của Quay phim")
        if not str(s.get("image_prompt") or "").strip():
            s["image_prompt"] = str(s["shots"][0].get("image_prompt") or "") if s["shots"] else ""
        total = round(sum(float(x.get("duration_s") or 0) for x in s["shots"]), 1)
        s.pop("duration_s", None)
        if 1 <= total <= 30:
            s["duration_s"] = total
        scenes.append(s)
        trade += [dict(t, scene=t.get("scene", sc["idx"])) for t in part.get("tradeoffs") or []]
        changes += part.get("normalized") or []
    obj["scenes"] = scenes
    if trade:
        obj["tradeoffs"] = trade
    if changes:
        obj["normalized"] = changes
    return obj


def review(obj: Dict) -> Dict:
    """Đạo diễn duyệt — code only: each scene's shots against its intent. `flags` need the person's eye (shown at Bước 1); `notes` are
    the acting / sound warnings of the scene's shots (soft, as in the Director report)."""
    from . import performance, sound_intent
    out = []
    for sc in obj.get("scenes") or []:
        intent = sc.get("intent") or {}
        shot_list = sc.get("shots") or []
        flags = []
        kept = kept_lines(sc)
        got = shot_lines(shot_list)
        if [(w, dialogue.norm(t)) for w, t in got] != [(w, dialogue.norm(t)) for w, t in kept]:
            flags.append("thoại trong shot lệch danh sách Đạo diễn giữ" + _first_mismatch(got, kept))
        total = round(sum(float(s.get("duration_s") or 0) for s in shot_list), 1)
        if intent.get("target_s"):
            lo, hi = frame_of(intent)
            if not lo - 0.05 <= total <= hi + 0.05:
                flags.append(f"tổng shot {total:g}s ngoài khung {lo:g}–{hi:g}s (Đạo diễn đặt {intent['target_s']:g}s)")
        focus = intent.get("focus")
        if focus and not any(focus in (s.get("characters") or []) for s in shot_list):
            flags.append(f"trọng tâm {focus} không có trong khung shot nào")
        peak = intent.get("peak")
        if isinstance(peak, int) and peak >= performance.STRONG and not any(float(s.get("duration_s") or 0) >= performance.HOLD_S
                                                                            for s in shot_list):
            flags.append(f"khoảnh khắc mạnh (peak {peak}) mà không shot nào ≥ {performance.HOLD_S:g}s để người xem thấm")
        notes = performance.warnings(shot_list) + sound_intent.warnings(shot_list)
        out.append({"idx": sc.get("idx"), "ok": not flags, "flags": flags, "notes": notes, "total_s": total,
                    "target_s": intent.get("target_s"), "shots": len(shot_list)})
    return {"scenes": out, "flagged": [r["idx"] for r in out if not r["ok"]]}


def review_text(rv: Dict) -> List[str]:
    rows = []
    for r in rv.get("scenes") or []:
        head = f"Cảnh {r['idx']}: {r['shots']} shot · {r['total_s']:g}s" + (f" / ý đồ {r['target_s']:g}s" if r.get("target_s") else "")
        rows.append(head + (" — ✅ đạt ý đồ" if r["ok"] else " — ⚠ " + "; ".join(r["flags"])))
    return rows


# ---- estimate ----------------------------------------------------------------------------------------------------------------------
def _model_of(client=None, model: Optional[str] = None) -> str:
    from .llm_runner import DEFAULT_MODEL
    return model or getattr(client, "model", "") or os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL


def _usd(model: str, tokens: Dict[str, float]) -> Optional[float]:
    from . import budget, cost
    pricing = cost.load_pricing()
    total = 0.0
    for tier, n in tokens.items():
        if not n:
            continue
        price = budget.token_price(pricing, model, tier, n)
        if price is None:
            return None
        total += price
    return round(total, 3)


def _ref_count(conn, project_id: int) -> int:
    from . import assets
    return sum(1 for a in assets.project_assets(conn, project_id) if a["kind"] in ("character", "pet") and a["images"])


def measured(conn, model: Optional[str] = None) -> Dict:
    """The output tokens of real Director calls (usage_events, stage 'director'): one call = the rows written at the same second for one
    project. A call with cache rows is a Tầng B (Quay phim) call, one without is Tầng A or the single Director. {"a_out", "b_out",
    "b_in", "b_common" (the cached shared part), "calls"} — the largest seen (0 when none)."""
    sql = ("SELECT COALESCE(project_id, deleted_project_id) pid, at, tier, quantity FROM usage_events WHERE kind='llm' AND stage='director'"
           + (" AND model=?" if model else "") + " ORDER BY id DESC LIMIT ?")
    calls: Dict = {}
    try:
        rows = conn.execute(sql, ((model,) if model else ()) + (MEASURE_CALLS * 4,)).fetchall()
    except Exception:  # noqa: BLE001 - no ledger table (old test data): nothing measured
        rows = []
    for r in rows:
        calls.setdefault((r[0], r[1]), {})[r[2]] = float(r[3] or 0)
    import datetime as _dt

    def when(at):
        try:
            return _dt.datetime.fromisoformat(str(at)[:19])
        except ValueError:
            return None
    items = list(calls.items())[:MEASURE_CALLS]
    b_calls = [(pid, when(at)) for (pid, at), tiers in items if tiers.get("cache_write") or tiers.get("cache_read")]
    out = {"a_out": 0, "b_out": 0, "b_in": 0, "b_common": 0, "calls": 0}
    for (pid, at), tiers in items:
        if tiers.get("cache_write") or tiers.get("cache_read"):
            out["b_out"] = max(out["b_out"], int(tiers.get("output", 0)))
            out["b_in"] = max(out["b_in"], int(tiers.get("input", 0)))
            out["b_common"] = max(out["b_common"], int(tiers.get("cache_write", 0) or tiers.get("cache_read", 0)))
            out["calls"] += 1
            continue
        t = when(at)                                  # Tầng A = a call followed by Tầng B calls of the same project (a single Director
        if t is not None and any(bp == pid and bt is not None and 0 <= (bt - t).total_seconds() <= 900 for bp, bt in b_calls):
            out["a_out"] = max(out["a_out"], int(tiers.get("output", 0)))     # run is not one: its 32k answers are not Tầng A's)
            out["calls"] += 1
    return out


def estimate(p: Pipeline, project_id: int, client=None, model: Optional[str] = None) -> Dict:
    """Rough cost of one Director run, both ways (luật chi phí: shown before the button). Input tokens are counted from the real prompt
    text (knowledge.approx_tokens, ~2,5 characters per token) + ~IMG_TOKENS per reference picture; output tokens are guessed from the
    number of shots (the current plan, else one per line + two per scene) × OUT_CHARS, × THINK for the thinking. Retries not included."""
    proj = p.project(project_id)
    model = _model_of(client, model)
    story = shots.story_scenes(p, project_id)
    n_scenes = max(1, len(story))
    n_lines = sum(len(dialogue.lines(s["text"])) for s in story)
    have = [r for r in shots.shots_of(p, project_id) if r["data"].get("shot_no")]
    n_shots = len(have) or (n_lines + 2 * n_scenes)
    n_chars = max(1, len(prompts.people_in_project(p, project_id)))
    imgs = _ref_count(p.conn, project_id) * IMG_TOKENS
    tok = lambda chars: round(knowledge.approx_tokens(chars) * INPUT_FACTOR)   # noqa: E731 - 08/10: measured undercount
    think = lambda chars: round(knowledge.approx_tokens(chars) * THINK)      # noqa: E731
    seen = measured(p.conn, model)
    single_in = tok(len(prompts.build_director_bundle(p, project_id))) + imgs
    single_out = think(n_shots * OUT_CHARS["shot"] + n_scenes * OUT_CHARS["scene"] + n_chars * OUT_CHARS["character"])
    single = {"calls": 1, "input": single_in, "output": single_out,
              "usd": _usd(model, {"input": single_in, "output": single_out})}
    out = {"model": model, "shots_guess": n_shots, "scenes": n_scenes, "single": single, "two_pass": None,
           "active": "two_pass" if enabled(proj) else "single", "measured": seen}
    if shots.mode(proj):
        intent_chars = n_scenes * OUT_CHARS["intent"] + n_chars * OUT_CHARS["character"]
        a_in = tok(len(prompts.build_intent_bundle(p, project_id))) + imgs
        a_out = max(think(intent_chars), seen["a_out"])                     # 08/10: never under the largest real Tầng A answer
        common = max(tok(len(prompts.dp_common(p, project_id, {"characters": [], "scenes": []})) + intent_chars), seen["b_common"])
        task = max(tok(OUT_CHARS["task"] + OUT_CHARS["intent"]), seen["b_in"])
        b_out = max(think(n_shots * OUT_CHARS["shot"]), seen["b_out"] * n_scenes)   # per scene call, measured floor
        tiers = {"input": a_in + task * n_scenes, "cache_write": common, "cache_read": common * (n_scenes - 1),
                 "output": a_out + b_out}
        out["two_pass"] = {"calls": 1 + n_scenes, "input": tiers["input"], "cache_write": common,
                           "cache_read": tiers["cache_read"], "output": tiers["output"], "usd": _usd(model, tiers),
                           "tier_a": {"input": a_in, "output": a_out}, "tier_b": {"common": common, "task": task, "output": b_out}}
    from . import director_byd
    if director_byd.enabled():                     # K1a cờ shot_intent: BYĐ mỗi shot (thêm phần ra) + tối đa 2 lượt sửa (tính dư)
        extra = director_byd.estimate(n_shots)
        for key in ("single", "two_pass"):
            if out[key]:
                out[key]["output"] += extra["extra_output"]
                out[key]["usd"] = _usd(model, {k: v for k, v in out[key].items() if k in ("input", "output", "cache_write", "cache_read")})
        extra["usd"] = _usd(model, {"input": extra["repair_input"], "output": extra["repair_output"]})
        out["byd"] = extra
    return out


def _n(x: float) -> str:
    return f"{int(x):,}".replace(",", ".")


def estimate_text(est: Dict) -> str:
    """One line for the button (no "$": Streamlit reads it as math — same as cost.price_tag)."""
    def money(x):
        return f"≈ {x['usd']:.2f} USD".replace(".", ",") if x.get("usd") is not None else "(model chưa có giá trong data/pricing.json)"
    s = est["single"]
    one = f"1 lượt · ~{_n(s['input'])} token vào / ~{_n(s['output'])} ra {money(s)}"
    tp = est.get("two_pass")
    two = (f"{tp['calls']} lượt (1 Đạo diễn + {tp['calls'] - 1} Quay phim, phần chung cache) · ~{_n(tp['input'] + tp['cache_write'])} token "
           f"vào + {_n(tp['cache_read'])} đọc cache / ~{_n(tp['output'])} ra {money(tp)}") if tp else ""
    if est["active"] == "two_pass":
        text = f"Ước tính Director hai lượt ({est['model']}): {two} — một lượt như cũ: {one}"
    else:
        text = f"Ước tính Director ({est['model']}): {one}" + (f" — nếu bật hai lượt: {two}" if two else "")
    seen = est.get("measured") or {}
    byd = est.get("byd")
    if byd:                                        # K1a cờ shot_intent (tắt → câu y cũ)
        text += (f" · BYĐ: đã cộng ~{_n(byd['extra_output'])} token ra; sửa BYĐ tối đa {byd['repair_calls_max']} lượt "
                 f"~{_n(byd['repair_input'])} vào / ~{_n(byd['repair_output'])} ra {money(byd)}")
    return (text +f" · tính dư, ~{est['shots_guess']} shot" + (f", sàn phần ra theo {seen['calls']} lượt Director thật" if seen.get("calls") else "")
            + ", chưa tính hỏi lại")


def _budget_guard(p: Pipeline, client, usd: Optional[float]) -> None:
    """Refuse before the first call when the whole run would not fit in the Claude money left (the per-call check in the client stays)."""
    from .llm_runner import LlmError
    if not getattr(client, "ledger", None) or usd is None:
        return
    from . import budget
    st = budget.status(p.conn)
    if st["llm_usd"] > 0 and usd > st["llm_left"] + 1e-9:
        raise LlmError(f"Director hai lượt ước tính ~${usd:.2f} nhưng tiền Claude còn ${st['llm_left']:.2f} — nạp thêm / nới trần "
                       "Claude (⚙) rồi chạy lại. Chưa gọi Claude, chưa tốn tiền.", code="budget")


# ---- run ---------------------------------------------------------------------------------------------------------------------------
def _fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def load_raw(p: Pipeline, project_id: int) -> Dict:
    row = p.project(project_id)
    try:
        return json.loads((row["director_intent_raw"] if "director_intent_raw" in row.keys() else None) or "{}")
    except ValueError:
        return {}


def intent_all(p: Pipeline, project_id: int) -> Dict:
    """The Director's intent per script scene for a reader that comes AFTER the Director (the rough-cut review, KE_HOACH_DUYET_BAN_THO P0):
    one reader of `director_intent_raw` instead of a second copy in `scenes.data` (CHUAN_XAY_DUNG luật 4 — one source). Returns
    {"source": "director_intent_raw" | "story_scene" | "none", "stale": bool, "fingerprint": str, "scenes": {idx: {...}}}.
    `director_intent_raw` (two passes) carries focus / peak / target_s / dp_notes / editor_notes / sound; a single-call project has only
    what the script scene itself stores (emotional_intent, beat) — said in `source`, never filled in silently. `stale` = the plan was
    replaced after the intent was written (forget()), so the intent no longer belongs to the shots. The fingerprint changes when the
    intent does, so a review built on the old one expires."""
    raw = load_raw(p, project_id)
    scenes: Dict[int, Dict] = {}
    source = "none"
    intent = raw.get("intent") if isinstance(raw.get("intent"), dict) else None
    if intent and not raw.get("stale"):
        for sc in intent.get("scenes") or []:
            if isinstance(sc, dict) and isinstance(sc.get("idx"), int):
                scenes[sc["idx"]] = {k: copy.deepcopy(sc[k]) for k in ("emotional_intent", "beat") + INTENT_KEYS if k in sc}
        source = "director_intent_raw" if scenes else "none"
    if not scenes:
        for r in p.conn.execute("SELECT idx, data FROM story_scenes WHERE project_id=? ORDER BY idx", (project_id,)):
            try:
                d = json.loads(r["data"] or "{}")
            except ValueError:
                d = {}
            got = {k: d[k] for k in ("emotional_intent", "beat") if d.get(k)}
            if got:
                scenes[r["idx"]] = got
        source = "story_scene" if scenes else "none"
    return {"source": source, "stale": bool(raw.get("stale")), "scenes": scenes,
            "fingerprint": _fingerprint(json.dumps([source, scenes], sort_keys=True, ensure_ascii=False))}


def intent_for(p: Pipeline, project_id: int, idx: int) -> Dict:
    """The intent of ONE script scene (see intent_all); {} when there is none."""
    return dict(intent_all(p, project_id)["scenes"].get(idx) or {})


def _save_raw(p: Pipeline, project_id: int, raw: Dict) -> None:
    p.set_project_field(project_id, "director_intent_raw", json.dumps(raw, ensure_ascii=False))


def forget(p: Pipeline, project_id: int) -> None:
    """The plan was replaced another way (single call, pasted JSON): the stored intent no longer belongs to it."""
    row = p.project(project_id)
    if "director_intent_raw" in row.keys() and row["director_intent_raw"]:
        old = load_raw(p, project_id)
        _save_raw(p, project_id, {"stale": True, "previous_intent": old.get("intent") or old.get("previous_intent")})


def pending_scenes(p: Pipeline, project_id: int) -> List[int]:
    """Scenes whose Tầng B answer is still missing after a failed run (a resume only asks these again)."""
    raw = load_raw(p, project_id)
    if not raw.get("intent") or raw.get("done"):
        return []
    have = {int(k) for k in (raw.get("parts") or {})}
    return [sc["idx"] for sc in raw["intent"].get("scenes") or [] if sc.get("idx") not in have]


def _ask_scenes(p: Pipeline, project_id: int, client, intent: Dict, todo: List[int], common: str,
                notes: Optional[Dict[int, str]] = None, currents: Optional[Dict[int, Any]] = None
                ) -> Tuple[Dict[int, Dict], Dict[int, str], int, int, List[Tuple[int, str]]]:
    """Tầng B for these scenes: the first one alone (it writes the cache), the rest in parallel threads (they read it). Threads only call
    Claude and run pure checks — every database write stays in this thread."""
    from .llm_runner import LlmError, ask_json, tagged
    names = {c["name"] for c in intent["characters"]}
    by_idx = {sc["idx"]: sc for sc in intent["scenes"]}
    parts: Dict[int, Dict] = {}
    errors: Dict[int, str] = {}
    retried: List[Tuple[int, str]] = []
    tokens = [0, 0]

    def one(idx: int):
        prompt = prompts.build_dp_bundle(p, project_id, intent, idx, note=(notes or {}).get(idx, ""),
                                         current=(currents or {}).get(idx), common=common)
        box: List[str] = []
        with tagged("director", project_id):
            try:
                part, tin, tout = ask_json(client, prompt, check_scene(by_idx[idx], names), note=box.append)
            except LlmError as e:
                return idx, None, str(e), box, e
        return idx, (part, tin, tout), None, box, None

    def collect(res):
        idx, ok, err, box, exc = res
        retried.extend((idx, m) for m in box)
        if ok:
            parts[idx] = ok[0]
            tokens[0] += ok[1]
            tokens[1] += ok[2]
        else:
            errors[idx] = err
            if exc is not None and exc.code in ("auth", "config", "budget"):
                raise exc                               # nothing else will work either: stop, keep what passed

    if todo:
        collect(one(todo[0]))
        rest = todo[1:]
        if rest:
            with ThreadPoolExecutor(max_workers=min(PARALLEL, len(rest))) as pool:
                for res in pool.map(one, rest):
                    collect(res)
    return parts, errors, tokens[0], tokens[1], retried


def run(p: Pipeline, project_id: int, client, resume: bool = False) -> Dict:
    """Tầng A → Tầng B (every scene) → merge → the single call's validation + storing → Đạo diễn duyệt. resume: reuse a stored Tầng A
    answer and the scene answers that passed, when the prompts they came from are unchanged (a failed run is not paid twice)."""
    access.need_edit(p, project_id, "chạy Director")
    from .llm_runner import LlmError, _director_references, _retry_note, ask_json
    conn = p.conn
    if shots.has_work(conn, project_id):          # store_plan would refuse AFTER paying: say it before any call (no money spent)
        raise SchemaError("Dự án đã có ảnh/video làm theo các cảnh hiện tại — bấm “↺ Làm lại” (hoặc tạo dự án mới) trước khi chia shot lại. "
                          "Chưa gọi Claude, chưa tốn tiền.")
    refs = _director_references(conn, project_id)
    diag.record(conn, "director", "info", f"Director xem {len(refs)} ảnh nhân vật/thú cưng: "
                + (", ".join(label.split("—", 1)[-1].strip(" :") for label, _ in refs) or "không có (nhân vật không gắn tài nguyên)")
                + " (Tầng A — Đạo diễn, hai lượt)", "director_refs", project_id)
    est = estimate(p, project_id, client)
    _budget_guard(p, client, (est.get("two_pass") or {}).get("usd"))
    bundle = prompts.build_intent_bundle(p, project_id)
    fp_a = _fingerprint(bundle)
    raw = load_raw(p, project_id) if resume else {}
    tin = tout = 0
    a_called = False
    if raw.get("intent") and raw.get("fp_a") == fp_a and not raw.get("done"):
        intent = raw["intent"]
        diag.record(conn, "director", "info", "Director hai lượt: dùng lại ý đồ Tầng A đã trả tiền (prompt không đổi)", "two_pass_resume",
                    project_id)
    else:
        a_called = True
        try:
            intent, tin, tout = ask_json(client, bundle, validate_intent(p, project_id), refs, note=_retry_note(p, "director", project_id))
        except LlmError as e:
            if e.partial is not None:
                _save_raw(p, project_id, {"truncated": True, "error": str(e), "text": e.partial, "pass": "A"})
            raise
        raw = {"fp_a": fp_a, "intent": intent, "parts": {}}
        _save_raw(p, project_id, raw)                  # paid for: kept even if Tầng B fails
    common = prompts.dp_common(p, project_id, intent)
    fp_b = _fingerprint(common)
    parts = {int(k): v for k, v in (raw.get("parts") or {}).items()} if raw.get("fp_b") == fp_b else {}
    reused = sorted(parts)
    raw.update(fp_b=fp_b, parts={str(k): v for k, v in parts.items()}, failed={})
    todo = [sc["idx"] for sc in intent["scenes"] if sc["idx"] not in parts]
    diag.record(conn, "director", "info", f"Quay phim (Tầng B): {len(todo)} lượt cho cảnh {todo}"
                + (f", dùng lại {len(reused)} cảnh đã chia {reused}" if reused else "")
                + f" — không gửi ảnh (dùng Character Bible Tầng A viết từ {len(refs)} ảnh); phần chung ~"
                  f"{_n(knowledge.approx_tokens(len(common)))} token cache", "dp_calls", project_id)
    new, errors, b_in, b_out, retried = _ask_scenes(p, project_id, client, intent, todo, common)
    for idx, message in retried:
        diag.record(conn, "director", "warn", f"Cảnh {idx} (Quay phim): {message}", "bad_json_retry", project_id)
    parts.update(new)
    tin, tout = tin + b_in, tout + b_out
    raw["parts"] = {str(k): v for k, v in parts.items()}
    raw["failed"] = {str(k): v for k, v in errors.items()}
    _save_raw(p, project_id, raw)
    if errors:
        raise LlmError("Quay phim chưa chia được cảnh " + ", ".join(map(str, sorted(errors))) + ": "
                       + " | ".join(f"cảnh {k}: {v[:160]}" for k, v in sorted(errors.items()))
                       + f" — {len(parts)} cảnh đã chia được giữ lại; bấm “↻ Chỉ hỏi lại cảnh lỗi” để hỏi lại riêng các cảnh này.",
                       code="bad_json")
    merged = merge(intent, parts)
    try:
        obj = llm_io.validate_for_project(p, project_id)(merged)   # normaliser (film total) + schema + every line of the script
    except SchemaError as e:
        p.set_project_field(project_id, "director_raw", json.dumps(dict(merged, invalid=str(e)), ensure_ascii=False))
        raise LlmError(f"kế hoạch ghép từ hai lượt không hợp lệ: {e}", code="bad_plan") from e
    obj["review"] = review(obj)
    calls = int(a_called) + len(todo)
    obj["two_pass"] = {"calls": calls, "reused_intent": not a_called, "reused_scenes": reused}
    from . import project_defaults                 # S3.8: which places (text + pictures) the plan was made with
    obj["places_at_plan"] = project_defaults.places_fingerprint(p.conn, project_id)
    from . import director_byd                     # K1a cờ shot_intent: kiểm BYĐ từng shot, sửa ≤ 2 vòng (tắt → không làm gì)
    director_byd.settle(conn, project_id, obj, client)
    p.set_project_field(project_id, "director_raw", json.dumps(obj, ensure_ascii=False))     # paid for: kept even if saving fails
    llm_io.store_scene_analysis(p, project_id, obj)
    raw["done"] = True
    _save_raw(p, project_id, raw)
    flagged = obj["review"]["flagged"]
    diag.record(conn, "director", "warn" if flagged else "info",
                "Đạo diễn duyệt: " + ("; ".join(review_text(obj["review"])) if flagged else f"{len(obj['scenes'])} cảnh đạt ý đồ"),
                "director_review", project_id)
    return {"characters": len(obj["characters"]), "scenes": len(obj["scenes"]), "input_tokens": tin, "output_tokens": tout,
            "ip_risk_notes": obj.get("ip_risk_notes") or [], "two_pass": True, "calls": calls,
            "reused_scenes": reused, "flagged": flagged, "estimate": est}


def replan_scene(p: Pipeline, project_id: int, scene_idx: int, client, note: str = "") -> Dict:
    """"↻ Chia shot lại cảnh này" with the two passes: one Tầng B call for that scene, from the stored intent (the shared part is the
    same text → read from the cache), merged into the stored plan, checked as a whole, then shots.replace_from (earlier scenes keep
    their rows and work)."""
    access.need_edit(p, project_id, "chia shot lại")
    from .llm_runner import LlmError
    raw = load_raw(p, project_id)
    plan = json.loads(p.project(project_id)["director_raw"] or "{}")
    if not raw.get("intent") or not plan.get("scenes") or plan.get("truncated") or plan.get("invalid"):
        raise LlmError("chưa có kế hoạch Director hai lượt đầy đủ để chia lại một cảnh — chạy Director cho cả kịch bản trước", code="config")
    intent = raw["intent"]
    if scene_idx not in {sc["idx"] for sc in intent["scenes"]}:
        raise LlmError(f"Cảnh {scene_idx} không có trong ý đồ Tầng A", code="config")
    current = [{k: s["data"].get(k) for k in ("shot_no", "size", "angle", "duration_s", "characters", "action", "dialogue")}
               for s in shots.shots_of(p, project_id) if s["data"].get("story_scene") == scene_idx]
    common = prompts.dp_common(p, project_id, intent)
    new, errors, tin, tout, retried = _ask_scenes(p, project_id, client, intent, [scene_idx], common, {scene_idx: note},
                                                  {scene_idx: current})
    for idx, message in retried:
        diag.record(p.conn, "director", "warn", f"Cảnh {idx} (Quay phim): {message}", "bad_json_retry", project_id)
    if errors:
        raise LlmError(f"Quay phim chưa chia lại được cảnh {scene_idx}: {errors[scene_idx]}", code="bad_json")
    parts = {sc["idx"]: {"idx": sc["idx"], "shots": sc["shots"], "tradeoffs": []} for sc in plan["scenes"]}
    parts[scene_idx] = new[scene_idx]
    base = [t for t in intent.get("tradeoffs") or [] if isinstance(t, dict)]      # the Director's own stay; the DP's of this scene go
    others = [t for t in plan.get("tradeoffs") or [] if isinstance(t, dict) and t not in base and t.get("scene") != scene_idx]
    merged = merge(dict(intent, tradeoffs=base + others), parts)
    obj = llm_io.validate_for_project(p, project_id)(merged)
    obj["review"] = review(obj)
    from . import director_byd                     # K1a cờ shot_intent: chỉ cảnh vừa chia lại
    director_byd.settle(p.conn, project_id, obj, client, only_scene=scene_idx)
    n = shots.replace_from(p, project_id, obj["scenes"], scene_idx)
    raw.setdefault("parts", {})[str(scene_idx)] = new[scene_idx]
    _save_raw(p, project_id, raw)
    p.set_project_field(project_id, "director_raw", json.dumps(obj, ensure_ascii=False))
    return {"scene": scene_idx, "rows": n, "input_tokens": tin, "output_tokens": tout, "normalized": obj.get("normalized") or [],
            "review": obj["review"]}
