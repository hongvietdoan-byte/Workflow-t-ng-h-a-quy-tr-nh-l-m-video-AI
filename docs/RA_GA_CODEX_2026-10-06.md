# S14.14 G-a — rà trên Codex ngày 06/10/2026

Phạm vi: nhánh `s14-14-ga-ui-v2-default` (`142e02a`), tích hợp `main` tại `881f93b` trên nhánh `codex/s14-14-ga-review`.

## Kết quả đối chiếu

- Kịch bản chỉ gọi `step1_v2`, Video chỉ gọi `step4_v2`, Theo dõi chỉ gọi `_monitor_v2`. Các đoạn bị gỡ là nhánh giao diện cũ; không sửa core autopilot, runner hay cổng chi phí.
- Không còn lời gọi Python tới `step1_refs.inputs_and_refs` hoặc `step4.video_card` đã xóa. Mọi chỗ gọi `is_next` đã dùng chữ ký một tham số.
- Thẻ Video v2 giữ Duyệt, Loại, gửi lại kèm câu sửa, hủy, nối task thật, làm lại từ đầu, gen lại và giữ bản QC đã loại; khóa điều khiển tương ứng vẫn có.
- `ui.inject_css`/`dark_on` và `app.shell_header` giữ đọc cờ theo bàn giao; phần header cũ còn tới G-b. Khi ép `FEATURE_UI_V2=0`, màn nhẹ vẫn dùng bố cục v2 nhưng CSS v2 chưa được nạp. Đây là trạng thái chuyển tiếp đã ghi trong nhánh.
- Test đổi theo bố cục mới vẫn kiểm hành vi và dữ liệu; các test màn nặng ghim cờ tắt được giữ tới G-b. Cặp test chỉ dành cho bố cục Kịch bản cũ đã bỏ có chủ ý.

## Lỗi chặn và sửa

Dashboard không import được vì `voice_rule_box` dùng `Optional[str]` nhưng thiếu import `Optional`. Lỗi đã được ghi ở bước 2 của bàn giao; lấy sửa một dòng vào G-a để chạy test trên tiến trình mới. Trước sửa: bộ liên quan 39 lỗi, 12 qua, phần lớn lỗi phát sinh từ `NameError`. Sau sửa: **49 test và 2 subtest qua** (38,68 s).

## Bằng chứng kiểm thử

- `tests/test_ui_v2_default.py`, `test_ui_script.py`, `test_ui_video.py`, `test_ui_v2_acceptance.py`: 49 qua, 2 subtest qua.
- `tools/ui_v2_acceptance.py clicks`: UI v2 **14 lần bấm** từ Dự án mới tới video đầu, bằng mốc cũ 14; cả hai cấu hình cờ tạo 2 job video mock. Nút `ap_start` có và bấm không gây exception (đây chỉ là kiểm UI, không chứng minh autopilot chạy hoàn tất).
- Cả bộ lần đầu: 2 lỗi, 2658 qua, 8 bỏ qua, 66 subtest qua (12 phút 19 giây). Hai lỗi ở test: chọn font phụ thuộc máy Windows và `query_params` trả chuỗi ở Streamlit 1.65. Sửa fixture font riêng cho test điều khiển Bản giao, giữ nguyên assertion về khóa; nhận chuỗi hoặc danh sách cho query parameter. Bộ `test_ui_deliver` + `test_users` sau sửa: 15 qua (12,14 s). Cả bộ bản cuối `12d2779`: **2748 qua, 8 bỏ qua, 66 subtest qua, 0 lỗi** (748,27 s; 12 phút 28 giây; 10 cảnh báo thư viện).
- Môi trường Linux, Python 3.12, Streamlit 1.65.0; công cụ nằm trong venv `/tmp/codex-video-venv`. Không gọi nhà cung cấp trả phí, không có dữ liệu máy chính.
- Chưa thử bằng trình duyệt thật trên máy Windows; chưa pull hoặc khởi động lại Dashboard 8501 / AI Dev System 8502 tại máy chính.

S14.14 hoàn tất phần code G-a; bản tích hợp `12d2779` đã xanh và được gộp/push main cùng cập nhật bàn giao. G-b, G-c, S13.3 và S13.10 vẫn mở.
