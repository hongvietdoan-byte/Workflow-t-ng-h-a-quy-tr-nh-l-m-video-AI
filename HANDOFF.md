# Bàn giao CX20-5 / Đ20 việc 5

Nhánh `codex/d20-viec5-kho-chu-the`, base `3fec1686`, xem `docs/RA_D20_VIEC5_CODEX_2026-10-20.md`.

- Đã build guard OFF + giữ queued không fallback khi Kho đầy/unknown; G59 tái dùng client đã cấu hình; cleanup cũ chuyển DRY-RUN bắt buộc C3-3; CLI DB/snapshot read-only; candidate policy bảo thủ.
- Đỏ7 → xanh42 (3 file,5,54s). Một đỏ UI vòng2 là fake env thiếu home, đã sửa harness, không nới assert.
- Không paid API, không dữ liệu thật/env production/migration/cờ/live/main/push/TODO/plan/restart. Version areas87 giữ nguyên.
- Root/reviewer tiếp: xem OPEN trong RA, đặc biệt parser snapshot thiếu/trang ngắn mâu thuẫn count; rà độc lập rồi sửa gom một vòng. CLI dependency legacy UNKNOWN đúng chủ ý, chưa owners/lifecycle chuẩn; allocator/reservation/fairness/fence/apply chưa làm. Không tuyên bố đủ5 dự án hoặc hoàn tất M1.5.
- Khi tích hợp cần cả bộ Windows (related_areas báo slow bắt buộc), không bật cờ hoặc chạy xóa thật. Chỉ root quản lý push/mailbox/gộp.
