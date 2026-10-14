# Bàn giao đề bài Đ18 việc 4

- Nhánh `codex/d18-viec4-de-bai`, base `46ac70ba`.
- Đã viết đề `docs/DE_BAI_D18_VIEC4_REGISTRY_A_2026-10-14.md`, nối mục Đ18v4 trong CODEX_TASKS, ghi dòng hòm thư TODO trên nhánh để phiên rà/gộp đưa lên main.
- RÀ NHẸ: tự rà 2b.5 và root đọc toàn đề/diff; bổ sung snapshot read transaction/CAS nhiều aggregate/continuation theo revision. Báo cáo RA cùng thư mục.
- Docs-only: không build code/test/areas/flags/PLAN, không API/Blender/data thật/live/main. Không tạo test đỏ giả; diff --check sạch.
- Đ18v1–3 và SFX đã main; registry A thực tế chưa triển khai. Người dùng đã chọn A, nhưng đề/schema/store/migration mới còn CHỜ DUYỆT; không hiểu im lặng là duyệt.
- Đề xuất store SQLite trong manifest, immutable revisions/CAS/ACL, migration dry-run giữ raw legacy, locks/proposals/approved layout_drift; chia 4a–4f. Không phụ thuộc anchor_by_spot (giữ OFF), own_camera không neo.
- Sau duyệt mới build từng nhánh. Queue portable dependency `codex/ban-dao-dien-hieu-nang` chưa main; không viết queue khác. Bộ góc/animatic/editor/Camera cùng A.
- An toàn mọi prompt/test: patch.object thay OBJECT os.environ bằng dict giả trước import/call/spawn; mock registry/credentials/provider/model, native whitelist env; pytest --tb=no; không đọc/in/assert/repr môi trường/token/payload bí mật. Không data thật/dashboard.env/API trả phí/main merge/live pull/restart/admin_auth/maintenance worker.
