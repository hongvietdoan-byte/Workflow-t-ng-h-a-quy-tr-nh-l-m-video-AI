# HANDOFF — Khóa đạo cụ dự án (cờ `project_prop_lock`, lỗi #27 12/10)

## Xong
- `core/prop_lock.py` (mới): xếp món Kho weapon/prop đã gắn dự án theo loại (súng / tường keo); shot chỉ nói từ chung (ranh giới từ,
  giữ dấu: "kéo" ≠ "keo") → câu "Prop lock" nêu tên + mô tả từ `assets.description` (bỏ nhãn nguồn `[..]`); nhiều món cùng loại → VÀNG
  phần `dao_cu`, không đoán. Dạng: đoạn "(a) MẶC ĐỊNH …; (b) skin …" trong mô tả; ảnh có `asset_images.variant` chỉ gửi khi chữ shot
  nhắc variant (vd "Gloowall"/"OB55"), không nhắc → dạng mặc định, không gửi ảnh skin.
- `core/runner.py` `build_image_prompt`: phần `_prop_part` sau phần hành động (cờ tắt → "" → prompt giữ nguyên từng byte).
- `core/assets.py` `scene_references`: món bị khóa vào ảnh tham chiếu (role object); món weapon/prop có tên → chọn ảnh theo variant.
- `core/prompt_formula.py`: `_prop_issues` vào `formula_check["image"]` (after_director + on_prompt_saved); nhãn "Đạo cụ dự án".
- `core/features.py`: cờ `project_prop_lock` (verified False). `devsys/areas.json`: thêm file + test (không tăng version).
- Test `tests/test_prop_lock.py` 8 test đỏ → xanh; chạy kèm 8 file test liên quan: 188 passed.

## Dở / rủi ro
- Chưa chạy thật (cờ tắt). Bật cờ rồi gen lại 1 shot rẻ của #27 (shot 1 "assault rifle", 1 shot tường keo) để có bằng chứng.
- Chỉ prompt ẢNH; motion prompt video chưa khóa đạo cụ.
- Từ chung "weapon" xếp vào loại súng; dự án có vũ khí cận chiến/lựu đạn khác loại súng chưa có loại riêng.

## Bước kế
- Phiên chính: rà theo quy ước 7 (`py tools/related_areas.py`), gộp vào main, cập nhật TODO.
