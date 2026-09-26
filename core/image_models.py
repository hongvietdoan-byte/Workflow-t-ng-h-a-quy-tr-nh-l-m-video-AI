"""Picture models of Deepix and their rules (W10: checked before sending — a request that breaks a rule is refused here, for free,
instead of failing at the provider). Rules live in data/provider_rules.json; the project picks its model (`projects.image_model`,
Step 1), else DEEPIX_MODEL, else the default (Seedream 5.0 Pro)."""
import json
import os
from typing import Dict, Optional

_RULES = os.path.join(os.path.dirname(__file__), "..", "data", "provider_rules.json")
DEFAULT = "dola-seedream-5-0-pro-260628"
_cache: Dict = {}


def models() -> Dict[str, Dict]:
    try:
        stamp = os.path.getmtime(_RULES)
    except OSError:
        return {}
    if _cache.get("stamp") != stamp:
        try:
            with open(_RULES, encoding="utf-8") as f:
                data = (json.load(f) or {}).get("image_models") or {}
        except (OSError, ValueError, AttributeError):
            data = {}
        _cache.update(stamp=stamp, data=data)
    return _cache["data"]


def rule(model: str) -> Dict:
    return models().get(model) or {}


def label(model: Optional[str]) -> str:
    return rule(model or "").get("label") or (model or "")


def of_project(proj) -> str:
    """The picture model this project uses."""
    chosen = proj["image_model"] if proj is not None and "image_model" in proj.keys() else None
    return chosen or os.environ.get("DEEPIX_MODEL", "").strip() or DEFAULT


def max_refs(model: str, fallback: int = 10) -> int:
    return int(rule(model).get("max_refs") or fallback)


def accepts_sheets(model: Optional[str]) -> bool:
    """The model can take a multi-angle design sheet as a reference without copying the sheet's layout (tested on GPT Image 2.5
    Sunburst 2026-09-24; Seedream copies it)."""
    return bool(rule(model or "").get("accepts_design_sheet"))


def cheapest_size(model: str, aspect: Optional[str]) -> Optional[str]:
    """The smallest picture (fewest pixels) the model accepts for the frame format, sides multiples of its `multiple`, shape within 1 %
    of the aspect (e.g. GPT Image 2.5, 9:16 → 608x1088 = 661,504 px ≥ 655,360; Seedream 5.0 Pro 9:16 → 720x1280). None when the
    model has no size rule (unknown model: the normal size is kept)."""
    spec = rule(model).get("size")
    if not spec:
        return None
    try:
        aw, ah = (float(x) for x in str(aspect or "16:9").split(":"))
    except ValueError:
        aw, ah = 16.0, 9.0
    ratio = aw / ah
    m = int(spec.get("multiple") or 1)
    lo = int(spec.get("min_pixels") or 0)
    for long_units in range(1, 4096 // m + 1):             # the long edge grows with the loop: the first valid size is the smallest
        long_edge = long_units * m
        short_edge = max(int(round(long_edge * min(ratio, 1 / ratio) / m)) * m, m)
        w, h = (long_edge, short_edge) if ratio >= 1 else (short_edge, long_edge)
        if abs((w / h) - ratio) / ratio > 0.01 or w * h < lo:
            continue
        if size_problem(model, f"{w}x{h}") is None:
            return f"{w}x{h}"
    return None


def size_for(proj, model: str) -> str:
    """The picture size a job of this project asks for: the frame format's normal size, or — in the 🧪 cheap test mode
    (projects.test_quality) — the smallest size the model accepts for that format."""
    from . import formats
    aspect = formats.project_aspect(proj) if proj is not None else None
    normal = formats.spec(aspect)["deepix"]
    cheap = proj is not None and "test_quality" in proj.keys() and bool(proj["test_quality"])
    return (cheapest_size(model, aspect or "16:9") or normal) if cheap else normal


def size_problem(model: str, size: Optional[str]) -> Optional[str]:
    """Why `size` is not accepted by `model` (None = fine). 'auto' / no size = the model decides (only where allowed)."""
    spec = rule(model).get("size")
    if not spec:
        return None                                   # unknown model: nothing to check against (the provider will say)
    if not size or str(size).lower() == "auto":
        return None if spec.get("auto") else f"{label(model)} cần kích thước pixel (vd 2048x1152)"
    try:
        w, h = (int(x) for x in str(size).lower().split("x"))
    except ValueError:
        return f"kích thước phải dạng 2048x1152, nhận '{size}'"
    m = int(spec.get("multiple") or 1)
    if w <= 0 or h <= 0 or w % m or h % m:
        return f"{label(model)}: hai cạnh phải là bội số của {m} ({size})"
    if max(w, h) / min(w, h) > float(spec.get("max_ratio") or 99):
        return f"{label(model)}: tỉ lệ khung tối đa {spec['max_ratio']}:1 ({size})"
    if spec.get("max_long_edge") and max(w, h) > int(spec["max_long_edge"]):
        return f"{label(model)}: cạnh dài tối đa {spec['max_long_edge']}px ({size})"
    lo, hi = int(spec.get("min_pixels") or 0), int(spec.get("max_pixels") or 10 ** 12)
    if not lo <= w * h <= hi:
        return f"{label(model)}: tổng pixel phải trong {lo:,}–{hi:,} ({size} = {w * h:,})"
    return None
