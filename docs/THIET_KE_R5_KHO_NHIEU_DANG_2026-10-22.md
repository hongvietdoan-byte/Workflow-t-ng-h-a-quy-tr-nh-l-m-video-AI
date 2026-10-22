# Gốc R5: một vật trong Kho có nhiều dạng (thiết kế, chưa code) — C-3D-GOC-B, 22/10/2026

Người dùng 22/10 yêu cầu sửa GỐC, sao cho đổi chỗ hay đổi cách dùng vật thì lỗi không quay lại. Gốc R5 (sổ lỗi `V31-GOC5`) gồm 3 lỗi:
- bom keo Kho #367 khai `kind=weapon`, nên sân khấu không dựng được tường keo trên sàn;
- rào mê cung #265 thấp khoảng 1,5 m (G8);
- nền ghép trông như ảnh 3D dán đè (P33-B4).

**Chưa code**, theo đề bài: phải chờ CX21-M23 (Kho forms v1/v2, `codex/v31-m23`, đang làm). Code R5 trước M23 sẽ tạo nguồn song song, trái với luật "giữ liên kết chặt".

## 1. Gốc chung
Kho đang mô tả một vật bằng **một dạng duy nhất**: một `kind`, một mô hình, một chiều cao. Một vật trong game có nhiều dạng theo trạng thái:

| Vật | Dạng | Vai trên sân khấu | Ai đọc |
|---|---|---|---|
| bom keo #367 | cầm tay (vũ khí) | prop cầm, không có khối sàn | Storyboard / VPA (ảnh tay cầm) |
| bom keo #367 | đã triển khai (tường keo) | khối sàn `block` cao ≈ người, chắn đường | 3D Artist (stage_auto / whitebox), Continuity Validator |
| rào #265 | rào mê cung | khối cao đúng **chiều cao thật trong game** (≈ 3 m lá + 1 m đá, theo video in-game người dùng 17/10) | 3D Artist, Quay phim (máy ngang tầm người) |

Vá từng ca (sửa `kind` của #367 thành block, nâng mô hình #265) chỉ đổi lỗi sang ca khác: bom keo trên tay lại thành khối giữa sàn.

## 2. Thiết kế: dạng vật dựa trên forms của M23
- **Dữ liệu (một nguồn):** hồ sơ Kho v2 (`core/kho_profile.py`, CX21-M23) đã có `forms[]` cho nhân vật. Mở rộng `forms[]` cho vật, mỗi dạng gồm:
  ```
  {"id": "trien_khai", "nhan": "tường keo đã triển khai", "stage_shape": {"kind": "block", "size_m": [3.0, 0.6, 1.9]},
   "height_m": 1.9, "khi": ["sau_nem", "trien_khai"], "anh": [asset_image ids], "provenance": {...}}
  ```
  Chiều cao / kích thước đo bằng ảnh Kho đã duyệt hoặc người nhập (USER_LOCKED). AI suy ra thì kèm provenance và không ghi đè số người nhập (D05).
- **Chọn dạng theo shot:** dùng cùng đường `kho_profile.forms_for_shot(conn, pid, scene, chosen)` với nhân vật. Trạng thái lấy từ BYĐ v2 `vat[].trang_thai` (cầm / ném / triển khai) do Director làm chủ. Không đoán từ chữ prompt. Thiếu trạng thái thì báo "khong_ro" (luật 1 CHUAN_XAY_DUNG).
- **Sân khấu (3D Artist):** `stage_auto` / `whitebox` dựng khối từ `stage_shape` của dạng đã chọn, không dựng từ `kind` cố định. Bản đồ cảnh `world_map` ghi `state.dang` của thực thể theo shot (valid_from / valid_to). Bất biến R1 của gói B tự áp vị trí lên dạng mới; không viết kiểm thứ hai.
- **Bất biến R5 (khi code):**
  - `R5-FORM-MISSING`: vật trong BYĐ có trạng thái mà Kho không có dạng tương ứng → KHÔNG RÕ.
  - `R5-SHAPE-SCALE`: chiều cao khối sân khấu khác `height_m` của dạng > 15 % → VÀNG. Cùng thước với R2 `check_framing` (người nộm `height_m`).
  - `R5-COMPOSITE`: nền ghép, nối với P33-B4. Chỉ đo được sau khi có cặp render / ảnh. Để REVIEW, không phán.

## 3. Điều kiện bắt đầu code
1. CX21-M23 gộp main (adapter v1/v2, `forms[]` có provenance, CAS revision).
2. Người dùng duyệt mở rộng `forms[]` cho vật (đổi schema hồ sơ Kho — Cấp 2), và duyệt chiều cao thật của #265 / #367.
3. Sau đó: test đỏ cho 3 bất biến R5 trên ca #367 cầm tay ↔ triển khai và #265, kèm test biến thể (đổi vật, đổi trạng thái theo shot).

Không thêm cờ mới khi CX21-GOLDEN7 chưa xong (luật tạm 22/10).
