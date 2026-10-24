# Rà soát CX23-A2F-ALIAS — Codex 2

- **Nhánh:** `codex/v31-a2f-alias`
- **Phạm vi:** bổ sung công cụ offline liệt kê bí danh tiếng Anh còn thiếu cho địa điểm Free Fire; mặc định chỉ đọc. Không gọi API, không chạy trên CSDL thật, không migration/backfill dữ liệu.
- **Cơ sở:** trường `assets.aliases` đã có trong schema và adapter. Kiểm thử fixture xác nhận A2f dùng cùng bí danh cho `Setting:` và câu nền plate khi các cờ fixture bật; khi cờ tắt vẫn giữ hành vi cũ.

## Thay đổi

- `tools/kho_place_alias.py` mở CSDL ở `mode=ro`/`query_only`, không tự tạo CSDL thiếu; chỉ đề xuất tên đã có trong catalog FF khớp chính xác sau chuẩn hóa. Thiếu hoặc nhiều nguồn khớp thì để trống, không dịch hay tự suy đoán.
- Chế độ ghi cần `--lam-that` và từng cặp `--duyet "ID=Bí danh"` đúng với bản đề xuất hiện tại. Nếu ID hoặc bí danh đổi sau khi người dùng xem trước, lệnh từ chối trước khi ghi. Chế độ ghi chỉ nhận `data/manifest.sqlite`, gọi sao lưu hiện có trước rồi xác minh lại trong transaction `BEGIN IMMEDIATE`; cập nhật dùng điều kiện so sánh hiện trạng và rollback khi có xung đột.
- Lệnh sao lưu truyền whitelist biến môi trường hệ thống cần thiết, không kế thừa credential/API env. Không thay đổi schema hoặc bật cờ.
- Đăng ký tool và test trong `devsys/areas.json`; giữ `version: 92` theo quy ước nhánh task.

## Kiểm chứng

- **Đỏ → xanh:** kiểm thử mới mô phỏng preview `2=Old Church`, sau đó candidate đổi thành `Church of the Village`; trước sửa, trường hợp này không bị ràng buộc theo bí danh; sau sửa lệnh trả lỗi và writer không được gọi.
- **Xanh:** 22 test liên quan đạt, gồm toàn bộ `tests/test_kho_place_alias.py`, 4 test hành vi A2f hiện có và 2 test ánh xạ khu vực DevSys.
- `py tools/related_areas.py tools/kho_place_alias.py tests/test_kho_place_alias.py devsys/areas.json` xác định vùng `assets` và `devsys`; không có khu vực gọi code bị thay đổi.
- Rà KỸ độc lập: không còn P1/P2 cho phê duyệt ID+bí danh, whitelist môi trường backup và thay đổi candidate giữa preview/apply. Kiểm tra `git diff --check` sạch.
- Một kiểm tra tổng thể `AreaMapTests.test_every_test_file_of_the_real_repo_maps_to_an_area` vẫn báo file có sẵn `tests/test_kpi_goc.py` chưa được gắn khu vực; đây là lỗi nền ngoài phạm vi. Hai kiểm tra ánh xạ còn lại xanh, bao gồm kiểm tra file mã và tên file/cờ.

## Giới hạn và bước bàn giao

- Chưa chạy trên `data/manifest.sqlite` thật, chưa ghi alias thật và chưa kiểm tra đầu ra bằng người dùng; phiên chính có thể chạy preview chỉ đọc rồi trình các đề xuất để người dùng duyệt.
- Ví dụ preview: `py tools/kho_place_alias.py --db <đường-dẫn-cơ-sở-dữ-liệu>`.
- Chỉ sau khi xem chính xác đề xuất mới dùng thao tác ghi được cho phép: `py tools/kho_place_alias.py --db <đường-dẫn-manifest> --lam-that --duyet "12=Clock Tower"`. Việc này tạo bản sao lưu và ghi đúng cặp đã duyệt; không phải bước Codex 2 đã thực hiện.
