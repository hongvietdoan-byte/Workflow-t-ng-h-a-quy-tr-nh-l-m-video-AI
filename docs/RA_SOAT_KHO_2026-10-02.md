# Rà soát tổng quát Kho tài nguyên — 02/10/2026

Số liệu máy tính: `py tools/library_audit.py --db D:/AI-Video-Pipeline/data/manifest.sqlite --repo D:/AI-Video-Pipeline` (chỉ đọc, 0 USD; bảng ở
`RA_SOAT_KHO_2026-10-02_so_lieu.md`). Mục tiêu: Kho là đầu vào của khâu chọn ảnh tham chiếu rồi gen ảnh — sai ở đây thì ảnh sinh ra sai theo.

## Tóm tắt
Kho **không hỏng file** (0 file mất, 0 ảnh không đọc được) nhưng **chất lượng dữ liệu để chọn ảnh còn yếu**: 358/407 ảnh nhân vật chưa gắn vai trò,
62/67 hồ sơ nhân vật mới là nháp, chỉ 2/100 địa điểm có ảnh gắn góc máy, và có ảnh KHÔNG phải nhân vật lọt vào nhóm ảnh tham chiếu.

## Phát hiện, theo mức ảnh hưởng

### P0 — ảnh hưởng trực tiếp tới ảnh gen
1. **Ảnh kỹ năng/biểu tượng bị nhập nhầm làm ảnh nhân vật** (từ website ff.garena.com): **CHRONO** (3 ảnh hình lục giác xanh) và **J BIEBS** (5/6 ảnh là
   biểu tượng "EP"). Trước khi sửa, `assets.best_references` chọn chính ảnh 550×800 biểu tượng làm ảnh tham chiếu số 1 của CHRONO (ảnh #956) →
   model sẽ vẽ quả cầu thay vì người. **Đã chuyển 8 ảnh (#956–958, #886–890) sang "chờ duyệt"** (không xóa). Phát hiện tự động bằng số không đủ phân biệt
   (đã thử độ trong suốt, khung bao, so với ảnh Drive) → cần một lượt Claude nhìn ảnh để quét 62 nhân vật còn lại (xem "Việc tiếp").
2. **Vai trò ảnh nhân vật gần như trống:** 358/407 ảnh đã duyệt không có `role`/`look` (62/67 nhân vật không có ảnh nào gắn vai trò). Bộ chọn
   ảnh chỉ còn dựa vào hình dáng + diện tích; chọn đúng góc (cận mặt / sau lưng / nghiêng) chỉ hoạt động cho Kelly, Maxim, Kenta, Orion (ảnh 3D + ảnh chuẩn).
3. **Ảnh nhỏ:** 196/407 ảnh nhân vật cạnh ngắn < 400 px (bản 220×394 từ Drive trùng nội dung với bản 220×394 của website; 100×100 là icon đầu). Với 62
   nhân vật, ảnh dùng được thực tế chỉ là 1–2 ảnh 550×800 — đủ làm tham chiếu thân, KHÔNG đủ làm tham chiếu mặt cận.
4. **Hồ sơ chuẩn:** 3 đã duyệt, 62 nháp (chưa duyệt, thiếu chiều cao), 2 chưa có (A PATROA không ảnh, Kenta ở OB55 = mục giữ chỗ). Chưa đối chiếu hồ sơ ↔ ảnh.

### P1 — địa điểm
5. Chỉ 2/100 địa điểm (Tháp Đồng Hồ, Cổng Trời) có ảnh gắn góc máy → chỉ hai nơi này gửi được nền thật; còn lại tới model dưới dạng chữ.
6. **12 mục tên rác** ("121212", "131313"… "99999") chứa ảnh bản đồ nhập từ thư mục — luật hệ thống không dùng ảnh bản đồ từ trên cao làm nền → xóa mục.
7. **26 nhóm ảnh dùng chung** giữa đảo và khu vực (vd "Khu vực - Dock" cùng ảnh với "Đảo Mặt Trời"): chọn khu vực có thể gửi ảnh cả đảo.
8. 37 địa điểm không có mô tả; 18 địa điểm không có ảnh nào được duyệt; 32 ảnh chờ duyệt.

### P2 — ít ảnh hưởng hiện tại
9. Đạo cụ / vũ khí / phong cách: 191 mục chưa dự án nào dùng; 85/86 đạo cụ và 31/31 phong cách không có mô tả; 153 ảnh nhỏ.
10. Ảnh chờ duyệt của nhân vật: 17 (Kelly có 2 cặp ảnh gần giống nhau #878/#879, #880/#881).
11. **Nguồn thông tin chồng chéo:** 65/67 nhân vật có khối `[ff.garena.com]`, 0 có `[AI đọc ảnh]`, 1 có `[Phân tích video kỹ năng]`. Lỗi mỗi công cụ cắt mô
    tại dấu của mình đã sửa (`assets.replace_block`); luật một-chủ-cho-mỗi-thông-tin ở `QUY_TAC_NGUON_THONG_TIN_NHAN_VAT.md`.

## Việc tiếp (xếp theo giá trị / chi phí)
| # | Việc | Chi phí | Kết quả |
|---|---|---|---|
| A | Gắn vai trò ảnh nhân vật theo kích thước + nguồn (550×800 = toàn thân, 220×394 = nửa người, 100×100 = icon đầu, bảng 1448×1086 = design_sheet) và lưu | 0 | 358 ảnh có vai trò; bộ chọn góc hoạt động |
| B | Claude nhìn ảnh theo lô (lưới ảnh mỗi nhân vật + hồ sơ nháp): đánh dấu ảnh không phải nhân vật / sai nhân vật / lệch hồ sơ | ≈ $0,4–1 | Danh sách ảnh cần gỡ + hồ sơ lệch |
| C | Người duyệt hồ sơ chuẩn 62 nháp (sau B) | 0 | Hồ sơ là nguồn chuẩn duy nhất cho ngoại hình |
| D | Dọn địa điểm: xóa 12 mục tên rác, tách ảnh dùng chung, gắn góc máy cho ảnh khu vực dùng được | 0 | Địa điểm chọn đúng nền |
| E | Bộ kiểm chất lượng chạy tự động mỗi lần đồng bộ (`library_audit` ở màn 🩺 Sức khỏe kho) | 0 | Lỗi mới lộ ngay |
