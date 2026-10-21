# HANDOFF — C-M73 (nhánh cloud/v31-m73, cloud-E nhánh phụ)
- Đã làm: cờ `ref_end_frames` (TẮT mặc định, REQUIRES end_frames + seedance_ref_groups); end_frames.needed/own_clip_reason/
  ref_unsupported_reason; seedance_refs._groups tách shot cần khung cuối + end_split_reason; runner gói `router_khung_cuoi`, VÀNG
  `end_frame_ref_unsupported`, chống gửi đôi khi bật giữa chừng; video_pregen VÀNG khung_cuoi; trainee_ui bỏ ghi chú "không tác dụng".
- Test: tests/test_v31_m73_ref_end_frames.py (đỏ 16 → xanh 17).
- Golden replay (3.14): sửa thứ tự điều kiện _build_package (job golden thiếu scene_id) + ghim `sent_package_relpath: false` (thiếu sẵn từ M2.6) → chỉ còn 3 đỏ môi trường.
- Còn: so nhóm A trước/sau (đang chạy), rà khâu related_areas, báo cáo docs/RA_CLOUD_M73_2026-10-21.md, xóa file này ở commit cuối.
