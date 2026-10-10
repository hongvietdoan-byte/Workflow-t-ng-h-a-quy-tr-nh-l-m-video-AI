"""Bộ dịch đặc tả → mệnh đề kiểm tra (Tổ QC, thiết kế docs/THIET_KE_TO_QC_2026-10-01.md mục 6).

A frame is checked against its OWN spec: the Director's shot row (who is in frame, where, looking at whom, doing what, size, time, light)
and the approved library profile of every person in it (asymmetric details, headwear direction, forbidden changes). Every new script
therefore brings its own questions; old labels are only the yardstick (mục 5).

An assertion (dict): id, type, role (C1 / C2 / C3 / T0), subject, claim_vi, question_en, expected, how (code / model / code+model),
severity_if_false (block / minor), priority (1 = characters … 5 = technical, mục 9.3), source (the field it came from), view.
"""
import hashlib
import re
from typing import Dict, List, Optional, Tuple

PRIORITY = {"identity": 1, "count": 1, "asym": 1, "headwear": 1, "skill": 1, "gaze": 2, "action": 2, "gesture": 2, "layout": 2,
            "light": 3, "weather": 3, "continuity": 3, "geometry": 3, "place": 4, "size": 5, "angle": 5, "text": 5}
ROLE = {"identity": "C1", "count": "C1", "asym": "C1", "headwear": "C1", "skill": "C1", "gaze": "C2", "action": "C2", "gesture": "C2",
        "layout": "C2", "light": "C3", "weather": "C3", "continuity": "C3", "geometry": "C3", "place": "C3", "size": "T0", "angle": "T0",
        "text": "T0"}
SIZES = ("ECU", "CU", "MCU", "MS", "MLS", "LS", "WS", "EWS")
_SIDE = re.compile(r"\b(LEFT|RIGHT)\b", re.I)
_ARM_HEAD = re.compile(r"\b(LEFT|RIGHT)\s+(arm|hand|side|leg)\s*:", re.I)
_HEADWEAR = re.compile(r"([\w\s-]{0,30}\b(?:cap|hat|helmet|hood|bandana|beanie)\b[^,;.]*?\b(?:backwards?|reversed|ngược)\b[^,;.]*)", re.I)
# GĐ3 01/10: "looking off-screen frame-left toward Maxim" (#8 job 352) did not match the old pattern → no gaze assertion
_LOOK = re.compile(r"\blook(?:s|ing)?\s+((?:off[- ]?(?:screen|frame)\s+)?(?:frame[- ](?:left|right)\s+)?(?:toward|towards|at|to)\s+[^,;.]+"
                   r"|off[- ]?(?:screen|frame)\s+(?:frame[- ])?(?:left|right)\b[^,;.]*|off\s+(?:toward|towards|at|to)\s+[^,;.]+)", re.I)


def view_of(data: Dict, name: str) -> Optional[str]:
    """'behind' / 'camera' / None from the shot's words (the same reading the image prompt uses)."""
    from .runner import seen_from_behind
    v = seen_from_behind(data, name)
    return "behind" if v is True else ("camera" if v is False else None)


def asym_details(text: str) -> List[Tuple[str, str]]:
    """[(side LEFT/RIGHT, detail)] from a profile's must_keep: "RIGHT arm: black sleeve, bandage, fingerless glove; LEFT arm: …" gives
    each item of the group its side; "star emblem on the LEFT shoulder" gives one item."""
    out: List[Tuple[str, str]] = []
    text = str(text or "")
    heads = list(_ARM_HEAD.finditer(text))
    covered = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end]
        stop = re.search(r";|\.\s|\b(?:shoulder|scarf|coat|hair|pants|trousers)\b", body)
        body = body[:stop.start()] if stop and stop.start() > 0 else body
        covered.append((m.start(), m.end() + len(body)))
        for item in re.split(r",", body):
            item = item.strip(" .;")
            if item:
                out.append((m.group(1).upper(), f"{m.group(1).upper()} {m.group(2).lower()}: {item}"))
    for chunk in re.split(r"[,;]", text):
        pos = text.find(chunk)
        if any(a <= pos < b for a, b in covered):
            continue
        m = _SIDE.search(chunk)
        if m and not _ARM_HEAD.search(chunk):
            out.append((m.group(1).upper(), chunk.strip(" .")))
    return out


def headwear_details(text: str) -> List[str]:
    return [m.group(1).strip(" ,.") for m in _HEADWEAR.finditer(str(text or ""))]


def _a(frame_job, type_, subject, claim_vi, question_en, expected, how, severity, source, view=None) -> Dict:
    tag = hashlib.md5(claim_vi.encode("utf-8")).hexdigest()[:6]          # stable across runs (replay matches by id)
    return {"id": f"{frame_job}#{type_}:{subject}:{tag}", "frame_job": frame_job, "type": type_,
            "role": ROLE[type_], "subject": subject, "claim_vi": claim_vi, "question_en": question_en, "expected": expected,
            "how": how, "severity_if_false": severity, "priority": PRIORITY[type_], "source": source, "view": view}


def plan_conflicts(data: Dict) -> List[str]:
    """playbook E: a shot row that contradicts itself — not sent to the specialists (redrawing cannot fix a wrong table)."""
    out = []
    cast = [str(c).upper() for c in data.get("characters") or []]
    words = " ".join(str(data.get(k) or "") for k in ("blocking", "image_prompt", "action")).lower()
    if str(data.get("angle") or "").lower() == "ots" and len(cast) < 2:
        out.append("góc qua vai (OTS) mà bảng shot chỉ có 1 người")
    if str(data.get("size") or "").upper() in ("CU", "MCU", "ECU") and re.search(r"full body|toàn thân|feet|head to toe", words):
        out.append(f"cỡ {data.get('size')} mà mô tả đòi thấy toàn thân")
    # a name placed IN the frame (frame-left / right / center / background…) that `characters` lacks; a name only looked at or
    # "off-frame" is normal (dry run 01/10: 5 of 6 flags were gaze targets off-frame)
    for m in re.finditer(r"\b([A-Z]{4,})\b([^,;.]{0,40})", str(data.get("blocking") or "")):
        name, rest = m.group(1).upper(), m.group(2).lower()
        in_frame = re.search(r"frame[- ]?(left|right|cent)|\bcentered\b|\bforeground\b|\bbackground\b", rest)
        if cast and name not in cast and name in {"KELLY", "KENTA", "MAXIM", "ORION"} and in_frame \
                and not re.search(r"off[- ]?(frame|screen)", rest):
            out.append(f"blocking đặt {name} trong khung nhưng `characters` không có")
    return sorted(set(out))


def compile_frame(conn, project_id: int, frame_job: int, data: Dict, profiles: Optional[Dict[str, Dict]] = None) -> Dict:
    """{"assertions": [...], "plan_conflicts": [...], "missing_profiles": [...]} for one frame. `profiles` (name → approved profile)
    may be given (tests / a whole scene at once); otherwise read with assets.standard_for."""
    from . import assets
    cast = [str(c).upper() for c in data.get("characters") or []]
    out: List[Dict] = []
    missing = []
    has_dialogue = bool([d for d in data.get("dialogue") or [] if isinstance(d, dict) and str(d.get("text") or "").strip()])
    out.append(_a(frame_job, "count", ",".join(cast) or "-", f"Trong khung có đúng {len(cast)} người: {', '.join(cast) or 'không ai'}",
                  f"Exactly {len(cast)} people are visible: {', '.join(cast) or 'nobody'}. Is that true? Also report `extra_people`.", len(cast), "code+model", "block",
                  "characters"))
    for name in cast:
        prof = (profiles or {}).get(name) if profiles is not None else (assets.standard_for(conn, project_id, name) if conn else None)
        view = view_of(data, name)
        if not prof:
            missing.append(name)
            out.append(_a(frame_job, "identity", name, f"{name} đúng ảnh chuẩn Kho (chưa có hồ sơ duyệt — chỉ so ảnh)",
                          f"Does {name} match the standard picture (face, hair, outfit)?", True, "model", "block", "characters", view))
            continue
        out.append(_a(frame_job, "identity", name, f"{name} đúng người, đúng trang phục chính theo hồ sơ",
                      f"Is {name} the same person as the standard picture, in the main outfit (" + str(prof.get("must_keep") or "")[:160]
                      + ")?", True, "model", "block", "profile.must_keep", view))
        if prof.get("forbidden"):
            out.append(_a(frame_job, "identity", name, f"{name} không có điều cấm: {str(prof['forbidden'])[:120]}",
                          f"Is any of these forbidden changes visible on {name}: {str(prof['forbidden'])[:200]}? (true = none visible)",
                          True, "model", "block", "profile.forbidden", view))
        forbidden = str(prof.get("forbidden") or "").lower()
        for side, detail in asym_details(prof.get("must_keep")):
            key = detail.split(":")[-1].strip().split(" ")[-1].lower()
            sev = "block" if (key and key in forbidden) or re.search(r"glove|gauntlet|emblem|găng|huy hiệu", detail, re.I) else "minor"
            out.append(_a(frame_job, "asym", name, f"{name}: {detail} — ở tay/bên {side} của CHÍNH {name}",
                          f"Where do you SEE this detail of {name} in the picture: {_SIDE.sub('one', detail)}? Report `facing` and "
                          f"`seen_at` only (the side is decided by code).", side, "code+model", sev,
                          "profile.must_keep", view))
        for _hw in headwear_details(prof.get("must_keep")):
            claim = (f"{name} quay lưng: thấy lưỡi trai che gáy (mũ đội ngược)" if view == "behind"
                     else f"{name}: khóa / dây mũ ở trán, lưỡi trai hướng ra sau (mũ đội ngược)")
            q = f"Look at {name}'s cap: what do you SEE at the forehead and at the nape? Report `cap_marks` only (the direction is decided by code)."
            out.append(_a(frame_job, "headwear", name, claim, q, True, "model", "block", "profile.must_keep", view))
    blocking = str(data.get("blocking") or "")
    for name in cast:
        m = re.search(rf"\b{re.escape(name)}\b[^,;.]*?\bframe[- ](left|right|center|centre)\b", blocking, re.I)
        if m:
            out.append(_a(frame_job, "layout", name, f"{name} ở nửa {m.group(1)} khung", f"Is {name} on the frame-{m.group(1)} side?",
                          m.group(1).lower(), "code+model", "minor", "blocking"))
        mm = re.search(rf"\b{re.escape(name)}\b[^.;]*?{_LOOK.pattern}", blocking, re.I)
        if mm:
            target = mm.group(1).strip()
            out.append(_a(frame_job, "gaze", name, f"{name} nhìn về {target}", f"Is {name} looking toward {target}?", target,
                          "code+model", "block" if has_dialogue else "minor", "blocking"))
    perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    if perf.get("body"):
        out.append(_a(frame_job, "gesture", cast[0] if cast else "-", f"Tư thế: {perf['body']}", f"Body / pose as described: {perf['body']}?",
                      True, "model", "minor", "performance.body"))
    if data.get("action"):
        out.append(_a(frame_job, "action", cast[0] if cast else "-", f"Hành động: {str(data['action'])[:120]}",
                      f"Does the frame show this action: {str(data['action'])[:200]}?", True, "model", "minor", "action"))
    size = str(data.get("size") or "").upper()
    if size in SIZES:
        out.append(_a(frame_job, "size", "-", f"Cỡ cảnh {size}", f"Shot size {size}?", size, "code", "minor", "size"))
    if data.get("time") or data.get("weather"):
        out.append(_a(frame_job, "light", "-", f"Giờ {data.get('time') or '?'} · trời {data.get('weather') or '?'} khớp ảnh toàn cảnh",
                      f"Does the light match time={data.get('time')} weather={data.get('weather')} and the scene's establishing picture?",
                      {"time": data.get("time"), "weather": data.get("weather")}, "code+model", "block", "time/weather"))
    if data.get("skill_phase"):
        out.append(_a(frame_job, "skill", cast[0] if cast else "-", f"Kỹ năng đúng giai đoạn {data['skill_phase']}",
                      f"Does the skill effect match phase {data['skill_phase']} of the skill dossier (and none of its never-draw items)?",
                      str(data["skill_phase"]), "model", "block", "skill_phase"))
    # GĐ3 01/10: for sides, cap direction and head count the model reports what it SEES (fixed choices) and qc_rules decides
    close = str(data.get("size") or "").upper() in ("ECU", "CU", "MCU", "MS")
    for a in out:
        obs = {"asym": "side", "headwear": "cap", "count": "count"}.get(a["type"])
        if obs:
            a.update(observe=obs, cast_n=len(cast), close=close)
    geo_missing = None
    from . import features
    if features.on("stage_camera"):         # 10/10 (#24 shot 4 + 8): the 3D stage's facts — the model reports, stage_facts judges
        from . import stage_facts
        res = stage_facts.for_shot(conn, project_id, data)
        geo_missing = res["missing"] if data.get("stage_camera") else None
        for f in res["facts"]:
            if not stage_facts.declared(f):          # N5 (người dùng 10/10): vị trí in_frame không khai
                continue
            a = _a(frame_job, "geometry", f["subject"], f"Hình học máy 3D — {f['id']} = {f['value']} (code tính)",
                   f["question"] + " Report `geo_seen` only (the code decides).", f["value"], "code+model", "block", "stage_camera")
            a.update(observe="geo", fact=f, options=list(f["options"]))
            out.append(a)
    out.sort(key=lambda a: (a["priority"], a["subject"]))
    return {"assertions": out, "plan_conflicts": plan_conflicts(data), "missing_profiles": missing,
            **({"geometry_missing": geo_missing} if geo_missing else {})}
