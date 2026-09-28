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

## E. Kiểm kê 3 tầng hiển thị (2026-09-28, kế hoạch sau #8 · S9.3) — CHỜ NGƯỜI DÙNG DUYỆT
Người dùng (sau #8): dashboard nay chạy chủ yếu bằng Claude API → phần không cần thao tác thì gọn lại / ẩn, **có nút hiện ra** khi muốn xem.
**Tầng 1 luôn hiện** (việc kế tiếp, nút chính, lỗi chặn, tiền) · **Tầng 2 thu gọn một dòng + "▸ Mở"** (`ui.fold`, S9.2 — đã dùng cho 1a Kịch bản)
· **Tầng 3 chỉ ở 🧠 Chế độ chuyên gia** (nhập tay, dán JSON, prompt, cài đặt kỹ thuật, thử nghiệm). Cột "Hiện tại": luôn mở / expander (đóng
hay mở sẵn) / chuyên gia. Mã (E-x) để góp ý: "E1.4 giữ tầng 1" v.v.

| Mã | Khung | Hiện tại | Đề xuất | Dòng tóm tắt khi thu gọn / lý do |
|---|---|---|---|---|
| **Mọi bước** | | | | |
| E0.1 | Dải "Việc tiếp theo" ở đầu mỗi bước (mới) | chưa có | **1** | "Việc kế: duyệt 10 khung chờ ở cổng storyboard" + 1 nút; lấy từ trạng thái chạy tự động / job chờ |
| E0.2 | Thanh đầu: dự án, người thao tác, ⚙ | luôn mở | **1** (giữ) | ⚙ đã gom cài đặt vào hộp thoại |
| E0.3 | Dòng tiền (đã dùng / trần / còn) | luôn mở | **1** | gộp với S6.4: "Đã dùng 42,85 / trần 43,1 USD · Claude 8,6 / 8,7" |
| **Bước 1** | | | | |
| E1.1 | 1a Kịch bản (tải file / dán / toàn văn / chia cảnh) | luôn mở | **2** ✅ đã làm (S9.1) | "📜 6 cảnh · 33 shot · 23 câu thoại · 1.234 ký tự"; mở sẵn khi chưa có kịch bản |
| E1.2 | "Hệ thống đã đọc kịch bản thế nào" | expander đóng | 2 (giữ) | — |
| E1.3 | 💵 Ngân sách dự án | expander | **1 khi chưa duyệt** (có nút Duyệt & KHÓA) · **2 khi đã khóa** | "🔒 Đã khóa 33,18 USD · đã dùng 29,24" |
| E1.4 | 1b Định dạng dự án (tỉ lệ, thể loại, look) | expander mở khi thiếu | 1 khi thiếu · 2 khi đủ (giữ) | "9:16 · Phim ngắn · in-game FF" |
| E1.5 | Tài nguyên dự án (gợi ý Kho, tải ảnh riêng) | expander | **2** | "4 tài nguyên đã gắn · 0 gợi ý mới" — nay tự gắn khi Director chạy |
| E1.6 | 🖼 Ảnh tham chiếu từng nhân vật | expander mở khi thiếu | 1 khi thiếu · 2 khi đủ (giữ) | "3/3 nhân vật có ảnh" |
| E1.7 | 🧩 Kho chủ thể Seedance | ẩn (biến môi trường) | 3 (giữ) | — |
| E1.8 | 🎨 World Bible | chuyên gia | 3 (giữ) | — |
| E1.9 | 1c 🚀 Tự động hoàn toàn | luôn mở | **1** | nút chính + ước tính |
| E1.10 | 1c 🧭 "Lần lượt từng bước" (chỉ là chữ giải thích) | luôn mở | **bỏ khung**, thành 1 dòng chú thích dưới E1.9 | không có nút nào |
| E1.11 | "Chạy lại từ đầu" | expander | **3** | thao tác phá dữ liệu, hiếm dùng |
| E1.12 | 1d Director (nút chạy + ước tính) | luôn mở | **1 trước khi chạy · 2 sau khi chạy** | "✅ 33 shot · Đạo diễn duyệt 6/6 · 1,27 USD · 11 phút" |
| E1.13 | Báo cáo Director: ⚖ đánh đổi, 📝 ghi chú kịch bản, 🎬 Đạo diễn duyệt, 🔧 code chuẩn hóa, kiểm tổ làm phim | 5 expander rời | **2, gom vào một** "📋 Báo cáo Director (n mục cần xem)" | cảnh báo chặn (nếu có) vẫn hiện tầng 1 |
| E1.14 | ✍ Prompt gửi Claude + dán JSON | chuyên gia | 3 (giữ) | — |
| E1.15 | 1e Character Bible (Lock, giọng, ảnh mốc) | luôn mở | **1 khi còn nhân vật chưa duyệt ảnh mốc · 2 khi đã khóa** | "👥 3 nhân vật · 🔒 đã khóa · giọng đủ" |
| E1.16 | ✏ Sửa / thêm nhân vật | expander | 2 (giữ) | — |
| E1.17 | 1f 🗣 Rà thoại | expander mở khi có vấn đề | 2 (giữ) | "23 câu · 0 cần chú ý" |
| E1.18 | 1g Storyboard previz 2D | chuyên gia | 3 (giữ) | — |
| E1.19 | Thanh "✔ Duyệt & khóa → Bước 2" | luôn mở | **1** | nút chính |
| **Bước 2** | | | | |
| E2.1 | ⚠ Khâu có lỗi đã biết | expander | **1 một dòng đỏ** + chi tiết tầng 2 | "⚠ 2 khâu đang dùng có lỗi đã biết — ▸ Mở" |
| E2.2 | Thanh nút gen ảnh + ước tính | luôn mở | 1 | nút chính |
| E2.3 | "Tùy chỉnh chi tiết" (mức sàn, chế độ QC…) | expander **mở sẵn** | **3** | cài đặt kỹ thuật |
| E2.4 | Nâng cao: prompt QC + dán điểm tay | chuyên gia | 3 (giữ) | — |
| E2.5 | Lưới khung theo cảnh | expander mở khi còn chờ duyệt | 1 cho cảnh còn chờ · 2 cho cảnh đã duyệt hết | "Cảnh 3 · 7/7 đã duyệt" |
| E2.6 | Kết quả QC theo cảnh / agent QC | expander mở khi có lỗi | 2 (giữ) | — |
| **Bước 3** | | | | |
| E3.1 | Motion prompt từng cảnh (33 hàng cao) | luôn mở | **2** — code/Claude viết sẵn; chỉ mở khi muốn sửa | "🎬 33/33 motion · 2 nhóm Seedance cần xem" |
| E3.2 | 🎥 Video tham chiếu chuyển động | chuyên gia | 3 (giữ) | — |
| E3.3 | ✍ Prompt gửi Claude & dán kết quả | chuyên gia | 3 (giữ) | — |
| E3.4 | 🎙 Giọng thoại (TTS) | expander mở khi thiếu | 1 khi thiếu · 2 khi đủ (giữ) | "23/23 câu có giọng" — S2 sẽ dời lên Bước 1 |
| E3.5 | 🎞 Animatic | expander | **1** sau S2 (cổng xem trước khi trả tiền video) | — |
| **Bước 4** | | | | |
| E4.1 | Thanh gen video + ước tính | luôn mở | 1 | nút chính |
| E4.2 | 🎛 Model cho từng cảnh | expander | **2** | "Seedance nhóm ×9 · đơn ×6" |
| E4.3 | 👄 Khớp môi: shot không khớp môi | expander | **1 một dòng** (thiếu khớp môi là lỗi người dùng đã nêu) + chi tiết tầng 2 | — |
| E4.4 | Danh sách job video | luôn mở | 1 cho job đang chạy / lỗi · 2 cho job đã duyệt | "33/33 clip đã duyệt" |
| E4.5 | 👀 Bản QC đã loại | expander | 2 (giữ) | — |
| E4.6 | 🧪 Thử nghiệm (Kling multi-shot, gộp shot) | chuyên gia | 3 (giữ) | PH 11: người thường không thấy — giữ vì là thử nghiệm |
| **Bước 5** | | | | |
| E5.1 | 5.1 Clip theo thứ tự cảnh (33 hàng) | luôn mở | **2** | "🎬 33/33 clip · 84,5 s" |
| E5.2 | 🎵 Nhạc nền đang chọn | luôn mở | 1 | nghe được ngay |
| E5.3 | Brief nhạc + lưới bản nháp | luôn mở | **2** | "Nhạc theo nhịp truyện · 2 bản nháp · đã chọn 1681" |
| E5.4 | Hiệu ứng âm thanh (AI đề xuất) + giọng đọc thêm | luôn mở / chuyên gia | **2** | "4 hiệu ứng gắn theo shot" |
| E5.5 | 5.3 Dựng video cuối: nút | luôn mở | 1 | — |
| E5.6 | 5.3 thiết lập dựng (chuyển cảnh, âm lượng nhạc…) | luôn mở | **2** | "Cắt thẳng · nhạc 0,6" |
| E5.7 | 🔤 Phụ đề · 🪧 Card cuối · 📐 Kích thước khác | expander | 2 (giữ) | "Phụ đề: bật · TikTok" |
| E5.8 | 5.5 Bản giao + 🔎 Kiểm bản dựng | luôn mở | **1** | lỗi chặn đỏ ở đầu bước |

**Ước lượng:** Bước 1 của #8 hiện mở sẵn ~14 khung → sau đề xuất còn ~5 (E0.1, E1.9, E1.19 + khung nào còn việc); mục tiêu nghiệm thu S9: giảm ≥ 40 %
chiều cao trang Bước 1 (đo bằng trình duyệt trước/sau trên dự án #8).
