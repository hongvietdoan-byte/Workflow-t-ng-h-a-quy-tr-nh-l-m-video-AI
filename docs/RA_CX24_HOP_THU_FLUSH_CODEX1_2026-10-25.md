# CX24-HOP-THU-FLUSH — Codex 1, 25/10/2026

## Lỗi và cách sửa

Helper cũ dựng lại toàn bộ khoảng 1.000 file metadata vào thư mục union, fsync từng file rồi lại dựng snapshot cache remote. Một lô nhỏ giữ khóa nhiều phút; PID chết còn có thể để khóa mồ côi. Bằng chứng vận hành trong đề bài và các phiên helper N9/TIN/nhận việc của Codex 1, không phải lỗi mất kết nối hay hết hạn mức.

- Kiểm raw/archive/receipt trong bộ nhớ bằng parser dùng chung; chỉ ghi diff vào index Git riêng, không mang code HEAD/staged lên main. Một barrier fsync cho phần scratch của lô; các ghi điều khiển lease/cache vẫn dùng atomic riêng, không tuyên bố tổng toàn chương trình chỉ có một fsync.
- Blob Git lạnh đọc theo batch và kiểm lại OID; cache remote thành một bundle atomic thay hàng nghìn file. Giữ khả năng đọc cache snapshot cũ, ID bất biến, union receipt/archive và lỗi cùng ID khác nội dung.
- Khóa JSON có PID, định danh lần sinh tiến trình, token, giờ bắt đầu/gia hạn. Kernel guard ngắn điều phối thao tác khóa; heartbeat gia hạn. PID chết, PID tái sử dụng hoặc lease xác minh được quá 600 giây không gia hạn được lưu khóa cũ vào `_luu_tru` trước khi nhận khóa mới. PID hợp lệ nhưng không xác minh được thì không giành; khóa legacy thiếu PID dùng tuổi file để tương thích.
- Writer phải kiểm lại token trước push và trước cache/cleanup; chủ cũ không xóa khóa của chủ kế tiếp. Windows dò tiến trình bằng API HANDLE, không dùng `os.kill(pid, 0)`.
- Hết thời gian chờ khóa: giữ pending, mã 0, báo “đã xếp hàng, lô sau sẽ đẩy”, không báo “Đã gửi”. Lỗi I/O/parse/whitelist/Git thật vẫn báo thất bại. Chỉ EACCES/EAGAIN của byte lock được coi là tranh khóa.
- Mỗi lệnh Git có timeout 30 giây; quá giờ báo lỗi chung và giữ queue, không in command/stdout hay coi là đã gửi.

## Bằng chứng kiểm tra

- RED đầu: 4 test flush thất bại. Rà độc lập bắt và sửa lỗi báo gửi giả, bỏ kiểm token khi guard bận, giành khóa PID không xác minh được; thêm RED→GREEN lỗi Windows EIO bị coi là tranh khóa.
- Root cuối gom unit flush + hồi quy store + native perf: **63 passed, 2 skipped / 20,65 giây**; hai ca physical symlink không có quyền Windows được skip theo bộ cũ, không coi là đã chạy. Không cộng trùng lượt unit builder 62 passed.
- **Native lạnh, 1.000 sự kiện cũ + 3 mới: flush 6,273 giây** trên bản cuối (mốc trước 6,102 giây), dưới mục tiêu 20 giây. Remote chỉ có 3 đường dẫn đổi, HEAD/index staged giữ nguyên, queue được dọn sau xác minh remote. Đây là Git bare giả trong TEMP trên máy Windows hiện tại; không đo trực tiếp hộp thư sản xuất.
- Native Git/concurrency/acceptance cũ: **11 passed / 40,64 giây**, gồm hai tiến trình đẩy đồng thời, không mất sự kiện và không đưa code riêng/staged lên remote.
- CLI hộp thư cũ + cảnh báo G3: **28 passed / 25,80 giây**.
- Test thay OBJECT `os.environ` bằng dict giả; HOME/config giả, Git chỉ remote file trong TEMP, không credential thật/provider/API/desktop. Không archive/ack hoặc thử reclaim khóa trên hộp thư thật.

## Bàn giao

Nhánh `codex/v31-hop-thu-flush`, worktree `.codex-wt/v31-hop-thu-flush`; đăng ký hai file test mới ở devsys, giữ version92, không thêm cờ. `related_areas.py` xác nhận khu vực devsys; reviewer độc lập RÀ KỸ bản cuối **0 P1/P2 còn mở**, root đọc lại hai lượt trước commit. Tổng các nhóm root không trùng là 102 passed, 2 skipped; chưa chạy cả bộ tích hợp hoặc benchmark nhiều nghìn receipt.

Helper nhận việc cũ tại mailbox worktree đang chạy theo phiên riêng; không kill/bypass/xóa khóa/queue thủ công và không chạy writer thứ hai cùng worktree. M6.10 thuộc Codex 3; M6.10B được phân Codex 1 theo thư 232823-wdcc, bắt đầu phần độc lập sau việc ưu tiên này, chờ M64/M610 gộp trước nối writer/UI. Không sửa dữ liệu dự án, main code hoặc tiến trình Dashboard.
