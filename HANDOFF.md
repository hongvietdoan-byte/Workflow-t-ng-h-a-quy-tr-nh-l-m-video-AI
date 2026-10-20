# Bàn giao Đ20 việc 2

Tranche capture/validation synthetic xong, **M1.9a OPEN**. Nhánh `codex/d20-viec2-golden`, gốc `c0ab784a`; chi tiết và lệnh #24/#27 COMPAT, #31/#33 CORRECTNESS ở `docs/RA_D20_VIEC2_CODEX_2026-10-20.md`.

17 test xanh sau rà độc lập (2 P2 đã sửa, đỏ 4 failed/13 passed → xanh 17 passed); fixture DB lấy SCHEMA thật bằng AST, không import app; không live data/API. Chưa có current-builder replay hoặc bằng chứng chất lượng thật. Bước kế: cung cấp input trước lắp gói từ snapshot, dùng `core.sent_package.build` với timestamp/external id cố định ở test rồi nối current production builder sau M1.2; byte comparator hiện chưa chứng minh đường đó.

Giữ nguyên areas version. Không push, không sửa TODO/kế hoạch/main. Phiên chính rà độc lập rồi quyết định công bố tranche; không đánh dấu việc 2 hoàn tất toàn bộ.
