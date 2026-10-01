"""Design tokens of the UI v2 ("AI product" look): ONE place for every colour / radius / spacing / type size.

CSS reads them as variables (`--bg`, `--surface`, `--grad-primary` …); Python tests check the contrast of the pairs we promise
(docs/THIET_KE_GIAO_DIEN_2026-10-01.md rule 3). Change a colour here, never as a hex inside a screen.
"""
from typing import Dict, List, Tuple

# ---- colours ---------------------------------------------------------------------------------------------------------------------
DARK: Dict[str, str] = {
    "bg": "#0B0D14", "surface": "#141824", "raised": "#1B2030", "glass": "rgba(255,255,255,0.045)", "glass-strong": "rgba(255,255,255,0.075)",
    "border": "#5C6A8A", "border-soft": "rgba(255,255,255,0.12)", "border-strong": "#8C99B8",
    "text": "#F2F4FA", "muted": "#AEB8CE", "disabled": "#7D87A0",
    "primary": "#8F7BFF", "on-primary": "#FFFFFF", "primary-soft": "rgba(143,123,255,0.16)", "focus": "#B7AAFF",
    "ok": "#5EEAA0", "ok-soft": "rgba(94,234,160,0.14)", "warn": "#FBBF55", "warn-soft": "rgba(251,191,85,0.14)",
    "bad": "#FF8B80", "bad-soft": "rgba(255,139,128,0.15)", "info": "#7DC4FF", "info-soft": "rgba(125,196,255,0.14)",
    "aurora-1": "rgba(124,92,255,0.34)", "aurora-2": "rgba(34,211,238,0.20)", "aurora-3": "rgba(236,72,153,0.16)",
    "glow": "rgba(124,92,255,0.45)", "shadow": "0 10px 30px rgba(0,0,0,0.45)",
}
LIGHT: Dict[str, str] = {
    "bg": "#F4F6FB", "surface": "#FFFFFF", "raised": "#FFFFFF", "glass": "rgba(255,255,255,0.72)", "glass-strong": "rgba(255,255,255,0.9)",
    "border": "#7C879A", "border-soft": "rgba(17,24,39,0.14)", "border-strong": "#5F6B7E",
    "text": "#111827", "muted": "#4B5563", "disabled": "#6B7280",
    "primary": "#4F3BE0", "on-primary": "#FFFFFF", "primary-soft": "rgba(79,59,224,0.10)", "focus": "#3B2BC0",
    "ok": "#13693A", "ok-soft": "rgba(19,105,58,0.11)", "warn": "#8A4B00", "warn-soft": "rgba(138,75,0,0.11)",
    "bad": "#B42318", "bad-soft": "rgba(180,35,24,0.10)", "info": "#1D4ED8", "info-soft": "rgba(29,78,216,0.10)",
    "aurora-1": "rgba(124,92,255,0.20)", "aurora-2": "rgba(34,211,238,0.16)", "aurora-3": "rgba(236,72,153,0.10)",
    "glow": "rgba(79,59,224,0.28)", "shadow": "0 8px 24px rgba(17,24,39,0.10)",
}
# gradient stops are the same in both themes; white text sits on them (each stop checked ≥ 4.5:1 below)
GRAD_STOPS: Tuple[str, str, str] = ("#6D4AFF", "#2563EB", "#0E7490")
GRAD_PRIMARY = f"linear-gradient(135deg,{GRAD_STOPS[0]} 0%,{GRAD_STOPS[1]} 58%,{GRAD_STOPS[2]} 100%)"
GRAD_TEXT = "linear-gradient(90deg,#B7AAFF 0%,#7DC4FF 55%,#5EEAD4 100%)"          # heading text gradient (dark theme)
GRAD_TEXT_LIGHT = "linear-gradient(90deg,#4F3BE0 0%,#1D4ED8 60%,#0E7490 100%)"

# ---- shape / space / type --------------------------------------------------------------------------------------------------------
RADIUS = {"sm": "8px", "md": "12px", "lg": "16px", "pill": "999px"}
SPACE = (4, 8, 12, 16, 24, 32)
TYPE = {"caption": "12.5px", "body": "14.5px", "label": "14px", "title": "17px", "h2": "22px", "h1": "30px"}      # px; none below 12
FONT = '"Inter","Segoe UI Variable","Segoe UI",system-ui,-apple-system,Roboto,sans-serif'


def css_vars(theme: str) -> str:
    """`:root{…}` block with every token of the theme ('dark' | 'light') plus the shared ones."""
    t = DARK if theme == "dark" else LIGHT
    body = ";".join(f"--{k}:{v}" for k, v in t.items())
    shared = (f"--grad-primary:{GRAD_PRIMARY};--grad-text:{GRAD_TEXT if theme == 'dark' else GRAD_TEXT_LIGHT};"
              + ";".join(f"--r-{k}:{v}" for k, v in RADIUS.items()) + f";--font:{FONT}")
    return ":root{" + body + ";" + shared + "}"


# ---- contrast (WCAG 2.x) ----------------------------------------------------------------------------------------------------------
def _rgb(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(h: str) -> float:
    def ch(v: float) -> float:
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def promised_pairs(theme: str) -> List[Tuple[str, str, str, float]]:
    """(name, foreground, background, minimum ratio) — only opaque hex tokens; the checks the tests run."""
    t = DARK if theme == "dark" else LIGHT
    pairs = [("text/bg", t["text"], t["bg"], 4.5), ("text/surface", t["text"], t["surface"], 4.5), ("text/raised", t["text"], t["raised"], 4.5),
             ("muted/surface", t["muted"], t["surface"], 4.5), ("muted/bg", t["muted"], t["bg"], 4.5),
             ("disabled/surface", t["disabled"], t["surface"], 3.0),
             ("primary/surface", t["primary"], t["surface"], 4.5 if theme == "dark" else 4.5),
             ("ok/surface", t["ok"], t["surface"], 4.5), ("warn/surface", t["warn"], t["surface"], 4.5),
             ("bad/surface", t["bad"], t["surface"], 4.5), ("info/surface", t["info"], t["surface"], 4.5),
             ("border/surface", t["border"], t["surface"], 3.0), ("border/bg", t["border"], t["bg"], 3.0),
             ("focus/surface", t["focus"], t["surface"], 3.0)]
    pairs += [(f"on-gradient stop {i + 1}", "#FFFFFF", c, 4.5) for i, c in enumerate(GRAD_STOPS)]
    return pairs
