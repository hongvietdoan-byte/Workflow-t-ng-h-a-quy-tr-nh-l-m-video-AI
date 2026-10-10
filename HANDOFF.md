# HANDOFF — stage_facts (sự thật hình học một nguồn, 10/10)

Nhánh phụ (worktree agent-a3c43529d54acd716). Chưa push, chưa sửa TODO.md.

## Đã làm
- `core/stage_facts.py`: sổ `FACTS` (top_visible, stand_in, in_frame, pitch_horizon, ref_viewpoint), mỗi loại derive/prompt/observe(+unsure)/judge/contradicts; `for_shot`, `prompt_block`, `contradictions`, `judge`, `horizon`.
- Nơi dùng: `runner.build_image_prompt` (khối "Geometry of this camera…" trước câu chốt chất lượng; `end_frames` dùng vị trí cuối máy), `change_audit` (mục `cau` đỏ + `de_xuat`; `change_review.code_rules` ghi `de_xuat`), `qc_spec` (loại `geometry`, C3, ưu tiên 3, observe `geo`), `qc_rules.observed` (geo → judge), `qc_team` (`schema_for` / `request_line` / GEO_NOTE — không có geo thì yêu cầu y hệt cũ), `qc_scene` (`geometry_block` trong build_request, `apply_geometry` sau validate), `plate_layout_qc` (chân trời giải tích khi render tối), prompt 21 (khóa `geo`).
- Test: `tests/test_stage_facts.py` + ca vàng `tests/fixtures/stage_facts_golden.json` (#24 shot 4, shot 8).
- Docs: `docs/PHUONG_PHAP_SAN_KHAU_3D.md` mục 14. `devsys/areas.json` khai file mới (không tăng version).

## Còn mở
- Chưa chạy `tools/related_areas.py` + agent rà (quy ước 7) — phiên chính làm trước khi merge.
- Chưa kiểm trên CSDL thật: shot 4 #24 sẽ có mục ĐỎ 'cau' ("its dark mouth facing us") → giữ gen tốn tiền shot 4 tới khi sửa câu Director.
- `in_frame` mới cho đạo cụ (stage_camera không chứa tọa độ người).
- Khi `scene_qc_trusted` bật: đỏ hình học biến 'pass' thành 'fix' → vẽ lại (đường cũ của verdict fix).
