"""The Editor and the Director review the rough cut together (docs/KE_HOACH_DUYET_BAN_THO_2026-10-02.md P2 — report only, nothing is applied).

    rough_cut.build  ->  Biên tập viên (Claude call 1: sheets of frames + numbers + the Director's intent, prompt 24, the review blocks of
                         editing.md)  ->  code vets every proposal against closed lists and the real shot clock  ->  Đạo diễn (Claude
                         call 2, text only, prompt 25) agrees / objects / adjusts each one against the intent they wrote  ->  code
                         reconciles: agreed / modified / contested (both reasons shown to the person; nothing is dropped on an objection).

The model states what it OBSERVED from a closed list (it cannot hear: sound reaches it as numbers) and proposes with the knobs that exist;
the code, not the model, decides what is allowed (GĐ3 lesson: the model sees right but concludes wrong). Feature `rough_cut_review`
(off). Costs Claude: shown before the click (`estimate`), one task cap (RUN_CAP_USD), cached by the render + intent fingerprint.

    run(p, project_id, client, data_dir, force=False) -> result (also saved: data/<pid>/editor_review.json)
    estimate(conn, images) -> USD or None;   lines(result) -> [text]
"""
import hashlib
import json
import os
import re
from typing import Dict, List, Optional, Tuple

from . import claude_tasks, cost, director_two_pass, features, llm_runner, rough_cut, shots as shots_mod, sound_intent

STAGE = "editor"
PROMPT_EDITOR, PROMPT_DIRECTOR = "24_editor_review.md", "25_director_on_editor.md"
PROMPT_VERSION = 3                       # bump when a prompt or a list below changes: a saved review then expires
MAX_FINDINGS = 6                         # a longer list drowns the cut ("fix everything" ruins its rhythm)
RUN_CAP_USD = 0.40                       # one review (two calls, ~0.17 USD estimated): the hard lock of the task (llm_runner.spend_cap)
AMOUNT_MIN, AMOUNT_MAX = 0.2, 3.0
OBSERVED = ("drag", "rush", "cut_off_beat", "peak_unsupported", "music_competes", "silence_wanted", "transition_jarring", "flat_run", "other")
ACTIONS = ("shorten_shot", "extend_hold", "music_cue", "transition", "slow_or_freeze", "suggest_flag", "retrim_from_raw", "none")
FLAG_HINTS = ("j_cut", "motion_trim", "speed_ramp")
TRANSITIONS = ("cut", "crossfade", "dip_to_black")
# The shared priority scale (knowledge/roles/README.md, Dựng row): clear speech / legible text first, then the cut's rhythm, then continuity,
# then looks. Used to order what the person reads — never to drop a proposal.
RANK = {"music_competes": 1, "peak_unsupported": 1, "silence_wanted": 1, "drag": 3, "rush": 3, "cut_off_beat": 3, "flat_run": 3,
        "transition_jarring": 4, "other": 5}
NEEDS_SHOT = ("shorten_shot", "extend_hold", "music_cue", "transition", "slow_or_freeze", "retrim_from_raw")
FILE = "editor_review.json"
_REVIEW = re.compile(r"^<!-- review -->\n(.*?)^<!-- /review -->", re.S | re.M)   # line-anchored: the book's own header mentions the mark in prose


def path_of(data_dir: str, project_id: int) -> str:
    return os.path.join(data_dir, str(project_id), FILE)


def load(data_dir: str, project_id: int) -> Optional[Dict]:
    try:
        with open(path_of(data_dir, project_id), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def editor_text() -> str:
    """The judgment parts of the Editor's book (the `<!-- review -->` blocks of editing.md) — the numeric rules (safe zones, loudness)
    stay with the code and are not sent."""
    return "\n\n".join(b.strip() for b in _REVIEW.findall(claude_tasks._read("knowledge", "editor", "editing.md")))


# ---- the Editor's answer ------------------------------------------------------------------------------------------------------------
def _check_editor(obj) -> None:
    """Shape only (a bad shape asks again once); what the proposals may DO is vetted after, item by item."""
    from .llm_io import SchemaError
    if not isinstance(obj, dict) or not isinstance(obj.get("summary"), str) or not isinstance(obj.get("findings"), list):
        raise SchemaError("expected {summary, findings: [...]}")
    for i, f in enumerate(obj["findings"]):
        if not isinstance(f, dict):
            raise SchemaError(f"findings[{i}]: expected an object")
        for key in ("observed", "evidence", "action", "why"):
            if not isinstance(f.get(key), str):
                raise SchemaError(f"findings[{i}].{key}: expected text")
        for key in ("at_s", "target_shot", "amount"):
            if f.get(key) is None:
                f[key] = 0
            if not isinstance(f[key], (int, float)) or isinstance(f[key], bool):
                raise SchemaError(f"findings[{i}].{key}: expected a number")
        f["value"] = str(f.get("value") or "")


def _scene_seconds(clock: List[Dict]) -> Dict[object, float]:
    out: Dict[object, float] = {}
    for s in clock:
        out[s["story_scene"]] = out.get(s["story_scene"], 0.0) + s["seconds"]
    return out


def vet(findings: List[Dict], res: Dict) -> Tuple[List[Dict], List[Dict]]:
    """Every proposal against the closed lists and the real clock → (accepted, rejected with the reason). Nothing here trusts the model:
    a shot with speech / lip sync is never touched, a cut never goes under the shortest shot, a scene is never pushed further from the
    Director's `target_s`, a transition only goes where a scene changes, flags are only suggested."""
    clock = {s["n"]: s for s in res.get("shots") or []}
    scenes = {s["scene"]: s for s in res.get("scenes") or []}
    seconds = _scene_seconds(res.get("shots") or [])
    accepted: List[Dict] = []
    rejected: List[Dict] = []
    seen = set()

    def no(f, why):
        rejected.append({"finding": f, "reason": why})

    for f in findings:
        if len(accepted) >= MAX_FINDINGS:
            no(f, f"quá {MAX_FINDINGS} đề xuất")
            continue
        if f.get("observed") not in OBSERVED:
            no(f, f"observed '{f.get('observed')}' không thuộc danh sách")
            continue
        if f.get("action") not in ACTIONS:
            no(f, f"action '{f.get('action')}' không thuộc danh sách")
            continue
        if not f.get("evidence", "").strip() or not f.get("why", "").strip():
            no(f, "thiếu evidence hoặc why")
            continue
        act, shot, value, amount = f["action"], clock.get(int(f.get("target_shot") or 0)), f.get("value", ""), float(f.get("amount") or 0)
        if act in NEEDS_SHOT and shot is None:
            no(f, f"shot {int(f.get('target_shot') or 0)} không có trong bản dựng")
            continue
        # The render's transition style (cut / crossfade / dip_to_black) is one setting for the whole film; a per-shot edge exists only
        # behind `shot_transitions` (unverified) — so a transition proposal is a suggestion, not something P3 can apply.
        applicable = act in ("shorten_shot", "extend_hold", "music_cue")
        if act in ("shorten_shot", "extend_hold", "slow_or_freeze") and (shot["dialogue"] or shot["lip_sync"]):
            no(f, f"shot {shot['n']} có thoại / khớp môi — không đụng")
            continue
        if act in ("shorten_shot", "extend_hold"):
            if not AMOUNT_MIN <= amount <= AMOUNT_MAX:
                no(f, f"amount {amount:g} ngoài {AMOUNT_MIN:g}–{AMOUNT_MAX:g} s")
                continue
            if act == "shorten_shot" and shot["seconds"] - amount < shots_mod.MIN_SHOT:
                no(f, f"cắt {amount:g} s làm shot {shot['n']} ngắn hơn {shots_mod.MIN_SHOT:g} s")
                continue
            delta = -amount if act == "shorten_shot" else amount
            sc = shot["story_scene"]
            target = (scenes.get(sc) or {}).get("target_s")
            if isinstance(target, (int, float)):
                tol = max(rough_cut.OFF_TARGET_MIN_S, rough_cut.OFF_TARGET_SHARE * float(target))
                before, after = abs(seconds[sc] - float(target)), abs(seconds[sc] + delta - float(target))
                if after > before and after > tol:
                    no(f, f"đẩy cảnh {sc} xa `target_s` {float(target):g} s hơn (còn lệch {after:.1f} s)")
                    continue
            seconds[sc] += delta
        elif act == "music_cue" and value not in sound_intent.MUSIC:
            no(f, f"value '{value}' không thuộc {'/'.join(sound_intent.MUSIC)}")
            continue
        elif act == "transition":
            prev = clock.get(shot["n"] - 1)
            if value not in TRANSITIONS:
                no(f, f"value '{value}' không thuộc {'/'.join(TRANSITIONS)}")
                continue
            if prev is None or prev["story_scene"] == shot["story_scene"]:
                no(f, f"shot {shot['n']} không phải shot đầu của một cảnh — chuyển cảnh chỉ đặt chỗ đổi cảnh")
                continue
        elif act == "slow_or_freeze":
            if value not in ("slow", "freeze"):
                no(f, f"value '{value}' không thuộc slow/freeze")
                continue
            applicable = bool(features.FEATURES["speed_ramp"]["verified"])        # an unverified flag is only suggested (luật 5)
        elif act == "suggest_flag" and value not in FLAG_HINTS:
            no(f, f"value '{value}' không thuộc {'/'.join(FLAG_HINTS)}")
            continue
        key = (act, shot["n"] if shot else value)
        if key in seen:
            no(f, "trùng với một đề xuất trước (cùng việc, cùng shot)")
            continue
        seen.add(key)
        accepted.append({"id": f"F{len(accepted) + 1}", "at_s": round(float(f.get("at_s") or (shot or {}).get("start") or 0), 2),
                         "scene": f.get("scene") if f.get("scene") is not None else (shot or {}).get("story_scene"),
                         "observed": f["observed"], "rank": RANK.get(f["observed"], 5), "evidence": f["evidence"].strip(),
                         "action": act, "target_shot": shot["n"] if shot else 0, "amount": amount, "value": value,
                         "why": f["why"].strip(), "applicable": applicable})
    return accepted, rejected


# ---- the Director's answer + reconciliation -------------------------------------------------------------------------------------------
def _check_director(ids: List[str]):
    def check(obj) -> None:
        from .llm_io import SchemaError
        if not isinstance(obj, dict) or not isinstance(obj.get("verdicts"), list):
            raise SchemaError("expected {verdicts: [...]}")
        got = []
        for i, v in enumerate(obj["verdicts"]):
            if not isinstance(v, dict) or v.get("verdict") not in ("agree", "object", "modify") or not isinstance(v.get("id"), str):
                raise SchemaError(f"verdicts[{i}]: {{id, verdict: agree|object|modify, reason, amount, value}}")
            v["reason"] = str(v.get("reason") or "")
            if v["verdict"] != "agree" and not v["reason"].strip():
                raise SchemaError(f"verdicts[{i}].reason: bắt buộc khi {v['verdict']}")
            for key in ("amount",):
                if not isinstance(v.get(key) or 0, (int, float)):
                    raise SchemaError(f"verdicts[{i}].{key}: expected a number")
            got.append(v["id"])
        if sorted(got) != sorted(ids):
            raise SchemaError("cần đúng một mục cho mỗi id: " + ", ".join(ids))
    return check


def reconcile(accepted: List[Dict], verdicts: List[Dict], res: Dict) -> List[Dict]:
    """agree → agreed · modify → modified when the changed numbers still pass the vetting, else contested · object → contested.
    Ordered by the priority scale, then by time. A contested proposal keeps BOTH reasons and is never applied by itself."""
    by_id = {v["id"]: v for v in verdicts}
    out = []
    for f in accepted:
        v = by_id.get(f["id"]) or {"verdict": "agree", "reason": ""}
        item = dict(f, director={"verdict": v["verdict"], "reason": v.get("reason", "")}, status="agreed")
        if v["verdict"] == "object":
            item["status"] = "contested"
        elif v["verdict"] == "modify":
            changed = dict(f, amount=float(v.get("amount") or f["amount"]), value=v.get("value") or f["value"])
            ok, why = vet([{**changed, "observed": f["observed"]}], res)
            if ok:
                item.update(amount=ok[0]["amount"], value=ok[0]["value"], status="modified",
                            editor_original={"amount": f["amount"], "value": f["value"]})
            else:
                item["status"] = "contested"
                item["director"]["reason"] += f" [sửa của Đạo diễn không hợp lệ: {why[0]['reason']}]"
        out.append(item)
    return sorted(out, key=lambda x: (x["rank"], x["at_s"]))


# ---- prompts ------------------------------------------------------------------------------------------------------------------------
_CLOCK_KEYS = ("n", "story_scene", "start", "end", "seconds", "dialogue", "lip_sync", "money_shot", "speed", "transition_in")
_SCENE_KEYS = ("scene", "start", "end", "seconds", "shots", "target_s", "peak", "focus", "emotional_intent", "editor_notes", "sound")


def _clock(res: Dict) -> List[Dict]:
    return [{k: s.get(k) for k in _CLOCK_KEYS} for s in res.get("shots") or []]


def editor_prompt(res: Dict) -> Tuple[str, List[Tuple[str, str]]]:
    """(text, images): the sheets are the images (never more than the API takes — rough_cut already packed them under the limit)."""
    sound = dict(res.get("sound") or {})
    cov = res.get("coverage") or {}
    parts = [claude_tasks._read("prompts", PROMPT_EDITOR), editor_text(),
             f"# Nguồn ý đồ Đạo diễn: {res.get('source')}" + (" (ĐÃ CŨ — không đáng tin)" if res.get("stale") else "")
             + ("\n(không có `target_s` / `peak` / `focus` — chỉ có cảm xúc từng cảnh; đừng đề xuất theo thời lượng / đỉnh)"
                if res.get("source") != "director_intent_raw" else ""),
             claude_tasks._block("Ý đồ Đạo diễn theo cảnh", [{k: s.get(k) for k in _SCENE_KEYS} for s in res.get("scenes") or []]),
             claude_tasks._block("Đồng hồ shot (giây trên bản dựng thô)", _clock(res)),
             claude_tasks._block("Số đo âm (bạn không nghe được — chỉ có số)", {k: sound.get(k) for k in
                                                                                  ("step_s", "mix_db", "silent_spans", "loudness", "music_breaths")}),
             claude_tasks._block("Cảnh báo của code", [f["text"] for f in res.get("flags") or []]),
             f"# Ảnh\nBạn thấy {cov.get('moments_seen', 0)}/{cov.get('moments_total', 0)} khoảnh khắc trong {len(res.get('sheets') or [])} tấm ảnh "
             "(đúng thứ tự thời gian, tấm 1 trước)." + (f" Không thấy: {', '.join(cov.get('dropped') or [])}." if cov.get("dropped") else "")]
    images = [(f"Tấm {i}", p) for i, p in enumerate(res.get("sheets") or [], 1)]
    return "\n\n---\n\n".join(parts), images


def director_prompt(p, project_id: int, res: Dict, accepted: List[Dict]) -> str:
    intent = director_two_pass.intent_all(p, project_id)
    shown = [{k: f[k] for k in ("id", "at_s", "scene", "observed", "evidence", "action", "target_shot", "amount", "value", "why")} for f in accepted]
    return "\n\n---\n\n".join([claude_tasks._read("prompts", PROMPT_DIRECTOR),
                              claude_tasks._block("Ý đồ của bạn (theo cảnh)", [{"scene": i, **s} for i, s in sorted(intent["scenes"].items())]),
                              claude_tasks._block("Đồng hồ shot", _clock(res)),
                              claude_tasks._block("Số đo âm", {k: (res.get("sound") or {}).get(k) for k in ("silent_spans", "loudness", "music_breaths")}),
                              claude_tasks._block("Đề xuất của Biên tập viên", shown)])


# ---- run ----------------------------------------------------------------------------------------------------------------------------
def estimate(conn, images: int = 0) -> Optional[float]:
    """USD of one review before the click: the Editor's call (with its pictures) + the Director's (text) + the usual margin."""
    one = cost.llm_estimate(conn, STAGE, 1, images=images)
    two = cost.llm_estimate(conn, STAGE, 1, images=0)
    return None if one is None or two is None else (one + two) * cost.LLM_MARGIN


def fingerprint(res: Dict) -> str:
    return hashlib.sha1(json.dumps([res.get("fingerprint"), PROMPT_VERSION], sort_keys=True).encode("utf-8")).hexdigest()[:16]


def run(p, project_id: int, client, data_dir: str, force: bool = False) -> Dict:
    """Review the newest rough cut. Same render + same intent → the saved review (no call). Raises ValueError without a render and
    llm_runner.LlmError when Claude is not configured, a lock refuses, or an answer is invalid twice — nothing is half-saved."""
    res = rough_cut.build(p, project_id, data_dir)
    fp = fingerprint(res)
    saved = load(data_dir, project_id)
    if not force and saved and saved.get("fingerprint") == fp:
        return saved
    if len(res.get("sheets") or []) > llm_runner.MAX_IMAGES:
        raise llm_runner.LlmError(f"{len(res['sheets'])} ảnh vượt giới hạn {llm_runner.MAX_IMAGES} ảnh mỗi lời gọi", code="too_many_images")
    text, images = editor_prompt(res)
    with llm_runner.spend_cap(RUN_CAP_USD, "Duyệt bản dựng thô") as cap:
        first = claude_tasks._run(p, project_id, STAGE, text, _check_editor, client, images)
        accepted, rejected = vet(first["findings"], res)
        final: List[Dict] = []
        if accepted:
            ids = [f["id"] for f in accepted]
            second = claude_tasks._run(p, project_id, STAGE, director_prompt(p, project_id, res, accepted), _check_director(ids), client)
            final = reconcile(accepted, second["verdicts"], res)
    result = {"fingerprint": fp, "rough_cut": res["fingerprint"], "summary": first["summary"], "proposals": final, "rejected": rejected,
              "proposed": len(first["findings"]), "intent_source": res.get("source"), "coverage": res.get("coverage"),
              "cost": {"usd": round(cap["spent"], 4), "calls": cap["calls"], "cap_usd": RUN_CAP_USD}}
    os.makedirs(os.path.dirname(path_of(data_dir, project_id)), exist_ok=True)
    with open(path_of(data_dir, project_id), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    return result


def describe(f: Dict) -> str:
    """One proposal in a few words ("bớt 0,6 s", "nhạc → cut")."""
    return {"shorten_shot": f"bớt {f['amount']:g} s", "extend_hold": f"giữ khung cuối thêm {f['amount']:g} s", "music_cue": f"nhạc → {f['value']}",
            "transition": f"chuyển cảnh → {f['value']}", "slow_or_freeze": f"{f['value']}", "suggest_flag": f"thử bật {f['value']}",
            "retrim_from_raw": "cắt lại từ clip gốc", "none": "nhận xét"}.get(f["action"], f["action"])


def lines(res: Optional[Dict]) -> List[str]:
    """What the screen shows. Contested proposals show both sides; nothing here says "applied" — P2 only reports."""
    if not res:
        return []
    mark = {"agreed": "✅", "modified": "✏️", "contested": "⚖️"}
    out = [f"🎬 Biên tập viên: {res.get('summary', '')}",
           f"   {len(res.get('proposals') or [])} đề xuất giữ lại / {res.get('proposed', 0)} đề xuất · {len(res.get('rejected') or [])} bị code bỏ · "
           f"ý đồ: {res.get('intent_source')} · tốn {((res.get('cost') or {}).get('usd', 0)):.3f} USD ({(res.get('cost') or {}).get('calls', 0)} lời gọi)"]
    for f in res.get("proposals") or []:
        what = describe(f)
        out.append(f"{mark.get(f['status'], '•')} {f['id']} @{f['at_s']:g}s cảnh {f['scene']} [{f['observed']}] shot {f['target_shot']}: {what} — {f['why']}"
                   + ("" if f.get("applicable") else " (chỉ gợi ý, chưa áp được)"))
        out.append(f"     chứng cứ: {f['evidence']}")
        d = f.get("director") or {}
        if f["status"] != "agreed" or d.get("reason"):
            out.append(f"     Đạo diễn ({d.get('verdict')}): {d.get('reason', '')}")
    for r in res.get("rejected") or []:
        out.append(f"🚫 code bỏ: {r['reason']}")
    return out
