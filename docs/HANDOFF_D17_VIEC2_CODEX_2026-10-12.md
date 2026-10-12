# Bàn giao Đ17 việc 2

- Worktree `D:\AI-Video-Pipeline\.codex-wt\d17-viec2-popup-shot`, nhánh `codex/d17-viec2-popup-shot`, base `3fa1a61c`.
- Đã có popup cuối từng shot, tách nền xanh chọn chủ động, safe box, manifest/diag VÀNG, hash stale, UI một shot đang chọn, save guard phía server.
- File: core/shot_popup.py mới; end_popup.py, delivery.py, final_cut.py, features.py, dashboard/steps/step5.py, devsys/areas.json; tests/test_shot_popup.py mới.
- Kiểm cuối: 71 passed + 10 subtests, 25,00 s; FFmpeg/ảnh/tiếng thật đều tệp temp; test đỏ caller draft chứng minh HEAD chưa gọi popup.
- Báo cáo: docs/RA_D17_VIEC2_CODEX_2026-10-12.md.
- Chưa commit/push theo root; bước kế: root rà độc lập + GUI 1440/1280, gom lỗi sửa một vòng, commit nhánh sau duyệt.
- Không API/tiền, dữ liệu thật, main, pull live/restart; không TODO/PLAN/global HANDOFF, areas version giữ nguyên.

- RÀ KỸ đã sửa gộp 4 lỗi: diag local, guard đường trước IO cho shot/hash, cleanup temp, parser/save cấu hình; selector giữ usable/sort/id và bỏ ảnh mất.
- Nhóm cuối **102 passed + 10 subtests, 22,87 s**; RA ghi đỏ→xanh và giới hạn legacy lookup. Root đọc diff sửa; chưa commit/push.
- Root rà cuối: video/staged normalize trước timeline/cleanup, invalid return VÀNG không IO; thêm focused 6 ĐỎ→6 xanh (0,21 s), không lặp nhóm rộng.
