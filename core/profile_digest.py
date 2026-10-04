"""Short forms of a character's standard profile (kế hoạch V4 4.4): three levels, each for the prompt that can hold it.

    lock_short   ≤ 200 characters — the few features that make the character recognisable (video prompts, a Kling multi-shot prompt
                                    of ≤ 512 characters)
    lock_medium  ≤ 500 characters — the look to draw (picture prompts)
    full profile                  — QC and the Bible (unchanged: identity, must_keep, may_change, forbidden, height, build)

Made by code, no Claude call (free): the profile's own clauses, whole clauses only, until the limit — the first identity clause always,
then the clauses the person wrote with a word in CAPITALS (LEFT / RIGHT: the detail a model got wrong before), then the rest in the
person's order; printed back in that order. It is kept in the profile (`digest`) with the hash of the fields it came from, so a changed
profile gives a new digest the next time one is asked for. A person may write a digest by hand (`source: "manual"`, same limits, same
checks); it is kept until the profile changes.

Checks (never silent, CHUAN_XAY_DUNG rule 1): the length, no age under 18, and no word that the profile names only as FORBIDDEN (a word
like "ponytail" in the short form of Kelly — whose profile forbids tying the hair — would draw exactly what is forbidden).
"""
import hashlib
import json
import re
from typing import Dict, List, Optional

SHORT, MEDIUM = 200, 500
SOURCE_KEYS = ("identity", "must_keep", "height_m", "build")        # what the digest is made from (the hash covers these + forbidden)
_UNDER_18 = r"(?:[1-9]|1[0-7])"
_UNDER_18_WORDS = (r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen)")
# S14.4 C1b (04/10): also 'aged 17', '17yo', '17 tuổi', 'seventeen-year-old', 'age 16' (only '17-year-old' was caught)
_MINOR_AGE = re.compile(
    rf"\b(?:{_UNDER_18}|{_UNDER_18_WORDS})[- ]?(?:-|\s)?years?[- ]old\b"
    rf"|\b(?:aged?|tuổi)\s*:?\s*{_UNDER_18}\b"
    rf"|\b{_UNDER_18}\s*(?:yo|y/o|yrs?)\b"
    rf"|\b{_UNDER_18}\s*tuổi(?!\w)", re.IGNORECASE)
_WORD = re.compile(r"[a-zA-Z]{4,}")                                  # "silver-white" = silver + white
_HEAD = re.compile(r"^[^—:]{1,40}—\s*")                              # "Kelly — " at the start of an identity line
_CAPS = re.compile(r"\b[A-Z]{4,}\b")
_COMMON = {"with", "under", "over", "into", "from", "that", "this", "never", "changing", "change", "removing", "looking", "losing",
           "another", "other", "color", "colour", "recoloring", "instead", "than", "older", "younger", "like", "swapping", "tying",
           "turning", "becoming", "adult", "child", "plain", "jacket", "hair", "look", "length"}


def source_hash(profile: Dict) -> str:
    keys = SOURCE_KEYS + ("forbidden",)
    return hashlib.sha1(json.dumps({k: profile.get(k) for k in keys}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _clauses(text: str, colon: bool = False) -> List[str]:
    """Split at commas / semicolons that are not inside brackets (and at colons for an identity line: "Kelly — sprinter: slim…");
    drop the "Name — " head of an identity line."""
    text = _HEAD.sub("", (text or "").strip())
    if colon:
        text = text.replace(":", ",")
    out, depth, cur = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch in ",;" and depth <= 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return [c.strip(" .") for c in out if c.strip(" .")]


def _pack(clauses: List[str], limit: int, keep_first: int = 0) -> str:
    """Whole clauses up to `limit` characters: the first `keep_first`, then the emphasised ones, then the rest; printed in order."""
    order = list(range(min(keep_first, len(clauses))))
    order += [i for i in range(len(clauses)) if i not in order and _CAPS.search(clauses[i])]
    order += [i for i in range(len(clauses)) if i not in order]
    chosen, used = [], 0
    for i in order:
        cost = len(clauses[i]) + (2 if chosen else 0)
        if used + cost <= limit:
            chosen.append(i)
            used += cost
    return ", ".join(clauses[i] for i in sorted(chosen))


def _same(a: str, b: str) -> bool:
    """Two clauses say the same thing (most of the shorter one's words are in the other)."""
    wa, wb = set(_WORD.findall(a.lower())), set(_WORD.findall(b.lower()))
    small = min(wa, wb, key=len)
    return bool(small) and len(wa & wb) >= 0.7 * len(small)


def build(profile: Dict) -> Dict:
    ident = [c for c in _clauses(profile.get("identity"), colon=True) if not _MINOR_AGE.search(c)]
    keep = [c for c in _clauses(profile.get("must_keep")) if not _MINOR_AGE.search(c)]
    short = _pack(ident, SHORT, keep_first=1)
    medium_parts = ident[:1] + [c for c in keep if not any(_same(c, i) for i in ident[:1])]
    height = f"about {profile['height_m']:g} m tall" if profile.get("height_m") else ""
    # the height matters for two people in one frame: room is kept for it
    medium = _pack(medium_parts, MEDIUM - (len(height) + 2 if height else 0), keep_first=1) + (f", {height}" if height else "")
    return {"hash": source_hash(profile), "lock_short": short, "lock_medium": medium, "source": "code"}


def forbidden_only_words(profile: Dict) -> List[str]:
    """Words the profile names only when saying what is FORBIDDEN (not in what must be kept / may change / who they are)."""
    allowed = set(_WORD.findall(" ".join(str(profile.get(k) or "") for k in ("identity", "must_keep", "may_change", "build")).lower()))
    words = set(_WORD.findall(str(profile.get("forbidden") or "").lower()))
    return sorted(w for w in words - allowed - _COMMON if not w.endswith("ing"))


def check(profile: Dict, digest: Dict) -> List[str]:
    problems = []
    banned = forbidden_only_words(profile)
    for key, limit in (("lock_short", SHORT), ("lock_medium", MEDIUM)):
        text = str(digest.get(key) or "")
        if not text.strip():
            problems.append(f"{key} trống")
        if len(text) > limit:
            problems.append(f"{key} dài {len(text)} > {limit} ký tự")
        if _MINOR_AGE.search(text):
            problems.append(f"{key} ghi tuổi dưới 18")
        said = set(_WORD.findall(text.lower()))
        bad = [w for w in banned if w in said]
        if bad:
            problems.append(f"{key} có chữ chỉ nằm trong phần CẤM: {', '.join(bad)}")
    return problems


def current(profile: Dict) -> Dict:
    """The digest to use: the stored one while the profile is unchanged (a hand-written one is kept), else a new one from code."""
    stored = profile.get("digest") if isinstance(profile.get("digest"), dict) else None
    if stored and stored.get("hash") == source_hash(profile) and not check(profile, stored):
        return stored
    return build(profile)


def refresh(conn, asset_id: int) -> Optional[Dict]:
    """Make / renew the digest of one library profile and keep it there. Returns it (None: no profile)."""
    from . import assets
    prof = assets.get_profile(conn, asset_id)
    if not prof.get("identity") and not prof.get("must_keep"):
        return None
    digest = current(prof)
    if prof.get("digest") != digest:
        prof["digest"] = digest
        conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(prof, ensure_ascii=False), asset_id))
        conn.commit()
    return digest


def for_character(conn, project_id: int, name: str, level: str = "lock_medium") -> Optional[str]:
    """The short form of a project character's approved library profile (None: no approved profile)."""
    from . import assets
    asset = assets.link_characters(conn, project_id, [name]).get(name)
    if asset is None:
        return None
    prof = assets.get_profile(conn, asset["id"])
    if not prof.get("approved"):
        return None
    digest = refresh(conn, asset["id"])
    return digest.get(level) if digest else None
