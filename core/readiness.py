"""F5-A (09/10): ô "sẵn sàng gen" của từng shot — hàm THUẦN, chỉ ĐỌC (không gọi model, không tiền, không ghi).

Gom mọi điều kiện đã có ở các khâu thành MỘT danh sách cho thẻ cảnh (Bước 2 ảnh, Bước 4 video), để người dùng biết TRƯỚC khi bấm
vì sao một shot sẽ bị giữ / chặn và sửa ở đâu (nút sửa đã có ở chỗ khác — ở đây chỉ nói "sửa ở Bước X"):

- công thức prompt: lỗi ĐỎ đúng như ImageRunner/VideoRunner._blocked (prompt_formula — cùng luật, gồm phần 'trồng thêm' và tiết
  chế máu FF) + cảnh báo vàng;
- nền 3D (chỉ ảnh, cờ place_render_refs): có render + góc rộng cùng trục / chưa render (tự render 0 USD khi gen) / hỏng (ảnh bị giữ)
  / chờ kịch bản chọn hướng máy;
- ảnh tham chiếu thiếu (assets.reference_gaps);
- model + giá ước tính (ảnh: model ảnh dự án; video: dashboard.model_line — nháp→cao, cảnh báo E1);
- ảnh khung đầu đã duyệt + motion prompt (video);
- vật mốc Kho chưa có kích thước thật mà xuất hiện ở ≥ 2 shot (gốc lỗi tỉ lệ giếng #24) → cảnh báo.

`project_ready(conn, data_dir, pid, kind)` tính phần chung MỘT lần cho cả lưới (nhân vật, model, giá, ảnh duyệt, motion, vật Kho,
dòng model) rồi từng shot chỉ chạy regex + vài đọc nhỏ — không N+1 nặng. `shot_ready` = một shot.
Mỗi mục: {"label", "state": ok|warn|red, "why", "fix_where"}; "ok" = không có mục red."""
import json
from typing import Dict, Iterable, List, Optional

ICON = {"ok": "✅", "warn": "⚠", "red": "⛔"}
WHERE_IMAGE_PROMPT = "sửa ở Bước 1/2 (Kịch bản → Director viết lại, hoặc ✎ Sửa trên thẻ ảnh Storyboard)"
WHERE_MOTION_PROMPT = "sửa ở Bước 3 (Storyboard · tab Motion — ✏ Sửa motion prompt)"
WHERE_PLATE = "sửa ở Bước 2 (Storyboard: nút “↻ Render lại nền 3D”, 0 USD)"
WHERE_SCRIPT_CAMERA = "sửa ở Bước 1 (Kịch bản: chọn hướng máy cho chỗ đứng)"
WHERE_REFS = "sửa ở Bước 1 (Kịch bản: nhân vật / Kho tài nguyên — gắn ảnh tham chiếu)"
WHERE_IMAGE_APPROVE = "sửa ở Bước 2 (Storyboard: duyệt ảnh khung đầu)"
WHERE_MODEL = "đổi ở Bước 4 (Video: bảng Model · Đổi)"
WHERE_KHO = "sửa ở Kho tài nguyên (Cài đặt → Kho: ô “Chiều cao thật (m)”)"


def _item(label: str, state: str, why: str, fix_where: str = "") -> Dict:
    return {"label": label, "state": state, "why": why, "fix_where": fix_where if state != "ok" else ""}


def _kind(kind: str) -> str:
    return "video" if kind in ("video", "motion") else "image"


# ---- phần chung của dự án (một lần mỗi lượt vẽ) ------------------------------------------------------------------------------
def context(conn, data_dir: str, pid: int, kind: str, lines: Optional[Dict] = None) -> Dict:
    from . import prompt_formula as pf
    kind = _kind(kind)
    proj = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    scenes = {r["id"]: r for r in conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=?", (pid,)).fetchall()}
    ctx: Dict = {"kind": kind, "pid": pid, "data_dir": data_dir, "proj": proj, "scenes": scenes, "formula": pf.enabled()}
    if ctx["formula"]:
        ctx["chars"] = pf._chars(conn, pid)
        ctx["ff"] = pf._is_ff(conn, pid)
        ctx["style_by_code"] = pf._style_by_code(conn, pid)
    ctx["motion"] = {r["scene_id"]: r["motion_prompt"] for r in conn.execute(
        "SELECT m.scene_id, m.motion_prompt FROM motion_prompts m JOIN scenes s ON s.id=m.scene_id WHERE s.project_id=?", (pid,))}
    try:
        from . import place_refs
        ctx["unsized"] = place_refs.unsized_objects(conn, pid)
    except Exception:  # noqa: BLE001 - a broken library read never breaks the card
        ctx["unsized"] = {}
    if kind == "image":
        ctx["image_model"], ctx["image_usd"] = _image_price(proj)
    else:
        ctx["approved"] = {r["scene_id"] for r in conn.execute(
            "SELECT DISTINCT scene_id FROM jobs WHERE project_id=? AND type='image_gen' AND state='approved'", (pid,))}
        if lines is None:
            try:
                from dashboard import model_line
                lines = model_line.shot_lines(conn, pid)
            except Exception:  # noqa: BLE001 - the model line is information
                lines = {}
        ctx["lines"] = lines or {}
    return ctx


def _image_price(proj):
    try:
        from . import image_models, money_policy
        model = image_models.of_project(proj) if proj is not None else None
        return model, money_policy.estimate("image", model, None, 1).get("usd")
    except Exception:  # noqa: BLE001
        return None, None


# ---- từng mục ------------------------------------------------------------------------------------------------------------------
def _formula(conn, ctx: Dict, sid: int, data: Dict) -> Dict:
    from . import prompt_formula as pf
    image = ctx["kind"] == "image"
    text = data.get("image_prompt") if image else ctx["motion"].get(sid)
    label = "Công thức prompt " + ("ảnh" if image else "motion")
    where = WHERE_IMAGE_PROMPT if image else WHERE_MOTION_PROMPT
    if not (text or "").strip():
        return _item(label, "red", "chưa có " + ("prompt ảnh" if image else "motion prompt"), where)
    if not ctx["formula"]:
        return _item(label, "ok", "kiểm công thức đang tắt (cờ)")
    k = "image" if image else "motion"
    # cùng luật với prompt_formula.red_issues (chặn gửi) — tính lại ở đây với nhân vật đọc MỘT lần cho cả lưới
    issues = (pf.lint_image(text, data, ctx["chars"], ctx["style_by_code"], ctx["ff"]) if image
              else pf.lint_motion(text, data, ctx["chars"], ctx["ff"]))
    fc = data.get("formula_check") or {}
    if fc and fc.get(f"{k}_sha") == pf._sha(text):
        issues += [g for g in fc.get("growth") or [] if g.get("kind") == k]
    gore = [i for i in issues if i["part"] == "luat_ff" and i["level"] == "red"]
    if ctx["ff"] and gore and pf._gore_goes(conn, sid, ctx["proj"], k, text, None):
        issues = [i for i in issues if i not in gore]
    reds = [f"{pf.PART_LABELS.get(i['part'], i['part'])}: {i['msg']}" for i in issues if i["level"] == "red"]
    warns = [f"{pf.PART_LABELS.get(i['part'], i['part'])}: {i['msg']}" for i in issues if i["level"] != "red"]
    if reds:
        return _item(label, "red", " · ".join(reds), where)
    if warns:
        return _item(label, "warn", " · ".join(warns[:3]) + (f" (+{len(warns) - 3})" if len(warns) > 3 else ""), where)
    return _item(label, "ok", "đủ phần, không lỗi")


def _plate(conn, ctx: Dict, sid: int, data: Dict) -> Optional[Dict]:
    from . import location_pack, place_refs
    if not place_refs.enabled() or not place_refs.wants_render(conn, ctx["pid"], data):
        return None                                          # cờ tắt / chỗ không có 3D: không có mục nền
    d, pid, label = ctx["data_dir"], ctx["pid"], "Nền 3D"
    rec = location_pack.plate_of(d, pid, sid)
    if rec is not None:
        wide = rec.get("wide") or {}
        import os
        if wide.get("plate") and os.path.exists(wide["plate"]):
            return _item(label, "ok", "có render góc máy của shot + góc rộng cùng trục")
        if rec.get("wide_failed"):
            return _item(label, "warn", "có render của shot, góc rộng cùng trục không render được — gửi không kèm góc rộng", WHERE_PLATE)
        return _item(label, "warn", "có render của shot, chưa có góc rộng cùng trục — tự render (Blender, 0 USD) trước khi gửi ảnh")
    need = location_pack.plate_needs(d, pid, sid)
    if need:
        return _item(label, "red", f"ảnh chờ kịch bản: {need}", WHERE_SCRIPT_CAMERA)
    why = place_refs.broken(conn, d, pid, sid, data)
    if why:
        return _item(label, "red", f"render nền hỏng — ảnh bị giữ, không gửi trần: {why}", WHERE_PLATE)
    return _item(label, "warn", "chưa render nền 3D — bấm gen thì tự render (Blender, 0 USD), ảnh chờ tới lúc có nền")


def _refs(conn, ctx: Dict, data: Dict) -> Dict:
    from . import assets
    try:
        gaps = assets.reference_gaps(conn, ctx["pid"], data)
    except Exception:  # noqa: BLE001
        gaps = []
    if gaps:
        return _item("Ảnh tham chiếu", "warn", " · ".join(gaps), WHERE_REFS)
    return _item("Ảnh tham chiếu", "ok", "đủ ảnh tham chiếu" if data.get("characters") else "shot không có nhân vật")


def _objects(conn, ctx: Dict, sid: int, data: Dict) -> Optional[Dict]:
    from . import place_refs
    try:
        objs = place_refs.shot_objects(conn, ctx["pid"], data)
    except Exception:  # noqa: BLE001
        return None
    if not objs:
        return None
    missing = [a["name"] for a in objs if not (a.get("size") or {}).get("height_m") and a["name"] in ctx["unsized"]]
    sized = [f"{a['name']} {a['size']['height_m']:g} m" for a in objs if (a.get("size") or {}).get("height_m")]
    if missing:
        return _item("Kích thước vật mốc", "warn", "; ".join(
            f"vật mốc {n} chưa có kích thước thật (xuất hiện ở {len(ctx['unsized'][n])} shot — model tự đoán, tỉ lệ dễ lệch giữa các shot)"
            for n in missing), WHERE_KHO)
    if sized:
        return _item("Kích thước vật mốc", "ok", "có số thật: " + ", ".join(sized))
    return None


def _model_image(ctx: Dict) -> Dict:
    from . import image_models
    model, usd = ctx.get("image_model"), ctx.get("image_usd")
    name = image_models.label(model) if model else "model ảnh mặc định"
    if usd is None:
        return _item("Model · giá", "warn", f"{name} · chưa có giá", "xem bảng giá (Cài đặt → Giá)")
    return _item("Model · giá", "ok", f"{name} · ≈ {usd:.2f} USD / ảnh")


def _model_video(conn, ctx: Dict, sid: int) -> Dict:
    line = ctx["lines"].get(sid)
    if line is None:
        try:
            from . import cost, model_router
            choice = model_router.scene_choice(conn, sid)
            usd = cost.clip_estimate(conn, sid)
            text = model_router.label(choice.get("model"), choice.get("resolution"))
            line = {"model_text": text, "usd": usd, "in_group": False, "warning": None}
        except Exception:  # noqa: BLE001
            return _item("Model · giá", "warn", "chưa đọc được model của shot", WHERE_MODEL)
    text = line.get("model_text") or line.get("text") or "?"
    usd = line.get("usd")
    price = "trong clip nhóm" if line.get("in_group") else (f"≈ {usd:.2f} USD" if usd is not None else "chưa có giá")
    if line.get("warning"):
        return _item("Model · giá", "warn", f"{text} · {price} — {line['warning']}", WHERE_MODEL)
    if usd is None and not line.get("in_group"):
        return _item("Model · giá", "warn", f"{text} · chưa có giá", WHERE_MODEL)
    return _item("Model · giá", "ok", f"{text} · {price}")


def _first_frame(ctx: Dict, sid: int) -> Dict:
    if sid in ctx["approved"]:
        return _item("Ảnh khung đầu", "ok", "đã duyệt")
    return _item("Ảnh khung đầu", "red", "chưa có ảnh khung đầu đã duyệt — video không gửi được", WHERE_IMAGE_APPROVE)


# ---- kết quả ------------------------------------------------------------------------------------------------------------------
def _shot(conn, ctx: Dict, sid: int) -> Dict:
    row = ctx["scenes"].get(sid)
    if row is None:
        return {"ok": False, "items": [_item("Shot", "red", "không tìm thấy shot", "")]}
    try:
        data = json.loads(row["data"] or "{}")
    except ValueError:
        data = {}
    items: List[Optional[Dict]] = [_formula(conn, ctx, sid, data)]
    if ctx["kind"] == "image":
        items += [_plate(conn, ctx, sid, data), _refs(conn, ctx, data), _objects(conn, ctx, sid, data), _model_image(ctx)]
    else:
        items += [_first_frame(ctx, sid), _objects(conn, ctx, sid, data), _model_video(conn, ctx, sid)]
    items = [i for i in items if i]
    return {"ok": not any(i["state"] == "red" for i in items), "items": items}


def shot_ready(conn, data_dir: str, pid: int, scene_id: int, kind: str, ctx: Optional[Dict] = None) -> Dict:
    """{"ok": bool, "items": [{"label", "state": ok|warn|red, "why", "fix_where"}]} của một shot. kind: 'image' | 'video' ('motion')."""
    ctx = ctx if ctx is not None and ctx.get("kind") == _kind(kind) else context(conn, data_dir, pid, kind)
    return _shot(conn, ctx, scene_id)


def project_ready(conn, data_dir: str, pid: int, kind: str, scene_ids: Optional[Iterable[int]] = None,
                  lines: Optional[Dict] = None) -> Dict[int, Dict]:
    """{scene_id: shot_ready} cho cả lưới — phần chung tính MỘT lần (lines: dòng model F4 nếu màn đã có, khỏi tính lại kế hoạch)."""
    ctx = context(conn, data_dir, pid, kind, lines)
    ids = list(scene_ids) if scene_ids is not None else sorted(ctx["scenes"], key=lambda s: ctx["scenes"][s]["idx"])
    out = {}
    for sid in ids:
        try:
            out[sid] = _shot(conn, ctx, sid)
        except Exception as e:  # noqa: BLE001 - one shot's broken data never hides the others' cards
            out[sid] = {"ok": True, "items": [_item("Kiểm sẵn sàng", "warn", f"không kiểm được: {e}", "")]}
    return out


def summary(res: Dict) -> str:
    """MỘT dòng gọn: "✅ Sẵn sàng" / "✅ Sẵn sàng · 1 lưu ý: …" / "⛔ 2 việc cần sửa: a; b"."""
    reds = [i for i in res.get("items") or [] if i["state"] == "red"]
    warns = [i for i in res.get("items") or [] if i["state"] == "warn"]
    if reds:
        return f"{ICON['red']} {len(reds)} việc cần sửa: " + "; ".join(f"{i['label']} — {_short(i['why'])}" for i in reds)
    if warns:
        return f"{ICON['ok']} Sẵn sàng · {len(warns)} lưu ý: " + "; ".join(i["label"] for i in warns)
    return f"{ICON['ok']} Sẵn sàng"


def blocked_reason(res: Dict) -> str:
    """Lý do ngắn hiện cạnh nút gen của shot red ('' khi không red)."""
    reds = [i for i in res.get("items") or [] if i["state"] == "red"]
    if not reds:
        return ""
    return "⛔ Gen sẽ bị giữ/chặn: " + "; ".join(f"{_short(i['why'])} → {i['fix_where']}" for i in reds)


def details_md(res: Dict) -> str:
    """Nội dung expander chi tiết (markdown)."""
    rows = []
    for i in res.get("items") or []:
        rows.append(f"- {ICON[i['state']]} **{i['label']}** — {i['why']}" + (f" · _{i['fix_where']}_" if i["fix_where"] else ""))
    return "\n".join(rows)


def _short(text: str, n: int = 110) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"
