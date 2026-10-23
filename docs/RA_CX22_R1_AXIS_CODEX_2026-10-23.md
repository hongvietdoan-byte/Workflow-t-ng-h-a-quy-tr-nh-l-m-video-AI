# Báo cáo CX22-R1-AXIS — đối chiếu trục shot 17→18

Ngày: 23/10/2026  
Nhánh: `codex/v31-r1-axis`  
Phạm vi: kết luận theo lựa chọn A trong hộp thư; chỉ đọc tài liệu, mã nguồn và bằng chứng lịch sử được phiên chính gửi. Không mở `data/`, manifest, ảnh/plate thật; không chạy công cụ lên dự án #31; không sửa mã hoặc dữ liệu.

## Kết luận

**KHÔNG XÁC MINH; nhiều khả năng là cảnh báo nhầm do world map và blocking không cùng trạng thái thời gian.** Đây không phải kết luận đã xem lại độc lập ảnh hoặc dữ liệu #31. Theo sự kiện hộp thư `20261023-105209-codex-t2h6.json`, ảnh đã duyệt 1103/1111 được phiên chính mô tả là shot 17 có địch bị tường che và shot 18 có địch ở bên phải. Cùng sự kiện ghi blocking hiện tại vẫn mô tả địch đứng sau tường, trong khi world map round `cc_20261016_104931` ghi địch đã nằm từ nhịp 15. Vì các nguồn mô tả khác thời điểm/trạng thái, dữ kiện hiện có không chứng minh nhân vật thật sự vượt trục.

Sự kiện trên cũng ghi số đo: yaw shot 17 là 169,6°, shot 18 là 174,0°; khi tính từ map/camera đã lưu, checker báo đổi bên phải→trái dù hai camera cùng phía trục. Đây là kết quả được phiên chính cung cấp, chưa được tôi tái chạy hay xác nhận từ dữ liệu gốc.

## Đối chiếu mã nguồn tĩnh

`core/position_invariants.py:263-281`, hàm `check_axis_jumps`, lấy vị trí từng thực thể qua `world_map.position_sentence`, rồi báo `R1-AXIS-JUMP` khi cùng thực thể đổi `left`↔`right` giữa hai shot liền nhau và `same_side_of_axis(...) is True`. Đoạn kiểm tra này không xét trạng thái hiện/ẩn hoặc che khuất. Do đó, khi world map giữ một thực thể ở trạng thái “đã nằm” còn blocking/ảnh biểu thị nó vẫn bị che hoặc ở trạng thái khác, checker có thể so sánh hai trạng thái không tương thích và phát cảnh báo.

## Giới hạn xác minh và việc phụ

Không có xác minh trực tiếp cho ảnh 1103/1111, nội dung blocking, world map hoặc các tệp stage của dự án #31 vì yêu cầu hiện tại cấm đọc dữ liệu và ảnh thật. Cũng chưa đủ bằng chứng trong các sự kiện được đọc để giải thích vì sao cảnh 3 thiếu `blocking.json`, hoặc vì sao chỗ đứng chính K1 của cảnh 4 chưa được đo. Đã gửi câu hỏi qua hộp thư cho phiên chính để làm rõ hai mục này; chúng được để **chưa xác minh**, không suy đoán nguyên nhân.

## Đề xuất B cho việc riêng sau này

Nếu cần loại bỏ nhóm cảnh báo tương tự, đề xuất tạo hợp đồng dữ liệu về trạng thái hiện/ẩn và che khuất theo nhịp/shot, có nguồn và thời điểm hiệu lực rõ ràng. `check_axis_jumps` chỉ so sánh cùng thực thể khi trạng thái hiện diện tương thích ở cả hai shot; trạng thái thiếu hoặc mâu thuẫn cần trả VÀNG/không rõ kèm nguồn gây lệch. Việc này cần đề bài riêng, test đỏ→xanh trên fixture tổng hợp và rà các caller trước khi sửa checker. Báo cáo này không triển khai đề xuất đó.
