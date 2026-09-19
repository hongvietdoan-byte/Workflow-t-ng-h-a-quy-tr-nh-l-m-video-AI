# TODO — Theo dõi tiến độ dự án Auto Pipeline Video AI

_Cập nhật lần cuối: 2026-09-19. Chi tiết kế hoạch xem `PLAN.md`. Đánh dấu `[x]` khi xong, ghi ngày cạnh mục._

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
- [x] Script parser docx → cảnh/nhân vật; FFmpeg command builders (concat/crossfade/mux nhạc); validators JSON cho Director/QC; lưu + khóa Character Bible; Pre-flight IP check + blocklist seed (2026-09-19)
- [x] Prompt templates (Director, QC, video motion, music brief) + `qc_checklist` + knowledge pack v0.1 (2026-09-19)
- [x] 3 MCP server vỏ mỏng: `project-db`, `qc-agent`, `ffmpeg-studio` + hướng dẫn `docs/V0_SETUP.md`; 36 test pass (2026-09-19)
- [x] Bước 3 core (lưu/duyệt motion prompt, `ready_for_video`), Pause/Resume/Cancel-all; Dashboard Streamlit V1 skeleton `dashboard/app.py` (stepper 7 tab, control bar, nút từng khâu, lịch sử) — Claude steps dán JSON tay; 44 test pass (2026-09-19)
- [x] 2 kịch bản mẫu `samples/` (parser tách đúng 6 cảnh mỗi file); PLAN.md Mục 9 = trạng thái triển khai (2026-09-19)
- [x] Lớp core Python: schema SQLite + state machine + luồng `auto`/`human_qc` + retry/escalate, 10 unit test pass (`core/`, `tests/`) (2026-09-19)

## ⏸ Tạm gác (theo yêu cầu 2026-09-19)
- [ ] API Clip AI/Kling (kiểm tra REST/webhook) và đọc tài liệu API Deepix (`deepix-1.4.1`) — làm sau; các module không cần API làm trước

## 🚧 Đang làm / kế tiếp (ưu tiên từ trên xuống)
- [ ] Cài FFmpeg trên máy (chưa có; chưa chạy thử render thật) — việc của người dùng hoặc duyệt cho tôi cài qua winget
- [ ] Cấu hình Claude Desktop theo `docs/V0_SETUP.md` và chạy thử luồng V0 thật
- [ ] Dashboard: chạy thử với dữ liệu thật + tinh chỉnh UI theo mockup (grid ảnh, badge, thanh tiến độ)
- [ ] Dashboard: nhúng "LLM runner" API (V1, cần API key Anthropic) thay cho dán JSON tay
- [ ] Vùng "chờ review" 0.6–0.85 cho QC (PLAN Comment 3) — tuỳ chọn
- [ ] MCP `deepix`, `clipai` (cần API — sau khi hết tạm gác); `music` để sau
- [ ] Knowledge Base + eval set cho Bước 1 & 3 (PLAN.md Mục 3.6); chọn "chuyên gia miền" duyệt
- [ ] Dry-run V0 với `samples/script_demo_1.docx`, `script_demo_2.docx` (đã có 2 kịch bản mẫu; cần Claude Desktop + MCP cấu hình)
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
