# Rà soát mô hình hoạt động: giới hạn và lỗi khi làm lần lượt từng bước (2026-09-20)

Cách kiểm tra: chạy thử toàn bộ chuỗi bằng nhà cung cấp giả lập (`tests/test_workflow.py`: kịch bản mẫu → Director → khóa → ảnh → QC → duyệt → motion prompt → video → gen lại → ghép) và thử các chuỗi thao tác "lệch" (bấm hai lần, hết lượt thử, đổi ý sau khi duyệt). Phần ghép âm thanh đã chạy với ffmpeg thật.

## A. Lỗi tìm thấy và ĐÃ SỬA
| # | Tình huống | Hậu quả trước đây | Đã sửa |
|---|---|---|---|
| 1 | Bấm "Phân tích" lần 2 khi dự án đã có cảnh | Trang **văng lỗi** (trùng số cảnh trong CSDL) | Báo rõ "Dự án đã có cảnh S01… Bấm Reset rồi phân tích lại"; không tạo dở dang |
| 2 | Ảnh bị loại quá số lần thử (mặc định 3) → cảnh "cần chú ý" | Cảnh **kẹt vĩnh viễn**: không có nút nào tạo job ảnh mới cho cảnh đó | Nút **"↺ Làm lại từ đầu"** (job mới, số lần thử về 0) |
| 3 | Video hỏng quá số lần thử | Job `failed` đã escalated **chặn** việc tạo job video mới cho cảnh | Cùng nút "↺ Làm lại từ đầu" (job cũ được hủy, job mới xếp hàng) |
| 4 | Đã **duyệt** ảnh rồi mới thấy sai | Không có đường quay lại (trạng thái duyệt là cuối) | Nút **"↩ Bỏ duyệt & gen lại ảnh"** kèm lý do; không bị giới hạn số lần thử. Video đã làm từ ảnh cũ không tự đổi |
| 5 | Bật "Model tự tạo âm thanh/lời thoại" rồi ghép | Bản ghép cuối **xóa mất âm thanh gốc của clip** (lệnh ghép luôn bỏ audio) → lời thoại/khớp môi mất | Ghép giữ âm thanh gốc (cắt, cross-fade, dip-to-black), nhạc nền **trộn dưới** lời thoại thay vì thay thế; ô "🔊 Giữ âm thanh gốc"; cảnh báo nếu có clip không có âm thanh (khi đó bỏ âm thanh gốc cho cả bản) |
| 6 | Kịch bản không có dòng "Cảnh N" | Cả kịch bản thành 1 cảnh "Mở đầu" mà không báo | Cảnh báo rõ + nút **➕ Thêm cảnh**, **🗑 Xóa cảnh**, sửa từng cảnh |
| 7 | File `.docx` hỏng | Lỗi kỹ thuật hiện ra | Báo lỗi gọn, không văng |

## B. Giới hạn còn lại (thiết kế hiện tại, cần biết)
1. **"Chạy heartbeat tới khi xong" chạy trong một lần tải trang.** Bấm bất kỳ nút nào khác trong lúc đó sẽ ngắt vòng lặp (job vẫn chạy bên nhà cung cấp và trạng thái nằm trong CSDL; bấm "Submit + Poll 1 lần" hoặc chạy lại để nhận kết quả). Không mất dữ liệu, nhưng không tự chạy nền khi đóng cửa sổ.
2. **Một cảnh = một ảnh khung đầu = một clip.** Cảnh nhiều góc máy nên tách thành nhiều cảnh (có nút thêm/xóa/sửa cảnh). Chưa dùng khung cuối, multi-shot, video tham chiếu (xem `docs/CLIPAI_FEATURES.md`).
3. **Độ dài clip:** Kling 3–15 s, Seedance 4–15 s (2.5 tới 30 s). Motion prompt cho phép 1–15 s; giá trị ngoài dải được kẹp lại khi gửi.
4. **Một người dùng, một máy:** CSDL SQLite cục bộ, không đăng nhập/phân quyền (đã hoãn theo yêu cầu). Hai cửa sổ cùng mở một dự án được, nhưng không nên thao tác đồng thời cùng một cảnh.
5. **Nhạc nền chỉ một bản cho cả video** (không theo từng cảnh); SFX/giọng đọc đặt theo giây trên toàn bản ghép.
6. **Nhân vật/đối tượng:** Character Bible nhận mọi thứ cần đồng nhất (người, sinh vật, linh vật, đạo cụ). Kho chủ thể chỉ **ảnh** (JPG/PNG/WebP), chỉ **Seedance**, tối đa 8 ảnh tham chiếu/cảnh (2.0) hoặc 29 (2.5); chưa dùng video chủ thể.
7. **Bản quyền Kho chủ thể:** chỉ game đã ký thỏa thuận (hiện là Free Fire) được coi là đã qua duyệt bản quyền; danh sách ở `data/games.json` (thêm được trong Dashboard).
8. **Chi phí** chỉ là ước tính từ bảng giá bạn nhập; token Claude API chưa ghi vào sổ.
9. **Chưa chạy thật:** audio Clip AI, âm thanh/lời thoại do model tạo, Kho chủ thể, Claude API. Mọi thứ này đúng theo tài liệu và đã có test bằng giao thức giả, nhưng cần thử thật.
10. Phần quét file thùng rác/giữ ảnh chạy mỗi lần tải trang: dự án rất lớn (hàng nghìn ảnh) có thể hơi chậm.
