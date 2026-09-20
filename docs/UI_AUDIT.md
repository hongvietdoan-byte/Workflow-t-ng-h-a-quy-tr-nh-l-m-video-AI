# Rà soát khung giao diện Dashboard (2026-09-20) — để tối ưu một thể

> **Cập nhật cùng ngày:** đợt gọn giao diện đầu tiên đã làm theo góp ý (Bước 1, thanh đầu, góc Rủi ro, Bước 2/4/5a/Lịch sử, xem video). Bản kiểm kê dưới đây là hiện trạng TRƯỚC đợt đó.

Ảnh từng màn (dữ liệu demo): `docs/images/audit_2026-09-20/`. Đây là bản kiểm kê **hiện trạng**, chưa sửa gì. Chưa xem: giao diện trên điện thoại (màn hẹp), dữ liệu thật nhiều cảnh (12+), ảnh thật.

## A. Khung chung (xuất hiện ở mọi bước)
| Khung | Nội dung | Nhận xét |
|---|---|---|
| ➕ Tạo dự án mới | expander | Chiếm 1 hàng ở đầu trang, ít dùng |
| Thanh đầu | logo, chọn dự án, chế độ QC, threshold, Pause/Resume/Cancel | Chế độ QC và threshold chỉ liên quan Bước 2 nhưng luôn hiện |
| 💲 Bảng giá | expander | Cài đặt, ít dùng; đứng chen giữa thanh đầu và thanh bước |
| Dòng chi tiêu | 1 dòng chữ nhỏ | Chỉ xuất hiện khi đã gọi API thật |
| Thanh bước | 7 tab, dấu ✓ | Tốt; chưa cho thấy tiến độ (n/N) |
→ ~250 px "hạ tầng" trước khi tới nội dung.

## B. Từng bước
**1 Kịch bản:** trái 3 khung (Input, cảnh báo IP, Director), phải 3 khung (Character Bible, Bảng phân cảnh, thanh Duyệt & khóa). Nút chính "Duyệt & khóa" nằm cuối cùng bên phải; Director có 3 cách cùng lúc (nút API, copy prompt, ô dán JSON); chữ "200MB per file" tiếng Anh; bảng phân cảnh cắt chữ ("Nữ chiến binh Ama"); "succeeded" + "Đã tách 8 cảnh" lặp ý.

**2 Gen ảnh + QC:** 5 lớp trước khi thấy ảnh đầu tiên (thanh 4 nút, hàng mức tự loại, hàng vùng chờ review, banner "Chưa cấu hình Deepix…", nút QC Claude, chip lọc) ≈ 700 px. Nút chỉ có biểu tượng (✔ ✖ 🔍 ↻ ■) không nhãn; thẻ cao thấp khác nhau; 2 nút QC Claude (cả lô và từng ảnh); ngưỡng threshold ở đầu trang còn mức sàn ở Bước 2.

**3 Video Prompt:** mỗi cảnh một hàng: ảnh nhỏ 96 px, ô prompt to, 2 nút chồng dọc, badge, thời lượng, rồi expander kịch bản, rồi đường kẻ → hàng rất cao, lặp lại nhiều lần; "Duyệt tất cả" ở góc trên tách khỏi danh sách.

**4 Gen video:** khung trên gộp chọn model + banner cấu hình + ước tính chi phí + 4 nút; rồi khung tiến độ; rồi cảnh báo risk control; rồi danh sách job. Danh sách job: tên cảnh, badge, retry, nút cách xa nhau (khoảng trắng lớn); không có ảnh cảnh hay xem trước clip ngay; "Xem" là ô tick còn "Xóa clip" là nút.

**5a Nhạc:** Music Brief (5 ô), lưới bản nháp (thẻ đang chạy trông như trống), Nhạc nền đang chọn (kết quả nằm ở dưới cùng), Hiệu ứng & giọng đọc (tab SFX/TTS + danh sách). Trang dài ~1700 px; "Kiểm tra + tải về" xuất hiện 2 lần (nhạc và SFX) dễ nhầm; nhạc đã chọn nên thấy ngay đầu trang.

**5b Ghép & Render:** trái danh sách clip (mỗi clip: ô tick, Xem, số giây, expander kịch bản), phải tùy chọn render. Bố cục ổn; nhãn "Cảnh 1 — CẢNH 1" lặp; cảnh thiếu clip là dòng cảnh báo dài.

**Lịch sử:** đoạn kịch bản, phiên bản (ảnh, video không có xem trước), danh sách job dạng expander, Thùng rác (tab Ảnh/Video). 4 kiểu khung khác nhau xếp dọc.

## C. Vấn đề chung
1. Mọi khung cùng độ nổi (cùng viền) → không có thứ bậc: khó thấy "việc kế tiếp".
2. Thiếu "đầu bước": mục tiêu bước + tiến độ (vd 3/8 ảnh đã duyệt) + nút hành động chính nằm cố định ở một chỗ.
3. Thông báo kỹ thuật (biến môi trường) chiếm chỗ trong luồng chính; nên thu gọn thành trạng thái ngắn ("Chế độ nhập tay") và chỉ hướng dẫn khi bấm.
4. Ngôn ngữ lẫn Anh–Việt (Approve/Reject/Retry/Cancel/Gen/Render) và biểu tượng không nhãn.
5. Cài đặt (dự án, bảng giá, mode, threshold, mức sàn) rải rác ở nhiều nơi.
6. Khoảng trắng lớn ở danh sách dạng hàng (Bước 4), chiều cao hàng không đều (Bước 3).
7. Chưa kiểm tra màn hẹp/điện thoại.

## D. Hướng tối ưu đề xuất (chờ bạn chọn)
- Một **thanh đầu duy nhất** (dự án ▾, ⚙ Cài đặt: tạo dự án, bảng giá, mode/threshold; Pause/Cancel) → nhả ~200 px.
- Mỗi bước có **đầu bước** thống nhất: tên + mục tiêu, tiến độ, 1 nút chính; mọi phần phụ (dán JSON, prompt copy, cấu hình) thu vào "Nâng cao".
- Chuẩn hóa **thẻ** (ảnh/clip/nhạc) cùng cấu trúc: nhãn "Cảnh N", trạng thái, hành động có chữ, "📖 kịch bản".
- Thống nhất từ ngữ tiếng Việt và cỡ chữ; kiểm tra bản điện thoại.
