# Rà Đ19 việc 4 — 20/10/2026

- Root RÀ NHẸ độc lập source/hợp đồng, không chạy code: xác nhận tên _hosted_pictures thay tên audit cũ, D03b và các veto/deadline/fence/unknown giữ đúng. Bổ sung ACL service viewer/editor/Owner/worker và giới hạn lộ dữ liệu khác dự án, cùng mốc lifecycle sau restore/reopen để không dùng retention cũ. Đây là đặc tả đề xuất Cấp 2/3 chưa triển khai; không pytest giả/SQL/API/asset thật.

RÀ NHẸ tài liệu; tự đối chiếu nguồn tại 7c41073c, không phải rà độc lập code.

- Đã đọc CLAUDE, TODO mới nhất, CHUAN_XAY_DUNG, skill vòng làm việc, CODEX_TASKS Đ19v4, gói sửa §3, master §4b và tracked decisions D03b.
- Đối chiếu actual subjects cache/picture_refs/overview/delete/rejected/cleanup/schedule, runner, delivered/archive, factory, ClipAI list/upload/delete và send_claim.
- Sửa lệch tên nguồn: audit gọi `_subject_refs`; base thực tế `_hosted_pictures:1637`, factory tại 1657, picture_refs tại 1667.
- Số 185/95/84 chỉ dẫn nguồn audit, không khẳng định số đo hiện tại hay đọc DB thật.
- Thiết kế phủ scope/SHA, transaction cấp chỗ, quarantine unknown, frozen refs, outbox/fence mọi writer, strict >72h, Cấp 2/3 và rollback legacy hazards.
- Không nhận face-only, xóa ngay TẠM/active approved, quota 60/40 hoặc fit 5 dự án làm quyết định.
- Không chạy code/test/SQL/API; chưa xác minh production, chưa sửa G59, chưa xóa asset.
- Việc mở: định nghĩa nháp cũ, inventory writer trước build, identity/idempotency/timestamp và duyệt phạm vi triển khai riêng.
