# Bản lưu dở Đ12 việc 5 — chưa nghiệm thu đầy đủ

- Nhánh `codex/d12-viec5-dong-thanh`, base `b8782dfe`; cờ unison_dialogue OFF/OPT_IN_ONLY, areas.version giữ60.
- 50 test liên quan xanh/22,00s; độc lập rà3finding đã sửa, thêm cache tiền legacy OFF→ON chỉ tạo B mới. Root đã đọc diff vòng sửa.
- LiveDB binding qua PRAGMA và đọc readonly; thiếu profile/schema/WAV/context chặn trước gửi; OFF giữ primary+C và WAV gốc.
- Trim silence đầu vào WAV dẫn xuất/cache SHA, mọi consumer cùng clock; onset proxy luôn VÀNG, không ASR/xác minh từng chữ.
- Đây là commit lưu an toàn phần đang dở, KHÔNG coi việc hoàn tất: còn QA GUI1440/1280, ghi Kết quả Codex, thử chất lượng người/model thật và cả bộ Windows trước gộp.
- Theo thứ tự mới: làm Đ15v3 trước, rồi quay lại nhánh này; Đ17v1–3 đã push. Đọc docs/HANDOFF_CODEX_2026-10-12_D17.md trên nhánh d17-viec3-ten-kho.
- Khi quay lại fetch/readmainmailbox, đối chiếu dependency/areas/flags mới. Không reset/merge/pull live hoặc API/data thật. Không tạo lại automation đã xóa.
