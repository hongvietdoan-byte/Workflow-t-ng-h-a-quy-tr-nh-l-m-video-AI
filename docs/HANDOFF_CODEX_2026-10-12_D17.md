# Bàn giao Codex sau Đ17 — 12/10/2026

## Đã làm, chỉ push nhánh
- Đ17v1 `codex/d17-viec1-dao-cu`: code `3b072ca3` + `2064df8b`, kết quả `7b3352f2`; 91 test +30 subtests xanh. User chốt súng khóa ưu tiên nền rộng phụ, giữ nền chính/storyboard; POV chỉ VÀNG vẫn chạy, không thêm gun lock refs/prompt. Cùng súng/dạng dùng chung ảnh đã có; collage nhiều món để sau, chưa thử model.
- Đ17v2 `codex/d17-viec2-popup-shot`: code `e129832c`, kết quả `2296962b`; 102 test +10 subtests xanh và focused video 6 đỏ→6 xanh. Flag shot_popup OFF/OPT_IN_ONLY, UI/ffmpeg timeline/âm/pixel thật trên dữ liệu giả đã kiểm.
- Đ17v3 `codex/d17-viec3-ten-kho`: code `e55255ca`; 154 test +4 subtests xanh, rà2finding sửa. Flag asset_english_names OFF/OPT_IN_ONLY. Kết quả trong CODEX_TASKS nhánh này.
- Mỗi nhánh có RA/HANDOFF và ảnh1440/1280. Chưa cả bộ Windows/model thật/gộp main/pull live/restart.

## Việc kế, theo bảng ưu tiên mới nhất
1. Đ15v3 vùng an toàn mọi lớp phủ; lấy origin/main mới. Popup Đ17v2 phải được gộp hoặc lấy đúng phần thiếu code `e129832c` trước sửa, không nhân đôi chức năng safe_box đã có.
2. Đ12v5 đồng thanh: worktree `D:\AI-Video-Pipeline\.codex-wt\d12-viec5-dong-thanh`, branch `codex/d12-viec5-dong-thanh`, bản lưu dở `d197de0c` đã push, base b8782dfe. Code đã 50 test xanh + rà3finding/cache tiền sửa; root đọc diff. Còn GUI/đóng RA/kết quả trước coi hoàn tất; docs/HANDOFF_D12_VIEC5_CODEX_2026-10-12.md có trạng thái. Giữ source WAV, readonly liveDB binding, OFF chọn primary+C, legacy chỉ gen B khi bật.
3. Đ11v1b bảng đánh giá cho người dùng chốt TRƯỚC mockup; rồi Đ14v3, project_budget gộp, Đ12v6, các việc còn lại theo bảng đầu CODEX_TASKS.
- #24 đã XONG; #27 đang chạy. Nhóm runner cuối danh sách vẫn chờ user/phiên máy chính chốt. Tin autoqc 17:58 gửi phiên rà Codex, chưa tự đổi thứ tự.

## Luật tiếp tục
- Gọi usage trước child; % là ĐÃ DÙNG. Cuối lượt83% đã dùng/17% còn; reset5h lúc22:47:22 ngày12/10 giờ Việt Nam, tuần27% đã dùng. Chưa mở việc lớn kế. Không reset credit/mua credit; user đã xóa lịch tiếp tục, KHÔNG tạo lại automation.
- Đọc AGENTS/CLAUDE/CHUAN/skill; fetch, đọc mailbox/TODO/CODEX_TASKS origin/main mới nhất. Không đổi nhánh/pull/restart live D:\AI-Video-Pipeline, không realdata/env/API.
- Mỗi việc nhánh riêng, đỏ→xanh, rà độc lập + callerCLAUDE7, root đọc vòng sửa, code/tests/flags areas giữ version, commit tiếng Việt+Codex, kết quả CODEX_TASKS rồi push nhánh. Không TODO/PLAN, không main.
- QA dùng DB/ảnh giả và temp ASSET_DIR/FEATURE_SETTINGS_FILE/KNOWLEDGE_USER_DIR; helper thumbnail có cache phải neo temp. Các server QA8519 đã dừng.
