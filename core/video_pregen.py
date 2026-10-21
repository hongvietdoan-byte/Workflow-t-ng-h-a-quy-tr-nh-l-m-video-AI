"""K3 (A17) — lớp code kiểm video TRƯỚC gen (docs/KE_HOACH_KIEM_SOAT_NHAT_QUAN_2026-10-10.md mục 3.4b hàng "TRƯỚC gen", N10, vân tay
gói mục 3.3). 0 USD, chỉ đọc CSDL + siêu dữ liệu tệp (ffprobe / ffmpeg -i, không đọc cả video). Cờ `video_pregen`, MẶC ĐỊNH TẮT.

check(conn, scene_id, plan) -> [{ma, muc: "do" | "vang", ly_do}] — "do" = không gửi (job giữ trong hàng đợi chờ người, một dòng ⚙ Chẩn
đoán), "vang" = gửi + ghi chẩn đoán. Thiếu dữ liệu để kiểm (ảnh duyệt không có, tệp không đọc được, video không đo được) → ĐỎ có lý do,
không coi là đạt (CHUAN_XAY_DUNG luật 1). Riêng "chưa có BYĐ" → VÀNG (BYĐ chưa bắt buộc ở mọi dự án).

Mã (ma): khung_dau (1) · khung_cuoi (2) · thoi_luong (3) · tham_chieu (4) · chuyen_dong (5) · van_tay (6) · byd (chưa có BYĐ) ·
byd_draft (BYĐ nháp của shot chèn, M2.4).

`plan` = cái runner SẮP gửi (plan_of dựng từ args / kwargs thật của provider.submit + gói `core/sent_package.build` dựng y như lúc gửi):
{job_id, project_id, data_dir, start_frame, prompt, duration, model, with_audio, subjects, image_references, reference_video,
 last_frame, reference_only, reference_audio, resolution, kling_mode, kling_image_refs, from_sample, group_ids, package}.

Luật model KHÔNG chép lại số: thời lượng / độ phân giải / khung cuối = core/video_rules (data/provider_rules.json `video_models`);
video tham chiếu = core/adapters/clipai.reference_video_problems (Kling ≥ 3 s, rộng 700–4553 px, SAR 1:1 …); trần ảnh = `max_images` /
`max_refs` của video_rules; enum chuyển động máy = core/shot_intent (CHUYEN_DONG / stage_solver.MOVES).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional

FLAG = "video_pregen"
DO, VANG = "do", "vang"
# job trước có clip (đã trả tiền + có kết quả) mới tính là "lần gen trước" của N10; lần trước hỏng ở nhà cung cấp (không có clip) thì
# gửi lại y gói là đúng (pipeline.retry PLAIN_RESEND), chỉ VÀNG
_HAD_CLIP = ("succeeded", "pending_review", "approved", "rejected")
_FP_KEYS = ("call", "prompt", "negative", "provider", "model", "params", "from_sample")
_MTIME_SLACK_S = 2.0


def enabled() -> bool:
    from . import features
    return features.on(FLAG)


def _issue(ma: str, muc: str, ly_do: str) -> Dict[str, str]:
    return {"ma": ma, "muc": muc, "ly_do": ly_do}


def _data(conn, scene_id: int) -> Dict:
    row = conn.execute("SELECT data FROM scenes WHERE id=?", (scene_id,)).fetchone()
    try:
        return json.loads(row["data"] or "{}") if row else {}
    except (TypeError, ValueError):
        return {}


def _tag(conn, scene_id: int, many: bool) -> str:
    if not many:
        return ""
    row = conn.execute("SELECT idx FROM scenes WHERE id=?", (scene_id,)).fetchone()
    return f"S{row['idx']:02d}: " if row and isinstance(row["idx"], int) else f"shot #{scene_id}: "


def _rel(path: Any) -> str:
    from .sent_package import rel_path
    return rel_path(str(path))


# ---- vân tay gói (N10, mục 3.3) -------------------------------------------------------------------------------------------------
def fingerprint(pkg: Any) -> Optional[str]:
    """Băm gói gửi (dạng core/sent_package): prompt + ảnh/video tham chiếu (vai + sha; tệp không băm được thì đường dẫn) + provider +
    model + tham số. Bỏ `at`, `external_id`, `v`, nhãn ảnh: hai lần gửi cùng đầu vào cho cùng vân tay. None = không phải gói."""
    if isinstance(pkg, str):
        try:
            pkg = json.loads(pkg)
        except (TypeError, ValueError):
            return None
    if not isinstance(pkg, dict):
        return None
    body = {k: pkg.get(k) for k in _FP_KEYS}
    body["refs"] = [{"param": r.get("param"), "role": r.get("role"), "sha256": r.get("sha256"),
                     "path": None if r.get("sha256") else r.get("path"), "extra": r.get("extra")}
                    for r in pkg.get("refs") or [] if isinstance(r, dict)]
    text = json.dumps(body, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _previous_sent(conn, scene_id: int, job_id: Optional[int]):
    """Job video gần nhất của shot đã gửi (có gói) — mọi trạng thái, trừ chính job này."""
    return conn.execute("SELECT id, state, result_path, sent_package FROM jobs WHERE scene_id=? AND type='video_gen' AND id<>? "
                        "AND sent_package IS NOT NULL AND sent_package<>'' ORDER BY id DESC LIMIT 1",
                        (scene_id, job_id or -1)).fetchone()


def _hero_second(conn, plan: Dict, scene_id: int) -> bool:
    """S0.14 T4 (cờ hero_takes): bản 2 của shot ⭐ CỐ Ý cùng đầu vào bản 1 (hai ứng viên, không phải gen lại vì lỗi)."""
    try:
        from . import hero_takes
        rec = hero_takes.load(conn, plan.get("project_id")).get(str(scene_id)) or {}
        return bool(plan.get("job_id")) and rec.get("second") == plan.get("job_id")
    except Exception:  # noqa: BLE001 - không đọc được sổ T4: coi như không phải bản 2 (kiểm N10 như thường)
        return False


def _check_fingerprint(conn, scene_id: int, plan: Dict, out: List[Dict]) -> None:
    pkg = plan.get("package")
    fp = fingerprint(pkg)
    if fp is None:
        out.append(_issue("van_tay", DO, "không dựng được gói gửi để lấy vân tay — không biết lần này có đổi đầu vào so với lần trước "
                                         "không (N10)"))
        return
    prev = _previous_sent(conn, scene_id, plan.get("job_id"))
    previous_fp = fingerprint(prev["sent_package"]) if prev else None
    if prev:
        try:
            previous_fp = json.loads(prev["sent_package"]).get("pregen_fingerprint") or previous_fp
        except (TypeError, ValueError, AttributeError):
            pass
    if prev is None or previous_fp != fp:
        return
    if _hero_second(conn, plan, scene_id):
        return
    if prev["result_path"] or prev["state"] in _HAD_CLIP:
        out.append(_issue("van_tay", DO, f"gói gửi trùng y lần gen trước (job {prev['id']}) — gen lại phải đổi đầu vào (N10): sửa "
                                         "motion prompt / ảnh khung đầu / tham chiếu / model, hoặc ghi câu sửa khi bấm gen lại"))
    else:
        out.append(_issue("van_tay", VANG, f"gửi lại y gói của job {prev['id']} (lần đó hỏng ở nhà cung cấp, chưa có clip)"))


# ---- (1) khung đầu = ảnh ĐÃ DUYỆT hiện hành của chính shot ----------------------------------------------------------------------
def _ref_sha(pkg: Any, param: str) -> Optional[str]:
    for r in (pkg or {}).get("refs") or [] if isinstance(pkg, dict) else []:
        if isinstance(r, dict) and r.get("param") == param:
            return r.get("sha256")
    return None


def _sha_file(path: str) -> Optional[str]:
    from .sent_package import sha256_of
    try:
        return sha256_of(path)
    except OSError:
        return None


def _readable_image(path: str) -> bool:
    from PIL import Image
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True
    except Exception:  # noqa: BLE001 - PIL ném cả SyntaxError (PNG hỏng checksum), struct.error, DecompressionBombError: đều = không đọc được
        return False


def _approved_at(conn, job_id: int) -> Optional[float]:
    row = conn.execute("SELECT at FROM job_events WHERE job_id=? AND to_state='approved' ORDER BY id DESC LIMIT 1", (job_id,)).fetchone()
    if row is None or not row["at"]:
        return None
    import datetime
    try:
        return datetime.datetime.fromisoformat(str(row["at"])).timestamp()
    except ValueError:
        return None


def _check_start(conn, scene_id: int, plan: Dict, out: List[Dict]) -> None:
    from . import shots
    path = plan.get("start_frame")
    path_needed = plan.get("reference_only") is None    # Seedance chỉ-ảnh-tham-chiếu: khung đầu KHÔNG gửi (ảnh từng shot ở mục 4)
    if path and os.path.basename(os.path.dirname(str(path))) == "chain":      # bắt đầu từ khung cuối clip trước ĐÃ DUYỆT (_chain_frame)
        if not _readable_image(str(path)):
            out.append(_issue("khung_dau", DO, f"không đọc được khung đầu cắt từ clip trước ({_rel(path)})"))
        return
    img_scene = shots.image_scene(conn, scene_id)
    row = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                       (img_scene,)).fetchone()
    if row is None:
        out.append(_issue("khung_dau", DO, "shot chưa có ảnh khung đầu ĐÃ DUYỆT (ảnh bị bỏ duyệt / chưa duyệt) — duyệt ảnh ở Bước 2"))
        return
    if not path:
        if path_needed:
            out.append(_issue("khung_dau", DO, "gói gửi không có ảnh khung đầu"))
        return
    m = re.fullmatch(r"job_(\d+)\.png", os.path.basename(str(path)))
    if not m or int(m.group(1)) != row["id"]:
        out.append(_issue("khung_dau", DO, f"khung đầu sắp gửi ({os.path.basename(str(path))}) không phải ảnh ĐÃ DUYỆT hiện hành của shot "
                                           f"(job {row['id']}) — ảnh đã bị thay"))
        return
    if not os.path.isfile(str(path)) or (path_needed and not _readable_image(str(path))):
        out.append(_issue("khung_dau", DO, f"không đọc được tệp ảnh khung đầu đã duyệt ({_rel(path)})"))
        return
    sha = _ref_sha(plan.get("package"), "image_path") or _sha_file(str(path))
    if not sha:
        out.append(_issue("khung_dau", DO, f"không tính được sha của ảnh khung đầu ({_rel(path)})"))
        return
    rel = _rel(path)
    for prev in conn.execute("SELECT id, sent_package FROM jobs WHERE scene_id=? AND type='video_gen' AND id<>? AND sent_package IS "
                             "NOT NULL ORDER BY id DESC", (scene_id, plan.get("job_id") or -1)).fetchall():
        try:
            refs = (json.loads(prev["sent_package"]) or {}).get("refs") or []
        except (TypeError, ValueError):
            continue
        for r in refs:
            if (isinstance(r, dict) and r.get("param") == "image_path" and r.get("path") == rel and r.get("sha256")
                    and r["sha256"] != sha):
                out.append(_issue("khung_dau", DO, f"tệp ảnh khung đầu job {row['id']} đã bị thay sau lần gửi job {prev['id']} (sha khác) "
                                                   "mà không duyệt lại — duyệt lại ảnh ở Bước 2"))
                return
    at = _approved_at(conn, row["id"])
    try:
        mtime = os.path.getmtime(str(path))
    except OSError:
        mtime = None
    if at is not None and mtime is not None and mtime > at + _MTIME_SLACK_S:
        out.append(_issue("khung_dau", VANG, f"tệp ảnh khung đầu job {row['id']} được ghi lại SAU lúc duyệt — kiểm lại ảnh trước khi "
                                             "tin clip"))


# ---- (2) khung cuối đã duyệt + khớp ket_thuc BYĐ ----------------------------------------------------------------------------------
def _byd(data: Dict) -> Optional[Dict]:
    b = data.get("byd")
    return b if isinstance(b, dict) else None


def _changes(byd: Dict) -> Optional[bool]:
    """True = BYĐ khai trạng thái cuối khác đầu (có ai đổi), False = có khai ket_thuc nhưng y hệt bat_dau, None = không khai ket_thuc."""
    ends = [(h.get("bat_dau"), h.get("ket_thuc")) for h in byd.get("hanh_dong") or [] if isinstance(h, dict) and h.get("ket_thuc")]
    if not ends:
        return None
    return any(a != b for a, b in ends)


def _check_end(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    from . import end_frames, shots
    lf = plan.get("last_frame")
    byd = _byd(data)
    in_place = _in_place(conn, scene_id, plan, data)
    if not lf:
        if in_place and end_frames.enabled() and not plan.get("group_ids") and end_frames.usable_path(conn, scene_id):
            out.append(_issue("khung_cuoi", VANG, f"{in_place} — không gửi khung cuối vẽ (cờ locomotion_end_frame)"))
        elif byd is not None and _changes(byd) and end_frames.enabled() and not plan.get("group_ids"):
            out.append(_issue("khung_cuoi", VANG, "BYĐ khai trạng thái cuối khác đầu nhưng clip gửi không kèm khung cuối"))
        return
    lf = str(lf)
    nxt = shots.last_frame_for(conn, plan.get("data_dir") or "", scene_id)          # shot nối tiếp: kết ở ảnh duyệt của shot sau
    drawn = end_frames.usable_path(conn, scene_id)                                  # K1: khung cuối vẽ từ ảnh khung đầu hiện hành
    same = lambda a, b: bool(a) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))  # noqa: E731
    if in_place and same(drawn, lf) and not same(nxt, lf):
        out.append(_issue("khung_cuoi", VANG, f"{in_place} — nên bỏ khung cuối vẽ, thêm câu mốc cảnh vật"))
    if not (same(nxt, lf) or same(drawn, lf)):
        row = end_frames.current(conn, scene_id)
        why = ("chưa có khung cuối" if row is None else
               f"khung cuối đang ở trạng thái '{row['state']}'" if row["state"] != "ready" else
               "khung cuối vẽ từ ảnh khung đầu cũ" if not end_frames.usable_path(conn, scene_id) else "tệp gửi không phải khung cuối hiện hành")
        out.append(_issue("khung_cuoi", DO, f"khung cuối sắp gửi ({_rel(lf)}) chưa được duyệt / không còn hiện hành ({why})"))
        return
    if not _readable_image(lf):
        out.append(_issue("khung_cuoi", DO, f"không đọc được tệp khung cuối ({_rel(lf)})"))
        return
    _check_end_distance(conn, scene_id, plan, lf, out)
    if byd is None:
        return                                       # VÀNG "chưa có BYĐ" nói một lần ở _check_motion
    ch = _changes(byd)
    if ch is None:
        out.append(_issue("khung_cuoi", VANG, "BYĐ không khai `ket_thuc` — không đối chiếu được khung cuối với trạng thái cuối"))
    elif ch is False and not same(nxt, lf):
        out.append(_issue("khung_cuoi", DO, "BYĐ khai trạng thái cuối = trạng thái đầu (không đổi) mà clip gửi kèm khung cuối vẽ trạng "
                                            "thái khác — sửa BYĐ hoặc bỏ khung cuối"))


def _check_end_distance(conn, scene_id: int, plan: Dict, lf: str, out: List[Dict]) -> None:
    """Cờ framing_guard (lỗi hệ thống 2): khung cuối khác khoảng cách máy với ảnh đầu → VÀNG có số đo (runner._end_frame đã bỏ khung
    đó; tới đây là đường khác gửi kèm). Không đo được → VÀNG nói rõ."""
    from . import framing_guard, shots
    if not framing_guard.enabled():
        return
    start = plan.get("start_frame") or shots.approved_image_path(conn, plan.get("data_dir") or "", plan.get("project_id") or 0,
                                                                  shots.image_scene(conn, scene_id))
    res = framing_guard.end_frame_check(str(start) if start else None, lf)
    if res and res.get("ok") is False:
        out.append(_issue("khung_cuoi", VANG, f"{res['why']} — nên bỏ khung cuối này hoặc vẽ lại cùng khoảng cách máy (cờ framing_guard)"))
    elif res and res.get("ok") is None:
        out.append(_issue("khung_cuoi", VANG, f"chưa đo được khoảng cách máy của khung cuối: {res.get('note')}"))


def _in_place(conn, scene_id: int, plan: Dict, data: Dict) -> Optional[str]:
    """Cờ locomotion_end_frame (hộp thư 12/10 18:13): cùng luật với runner._runs_in_place — shot chạy/đi sinh dài hơn shot × 1,3."""
    from . import features, motion_physics
    from .adapters.clipai import effective_duration
    if not features.on(motion_physics.LOCOMOTION_FLAG) or plan.get("group_ids"):
        return None
    canonical, family = _model(plan)
    if canonical is None:
        return None
    mp = conn.execute("SELECT duration_sec FROM motion_prompts WHERE scene_id=? AND state='approved'", (scene_id,)).fetchone()
    try:
        secs = float((mp["duration_sec"] if mp is not None and mp["duration_sec"] else None) or data.get("duration_s") or 0)
        sent = float(plan.get("duration") or 0)
    except (TypeError, ValueError):
        return None
    if secs <= 0 or sent <= 0:
        return None
    return motion_physics.in_place_risk(data, secs, effective_duration(canonical, family, sent))


# ---- (3) thời lượng hợp model + khớp thoại -----------------------------------------------------------------------------------------
def _model(plan: Dict):
    from .adapters.clipai import resolve_model
    from .providers import ProviderError
    try:
        return resolve_model(plan.get("model"))
    except (ProviderError, AttributeError):
        return None, None


def _real_voice(conn, scene_id: int, plan: Dict) -> Optional[float]:
    """15/10: giây clip cần cho giọng THẬT của shot (đầu clip voice._lead + các câu + khoảng giữa, như voice.layout đặt) khi mọi câu
    của shot đã có giọng; None = chưa đủ giọng (dùng ước tính) / thiếu dự án hay thư mục."""
    from . import voice
    pid, data_dir = plan.get("project_id"), plan.get("data_dir")
    if not pid or not data_dir:
        return None
    secs = voice.scene_seconds(conn, int(pid), str(data_dir)).get(scene_id)
    return None if secs is None else round(voice._lead(conn, scene_id) + float(secs), 2)


def _check_duration(conn, scene_id: int, plan: Dict, data: Dict, out: List[Dict]) -> None:
    from . import dialogue, ffmpeg_studio, video_rules
    from .adapters.clipai import effective_duration
    canonical, family = _model(plan)
    if canonical is None:
        out.append(_issue("thoi_luong", VANG, f"model '{plan.get('model')}' không có trong bảng luật — không kiểm thời lượng / tham chiếu"))
        return
    try:
        dur = float(plan.get("duration") or 0)
    except (TypeError, ValueError):
        out.append(_issue("thoi_luong", DO, f"thời lượng gửi không đọc được ({plan.get('duration')!r})"))
        return
    if dur <= 0:
        out.append(_issue("thoi_luong", DO, "thời lượng gửi = 0 s"))
        return
    if plan.get("from_sample"):
        return                                       # N1: bản cao nâng từ nháp — độ dài + model là của nháp (đã kiểm khi gửi nháp)
    rule = video_rules.rule(canonical)
    span = rule.get("duration") or {}
    eff = effective_duration(canonical, family, dur)
    top = span.get("max")
    if top and dur > float(top) + 0.5:
        out.append(_issue("thoi_luong", DO, f"shot cần {dur:g} s nhưng {rule.get('label') or canonical} chỉ làm tối đa {top:g} s — clip "
                                            "sẽ bị cắt ngắn: chia shot hoặc đổi model"))
    for p in video_rules.problems(canonical, dur, resolution=plan.get("resolution") if family == "seedance" else None,
                                  kling_mode=plan.get("kling_mode") if family == "omni" else None,
                                  reference_video=bool(plan.get("reference_video")), with_audio=bool(plan.get("with_audio")),
                                  last_frame=bool(plan.get("last_frame")), audios=len(plan.get("reference_audio") or [])):
        out.append(_issue("thoi_luong", DO, p))
    if plan.get("group_ids"):
        return                                       # clip nhóm: thoại theo từng shot do dialogue_take / seedance_refs lo
    lines = dialogue.scene_lines(data)
    if not lines:
        return
    audio = list(plan.get("reference_audio") or [])
    if audio:
        got = ffmpeg_studio.probe_duration(str(audio[0])) if os.path.isfile(str(audio[0])) else None
        if got is None:
            out.append(_issue("thoi_luong", DO, f"không đo được độ dài giọng gửi kèm ({_rel(audio[0])})"))
        elif got > eff + 0.05:
            out.append(_issue("thoi_luong", DO, f"giọng thoại dài {got:.1f} s, clip chỉ {eff} s — thoại bị cắt: tăng thời lượng / chia shot"))
        return
    real = _real_voice(conn, scene_id, plan)
    if real is not None:                             # 15/10: giọng thật đã có → so bằng độ dài thật, không bằng ước tính
        if real > eff + 0.05:
            out.append(_issue("thoi_luong", DO, f"giọng thật của shot cần {real:.1f} s (đầu clip + các câu), clip chỉ {eff} s — câu "
                                                "bị cắt: ⏱ Đặt thời lượng clip theo giọng thật (Bước 3) hoặc chia shot"))
        return
    need = dialogue.needed_seconds(lines, dialogue.speech_ctx(conn, int(plan.get("project_id") or 0)))
    if need > eff:
        out.append(_issue("thoi_luong", VANG, f"thoại ước cần ~{need:g} s, clip {eff} s (ước theo số âm tiết, chưa có giọng thật)"))


# ---- (4) ảnh / video tham chiếu theo luật model --------------------------------------------------------------------------------
def _videos(plan: Dict) -> List[Dict]:
    rv = plan.get("reference_video")
    items = rv if isinstance(rv, list) else ([rv] if rv else [])
    return [v if isinstance(v, dict) else {"path": v} for v in items]


def _check_refs(conn, scene_id: int, plan: Dict, out: List[Dict]) -> None:
    from . import video_rules
    from .adapters import clipai
    canonical, family = _model(plan)
    if canonical is None or plan.get("from_sample"):
        return
    rule = video_rules.rule(canonical)
    videos = _videos(plan)
    if videos:
        infos = []
        for v in videos:
            path = str(v.get("path") or "")
            if not path or not os.path.isfile(path):
                out.append(_issue("tham_chieu", DO, f"không đọc được video tham chiếu ({_rel(path)})"))
                continue
            info = clipai._probe_video(path)                 # ffprobe: chỉ siêu dữ liệu, không đọc cả tệp
            if not info.get("width") or info.get("duration") is None:
                out.append(_issue("tham_chieu", DO, f"không đo được video tham chiếu bằng ffprobe ({_rel(path)}) — không biết có đạt luật "
                                                    "model không"))
                continue
            infos.append(info)
        for p in clipai.reference_video_problems(family, canonical, infos):
            out.append(_issue("tham_chieu", DO, p))
    ro = plan.get("reference_only")
    if ro is not None:
        n, cap = len(ro or []) + (1 if plan.get("last_frame") else 0), rule.get("max_images")   # the end frame goes as one more picture
        what = "ảnh tham chiếu (chỉ-ảnh-tham-chiếu, kể cả khung cuối)"
    elif family == "seedance":
        extra = (len(plan.get("image_references") or []) + len(plan.get("subjects") or [])) if clipai.SEEDANCE_REFS_WITH_FIRST_FRAME else 0
        n, cap = 1 + extra, rule.get("max_images")
        what = "ảnh (khung đầu + tham chiếu)"
    else:
        n = len(plan.get("image_references") or []) if plan.get("kling_image_refs") else 0
        cap = rule.get("max_refs_with_reference_video") if videos else rule.get("max_refs")
        what = "ảnh tham chiếu"
    if cap and n > int(cap):
        out.append(_issue("tham_chieu", DO, f"{n} {what} — {rule.get('label') or canonical} nhận tối đa {cap}"
                                            + (" khi có video tham chiếu" if videos and family == "omni" else "")))
    _check_roles(plan, family, out)
    images = list(plan.get("reference_only") or [])
    if plan.get("reference_only") is None and family == "seedance" and clipai.SEEDANCE_REFS_WITH_FIRST_FRAME:
        images += list(plan.get("image_references") or [])
    for image in images:
        path = (image.get("path") or image.get("file")) if isinstance(image, dict) else image
        if path and not str(path).startswith(("http://", "https://", "asset://")) and not _readable_image(str(path)):
            out.append(_issue("tham_chieu", DO, f"không đọc được ảnh tham chiếu ({_rel(path)}) — tệp mất / ảnh hỏng"))
    # rà video #27 (12/10): KAPELLA 220×394 and a 0.38-wide picture passed here and ClipAI's adapter refused them AT SEND → the job
    # failed instead of waiting with a reason. The same rule as the adapter (clipai.reference_image_problems on the local reference-only
    # pictures + the end frame sent as one more), measured on the same files. A picture the runner is about to host in the Subject
    # Library (plan["hosted_pending"], flag seedance_subjects) goes as asset://… which the adapter does not measure → VÀNG, not held.
    if plan.get("reference_only") is not None and family == "seedance":
        local = [r for r in plan.get("reference_only") or [] if not isinstance(r, dict)]
        if plan.get("last_frame"):
            local.append(plan["last_frame"])
        hosted = {os.path.normcase(os.path.abspath(str(x))) for x in plan.get("hosted_pending") or []}
        for k, path in enumerate(local, 1):
            if str(path).startswith(("http://", "https://", "asset://")):
                continue
            size = _image_size(str(path))
            if not size:                                 # unreadable: said above
                continue
            for p in clipai.reference_image_problems(family, [size]):
                maybe = os.path.normcase(os.path.abspath(str(path))) in hosted
                out.append(_issue("tham_chieu", VANG if maybe else DO,
                                  f"ảnh tham chiếu {k} không đạt luật ClipAI: {p.replace('ảnh 1 ', '')} — {_rel(path)} ("
                                  + ("gửi qua Kho chủ thể; nếu Kho không nhận thì ClipAI từ chối lúc gửi" if maybe else
                                     "ClipAI sẽ từ chối lúc gửi") + "; đổi ảnh Kho cạnh ≥ 300 px, tỉ lệ rộng/cao 0,4–2,5)"))


def _image_size(path: str):
    from PIL import Image
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:  # noqa: BLE001 - unreadable: _readable_image says it
        return None


def _check_roles(plan: Dict, family: str, out: List[Dict]) -> None:
    """Seedance: mỗi tài sản một vai (tài liệu Seedance 2.5 — docs/NGHIEN_CUU_PROMPT_THAM_CHIEU_2026-09-30.md). Chỉ tính thứ THẬT gửi:
    chỉ-ảnh-tham-chiếu thì khung đầu không gửi; có khung đầu thì ảnh tham chiếu không đi kèm (clipai.SEEDANCE_REFS_WITH_FIRST_FRAME)."""
    from .adapters import clipai
    pkg = plan.get("package")
    if family != "seedance" or not isinstance(pkg, dict):
        return
    # rà video #27 (12/10): reference-only sends neither the first frame nor image_references / references (adapter clipai.submit:
    # only `reference_only` + the end frame) — counting them held 4 groups for a "2 roles" that never goes out
    skip = {"image_path", "image_references", "references"} if plan.get("reference_only") is not None else (
        set() if clipai.SEEDANCE_REFS_WITH_FIRST_FRAME else {"image_references", "references"})
    roles: Dict[str, set] = {}
    shown: Dict[str, str] = {}
    for r in pkg.get("refs") or []:
        if not isinstance(r, dict) or r.get("param") in skip:
            continue
        if not r.get("sha256") and not r.get("url"):
            out.append(_issue("tham_chieu", DO, f"không đọc được tệp tham chiếu {r.get('path')} (vai {r.get('role')})"))
            continue
        key = r.get("sha256") or r.get("path")
        roles.setdefault(key, set()).add(str(r.get("role") or r.get("param")))
        shown.setdefault(key, str(r.get("file") or r.get("path")))
    for key, rs in roles.items():
        if len(rs) > 1:
            out.append(_issue("tham_chieu", DO, f"Seedance: tài sản {shown[key]} được gửi với {len(rs)} vai ({', '.join(sorted(rs))}) — "
                                                "mỗi tài sản một vai"))


# ---- (5) motion đủ đầu–đỉnh–cuối + chuyển động máy thuộc enum -------------------------------------------------------------------
def _check_motion(conn, scene_id: int, plan: Dict, out: List[Dict]) -> None:
    from . import shot_intent
    ids = list(plan.get("group_ids") or []) or [scene_id]
    many = len(ids) > 1
    missing = []
    for sid in ids:
        byd = _byd(_data(conn, sid))
        tag = _tag(conn, sid, many)
        if byd is None:
            missing.append(tag.rstrip(": ") or "shot")
            continue
        if shot_intent.is_draft(byd):                  # M2.4 (insert_inherit): shot chèn — BYĐ chép nháp, chưa duyệt; chưa kiểm được nhịp / máy
            src = conn.execute("SELECT idx FROM scenes WHERE id=?", (byd["_p"].get("from"),)).fetchone()
            out.append(_issue("byd_draft", VANG, f"{tag}BYĐ nháp" + (f" từ shot {src['idx']}" if src else "")
                              + " (shot chèn) — duyệt / điền hành động + máy ở Bước 3; chưa kiểm được nhịp đầu–đỉnh–cuối, chuyển động máy"))
            continue
        may = byd.get("may") if isinstance(byd.get("may"), dict) else {}
        if may.get("chuyen_dong") in (None, ""):
            out.append(_issue("chuyen_dong", DO, f"{tag}BYĐ thiếu chuyển động máy (may.chuyen_dong: một trong "
                                                 f"{', '.join(shot_intent.CHUYEN_DONG)})"))
        else:
            for i in shot_intent.validate({"may": may}):
                if str(i.get("truong", "")).startswith("may.chuyen_dong"):
                    out.append(_issue("chuyen_dong", DO, f"{tag}chuyển động máy: {i['loi']}"))
        for k, h in enumerate(byd.get("hanh_dong") or []):
            if not isinstance(h, dict):
                continue
            who = h.get("ai") or f"hanh_dong[{k}]"
            if not h.get("bat_dau"):
                out.append(_issue("chuyen_dong", DO, f"{tag}{who}: thiếu nhịp đầu (bat_dau)"))
                continue
            # Một tư thế (cả khi ghi nhịp sau cùng tư thế) = đạt. Đổi tư thế mà thiếu một nhịp → VÀNG, vẫn gửi (người dùng 14/10: điều
            # phải đúng là TƯ THẾ theo kịch bản, không phải số nhịp; prompts/31_director_byd.md cho `dinh` tùy chọn — #29 shot 5 dung→ngoi).
            lack = shot_intent.missing_beat(h)
            if lack:
                lack = "đỉnh (dinh)" if lack == "dinh" else "cuối (ket_thuc)"
                out.append(_issue("chuyen_dong", VANG, f"{tag}{who}: hành động đổi tư thế nhưng không ghi nhịp {lack} — model tự nối "
                                                       "đầu→cuối; kiểm tư thế đầu/cuối đúng kịch bản"))
    if missing:
        out.append(_issue("byd", VANG, "chưa có BYĐ" + (f" ({', '.join(missing)})" if many else "")
                          + " — chưa kiểm được nhịp đầu–đỉnh–cuối, chuyển động máy, khung cuối"))


# ---- cổng --------------------------------------------------------------------------------------------------------------------------
def check(conn, scene_id: int, plan: Dict) -> List[Dict[str, str]]:
    """Mọi lỗi của lần gửi video `plan` cho shot `scene_id` (rỗng = đạt). Không gọi mạng, không tốn tiền."""
    out: List[Dict[str, str]] = []
    data = _data(conn, scene_id)
    _check_start(conn, scene_id, plan, out)
    _check_end(conn, scene_id, plan, data, out)
    _check_duration(conn, scene_id, plan, data, out)
    _check_refs(conn, scene_id, plan, out)
    _check_motion(conn, scene_id, plan, out)
    _check_fingerprint(conn, scene_id, plan, out)
    return out


def plan_of(job, args, kwargs: Dict, package: Optional[str], data_dir: str, group_ids=None) -> Dict:
    """Dạng `plan` từ đúng args / kwargs mà runner sắp đưa provider.submit (VideoRunner._submit_args / _submit_kwargs)."""
    args = tuple(args or ())
    at = lambda i: args[i] if len(args) > i else None  # noqa: E731
    kw = dict(kwargs or {})
    try:
        pkg = json.loads(package) if package else None
    except (TypeError, ValueError):
        pkg = None
    return {"job_id": job["id"], "project_id": job["project_id"], "data_dir": data_dir,
            "start_frame": at(0), "prompt": at(1), "duration": at(3), "model": at(4), "with_audio": bool(at(5)),
            "subjects": at(6) or kw.get("subjects"), "image_references": at(7) or kw.get("image_references"),
            "reference_video": at(8) or kw.get("reference_video"), "last_frame": kw.get("_last_frame_source") or kw.get("last_frame"),   # 11/10: a reference-only send carries a marked copy of the drawn end frame
            "reference_only": kw.get("reference_only"), "reference_audio": kw.get("reference_audio"),
            "resolution": None if kw.get("high_res_sample") else ("480p" if kw.get("draft") else kw.get("resolution")), "kling_mode": kw.get("kling_mode"),
            "kling_image_refs": bool(kw.get("kling_image_refs")), "from_sample": kw.get("_from_sample"),
            "group_ids": list(group_ids or []), "package": pkg}


def summary(issues: List[Dict]) -> str:
    """Một dòng tiếng Việt cho ⚙ Chẩn đoán / lý do giữ."""
    return " · ".join(i["ly_do"] for i in issues)
