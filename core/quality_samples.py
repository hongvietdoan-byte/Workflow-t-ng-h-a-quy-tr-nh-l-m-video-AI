"""Explicit, separately billed Seedance 2.5 quality samples; never replace pipeline jobs."""
import hashlib
import json
import math
import os
import time
from pathlib import Path

from . import access, budget, cost, dialogue, features, place_refs, seedance_refs, shots, spend_gate

MODEL = "dreamina-seedance-2-5-260628"
TIERS = {"direct": "720p", "draft": "480p", "final": "1080p", "high": "1080p"}
LABELS = {"direct": "A · 720p", "draft": "B · bản mẫu 480p", "final": "B · bản cuối 1080p", "high": "C · 1080p gen thẳng"}
# API từ chối rõ ràng (chưa tạo task) → không ghi nợ; lỗi mạng/không rõ vẫn giữ "uncertain" và tạm tính tiền.
REJECTED_CODES = {"rule_violation", "unsupported_option", "feature_off", "prompt_too_long", "missing_image", "bad_input",
                  "http_error", "api_error", "too_large", "auth", "config"}


def _path(data_dir, pid):
    return Path(data_dir) / str(pid) / "experiments" / "quality_samples.json"


def load(data_dir, pid):
    path = _path(data_dir, pid)
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list) or any(not isinstance(e, dict) or not all(k in e for k in ("scene_id", "kind", "state", "usd"))
                                              or e["kind"] not in TIERS or not isinstance(e["scene_id"], int)
                                              or not isinstance(e["usd"], (int, float)) or not math.isfinite(e["usd"]) or e["usd"] < 0
                                              for e in items):
            raise ValueError("invalid entries")
        return items
    except (OSError, ValueError) as ex:
        raise ValueError(f"Dữ liệu phép thử hỏng: {path}; giữ nguyên file, không gửi lại.") from ex


def _save(data_dir, pid, items):
    path = _path(data_dir, pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def candidates(p, pid, data_dir):
    return [dict(r) for r in p.conn.execute(
        "SELECT s.id,s.idx,s.data,m.duration_sec,m.ref_video_path FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id "
        "WHERE s.project_id=? AND m.state='approved' AND m.duration_sec>0 AND m.duration_sec<=4 ORDER BY s.idx", (pid,))
        if not r["ref_video_path"] and not dialogue.scene_lines(json.loads(r["data"] or "{}"))
        and shots.approved_image_path(p.conn, data_dir, pid, r["id"]) is not None]


def plan(p, pid, sid, data_dir):
    row = p.conn.execute("SELECT s.id,s.data,m.motion_prompt,m.duration_sec,m.negative_prompt,m.ref_video_path "
                         "FROM scenes s JOIN motion_prompts m ON m.scene_id=s.id "
                         "WHERE s.id=? AND s.project_id=? AND m.state='approved'", (sid, pid)).fetchone()
    if row is None or not 0 < float(row["duration_sec"] or 0) <= 4:
        raise ValueError("Chọn shot có motion đã duyệt, dài 3–4 giây hoặc ngắn hơn để thử 4 giây.")
    from . import formats
    aspect = formats.spec(formats.project_aspect(p.project(pid)))["clip"]
    if aspect != "9:16":
        raise ValueError("Phép so này dùng khung dọc 9:16; chọn dự án dọc.")
    image = shots.approved_image_path(p.conn, data_dir, pid, sid)
    if not image or not os.path.isfile(image):
        raise ValueError("Shot chưa có file ảnh đã duyệt.")
    rows = [{"id": sid, "data": json.loads(row["data"] or "{}")}]
    from . import dialogue, looks
    from .runner import no_minor_age
    if row["ref_video_path"] or dialogue.scene_lines(rows[0]["data"]):
        raise ValueError("Phép so 4 giây này dùng shot không thoại và không video tham chiếu; chọn shot 6 Kelly.")
    ref_only = seedance_refs.uses_refs(p.conn, sid)
    text, pictures = no_minor_age(row["motion_prompt"]), []
    if ref_only and place_refs.enabled():               # KLD-6: never a paid sample on a render of another camera
        res = place_refs.resolution_of(p.project(pid))
        old = place_refs.stale(p.conn, data_dir, pid, res).get(sid)
        if old:
            place_refs.ensure_async(p.conn, pid, data_dir, res)
            raise ValueError(f"{old['why']} — đang dựng lại nền (0 USD); thử lại sau ít phút.")
    if ref_only:
        ids = seedance_refs.identity_pictures(p.conn, pid, rows, seedance_refs.MAX_PICTURES - 1)
        places = seedance_refs.place_pictures(data_dir, pid, rows)
        if place_refs.enabled() and place_refs.wants_render(p.conn, pid, rows[0]["data"]) and not places:
            raise ValueError("Thiếu render địa điểm 3D của shot; tạo render trước khi thử.")
        pictures = [image] + [path for _, path in ids] + [r["path"] for r in places]
        text = seedance_refs.prompt([(text, 4)], ids, clip_seconds=4, model=MODEL, places=places)
    proj = p.project(pid)
    text, _ = looks.clean_prompt(proj, no_minor_age(text))
    lock = looks.video_sentence(proj)
    if lock and lock not in text:
        text = f"{lock} {text}"
    errors = seedance_refs.lint_group(text, 1, len(pictures) if ref_only else 1, len(pictures) if ref_only else 1,
                                     [4], False, model=MODEL)
    if errors:
        raise ValueError("; ".join(errors))
    return {"scene_id": sid, "seconds": 4, "aspect": aspect, "prompt": text,
            "pictures": pictures, "image": image, "reference_only": ref_only,
            "negative": looks.video_negative(proj, row["negative_prompt"])}


def estimate(kind):
    if kind not in TIERS:
        raise ValueError("Loại phép thử không hợp lệ.")
    return cost.seedance_estimate(MODEL, TIERS[kind], "9:16", 4)


def _hash(plan):
    digest = hashlib.sha256(json.dumps({k:plan.get(k) for k in ("prompt", "negative", "seconds", "aspect", "reference_only")},
                                      sort_keys=True).encode("utf-8"))
    for path in plan["pictures"] or [plan["image"]]:
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def send(p, pid, sid, kind, provider, data_dir, max_usd=4.0):
    access.need_edit(p, pid, "gửi phép thử độ nét")
    if not features.on("seedance_sample_mode"):
        raise ValueError("Bật tính năng thử độ nét Seedance 2.5 trước khi gửi.")
    usd = estimate(kind)
    if not math.isfinite(float(max_usd)) or max_usd <= 0 or max_usd > 4.0:
        raise ValueError("Trần phép so phải > 0 và ≤ 4 USD.")
    with budget.SPEND_LOCK:
        items = load(data_dir, pid)
        prior = next((e for e in items if e["scene_id"] == sid and e["kind"] == kind), None)
        if prior:
            return prior  # uncertain/failed are retained too; never automatic re-send
        related = [e for e in items if e["scene_id"] == sid]
        if sum(float(e["usd"]) for e in related) + usd > max_usd + 1e-9:
            raise ValueError("Trần phép so chặn lần gửi này; không gửi.")
        source = None
        if kind == "final":
            source = next((e for e in related if e["kind"] == "draft" and e["state"] == "succeeded"), None)
            if not source or not source.get("external_id"):
                raise ValueError("Bản mẫu phải tải về thành công trước khi gen bản cuối.")
            meta = provider.task_usage(source["external_id"])
            expiry = float((meta or {}).get("draft_expired_at") or 0)
            if expiry > 1e12:
                expiry /= 1000
            if not meta or not meta.get("is_draft") or expiry <= time.time() or abs(float(meta.get("duration") or 0) - 4) > 0.1:
                raise ValueError("Chưa xác nhận bản mẫu 4 giây còn hạn; kiểm tra lại metadata trước khi trả tiền bản cuối.")
            input_plan = source["input_plan"]
            input_hash = source["input_hash"]
        else:
            input_plan = plan(p, pid, sid, data_dir)
            input_hash = _hash(input_plan)
            if related and any(e.get("input_hash") != input_hash for e in related):
                raise ValueError("Đầu vào shot đã đổi sau phép thử đầu; không tạo cặp so sánh khác đầu vào.")
        with spend_gate.spend(p.conn, "video", provider.name, project_id=pid, model=MODEL, tier=TIERS[kind], units=4,
                              ledger_stage="quality_sample") as slot:
            slot.raise_if_over("Không gửi phép thử")
            entry = {"scene_id": sid, "kind": kind, "state": "sending", "usd": usd, "seconds": 4,
                     "input_plan": input_plan, "input_hash": input_hash, "at": time.time()}
            items.append(entry)
            _save(data_dir, pid, items)  # survive interrupted/uncertain POST; prevents paying twice
            attempted = False
            try:
                if source:
                    attempted = True
                    ext = slot.send(provider.submit_final_from_sample, source["external_id"])
                else:
                    kwargs = {"aspect_ratio": "9:16", "resolution": TIERS[kind], "draft": kind == "draft"}
                    if kind == "high":
                        kwargs["high_res_sample"] = True    # explicit 1080p override for 2.5, this path only
                    if input_plan["reference_only"]:
                        marked = os.path.join(data_dir, str(pid), "experiments", "quality_refs")
                        kwargs["reference_only"] = [seedance_refs.mark(path, marked) for path in input_plan["pictures"]]
                    attempted = True
                    ext = slot.send(provider.submit, input_plan["image"], input_plan["prompt"], input_plan.get("negative"), 4, MODEL,
                                    with_audio=False, **kwargs)
                entry.update(external_id=ext, state="running")
                _save(data_dir, pid, items)  # durable task before ledger / later polling
                slot.record()
            except Exception as ex:
                if kind == "high" and not entry.get("external_id") and getattr(ex, "code", None) in REJECTED_CODES \
                        and not getattr(ex, "transient", False):
                    # Definite refusal (e.g. API does not take 1080p for 2.5): say it clearly, nothing was created → no charge, no retry.
                    entry.update(state="failed", rejected=True, usd=0, usd_estimated=usd,
                                 message=f"Nhà cung cấp từ chối gen thẳng 1080p: {str(ex)[:300]}")
                    _save(data_dir, pid, items)
                    raise
                if not entry.get("external_id"):
                    entry.update(state="uncertain", message=str(ex)[:400])
                _save(data_dir, pid, items)
                if attempted and not entry.get("external_id"):
                    # Unknown POST outcome: conservatively reserve its estimated charge, never hide a possibly paid call.
                    slot.record()
                    entry["charge_uncertain"] = True
                    _save(data_dir, pid, items)
                raise
        return entry


def refresh(p, pid, provider, data_dir):
    access.need_edit(p, pid, "lấy kết quả phép thử độ nét")
    with budget.SPEND_LOCK:
        items = load(data_dir, pid)
        for entry in items:
            if entry["state"] != "running":
                continue
            status = provider.status(entry["external_id"])
            if status.state == "succeeded":
                dest = str(_path(data_dir, pid).parent / f"quality_{entry['scene_id']}_{entry['kind']}.mp4")
                result = provider.download(entry["external_id"], dest)
                if not result or not os.path.isfile(result):
                    raise ValueError("Nhà cung cấp báo xong nhưng chưa tải được file; kiểm tra lại, không gửi lại.")
                entry.update(state="succeeded", file=result)
            elif status.state == "failed":
                entry.update(state="failed", message=getattr(status, "error_message", "Nhà cung cấp báo lỗi"))
        _save(data_dir, pid, items)
        return items
