# TODO — Theo dõi tiến độ dự án Auto Pipeline Video AI

_Cập nhật lần cuối: 2026-09-19. Chi tiết kế hoạch xem `PLAN.md`. Đánh dấu `[x]` khi xong, ghi ngày cạnh mục._

## 📌 Bàn giao sang phiên chat khác (chốt 2026-09-19)
**Trạng thái:** repo `main` đã push đầy đủ; 58 unit test pass; cấu hình Claude Desktop (`mcpServers`: project-db, qc-agent, ffmpeg-studio) đã ghi và kiểm thử qua MCP stdio thật. **Đang chờ bạn:** thoát hẳn + mở lại Claude Desktop rồi chạy thử V0 trong tab Chat (`docs/V0_SETUP.md` mục 3), báo kết quả/lỗi cho phiên sau.

**Cách tiếp tục:** `git pull` → đọc `CLAUDE.md`, `PLAN.md` (Mục 5 quyết định, Mục 7 lộ trình, Mục 9 trạng thái) và file này. Chạy test: `py -m unittest discover -s tests -t .`. Dashboard: `py -m streamlit run dashboard/app.py`.

**Quyết định đã chốt:** 1 Dashboard duy nhất theo thứ tự bước; `operating_mode` mặc định `human_qc`; QC Agent = Claude Vision; V0 (Claude Desktop + MCP, dán JSON tay) → V1 (Dashboard + API Anthropic); Clip AI (đa model: Seedance/Kling/MiniMax + audio) **đã có API**, dùng polling; ngân sách V0 nhỏ (~2 kịch bản, 10–20 clip); repo sẽ chuyển private.

**Lưu ý kỹ thuật (đã gặp lỗi, tránh lặp):**
- Python (`py`, bản Store) **không thấy** `%APPDATA%\Claude\...` → đọc/sửa config Claude bằng PowerShell hoặc Read/Edit tool, không dùng Python.
- Heredoc bash chứa nhiều ký tự đặc biệt/tiếng Việt hay lỗi → dùng Write tool tạo file rồi chạy; `pkill -f "streamlit run"` sẽ tự giết shell.
- FFmpeg cài qua winget (đường dẫn trong `FFMPEG_PATH` của config); shell mới mới thấy `ffmpeg` trong PATH.
- Figma MCP hết hạn mức gói Starter; mockup đầy đủ ở `mockup/*.html` và đã import vào Figma bằng plugin html.to.design.
- `deepix-*` và `data/manifest.sqlite` nằm ngoài git (`.gitignore`).
- Sau mỗi thay đổi `PLAN.md`: `bash tools/build_docs.sh` rồi commit cả `PLAN.docx`/`PLAN.pdf`.


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
- [x] Cài FFmpeg 9.0.1 qua winget; render thật đã chạy thử OK (cut 8s / crossfade 7s, có nhạc) (2026-09-19). Lưu ý: shell mới mới thấy `ffmpeg` trong PATH; shell cũ đặt `FFMPEG_PATH`
- [x] Bộ chạy Bước 4 không cần API thật: provider interface + `MockVideoProvider`, `VideoRunner` (submit/heartbeat poll/tải video/risk-control log không retry/transient retry/concurrency/pause/cancel), MCP `clipai`, nối Dashboard Bước 4 (`VIDEO_PROVIDER=mock`); 53 test pass. Khi có API chỉ cần viết adapter `VideoProvider` (2026-09-19)
- [x] Bộ chạy Bước 2 (`ImageRunner` + `MockImageProvider`, dùng chung vòng heartbeat với Bước 4; prompt retry tự thêm "Fix: <ghi chú reject>"), nối Dashboard Bước 2 (`IMAGE_PROVIDER=mock`); 58 test pass (2026-09-19)
- [x] Cấu hình Claude Desktop (`mcpServers`: project-db, qc-agent, ffmpeg-studio; có bản sao lưu `.bak-20260919`); smoke test toàn luồng V0 qua MCP stdio thật OK (12+8+1 tool) (2026-09-19)
- [x] Bước 2 Knowledge Base: `knowledge/genre_guides.md` (7 thể loại + công thức image prompt), `ai_image_failure_modes.md`, few-shot từ `eval/golden.json`; bộ đánh giá 12 mẫu `eval/cases.json` + bộ chấm tự động + phiếu duyệt (`py -m core.evalset ...`); nối vào prompt Director/QC/motion (+MCP `get_motion_prompt_bundle`); 69 test pass. Người duyệt: chủ dự án (tạm) (2026-09-19)
- [x] Ghi nhận Clip AI = nền tảng đa model (Seedance, Kling, MiniMax; Seed Audio, ElevenLabs; game assets): PLAN Mục 3.3b, `video_model` theo dự án (DB + runner + Dashboard Bước 4), music_provider ưu tiên Clip AI; 71 test pass (2026-09-19)
- [x] Nghiên cứu ~10 repo đạo diễn/prompt phim AI: `knowledge/sources.md` (độ tin cậy, license, cách dùng), `knowledge/research_notes.md` (16 nguyên tắc + 8 chiều điện ảnh), đã nối vào prompt Director/motion và thêm check "từ khen rỗng" cho eval (2026-09-19)
- [x] Đã có API Clip AI; bỏ các sơ đồ/tài liệu xin duyệt API khỏi repo (2026-09-19)
- [x] Đọc 2 skill Deepix 1.4.1 và Clip AI 1.3.1; viết adapter thật `core/adapters/` (HTTP stdlib, Deepix Seedream 5.0 Pro, Clip AI Kling Omni + Seedance, factory theo env, kiểm tra kết nối chỉ đọc), runner chịu lỗi mạng/risk control, `docs/api_notes.md`; 92 test pass. Thư mục skill để ngoài git (2026-09-19)
- [x] Kết nối thật đã xác nhận: Clip AI OK (537 tác vụ trong tài khoản) và Deepix OK; sửa lỗi nhập token (lệnh SecureString cũ của tôi sai → dùng `NetworkCredential`); thêm `core.adapters.trial` (1 ảnh + 1 clip, cần `--yes`); 98 test pass (2026-09-19)
- [x] Chạy thật OK: ảnh Deepix 31s (JPEG 2048x1152), clip Kling 84s (1920x1080, 24fps, 5s, ~10.7MB), nhân vật nhất quán, camera đúng prompt; adapter gửi ảnh đúng định dạng thật; 99 test pass. Kết quả ghi ở `docs/api_notes.md` (2026-09-19)
- [x] Lớp core Python: schema SQLite + state machine + luồng `auto`/`human_qc` + retry/escalate, 10 unit test pass (`core/`, `tests/`) (2026-09-19)

## ⏸ Tạm gác (theo yêu cầu 2026-09-19)

## 🚧 Đang làm / kế tiếp (ưu tiên từ trên xuống)
- [ ] **Bạn làm:** thoát hẳn + mở lại Claude Desktop, rồi chạy thử V0 trong Chat theo `docs/V0_SETUP.md` mục 3 (config đã ghi sẵn, đã kiểm thử qua MCP stdio)
- [ ] Dashboard: chạy thử với dữ liệu thật + tinh chỉnh UI theo mockup (grid ảnh, badge, thanh tiến độ)
- [ ] Dashboard: nhúng "LLM runner" API (V1, cần API key Anthropic) thay cho dán JSON tay
- [ ] Vùng "chờ review" 0.6–0.85 cho QC (PLAN Comment 3) — tuỳ chọn
- [ ] Adapter audio Clip AI (nhạc `music_v2`, TTS, SFX) cho Bước 5a + `mcp-server-music`
- [ ] Tối ưu prompt Seedance theo tài liệu chính thức 2.0/2.5 (`Get this Skill to Claude/clipai-1.3.1/clipai/references/*optimizer.md`, 15 KB + 65 KB): chắt lọc thành `knowledge/seedance_prompting.md` và áp dụng khi `video_model` là seedance
- [ ] Đối chiếu hành vi thật của API: negative prompt (`CLIPAI_NEGATIVE=append`?), thông điệp risk control từng model, thời hạn `video_url`, hạn mức credit; ghi vào `docs/api_notes.md`
- [ ] **Bạn duyệt tạm (không cần chuyên gia lúc này):** chạy vòng đánh giá đầu tiên theo `eval/README.md` (12 mẫu, 9 held-out), chấm phiếu thẩm mỹ, chỉnh `knowledge/`/`prompts/` theo lỗi lặp lại, rồi khóa version. Khi có chuyên gia miền thì bàn giao phần chấm thẩm mỹ
- [ ] Dry-run V0 với `samples/script_demo_1.docx`, `script_demo_2.docx` (đã có 2 kịch bản mẫu; cần Claude Desktop + MCP cấu hình)
- [ ] Dry-run 2 mode, đo % đồng thuận QC Agent–người → hiệu chỉnh `qc_auto_pass_threshold`

## 👤 Việc cần người dùng quyết định / cung cấp
- [ ] Chuyển repo GitHub sang **private** (người dùng tự làm)
- [ ] **Bạn làm:** thử Seedance với ảnh đã có: `py -m core.adapters.trial --yes --model seedance --image data/trial/trial_image.png` và so sánh với Kling (chất lượng, thời gian); rồi chạy 1 cảnh thật qua Dashboard (`IMAGE_PROVIDER=deepix`, `VIDEO_PROVIDER=clipai`)
- [ ] Hỏi admin Claude Enterprise: có Console org / API key Anthropic cho V1 không, hạn mức token, chính sách data ảnh nhân vật
- [ ] Chọn `music_provider`: ưu tiên audio của Clip AI (ElevenLabs/Seed Audio) nếu API mở; Suno không có API chính thức — không chặn V0
- [ ] Chọn `video_model` mặc định: `kling` (kling-v3-omni) hoặc `seedance` (MiniMax không có trong API) — sau khi thử thực tế cả hai
- [ ] Chọn framework Dashboard V1: Streamlit hay web frontend riêng (nếu cần sát mockup Figma)
- [ ] Cấp danh sách nhân vật/IP dự kiến để build blocklist IP v1

## 🐞 Tồn đọng / cần sửa lại
- [ ] Figma: component **Stepper đang chồng lên Screen 1** trên canvas — dời vị trí (Figma MCP đang hết hạn mức Starter; sửa tay hoặc chờ reset)
- [ ] Figma: frame import từ html.to.design là layer tự động — tách từng màn, đặt tên, componentize nếu dùng làm design system
- [ ] Memory repo (`{{MEMORY_DIR}}`/bootstrap URL) trong `~/.claude/CLAUDE.md` chưa điền URL thật → chưa setup được memory sync

## 🗓 Mốc theo PLAN.md (Mục 7)
- [ ] V0 (~3–4 tuần): pipeline end-to-end qua Claude Desktop + MCP, threshold đã hiệu chỉnh
- [ ] V1 (~+3–4 tuần): Dashboard hợp nhất + Anthropic API + nhạc nền + đóng gói/runbook
