# HANDOFF — Codex 06/10/2026

Bản tích hợp G-a + hai nhánh cloud nằm trên `codex/s14-14-ga-review`.

- G-a: bật UI v2 mặc định, gỡ bố cục cũ Kịch bản / Video / Theo dõi; giữ CSS/header theo cờ tới G-b. Báo cáo `docs/RA_GA_CODEX_2026-10-06.md`.
- Cloud: S14.24, S14.25 Đợt 6a, S14.45, S14.50, S14.51, P1; bốn test hồi quy mới đỏ→xanh. Báo cáo `docs/RA_CLOUD_CODEX_2026-10-06.md`.
- Không gộp code S14.29; chỉ giữ bản lưu trong `docs/cat_giu/`.
- `devsys/areas.json` version 24: tăng một lần cho bản tích hợp; đủ file mới, test và cờ.
- Chờ cả bộ test bản tích hợp xanh trước khi push main. Không gọi API trả phí; chưa pull hoặc khởi động lại máy Windows chính.

Bước tiếp sau khi push: S14.47(2), rồi G-b / G-c / S13.3 / S13.10. S14.12 người dùng tự chạy trên Dashboard; mọi việc trả phí phải hỏi trước.
