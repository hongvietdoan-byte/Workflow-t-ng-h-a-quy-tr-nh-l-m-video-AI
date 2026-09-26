"""File điểm của AI Development System: kiểm, chuẩn hóa, lưu, gộp.

Điểm luôn do code tính lại từ các khoản trừ (người chấm AI, người chấm ngoài hay file sửa tay đều như nhau), rồi áp giới hạn do code
(thang: devsys/rubric.md). Một file = một khu vực của một lần chấm: devsys/data/scores/<giờ>_<khu_vực>.json
"""
import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from . import collect

FORMAT = "devsys-score/1"
CRITERIA: Tuple[Tuple[str, str, int], ...] = (
    ("chuc_nang", "Hoàn thiện chức năng", 30),
    ("bang_chung", "Bằng chứng chạy thật", 20),
    ("test", "Test", 15),
    ("tuan_thu", "Tuân thủ CHUAN_XAY_DUNG", 15),
    ("trai_nghiem", "Trải nghiệm người dùng", 10),
    ("tai_lieu", "Tài liệu khớp code", 10),
)
CRITERIA_MAX = {k: m for k, _, m in CRITERIA}
CRITERIA_LABEL = {k: n for k, n, _ in CRITERIA}
REAL_RUN_PLACES = ("TODO.md", "PLAN.md", "docs/", "data/", "tests/fixtures/", "research/", "eval/")
_LINE_REF = re.compile(r"^(?P<path>[^\s:]+?)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$")


class ScoreError(ValueError):
    """A score answer / file that does not follow the format (the scorer is asked again once, a file is refused)."""


def rubric_hash(root: str = collect.ROOT) -> str:
    try:
        with open(os.path.join(root, "devsys", "rubric.md"), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "khong-co-rubric"


def scores_dir(root: str = collect.ROOT) -> str:
    return os.path.join(collect.data_dir(root), "scores")


def check_evidence(item: str, root: str, todo_lines: Optional[int] = None) -> Optional[str]:
    """None when an evidence string can be verified in the repo, else why not."""
    item = str(item).strip()
    if not item:
        return "rỗng"
    if item.startswith(("test:", "flag:", "absent:")):
        if item.startswith("test:") and "tests/" in item:
            path = item[5:].split("::")[0].strip()
            if not os.path.isfile(os.path.join(root, path)):
                return f"không có file test {path}"
        if item.startswith("flag:"):
            name = item[5:].strip()
            if name not in collect.read_features(root):
                return f"không có cờ {name} trong core/features.py"
        return None
    m = _LINE_REF.match(item)
    if not m:
        return "không đúng dạng file:dòng"
    path = m.group("path").strip("`")
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return f"không có file {path}"
    if m.group("a"):
        n = collect.line_count(full)
        last = int(m.group("b") or m.group("a"))
        if last > n or int(m.group("a")) < 1:
            return f"dòng {last} vượt độ dài {path} ({n} dòng)"
    return None


def _is_real_run_ref(item: str) -> bool:
    path = str(item).split(":")[0].strip("`")
    return any(path == p or path.startswith(p) for p in REAL_RUN_PLACES)


def normalize(raw: Dict, root: str = collect.ROOT, area_ids: Optional[Sequence[str]] = None, facts: Optional[Dict] = None) -> Dict:
    """Validate a scorer answer / score file and compute the score. Raises ScoreError on a structural problem.

    facts (from the collector, optional): {"test_files": int, "has_run": bool, "failed": int} — used for the code caps."""
    if not isinstance(raw, dict):
        raise ScoreError("câu trả lời phải là một object JSON")
    area = raw.get("area")
    if not isinstance(area, str) or not area:
        raise ScoreError("thiếu 'area'")
    if area_ids is not None and area not in area_ids:
        raise ScoreError(f"khu vực '{area}' không có trong devsys/areas.json")
    crit = raw.get("criteria")
    if not isinstance(crit, dict):
        raise ScoreError("thiếu 'criteria' (object 6 tiêu chí)")
    missing = [k for k in CRITERIA_MAX if k not in crit]
    if missing:
        raise ScoreError(f"thiếu tiêu chí: {', '.join(missing)}")
    out_crit, unverified, caps = {}, [], []
    for key, mx in CRITERIA_MAX.items():
        c = crit[key] if isinstance(crit[key], dict) else {}
        deds = c.get("deductions", [])
        if not isinstance(deds, list):
            raise ScoreError(f"{key}.deductions phải là danh sách")
        clean = []
        for i, d in enumerate(deds):
            if not isinstance(d, dict):
                raise ScoreError(f"{key}.deductions[{i}] phải là object")
            try:
                pts = float(d.get("points"))
            except (TypeError, ValueError):
                raise ScoreError(f"{key}.deductions[{i}].points phải là số") from None
            if pts <= 0:
                raise ScoreError(f"{key}.deductions[{i}].points phải > 0 (số điểm bị trừ)")
            ev = d.get("evidence")
            if isinstance(ev, str):
                ev = [ev]
            if not ev or not isinstance(ev, list):
                raise ScoreError(f"{key}.deductions[{i}] không có bằng chứng ('evidence') — mọi khoản trừ phải có bằng chứng")
            reason = str(d.get("reason") or "").strip()
            if not reason:
                raise ScoreError(f"{key}.deductions[{i}] thiếu 'reason'")
            bad = [(e, check_evidence(e, root)) for e in ev]
            for e, why in bad:
                if why:
                    unverified.append({"criterion": key, "evidence": e, "why": why})
            clean.append({"points": round(pts, 1), "reason": reason, "evidence": [str(e) for e in ev],
                          "unverified": [e for e, why in bad if why]})
        ev_for = c.get("evidence_for") or []
        if isinstance(ev_for, str):
            ev_for = [ev_for]
        score = max(0.0, mx - sum(d["points"] for d in clean))
        crit_caps = []
        if key == "bang_chung" and score > 0:
            ok = [e for e in ev_for if _is_real_run_ref(e) and not check_evidence(e, root)]
            if not ok:
                crit_caps.append("code hạ về 0: không có trích dẫn chạy thật kiểm được (TODO.md / docs / data / tests/fixtures) trong evidence_for")
                score = 0.0
        if key == "test" and facts is not None:
            limit = None
            if facts.get("test_files", 0) == 0:
                limit, why = 3, "không có test file nào nhắm vào khu vực"
            elif not facts.get("has_run"):
                limit, why = 8, "chưa có lần chạy test lưu lại"
            elif facts.get("failed", 0) > 0:
                limit, why = 7, f"lần chạy mới nhất có {facts['failed']} test của khu vực lỗi"
            if limit is not None and score > limit:
                crit_caps.append(f"code giới hạn {limit}/{mx}: {why}")
                score = float(limit)
        caps += [f"{key}: {c_}" for c_ in crit_caps]
        out_crit[key] = {"score": round(score, 1), "max": mx, "deductions": clean, "evidence_for": [str(e) for e in ev_for],
                         "code_caps": crit_caps}
    total = round(sum(c["score"] for c in out_crit.values()), 1)
    checks = raw.get("can_kiem_lai") or []
    if not isinstance(checks, list):
        raise ScoreError("'can_kiem_lai' phải là danh sách")
    checks = [c if isinstance(c, dict) else {"what": str(c)} for c in checks]
    return {"format": FORMAT, "area": area, "score": total, "criteria": out_crit, "can_kiem_lai": checks,
            "summary": str(raw.get("summary") or "").strip(), "unverified_evidence": unverified, "code_caps": caps}


def save(score: Dict, root: str = collect.ROOT) -> str:
    d = scores_dir(root)
    os.makedirs(d, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = os.path.join(d, f"{stamp}_{score['area']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(score, f, ensure_ascii=False, indent=1)
    return path


def load_all(root: str = collect.ROOT, area_ids: Optional[Sequence[str]] = None) -> Tuple[List[Dict], List[str]]:
    """All score files, oldest first, each re-normalised (score recomputed by code). Returns (scores, problems)."""
    d = scores_dir(root)
    out, problems = [], []
    if not os.path.isdir(d):
        return out, problems
    for n in sorted(os.listdir(d)):
        if not n.endswith(".json"):
            continue
        path = os.path.join(d, n)
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("format") != FORMAT:
                raise ScoreError(f"format phải là '{FORMAT}'")
            if not raw.get("scorer"):
                raise ScoreError("thiếu 'scorer' (ai chấm: claude-api, mock, claude-code-session…)")
            norm = normalize(raw.get("raw") or raw, root, area_ids, raw.get("facts"))
        except (OSError, ValueError) as e:
            problems.append(f"{n}: {e}")
            continue
        rec = {**{k: raw.get(k) for k in ("scorer", "model", "date", "commit", "dirty", "input_hash", "rubric_hash", "fingerprint",
                                          "usage", "facts", "provider")}, **norm, "_file": n}
        rec["date"] = rec.get("date") or datetime.fromtimestamp(os.path.getmtime(path)).astimezone().isoformat(timespec="seconds")
        out.append(rec)
    out.sort(key=lambda r: (r.get("date") or "", r["_file"]))
    return out, problems


def latest_by_area(scores: Sequence[Dict]) -> Dict[str, Dict]:
    """The newest score of each area (mock scores never replace a real one: they only count when an area has nothing else)."""
    real, mock = {}, {}
    for s in scores:
        (mock if str(s.get("scorer", "")).startswith("mock") else real)[s["area"]] = s
    return {**mock, **real}


def overall(latest: Dict[str, Dict], cfg: Dict, include_mock: bool = False) -> Dict:
    """Weighted average of the latest area scores (areas.json `weight`), plus how much of the system it covers."""
    num = den = 0.0
    covered = []
    total_w = sum(float(a.get("weight", 1)) for a in cfg["areas"])
    for a in cfg["areas"]:
        s = latest.get(a["id"])
        if not s or (not include_mock and str(s.get("scorer", "")).startswith("mock")):
            continue
        w = float(a.get("weight", 1))
        num += w * s["score"]
        den += w
        covered.append(a["id"])
    return {"score": round(num / den, 1) if den else None, "covered": covered, "areas": len(cfg["areas"]),
            "weight_share": round(den / total_w, 3) if total_w else 0.0}


def trend(scores: Sequence[Dict], cfg: Dict, include_mock: bool = False) -> List[Dict]:
    """Overall completion after every scoring, replaying the score files in time order."""
    state: Dict[str, Dict] = {}
    points = []
    for s in scores:
        if not include_mock and str(s.get("scorer", "")).startswith("mock"):
            continue
        state[s["area"]] = s
        o = overall(state, cfg, include_mock)
        points.append({"date": s.get("date"), "overall": o["score"], "covered": len(o["covered"]), "area": s["area"], "score": s["score"]})
    return points


def band(score: Optional[float]) -> str:
    if score is None:
        return "none"
    return "ok" if score >= 80 else "warn" if score >= 60 else "bad"
