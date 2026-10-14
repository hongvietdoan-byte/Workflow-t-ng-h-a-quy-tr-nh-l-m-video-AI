"""Đ11v4: QC số local, chỉ đọc. Cỡ đo là cỡ MẶT, không giả cỡ toàn thân.

Đầu/cuối clip đọc bằng seek, không nạp cả video. Không tải model/URL/UNC.
Ngưỡng chưa hiệu chỉnh; khớp số không chứng minh toàn bộ ảnh đạt.
"""
import math
import os
from pathlib import Path

from . import features, plate_camera


def _issue(text):
    return {"muc": "vang", "loi": text, "de_xuat": "Đổi đầu vào (máy/ảnh bố cục/prompt) rồi dùng nút gen lại có báo giá; không tự gen"}


def compare(measured, expected):
    out = []
    for key, label, threshold in (("face_height", "cỡ mặt", .08), ("eyes", "vị trí/độ cao mắt", .08), ("horizon", "chân trời", .08)):
        a, b = measured.get(key), expected.get(key)
        if a is None or b is None:
            out.append(_issue(f"không đo được {label} để so với máy — VÀNG, ngưỡng chưa hiệu chỉnh"))
            continue
        try:
            values_a = list(a) if isinstance(a, (tuple, list)) else [a]
            values_b = list(b) if isinstance(b, (tuple, list)) else [b]
            if len(values_a) != len(values_b) or not all(math.isfinite(float(v)) for v in values_a + values_b):
                raise ValueError
            if max(abs(x - y) for x, y in zip(values_a, values_b)) > threshold:
                out.append(_issue(f"{label} lệch máy > {threshold:.0%} khung — ngưỡng chưa hiệu chỉnh"))
        except (TypeError, ValueError):
            out.append(_issue(f"không đo được {label}: số không hợp lệ — ngưỡng chưa hiệu chỉnh"))
    for issue in out:
        issue.update(measured=dict(measured), expected=dict(expected))
    return out


def expected(camera, actor=None, aspect=9 / 16):
    out = {}
    try:
        args = camera["location"], camera["look_at"], float(camera["lens"]), aspect
        out["horizon"] = plate_camera.horizon_y(*args)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return {}
    try:
        if isinstance(actor, dict) and actor:
            xy, z, h = actor["xy"], float(actor["z"]), float(actor["H"])
            eyes = plate_camera.project(*args, [xy[0], xy[1], z + h * .93])
            top = plate_camera.project(*args, [xy[0], xy[1], z + h])
            chin = plate_camera.project(*args, [xy[0], xy[1], z + h * .86])
            out.update(eyes=eyes, face_height=abs(chin[1] - top[1]) if chin and top else None)
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        pass
    return out


def _local(path):
    raw = str(path or "")
    return bool(raw and not raw.startswith(("\\\\", "//")) and "://" not in raw and Path(raw).is_file())


def _measure(frame):
    from . import clip_measure, plate_layout_qc
    cv = clip_measure._cv()
    height, width = frame.shape[:2]
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY).astype(float) / 255
    out = {"horizon": plate_layout_qc.horizon_row(gray, plate_layout_qc._mask(gray.shape, None))}
    from . import text_placement
    # Chặn UNC/URL trước model_path (hàm đó kiểm exists, có thể chạm mạng).
    model = os.environ.get("FACE_MODEL") or text_placement.FACE_MODEL
    faces = clip_measure._faces(frame) if _local(model) else []
    # Chưa có nhận dạng: nhiều mặt không được gán bừa cho chủ thể.
    if len(faces) == 1:
        _, _, _, fh, points = faces[0]
        out.update(face_height=fh / height, eyes=[sum(p[0] for p in points[:2]) / (2 * width), sum(p[1] for p in points[:2]) / (2 * height)])
    return out


def _subject_warnings(actor):
    # Detector chỉ tìm mặt, chưa nhận dạng ID: một mặt cũng không chứng minh đúng người.
    text = "chưa xác minh danh tính chủ thể bằng công cụ local; số mặt/mắt không chứng minh đúng ID"
    if not isinstance(actor, dict) or not actor:
        text += "; thiếu trạng thái chủ thể đã duyệt hoặc trạng thái không hợp lệ để so cỡ mặt/vị trí mắt"
    elif not actor.get("id"):
        text += "; thiếu ID chủ thể đã duyệt; số hình học chỉ là tham khảo chưa gắn danh tính"
    return [dict(_issue(text), code="subject_identity_unverified")]



def check_image(path, camera, actor=None, aspect=9 / 16):
    if not features.on("camera_match_qc"):
        return []
    target = expected(camera, actor, aspect)
    measured = {}
    if _local(path):
        try:
            from . import clip_measure
            frame = clip_measure._cv().imread(str(path))
            if frame is not None:
                measured = _measure(frame)
        except Exception:  # Công cụ/model local thiếu: không gọi API thay thế.
            pass
    issues = compare(measured, target) + _subject_warnings(actor)
    for issue in issues:
        issue.update(measured=dict(measured), expected=dict(target))
    return issues


def check_clip(path, camera, actor=None, aspect=9 / 16, end_actor=None):
    if not features.on("camera_match_qc"):
        return []
    out, cap = [], None
    try:
        if not _local(path):
            raise ValueError
        from . import clip_measure
        cv = clip_measure._cv()
        cap = cv.VideoCapture(str(path))
        count = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
        if count < 1:
            raise ValueError
        for label, index in (("đầu", 0), ("cuối", count - 1)):
            sought = cap.set(cv.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read() if sought else (False, None)
            target = camera
            if label == "cuối" and camera.get("move"):
                # Máy di chuyển: không so khung cuối với máy đầu nếu thiếu máy cuối.
                target = camera.get("end_camera") or {}
            state = actor if label == "đầu" else end_actor
            subject_issues = _subject_warnings(state)
            if label == "cuối" and isinstance(actor, dict) and isinstance(end_actor, dict):
                start_id, end_id = actor.get("id"), end_actor.get("id")
                if start_id is not None and end_id is not None and start_id != end_id:
                    state = None
                    subject_issues.append(_issue("ID chủ thể đầu/cuối không khớp; không so mắt/cỡ mặt của hai người khác nhau"))
            measured = _measure(frame) if ok else {}
            projected = expected(target, state, aspect)
            issues = compare(measured, projected) + subject_issues
            for issue in issues:
                issue.update(measured=dict(measured), expected=dict(projected))
            out.extend(dict(i, loi=f"Khung {label}: {i['loi']}") for i in issues)
    except Exception:
        out.append(_issue("không đo được khung đầu/cuối clip bằng công cụ local"))
    finally:
        if cap is not None:
            cap.release()
    return out
