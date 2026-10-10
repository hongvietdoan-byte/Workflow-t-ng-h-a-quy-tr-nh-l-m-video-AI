# HANDOFF — K0b phần 2, nhánh B (10/10)

Nhánh `claude/k0b-p2-nhanh-b` (từ e735519). 0 USD, không nối vào luồng gen. Chưa push, chưa sửa TODO.md.

## Đã làm
1. Tư thế: `core/shot_intent.TU_THE` thêm `nga_ngua`, `nam`; prompt 29 dòng 13 thêm tỉ lệ H + liệt kê mã enum (không đổi câu khác);
   `tools/dryrun_k0b_p24.py` suy "fallen back…" → `nga_ngua`, "lying…" → `nam`; ca `p24_shot4_pose_job635` đổi BYĐ/kỳ vọng sang `nga_ngua`.
2. `core/world_rules.py` + `knowledge/world_rules.json` (1 luật chung `ff_xe_khong_bay`). Luật dự án: `<data_dir>/<id>/world_rules.json`
   (neo ROOT, không theo cwd). `load_file/load_project/load_all`, `validate_rule`, `tim` (shot > dự án > chung; kho > loai; ngữ cảnh > *),
   `add` / `remove` (gỡ = đánh dấu, ghi nguyên tử). Chưa nối.
3. Ô `khai_bao_chu` trong `assets.profile` JSON (không migration): `identity_declare.validate_khai_bao_chu`, `declare_from_profile`
   (ưu tiên ô; món chưa có ô → suy + VÀNG nhắc điền), `check` dùng đồng nghĩa món/màu + cách viết dấu hiệu, `color_conflicts` (mô tả Kho ↔
   khai báo lệch màu chính → VÀNG). `assets.set_profile` GIỮ ô khi lưu hồ sơ, gửi ô sai dạng → AssetError. Dryrun đọc ô khi có.
4. Ca hồi quy 11 → 16; test chỉ tiêu K0b trong `tests/test_devsys_stages.py`; README golden thêm khóa `world_rules`, `am_chu`, `dung`.

## Việc mở
- Quy ước 7 (agent rà khâu liên quan) CHƯA chạy trong nhánh này — phiên chính chạy `py tools/related_areas.py` trên diff nhánh.
- `change_review.ASSET_WATCH` chưa có `khai_bao_chu` (đổi ô chưa kích hoạt Tổ rà soát) — cân nhắc ở K1a.
- K1a: điền `khai_bao_chu` cho Kelly #23, yêu nữ #418/#419 (máy chính); sửa mô tả Kho #418 "đai đỏ" theo ảnh mẫu.
- Ca âm/chữ (A1, A4) chưa có lớp chạy (K6); ca `p24_shot4_nga_ngua_job639_dung` dùng `goi` của job 635.
