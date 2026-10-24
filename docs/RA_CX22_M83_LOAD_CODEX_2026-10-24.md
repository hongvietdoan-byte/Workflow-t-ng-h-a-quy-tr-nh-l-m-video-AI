# Rà soát tiến độ — CX22-M83-LOAD

**Trạng thái:** đang làm; chưa có số đo tải trình duyệt.  
**Làn/nhánh:** Codex 2 — `codex/v31-m83-load`.  
**Phạm vi checkpoint:** entrypoint tương thích, cô lập môi trường và dữ liệu giả, kiểm thử hồi quy.

## Đã hoàn thành

- Thêm `tools/load_test_dashboard.py` làm entrypoint mỏng gọi lại harness `tools/load_test_ui.py`, tránh nhân đôi logic.
- Giới hạn biến môi trường truyền cho Streamlit, Playwright driver và Chromium bằng allowlist; các bài test dùng `patch.object(os, "environ", fake_dict)` trước khi gọi subprocess.
- Chạy mặc định chỉ tạo sidecar tổng hợp rỗng thay vì sao chép `retired_topics.json` hoặc `knowledge_user` từ repo.
- Khai báo entrypoint và bài test trong `devsys/areas.json`; giữ nguyên `areas.version`.

## Bằng chứng

- `tests/test_load_test_ui.py` và `tests/test_load_test_dashboard.py`: **37 passed, 2 skipped**, 24.98 giây; pytest chạy với `--tb=no`, không cache, môi trường tiến trình được giới hạn.
- Rà độc lập chỉ đọc: **không có finding P1/P2**; lỗi trước đó về subprocess kế thừa môi trường thật đã được đóng bằng fixture môi trường giả cấp module.
- `git diff --check`: sạch.

## Còn thiếu / giới hạn

- Chưa chạy đo N=1, chưa khởi Dashboard/Chromium, chưa có số liệu CPU/RAM/SQLite/thread. Lần khởi tạo runtime cô lập cho phép đo bị execution policy từ chối; không thử cách lách và không có server nào được khởi chạy.
- Theo chỉ dẫn phiên chính ngày 24/10 19:54, N=5/N=10 không được chạy trước 22:00 vì máy cần RAM. Sau 22:00 cần tiếp tục bằng runner được phép; chỉ kết luận các mức thực sự đã đo.
- Blender lock và hàng đợi Claude CLI không được kích hoạt trong kiểm thử provider giả; báo cáo cuối phải ghi rõ nếu harness không thể đo hai chỉ số này mà không mở luồng thật.

## Bước kế

Xin phiên chính chỉ rõ runner được phép cho phép đo N=1 trong môi trường cô lập. Sau khi đo N=1, thực hiện N=5/N=10 chỉ khi đã qua mốc 22:00 và máy vẫn đủ RAM; bổ sung số liệu vào báo cáo này, rà lại, xóa `HANDOFF.md` ở commit hoàn tất rồi gửi sự kiện `xong`.
