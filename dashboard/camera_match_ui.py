"""QC số ngay ảnh/clip đang xem, không nút gen mới, không gửi job."""
import json

import streamlit as st

from core import camera_match_qc, cost, features, image_models, location_pack


def render(p, pid, scene_id, path, kind="image"):
    if not features.on("camera_match_qc"):
        return
    try:
        from dashboard import common as C
        # Tệp sinh ra ở bản chính do caller truyền; chỉ đọc, không ghi đo vào dữ liệu.
        rec = location_pack.plate_of(C.DATA, pid, scene_id) or {}
        row = p.conn.execute("SELECT data FROM scenes WHERE id=? AND project_id=?", (scene_id, pid)).fetchone()
        data = json.loads(row["data"] or "{}") if row else {}
        camera = data.get("stage_camera") or rec.get("camera_plan") or {}
        if scene_id in location_pack.stale_plates(p.conn, pid, C.DATA):
            rec = {}
            camera = data.get("stage_camera") or {}
        if data.get("stage_camera") and any(camera.get(k) != (rec.get("camera_plan") or {}).get(k) for k in ("location", "look_at", "lens")):
            rec = {}  # Máy mới/ảnh render cũ: không lấy vị trí chủ thể cũ.
        subject = (rec.get("camera_plan") or {}).get("subject") or {}
        actor = None
        chars = data.get("characters") or []
        if len(chars) == 1 and subject.get("name") == chars[0] and subject.get("location") and subject.get("height_m"):
            xyz = subject["location"]
            actor = {"xy": xyz[:2], "z": xyz[2], "H": subject["height_m"]}
        check = camera_match_qc.check_clip if kind == "video" else camera_match_qc.check_image
        # Chưa có contract snapshot đã duyệt chứa ID/trạng thái cuối.
        # Tên chỉ giúp đọc số hình học, không chứng minh đúng người hay vị trí cuối.
        issues = check(path, camera, actor, end_actor=None) if kind == "video" else check(path, camera, actor)
        if actor:
            note = "Tên chủ thể trong camera_plan chưa xác minh ID; số hình học chỉ tham khảo"
            if kind == "video":
                note += "; thiếu snapshot trạng thái cuối đã duyệt"
            if not any(i.get("code") == "subject_identity_unverified" for i in issues):
                issues.append({"muc": "vang", "loi": note})
        # Ngay khi số khớp cũng không tuyên bố cả ảnh/clip đạt QC.
        with st.expander("📐 So với máy — ngưỡng chưa hiệu chỉnh", expanded=False):
            if issues:
                st.warning(issues[0]["loi"] if len(issues) == 1 else "\n".join("- " + i["loi"] for i in issues))
            if actor and any(i.get("code") == "subject_identity_unverified" for i in issues):
                st.caption(note)
            if issues and issues[0].get("measured") is not None:
                st.caption("Số đo local / dự kiến từ máy (None = chưa đo):")
                st.json({"do": issues[0]["measured"], "may": issues[0]["expected"]})
            if not issues:
                st.caption("Các số đo local trong ngưỡng tạm; cần duyệt hình ảnh.")
            if issues:
                try:
                    tag = cost.video_button_tag(p.conn, [scene_id]) if kind == "video" else cost.image_button_tag(image_models.of_project(p.project(pid)), 1, retake_conn=p.conn)
                except Exception:
                    tag = " — chưa có giá"
                st.caption("Gợi ý: đổi máy/ảnh bố cục/prompt trước khi dùng nút gen lại" + tag)
    except Exception:
        st.warning("Không đo được ảnh/clip theo máy bằng công cụ local — VÀNG; chưa hiệu chỉnh")
