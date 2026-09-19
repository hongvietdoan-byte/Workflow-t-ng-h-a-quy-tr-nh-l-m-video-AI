"""Evaluation set for the Director prompts (Step 1 scene analysis, Step 3 motion prompts).

Automatic checks cover what is objective (schema, language, length, character reuse, banned IP terms,
camera vocabulary...). Aesthetic judgement stays with the human reviewer via `review_sheet`.

CLI:  py -m core.evalset list
      py -m core.evalset prompt <case_id> [--motion]
      py -m core.evalset score <outputs.json>
      py -m core.evalset sheet <outputs.json> [out.md]
"""
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

from .llm_io import SchemaError, validate_motion_prompts, validate_scene_analysis
from .script_parser import split_scenes

ROOT = os.path.join(os.path.dirname(__file__), "..")
CASES_PATH = os.path.join(ROOT, "eval", "cases.json")
GOLDEN_PATH = os.path.join(ROOT, "eval", "golden.json")
VOCAB_PATH = os.path.join(ROOT, "data", "motion_vocab.json")
VAGUE_WORDS = ("beautiful", "stunning", "amazing", "awesome", "masterpiece", "gorgeous", "incredible")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    hard: bool = True


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_cases(path: str = CASES_PATH) -> List[Dict]:
    return _load(path)["cases"]


def load_golden(path: str = GOLDEN_PATH) -> Dict:
    return _load(path)["outputs"]


def get_case(case_id: str) -> Dict:
    for c in load_cases():
        if c["id"] == case_id:
            return c
    raise KeyError(case_id)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", text.lower())).strip()


def _words(text: str) -> int:
    return len(text.split())


def _non_ascii_ratio(text: str) -> float:
    return sum(1 for ch in text if ord(ch) > 127) / max(len(text), 1)


def _any(text: str, keywords: List[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


# ---- Step 1 ---------------------------------------------------------------
def check_scene_analysis(case: Dict, analysis) -> List[Check]:
    exp = case["expect"]
    try:
        obj = validate_scene_analysis(analysis)
    except (SchemaError, ValueError) as e:
        return [Check("schema", False, str(e))]
    checks = [Check("schema", True)]
    expected_scenes = len(split_scenes(case["script"]))
    scenes = obj["scenes"]
    checks.append(Check("scene count", len(scenes) == expected_scenes,
                        f"expected {expected_scenes}, got {len(scenes)}"))
    checks.append(Check("scene idx sequential", [s["idx"] for s in scenes] == list(range(1, len(scenes) + 1))))
    names = [c["name"].lower() for c in obj["characters"]]
    if exp["characters"]:
        missing = [n for n in exp["characters"] if not any(n.lower() in x for x in names)]
        checks.append(Check("expected characters present", not missing, f"missing: {missing}"))
    else:
        used = any(s["characters"] for s in scenes)
        checks.append(Check("no characters (environment scene)", not used and not obj["characters"]))
    desc = {c["name"]: _norm(c["description"]) for c in obj["characters"]}
    scan = json.dumps({k: v for k, v in obj.items() if k != "ip_risk_notes"}, ensure_ascii=False).lower()
    banned = [t for t in exp["must_not"] if t.lower() in scan]
    checks.append(Check("no banned terms", not banned, f"found: {banned}"))
    if exp.get("ip_trap"):
        checks.append(Check("IP risk flagged", bool(obj.get("ip_risk_notes")), "ip_risk_notes is empty"))
    for s in scenes:
        tag = f"scene {s['idx']}"
        prompt = s["image_prompt"]
        checks.append(Check(f"{tag}: image_prompt in English", _non_ascii_ratio(prompt) < 0.03))
        n = _words(prompt)
        checks.append(Check(f"{tag}: image_prompt length 25-90 words", 25 <= n <= 90, f"{n} words"))
        checks.append(Check(f"{tag}: shot matches", _any(s["shot"] + " " + prompt, exp["shot_any"]),
                            f"want one of {exp['shot_any']}"))
        checks.append(Check(f"{tag}: lighting matches", _any(s["lighting"] + " " + prompt, exp["lighting_any"]),
                            f"want one of {exp['lighting_any']}"))
        checks.append(Check(f"{tag}: mood matches", _any(s["mood"] + " " + prompt, exp["mood_any"]),
                            f"want one of {exp['mood_any']}", hard=False))
        vague = [w for w in VAGUE_WORDS if w in _norm(prompt).split()]
        checks.append(Check(f"{tag}: no empty praise words", not vague, f"found: {vague}", hard=False))
        checks.append(Check(f"{tag}: has 'no text' guard", "no text" in prompt.lower(), hard=False))
        for name in s["characters"]:
            head = " ".join(desc.get(name, "").split()[:4])
            ok = bool(head) and head in _norm(prompt)
            checks.append(Check(f"{tag}: {name} description reused", ok, f"'{head}' not found in image_prompt"))
    return checks


# ---- Step 3 ---------------------------------------------------------------
def check_motion(case: Dict, motion) -> List[Check]:
    exp = case["expect"]
    vocab = _load(VOCAB_PATH)
    try:
        obj = validate_motion_prompts(motion)
    except (SchemaError, ValueError) as e:
        return [Check("motion schema", False, str(e))]
    checks = [Check("motion schema", True)]
    expected_scenes = len(split_scenes(case["script"]))
    checks.append(Check("motion scene count", len(obj["scenes"]) == expected_scenes,
                        f"expected {expected_scenes}, got {len(obj['scenes'])}"))
    for s in obj["scenes"]:
        tag = f"motion {s['idx']}"
        text = s["motion_prompt"]
        n = _words(text)
        checks.append(Check(f"{tag}: length 10-60 words", 10 <= n <= 60, f"{n} words"))
        checks.append(Check(f"{tag}: camera move fits genre", _any(text, exp["motion_camera_any"]),
                            f"motion_prompt should name one of {exp['motion_camera_any']}"))
        used = [t for t in vocab["camera_terms"] if t in text.lower()]
        checks.append(Check(f"{tag}: one main camera move", 1 <= len(used) <= 2, f"terms: {used}", hard=False))
        checks.append(Check(f"{tag}: no appearance re-description",
                            not [t for t in vocab["appearance_terms"] if t in text.lower()],
                            "describe motion only", hard=False))
        checks.append(Check(f"{tag}: duration 3-8s", 3 <= s.get("duration_sec", 5) <= 8, hard=False))
        checks.append(Check(f"{tag}: negative prompt present", bool(s.get("negative_prompt")), hard=False))
    return checks


# ---- aggregation ----------------------------------------------------------
def summarize(checks: List[Check]) -> Dict:
    hard = [c for c in checks if c.hard]
    failed = [c for c in hard if not c.ok]
    warnings = [c for c in checks if not c.hard and not c.ok]
    return {"passed": len(hard) - len(failed), "total": len(hard),
            "score": (len(hard) - len(failed)) / len(hard) if hard else 0.0,
            "failed": [f"{c.name} ({c.detail})" if c.detail else c.name for c in failed],
            "warnings": [f"{c.name} ({c.detail})" if c.detail else c.name for c in warnings]}


def run_case(case: Dict, output: Dict) -> Dict:
    checks: List[Check] = []
    if "analysis" in output:
        checks += check_scene_analysis(case, output["analysis"])
    if "motion" in output:
        checks += check_motion(case, output["motion"])
    if not checks:
        checks = [Check("output present", False, "no 'analysis' or 'motion' in output")]
    return summarize(checks)


def run_all(outputs: Dict[str, Dict]) -> Dict[str, Dict]:
    cases = {c["id"]: c for c in load_cases()}
    results = {}
    for case_id, out in outputs.items():
        results[case_id] = run_case(cases[case_id], out) if case_id in cases else {
            "passed": 0, "total": 1, "score": 0.0, "failed": ["unknown case id"], "warnings": []}
    return results


# ---- prompts & human review sheet ----------------------------------------
def _read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def few_shot_text() -> str:
    golden, cases = load_golden(), {c["id"]: c for c in load_cases()}
    blocks = []
    for case_id, out in golden.items():
        blocks.append(f"### Ví dụ: {case_id}\nKịch bản:\n" + "\n".join(cases[case_id]["script"]) +
                      "\n\nJSON đúng:\n```json\n" + json.dumps(out["analysis"], ensure_ascii=False, indent=2) + "\n```")
    return "# Ví dụ mẫu (few-shot)\n\n" + "\n\n".join(blocks)


def director_bundle(case: Dict) -> str:
    return "\n\n---\n\n".join([
        _read("prompts", "01_director_scene_analysis.md"), _read("knowledge", "cinematography_basics.md"),
        _read("knowledge", "genre_guides.md"), _read("knowledge", "research_notes.md"), few_shot_text(),
        "# Kịch bản cần phân tích\n\n" + "\n".join(case["script"])])


def motion_bundle(case: Dict, analysis: Dict) -> str:
    return "\n\n---\n\n".join([
        _read("prompts", "03_video_motion.md"), _read("knowledge", "video_motion_vocab.md"),
        _read("knowledge", "research_notes.md"),
        "# Thông số cảnh và nhân vật (đã duyệt)\n```json\n" + json.dumps(analysis, ensure_ascii=False, indent=2) + "\n```"])


def review_sheet(outputs: Dict[str, Dict]) -> str:
    """Markdown sheet for the human reviewer: automatic results + aesthetic yes/no questions per case."""
    cases = {c["id"]: c for c in load_cases()}
    results = run_all(outputs)
    lines = ["# Phiếu duyệt bộ đánh giá Director", "",
             "Đánh dấu [x] khi ĐẠT. Phần 'Tự động' đã chấm sẵn; bạn chỉ chấm phần thẩm mỹ.", ""]
    for case_id, res in results.items():
        case = cases.get(case_id)
        if not case:
            continue
        lines += [f"## {case_id} ({case['genre']}) — tự động: {res['passed']}/{res['total']}", ""]
        for f in res["failed"]:
            lines.append(f"- ❌ Tự động: {f}")
        for w in res["warnings"]:
            lines.append(f"- ⚠ Gợi ý: {w}")
        for q in case["review_questions"]:
            lines.append(f"- [ ] {q}")
        analysis = outputs[case_id].get("analysis")
        if analysis:
            for s in analysis.get("scenes", []):
                lines += ["", f"**image_prompt (cảnh {s.get('idx')}):** {s.get('image_prompt', '')}"]
        motion = outputs[case_id].get("motion")
        if motion:
            for s in motion.get("scenes", []):
                lines += ["", f"**motion_prompt (cảnh {s.get('idx')}):** {s.get('motion_prompt', '')}"]
        lines += ["", "Nhận xét: ", ""]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] == "list":
        golden = set(load_golden())
        for c in load_cases():
            print(f"{c['id']:32s} {c['genre']:14s} {'(golden/few-shot)' if c['id'] in golden else ''}")
        return 0
    if argv[0] == "prompt":
        case = get_case(argv[1])
        if "--motion" in argv:
            print(motion_bundle(case, load_golden().get(case["id"], {}).get("analysis", {})))
        else:
            print(director_bundle(case))
        return 0
    if argv[0] in ("score", "sheet"):
        with open(argv[1], encoding="utf-8") as f:
            outputs = json.load(f)
        if argv[0] == "sheet":
            text = review_sheet(outputs)
            if len(argv) > 2:
                with open(argv[2], "w", encoding="utf-8") as f:
                    f.write(text)
            else:
                print(text)
            return 0
        golden = set(load_golden())
        results = run_all(outputs)
        for case_id, r in results.items():
            mark = " (golden — không tính held-out)" if case_id in golden else ""
            print(f"{case_id:32s} {r['passed']}/{r['total']}  {r['score']:.0%}{mark}")
            for item in r["failed"]:
                print(f"    FAIL  {item}")
        held = [r for cid, r in results.items() if cid not in golden]
        if held:
            print(f"Held-out trung bình: {sum(r['score'] for r in held) / len(held):.0%} ({len(held)} mẫu)")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
