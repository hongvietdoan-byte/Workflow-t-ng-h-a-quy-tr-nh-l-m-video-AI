# Ghi chú: chỉnh giao diện Dashboard theo so sánh với FateBreaker (10/10) — CHƯA LÀM

> Trạng thái: **chỉ ghi chú, chưa làm** (người dùng 10/10: "tạo 1 nhánh note lại, chưa làm vội"). Nhánh `ghi-chu-giao-dien-fatebreaker`.
> Khi làm: thảo mockup trong `mockup/` trước (0 USD) → người dùng duyệt → mới sửa `dashboard/`. Nên làm cùng/sau K1a (cột giữa cần `jobs.sent_package`).

## Nguồn so sánh
- FateBreaker: 2 ảnh chụp người dùng gửi 10/10 — màn Render "Video Studio" (3 cột) và màn Asset (lưới thẻ Nguồn ↔ Đích).
- Dashboard: chụp thật dự án #22 (Kịch bản · Storyboard "Ảnh + QC" · Video) trên localhost:8501 ngày 10/10.

## Khác biệt gốc
FateBreaker tổ chức theo **không gian làm việc** (một màn chứa mọi thứ của một clip, 3 cột); Dashboard tổ chức theo **dây chuyền**
(stepper 1–4, mỗi shot một thẻ dài xếp dọc, cuộn nhiều).

| Mặt | FateBreaker | Dashboard |
|---|---|---|
| Điều hướng | 6 tab phẳng; dự án + tập ở góc trái | stepper 1–4 + "Bấm tiếp" — rõ thứ tự |
| Bố cục | 3 cột cố định: tham chiếu + checklist · keyframe + prompt · video + phiên bản; dải phim dưới đáy | 1 cột thẻ shot dọc; một shot ≈ cả màn |
| Phiên bản | ô V1–V4 có trạng thái (Xong/Lỗi · 480p), nhãn "Đang dùng" | ảnh có v1…v10 ‹ ›; clip video không có dải phiên bản |
| Tham chiếu | luôn hiện; nhân vật + variation + nghe giọng; prompt gắn `@image1…` kèm ảnh nhỏ | ẩn trong "Chi tiết" ("4/4 nhân vật"); không thấy gói gửi |
| Prompt | trung tâm; Đọc & duyệt / Chỉnh / Sao chép / Agent / Đối chiếu nguồn | ẩn theo A13 (người dùng không đọc prompt) — khác triết lý, giữ |
| Kiểm | checklist ngắn 3 dòng + "2 điểm cần đối chiếu" | sâu hơn (QC tiêu chí, chặn khác Kho, đo lớp 0, rà soát tác động) nhưng là chữ dài trong thẻ |
| Tiền | gần như không thấy | khắp nơi (ước tính từng nút, mục tiêu phim, trần) — điểm mạnh, giữ |
| Kho | thẻ ghép đôi Nguồn (khung gốc + mốc giây) ↔ Đích đã duyệt; nhãn Chính/Phụ/Nền | không đặt ảnh nguồn cạnh hồ sơ/đích |
| Mật độ | nền tối phẳng, chữ nhỏ, dày thông tin | gradient tím, thẻ bo, emoji, chữ to — tốn chỗ |

## Việc đề xuất (chưa làm)
1. **Màn "một clip" 3 cột cho bước Video** (và có thể Storyboard): trái = tham chiếu của shot (nhân vật/bối cảnh/đạo cụ) + checklist;
   giữa = khung đầu + gói gửi; phải = trình xem clip + dải phiên bản; dưới = dải phim các shot để nhảy nhanh. Mục tiêu: giảm cuộn.
2. **Dải phiên bản V1…Vn có trạng thái + "đang dùng"** cho cả ảnh và clip; bấm để so cạnh nhau.
3. **Hiện gói gửi bằng ảnh nhỏ + vai** (`@image1 = Kelly · nhận diện`, `@image2 = nền 3D`…) — đọc từ `jobs.sent_package` (K1a);
   giúp người duyệt ④ thấy ngay vai ảnh sai (vd #24 "nền mẫu Kho thay render 3D", mục 4b #3 kế hoạch kiểm soát).
4. **Thẻ Kho ghép đôi Nguồn ↔ Đích**: ảnh mẫu Kho cạnh mô tả / `khai_bao_chu` — phục vụ loại lỗi R1 (vd #418 "đai đỏ" lệch ảnh).
5. **Checklist ngắn 3–4 dòng có chấm trạng thái** thay các dòng cảnh báo dài; chi tiết vẫn trong "Chi tiết".

## Không chép
- Prompt thô làm trung tâm màn (trái A13/A14).
- Bỏ stepper / "Bấm tiếp".
- Giấu tiền (trái `docs/CHUAN_XAY_DUNG.md`: mọi lời gọi tốn tiền có ước tính trước).

## Ràng buộc khi làm
- Theo kế hoạch nâng cấp dashboard 04/10 (UI v2, chữ 12,5 px) và test `tests/test_ui_v2_acceptance.py` (không đổi key widget ngoài danh sách đổi tên).
- Đổi `dashboard/` → khởi động lại Dashboard; rà khâu liên quan theo quy ước 7 trước commit.
