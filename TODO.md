# TODO — Theo dõi tiến độ dự án Auto Pipeline Video AI

_Cập nhật lần cuối: 2026-09-19. Chi tiết kế hoạch xem `PLAN.md`._ Đánh dấu `[x]` khi xong, ghi ngày cạnh mục.

## 🔁 Việc phải làm lại MỖI LẦN (checklist cố định)
- [ ] Sửa nội dung kế hoạch → chỉ sửa `PLAN.md`, không sửa tay docx/pdf
- [ ] **Build lại `PLAN.docx` + `PLAN.pdf` bản mới nhất:** `bash tools/build_docs.sh`
- [ ] **Cập nhật `TODO.md` này** (tick việc xong, thêm việc mới, đổi ngày cập nhật)
- [ ] `git add` các file liên quan → commit (có dòng `Co-Authored-By`) → **push lên GitHub** (`main`)
- [ ] Không commit secrets/API key; file Deepix (`deepix-*`) giữ ngoài repo (đã có trong `.gitignore`)
- [ ] Đầu session mới: `git pull`, đọc `PLAN.md` Mục 5 (quyết định) và file này

## ✅ Đã xong
- [x] Phân tích docx gốc + 4 comment, viết `PLAN.md` (2026-09-18)
- [x] Chốt `operating_mode` auto/human_qc, `qc_agent_provider` = Claude Vision (2026-09-18)
- [x] Bổ sung kiến trúc hợp nhất 1 Dashboard, stepper 5 bước, nút điều khiển từng khâu (2026-09-19)
- [x] Chốt V0/V1, kiến trúc core + MCP mỏng + LLM runner (2026-09-19)
- [x] Chốt V0: `human_qc` mặc định, ngân sách credit nhỏ (2026-09-19)
- [x] Mockup HTML tương tác (`mockup/`) + import đủ 7 màn vào Figma (2026-09-19)
- [x] Xuất `PLAN.docx`/`PLAN.pdf` + `tools/build_docs.sh` + `CLAUDE.md` quy ước repo (2026-09-19)
- [x] Đưa Deepix package ra ngoài repo bằng `.gitignore` (2026-09-19)

## 🚧 Đang làm / kế tiếp (ưu tiên từ trên xuống)
- [ ] **Kiểm tra Clip AI/Kling có REST API (+webhook) không** — chặn thiết kế `mcp-server-clipai` (nếu chỉ Web → Playwright, +1–2 tuần)
- [ ] Đọc `deepix-1.4.1` (tài liệu API Deepix) → ghi endpoint/auth/rate limit vào PLAN.md
- [ ] Khởi động lớp core Python: schema SQLite (`scenes`, `jobs`, `qc_results`, `content_moderation_failures`, `review_log`) + state machine
- [ ] Build MCP `project-db`, `deepix`, `qc-agent`, `clipai`, `ffmpeg` (V0); `music` để sau
- [ ] Knowledge Base + eval set cho Bước 1 & 3 (PLAN.md Mục 3.6); chọn "chuyên gia miền" duyệt
- [ ] Chuẩn bị 2 kịch bản mẫu (5–10 cảnh) cho dry-run V0
- [ ] Dry-run 2 mode, đo % đồng thuận QC Agent–người → hiệu chỉnh `qc_auto_pass_threshold`

## 👤 Việc cần người dùng quyết định / cung cấp
- [ ] Chuyển repo GitHub sang **private** (người dùng tự làm)
- [ ] Xác nhận API Clip AI/Kling (hỏi team dev nội bộ)
- [ ] Hỏi admin Claude Enterprise: có Console org / API key Anthropic cho V1 không, hạn mức token, chính sách data ảnh nhân vật
- [ ] Chọn `music_provider` (Suno không có API chính thức; ứng viên ElevenLabs Music, cần xác minh) — không chặn V0
- [ ] Chọn framework Dashboard V1: Streamlit hay web frontend riêng (nếu cần sát mockup Figma)
- [ ] Cấp danh sách nhân vật/IP dự kiến để build blocklist IP v1

## 🐞 Tồn đọng / cần sửa lại
- [ ] Figma: component **Stepper đang chồng lên Screen 1** trên canvas — dời vị trí (Figma MCP đang hết hạn mức Starter; sửa tay hoặc chờ reset)
- [ ] Figma: frame import từ html.to.design là layer tự động — tách từng màn, đặt tên, componentize nếu dùng làm design system
- [ ] Memory repo (`{{MEMORY_DIR}}`/bootstrap URL) trong `~/.claude/CLAUDE.md` chưa điền URL thật → chưa setup được memory sync

## 🗓 Mốc theo PLAN.md (Mục 7)
- [ ] V0 (~3–4 tuần): pipeline end-to-end qua Claude Desktop + MCP, threshold đã hiệu chỉnh
- [ ] V1 (~+3–4 tuần): Dashboard hợp nhất + Anthropic API + nhạc nền + đóng gói/runbook
