# Dashboard v2 — Báo cáo test một lượt (Giai đoạn 9, 2026-09-23)

Theo kế hoạch v2: làm hết GĐ0–8 rồi mới test một lượt, liệt kê lỗi, sửa một thể. Test gồm 2 phần:

1. **Bộ unit test** `py -m unittest discover -s tests -t .` — lần chạy đầu sau GĐ8: 66 lỗi; sau vòng sửa: **632 test, 0 lỗi** (thêm `tests/test_v2.py`: 32 test cho v2).
2. **Chạy thử qua trình duyệt** bằng kịch bản thật của người dùng *"KỊCH BẢN FREE FIRE: KENTA XUYÊN TƯỜNG CƯỚP KILL?!"* (3 cảnh, Kelly/Maxim/Kenta, 14 câu thoại, "TEXT CUỐI"), dự án 9:16, ưu tiên model "Cân bằng", mọi nhà cung cấp giả lập (không tốn credit), đi hết Bước 1 → 5 bằng cách bấm trên giao diện.

## Kết quả chạy thử bằng kịch bản Kenta

| Khâu | Kết quả |
|---|---|
| Tách cảnh | 3 cảnh; phần trước "CẢNH 1" (thời lượng 45–55s, nhân vật, bối cảnh Map Đảo Quân Sự) gửi cho Director; "TEXT CUỐI" thành card cuối, không lẫn vào cảnh 3 |
| Thoại | 14 câu, người nói viết kiểu "Kelly:" được nhận; "Maxim nhìn xuống: …" (hành động) không bị coi là thoại |
| Rà thoại (1f) | ước lượng 13,6s / 11,4s / 13,4s → nút "Tự tăng thời lượng" đặt clip 14s / 12s / 14s |
| Nhân vật | Lock + giọng + ảnh mốc từng nhân vật; Claude chọn giọng |
| Ảnh | 3 ảnh khung dọc, QC 8 tiêu chí, kiểm tra đồng bộ cả bộ: ổn |
| Motion + giọng | 3 prompt, rà prompt: ổn; TTS 14 câu; thời lượng theo giọng thật 15s / 15s / 26s; animatic 1080×1920, 56s, có tiếng |
| Model theo cảnh | S01 Kling 3.0 Omni (đối thoại 2 người, $1,20) · S02 Seedance 2.0 (3 nhân vật, $2,25) · S03 Seedance 2.5 (cảnh then chốt + phức tạp, 26s, $5,98) — tổng ≈ $9,43; so sánh Chất lượng $10,48 / Tiết kiệm $6,12 |
| Video | 3 clip, QC video 4 tiêu chí, duyệt tất cả |
| Bản giao | dựng 56s (nhạc + 14 câu thoại) → phụ đề tiếng Việt → card cuối "Kenta được làm lại kỹ năng. Maxim vẫn chưa được làm lại IQ!" (59s) → bản vuông 1080×1080; cả 5 bước ✓ |

Kiểm tra bằng khung hình trích từ file xuất: phụ đề và card cuối hiện đủ dấu tiếng Việt; bản vuông giữ phụ đề và card (sau khi sửa lỗi #3).

## Lỗi tìm được và đã sửa

### Từ bộ unit test (lần chạy đầu)
| # | Lỗi | Sửa |
|---|---|---|
| U1 | Nút bấm dùng callback chạy ở luồng khác → lỗi SQLite "created in a thread" | callback tự mở kết nối mới (`header._create_project`, `step1._lock_and_go`) |
| U2 | Dự án cũ (chưa chọn ưu tiên model) bị chuyển sang Seedance | `model_router.chosen_priority`: dự án cũ giữ Kling, có nút chọn ưu tiên |
| U3 | Bước 5 mất phần xem nội dung kịch bản từng cảnh | thêm lại `scene_expander` |
| U4 | Bước 4 ẩn ước tính chi phí khi chưa cấu hình nhà cung cấp | luôn hiện ước tính |
| U5 | Bước 1 ẩn "Chuẩn bị" và Character Bible khi chưa có cảnh | luôn hiện 1b; Character Bible hiện khi có nhân vật |
| U6 | Nhà cung cấp giả lập bị tạo lại mỗi lần tải trang → job giả lập "mất" | giả lập dùng chung một bản cho cả tiến trình (`factory._MOCKS`) |
| U7 | Sửa chữ của cảnh nhưng thoại có cấu trúc vẫn là bản cũ | `update_scene` tách lại thoại (trừ khi thoại đã sửa tay) |
| U8 | 50+ test cũ theo hành vi v1 (cổng duyệt nhân vật mặc định bật, nhãn tiếng Việt mới, "Bước 5a/5b") | cập nhật test theo hành vi v2 |

### Từ kịch bản thật của người dùng
| # | Lỗi | Sửa |
|---|---|---|
| K1 | Người nói viết "Kelly:" (không viết hoa hết) không được nhận là thoại | `dialogue._is_speaker`: nhận tên viết hoa chữ đầu (≤3 từ), loại tiêu đề như "Ghi chú", "TEXT CUỐI" |
| K2 | "TEXT CUỐI" bị gộp vào cảnh 3 | `script_parser.split_end_card` → card cuối bật sẵn ở Bước 5 |
| K3 | Director không thấy phần mở đầu (thời lượng, bối cảnh chung) | `prompts.script_preamble` |

### Từ chạy thử qua trình duyệt
| # | Mức | Lỗi | Sửa |
|---|---|---|---|
| 1 | Cao | Thanh bước **nhảy về Bước 1** mỗi khi nhãn tiến độ đổi (ảnh xong, clip xong, bản giao cũ → mới): Streamlit coi radio có nhãn khác là widget mới | `app.py` gán lại bước đang mở trước khi vẽ thanh bước |
| 2 | Cao | Bảng trộn âm ở Bước 5 **ghi đè ngược** vị trí giọng thoại vừa được xếp khi dựng → 14 câu thoại bị tắt khỏi bản ghép, bản giao báo "⚠ cũ" ngay sau khi dựng | khóa widget gắn theo giá trị trong file (`step5.extras_section`) |
| 3 | Cao | Bản xuất khác tỉ lệ bằng "cắt khung" **cắt mất phụ đề** (phụ đề ở đáy khung dọc nằm ngoài khung vuông) | `delivery._reframe`: cắt video gốc → in lại phụ đề (lưu `cue_list` ở lớp phụ đề) → vẽ card theo khung mới → nén |
| 4 | Trung bình | Nút "⏱ Tự tăng thời lượng" ở Bước 1 không làm gì (chỉ sửa được khi đã có motion prompt) | lưu `duration_s` của cảnh (khóa 🔒), motion prompt viết sau dùng giá trị này; giới hạn 1–30s (Seedance 2.5) |
| 5 | Trung bình | Kịch bản toàn thoại nhưng phụ đề mặc định tắt → bản giao không có phụ đề | nhập kịch bản có thoại thì bật phụ đề (người dùng tắt được) |
| 6 | Trung bình | Brief nhạc 30s trong khi phim 56s | độ dài nhạc ≥ tổng thời lượng phim |
| 7 | Trung bình | Ảnh/clip giả lập là file 1×1 / "MOCK-MP4" → không thử được dựng/phụ đề/xuất bản | `MOCK_REAL_MEDIA=1` (bật trong `tools/run_demo.ps1`): giả lập ghi ảnh/clip thật nhỏ đúng khung dự án |
| 8 | Thấp | Chọn giọng bằng Claude xong, ô chọn giọng vẫn hiện "— chưa chọn —" | xóa trạng thái widget sau khi chọn |
| 9 | Thấp | Nút "Ảnh tham chiếu ở trên là đúng" hiện cả khi nhân vật chưa có ảnh | chưa có ảnh: nói rõ và nút "Vẫn vẽ theo mô tả chữ — bỏ qua ảnh mốc" |
| 10 | Thấp | Dòng chi phí ghi "gửi API thật" khi toàn bộ là giả lập | "Nhà cung cấp giả lập … — không tốn credit" |
| 11 | Thấp | Thanh bước tràn ngang ở màn hẹp (Bước 5 và 📊 bị khuất) | thanh bước tự xuống dòng |
| 12 | Thấp | "$" trong dòng so sánh chi phí bị hiểu là công thức toán | thoát ký tự `$` |
| 13 | Thấp | "▶ Gen video (3 cảnh sẵn sàng)" đếm cả cảnh đã có clip | `batch.videos_to_make` |
| 14 | Thấp | Bước 4 thiếu "Duyệt tất cả" (Bước 2, 3 đều có) | thêm "✔ Duyệt tất cả (N clip)" có hỏi lại |
| 15 | Thấp | Thoại dài hơn clip tối đa của model chỉ khuyên rút thoại/tách cảnh | thêm gợi ý đổi cảnh sang Seedance 2.5 (tối đa 30s) |
| 16 | Thấp | Nhãn "⚠ 5 · … · ⚠ cũ" hai dấu ⚠; "0/0" khi chưa có cảnh | một dấu; không hiện "0/0" |
| 17 | Thấp | Bản giao liệt kê cả bản xuất cũ cùng tên file (đã bị ghi đè) kèm "⚠ cũ" | mỗi file chỉ hiện bản ghi mới nhất |
| 18 | Thấp | Chú thích Bước 2 bảo "khóa Character Bible" dù đã khóa | sửa chữ |

Mỗi lỗi mức Cao/Trung bình có test hồi quy trong `tests/test_v2.py` (`WalkthroughFixTests`, `ReframeExportTests`) hoặc test cũ đã cập nhật.

## Chưa kiểm được / ghi chú
- **Chưa chạy API thật** (Deepix 9:16, Clip AI theo model từng cảnh, TTS tiếng Việt, Claude thật cho Director/QC/rà thoại) — cần người dùng đồng ý vì tốn credit. Việc cần xác nhận: Seedance 2.5 nhận clip 26s; giá thật so với giá ước tính; Kling tự sinh giọng tiếng Việt (nghi không hỗ trợ).
- **Chế độ tự động** chỉ kiểm bằng unit test (dừng ở cổng duyệt nhân vật → chạy tới bản giao → trả lại cách duyệt), chưa bấm qua giao diện đến hết.
- **Tải file lên** (ảnh nhân vật, font) không thử được bằng công cụ trình duyệt → Kelly/Maxim/Kenta trong lần thử vẽ theo mô tả chữ.
- Director giả lập chỉ lấy người nói làm nhân vật cảnh (Kenta "xuất hiện phía sau" ở cảnh 1 nhưng không có thoại nên không vào danh sách) — Director thật đọc cả câu hành động.
- Giọng giả lập dài hơn giọng thật nên S01/S02 báo "thoại dài hơn clip 15s" — đúng hành vi cảnh báo; với giọng thật cần đo lại.
- Ở màn hẹp (< 640px) các nút đầu trang xếp dọc (cách Streamlit xếp cột) — dùng được, chưa tối ưu cho điện thoại.
