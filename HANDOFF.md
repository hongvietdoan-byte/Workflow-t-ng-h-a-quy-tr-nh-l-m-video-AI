# Bàn giao — thẩm định 5 lỗ hổng #4 + #5 (A18 đo trên #22 + #24, A25) — 10/10

Nhánh: `worktree-agent-a1c3f4ddf9889aceb` (gốc 862e17b). Chưa push. 0 USD (không gọi model; CSDL bản chính chỉ đọc `mode=ro`).

## Đã làm
1. `tools/dryrun_k0b_p24.py` tham số hóa dự án: `--project 24|22` (mặc định 24), cấu hình `PROJECTS`, `project_config(pid)` (dự án lạ →
   SystemExit), ra `data_out/k0b_p<id>/` neo gốc repo. #22 không có shot_specs → `spec_from_scene` (size / angle / characters / blocking,
   ghi `suy_tu_chu`) rồi cùng `shot_intent.from_shot_spec` → `build_byd`. Nhân vật mặc bộ Kho ('MAXIM KL', 'KELLY KL'): khóa = tóc/mặt/mắt
   của nhân vật + món của trang phục 416/417 (`IDENTITY_ITEMS`). Sửa thứ tự `hanh_dong` không ổn định (set → thứ tự thanh_phan).
2. `tools/nhan_bao_nham_a18.py`: bảng GỘP #22 + #24 (`--projects`), cột dự án, số trước/sau lọc từng dự án, chọn 30 mục chia đều (15/15),
   xoay vòng theo shot (`pick`); NGUONG theo A25. Sinh lại `docs/NHAN_BAO_NHAM_A18_2026-10-10.md` (cột người dùng trống).
3. `knowledge/world_rules.json`: +5 luật có phạm vi (vat kho:416/417/419, loai:loi_vao_nha), có nguồn #22/#24.
4. `core/identity_declare.segment`: hòa vị trí → từ đánh dấu dài hơn thắng; hòa hẳn (cùng từ) → mệnh đề thuộc cả hai.
5. Test mới trong `tests/test_identity_declare.py` (+1 ở `tests/test_world_rules.py`).

## Số đo (chạy thật 10/10 trên CSDL chính)
- #22: 9 shot, BYĐ 8/9 hợp lệ (shot 2 không người → ĐỎ 'thanh_phan rỗng', đúng). Bị báo trước → sau lọc: 32 → 26 (thieu 31 → 26,
  thieu_mau 0, sai_mau 0), khong_can 6. Hình học: 0 sự thật (#22 không có stage_camera — summary ghi rõ).
- #24 (chạy lại sau sửa segment): 39 → 35 (thieu 35 → 31, thieu_mau 2, sai_mau 2), khong_can 9.

## Việc mở
- Người dùng gán nhãn 30 mục → tính tỉ lệ báo nhầm theo A25; tổng mục bị báo 61 nên n ≥ 30 đủ.
- Món `khong_nhan_ra` (bomber / quần Maxim, "Hoodie đỏ…" Kho 416) không được kiểm → K1a cần ô `khai_bao_chu`.
- Đoạn "biến hình từ dạng A sang dạng B" (#24 shot 7) vẫn tính cho cả hai dạng.
- Quy ước 7 CLAUDE.md: `py tools/related_areas.py` đã chạy (step1, knowledge, assets gọi identity_declare chỉ qua validate_khai_bao_chu);
  CHƯA có agent rà độc lập — phiên điều phối giao.
