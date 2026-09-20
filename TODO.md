# TODO — Theo dõi tiến độ dự án Auto Pipeline Video AI

_Cập nhật lần cuối: 2026-09-20 (nhóm việc tự động đã xong: Seedance, QC review zone, SFX/TTS, LLM runner, waveform, runbook)._ Chi tiết kế hoạch xem `PLAN.md`. Đánh dấu `[x]` khi xong, ghi ngày cạnh mục._

## 📌 Bàn giao sang phiên chat khác (chốt 2026-09-20)
**Trạng thái:** repo `main` đã push đầy đủ, **196 unit test pass**. Đã có: core + state machine + luồng `auto`/`human_qc` (kèm vùng chờ review); Dashboard Streamlit theo mockup, mở như phần mềm bằng shortcut Desktop (`Start-Dashboard.bat`); **adapter thật Deepix (ảnh), Clip AI (Kling Omni + Seedance) và Clip AI audio (nhạc/SFX/TTS)**; **LLM runner gọi API Anthropic** (Director/QC/motion, có `mock`); ước tính chi phí + sổ mức dùng (ảnh/clip/âm thanh); ghép + render (cut/crossfade/dip-to-black, nhạc, SFX, giọng đọc); knowledge pack (kể cả `seedance_prompting.md`); bộ đánh giá `eval/`; runbook `docs/RUNBOOK.md`. **Đã chạy thật (2026-09-19):** token Clip AI/Deepix OK; 1 ảnh + 1 clip Kling + 1 clip Seedance (số liệu ở `docs/api_notes.md`). **Chưa chạy thật:** audio Clip AI, LLM runner với key Anthropic, một cảnh end-to-end qua Dashboard.
**Nhóm việc tôi (Claude) tự làm được: đã hết.** Còn lại đều cần người dùng (mục "Việc cần người dùng" và "Đang làm / kế tiếp"), theo ưu tiên: (1) đo giá thật → điền `data/pricing.json`; (2) chạy 1 cảnh thật qua Dashboard (thử Seedance 1080p, cảnh cận cảnh/hành động) để chọn `video_model` mặc định; (3) thử Bước 5a với API audio thật; (4) hỏi admin về API key Anthropic rồi thử LLM runner; (5) chạy vòng đánh giá `eval/` + dry-run 2 mode để hiệu chỉnh threshold.

**Cách tiếp tục:** `git pull` → đọc `CLAUDE.md`, `PLAN.md` (Mục 5 quyết định, Mục 7 lộ trình, Mục 9 trạng thái), `docs/RUNBOOK.md` (vận hành) và file này. Chạy test: `py -m unittest discover -s tests -t .`. Mở Dashboard: shortcut **AI Video Pipeline** trên Desktop (tạo bằng `tools/make_shortcut.ps1`) hoặc `py -m streamlit run dashboard/app.py`; xem thử không tốn credit: `py tools/seed_demo.py` + `powershell -File tools/run_demo.ps1`.

**Quyết định đã chốt:** 1 Dashboard duy nhất theo thứ tự bước; `operating_mode` mặc định `human_qc`; QC Agent = Claude Vision; V0 (Claude Desktop + MCP, dán JSON tay) → V1 (Dashboard + API Anthropic); Clip AI (đa model: Seedance/Kling/MiniMax + audio) **đã có API**, dùng polling; ngân sách V0 nhỏ (~2 kịch bản, 10–20 clip); repo đã private; MCP Claude/V0 tạm gác; dùng chung nhiều người/đăng ký user chỉ bàn lại khi quy trình ổn định (mục "Tạm gác").

**Lưu ý kỹ thuật (đã gặp lỗi, tránh lặp):**
- **Token API** (`CLIPAI_TOKEN`, `DEEPIX_TOKEN`) chỉ đặt trong biến môi trường PowerShell của người dùng; **không bao giờ** ghi vào repo/chat/log. Nhập bằng `Read-Host` (lệnh SecureString kiểu `PtrToStringAuto` đã từng cho kết quả 1 ký tự — dùng `NetworkCredential`). Kiểm tra: `py -m core.adapters.check`; thử thật (tốn credit): `py -m core.adapters.trial --yes`; chỉ đọc: `py -m core.adapters.inspect_api --usage`.
- Khi tạo/sửa file có chuỗi thoát byte hoặc xuống dòng bằng script Python trong heredoc, ký tự thoát dễ bị ghi sai (đã làm hỏng 1 commit): dùng Write/Edit tool, hoặc `bytes([0x..])`, rồi **chạy test trước khi commit/push**.
- Deepix trả ảnh JPEG dù ta lưu đuôi `.png` (adapter Clip AI gửi đúng định dạng theo nội dung).
- MiniMax **không** có trong API Clip AI (chỉ Kling Omni và Seedance).
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
- [x] Thử Seedance 2.0 (720p): 167s, 1280x720, 3,6MB, chất lượng gần Kling (Kling 84s, 1080p, 10,7MB); trial lưu file riêng từng model; so sánh ghi ở `docs/api_notes.md` (2026-09-19)
- [x] `core.adapters.inspect_api` (chỉ đọc): xem trường trả về/có trường chi phí không + thống kê mức dùng Clip AI (`--usage`). Tài liệu API không có endpoint số dư/giá (2026-09-19)
- [x] Ước tính chi phí trong Dashboard: `core/cost.py` + `data/pricing.json` (bảng giá do bạn điền, chưa có số bịa), ước tính trước khi chạy (min/max nếu retry), sổ ghi mức dùng `usage_events` mỗi lần gửi API thật, dòng "đã ghi nhận" trên thanh điều khiển, chốt xác nhận cho batch từ `confirm_batch_at` mục trở lên; 108 test pass (2026-09-19)
- [x] LLM runner API Anthropic (`core/llm_runner.py`): Director / QC (Vision) / motion prompt chạy bằng nút trong Dashboard, cùng prompt bundle + validator với dán tay; JSON sai thì tự hỏi lại 1 lần kèm lỗi; retry 429/5xx có backoff; QC agent tự đưa `issues` cụ thể vào lý do gen lại ảnh; chỉ tạo motion prompt cho cảnh chưa có (không ghi đè bản đã duyệt); key chỉ ở `ANTHROPIC_API_KEY`, không lọt vào lỗi; `LLM_PROVIDER=mock` để thử offline. Chưa gọi API thật, chưa ghi token vào sổ chi tiêu (2026-09-20)
- [x] Waveform thật cho nhạc (peaks từ wav/ffmpeg, SVG), Dashboard không còn crash khi file ảnh hỏng (`show_image`); 168 test pass (2026-09-20)
- [x] Sửa Character Bible ngay trong Dashboard (đổi tên cập nhật cả danh sách nhân vật của cảnh; khóa/mở khóa) — `llm_io.update_character` / `unlock_character_bible` (2026-09-20)
- [x] Sổ mức dùng có âm thanh: `usage_events` thêm `project_id`, `job_id` tùy chọn, loại `audio` (tự migrate DB cũ, giữ dữ liệu); mỗi bản nhạc/SFX/TTS gửi đi được ghi; bảng giá `per_audio` trong `data/pricing.json`; dòng chi tiêu trên Dashboard hiện số âm thanh (2026-09-20)
- [x] SFX + giọng đọc (TTS) ở Bước 5a: tạo, nghe thử, chọn đưa vào bản ghép với thời điểm bắt đầu + âm lượng; Bước 5b trộn bằng ffmpeg (`build_extras_mix_cmd`, adelay/amix; nhạc nền ngắn hơn video vẫn đúng độ dài). Đã render thử thật: dip-to-black + nhạc + SFX = 6,0s đúng; 148 test pass (2026-09-20)
- [x] `knowledge/seedance_prompting.md` (chắt lọc tài liệu Seedance 2.0/2.5: 10 nguyên tắc, cấu trúc khung-hình-đầu → sự kiện → camera → kết, giai đoạn cho clip dài, negative viết tích cực, checklist); tự nối vào bundle motion prompt khi `video_model` là seedance (2026-09-20)
- [x] Vùng "chờ review" cho QC (auto mode): điểm trong [mức sàn, threshold) không tự loại mà chờ người duyệt; cột `projects.qc_review_floor` (migration tự động), điều khiển ở Bước 2 (2026-09-20)
- [x] Transition "Dip to black" (xfade fadeblack) ở Bước 5b; 133 test pass (2026-09-20)
- [x] Duyệt hàng loạt có xác nhận Có/Không: Bước 2 "Duyệt tất cả (N ảnh)" và Bước 3 "Duyệt tất cả (N prompt)" — bấm một lần hiện câu hỏi, chỉ "Có, duyệt hết" mới duyệt; nếu danh sách chờ thay đổi thì hỏi lại. Duyệt từng ảnh vẫn bấm ngay tại ảnh. human_qc: điểm cao vẫn chờ người duyệt (2026-09-20)
- [x] Ảnh điểm thấp tự loại + xếp hàng gen ảnh mới, ở cả hai chế độ: mức sàn `qc_reject_floor` mặc định 0,50 (chỉnh 0,30–0,80, ví dụ 0,70; tắt được) ở Bước 2; lỗi cụ thể của QC vào lý do gen lại; ảnh mới chỉ gen khi bạn bấm chạy; quá số lần retry thì escalated (2026-09-20)
- [x] Thùng rác (`core/trash.py`): 2 thư mục riêng `trash/images` và `trash/videos` trong từng dự án; ảnh bị loại, ảnh/clip bị xóa (nút 🗑) và clip bị thay bằng bản gen lại đều vào đây; tab Lịch sử có mục 🗑 Thùng rác (xem, khôi phục); **tự xóa vĩnh viễn sau 30 ngày** (`TRASH_DAYS` chỉnh được, kiểm tra tối đa mỗi giờ); khôi phục không ghi đè file đang có; 196 test pass (2026-09-20)
- [x] Mỗi ảnh/video ghi rõ **Cảnh số mấy** và có mũi tên sổ xuống "📖 nội dung kịch bản" (đoạn kịch bản gốc + bối cảnh/nhân vật/mood/prompt ảnh, video thêm motion prompt) để đối chiếu với kịch bản: Bước 2 (thẻ ảnh + panel chi tiết tự mở), Bước 3, Bước 4, Bước 5b, Lịch sử; 175 test pass (2026-09-20)
- [x] Bảng giá chỉnh ngay trong Dashboard (💲 Bảng giá): giá theo đúng thiết lập trên web Clip AI (`model:mức:Ns` → `model:mức` → giá mỗi giây), ước tính từng clip theo độ dài riêng; thiếu giá clip nào thì không bịa tổng; lưu thẳng `data/pricing.json`; 174 test pass (2026-09-20)
- [x] Runbook vận hành `docs/RUNBOOK.md` (cài đặt, biến môi trường, quy trình 7 bước, chế độ QC, xử lý sự cố, chi phí, sao lưu, cập nhật, bảo mật) — hạng mục đóng gói V1 (2026-09-20)
- [x] Mở Dashboard như phần mềm: `Start-Dashboard.bat` (đúp chuột: tự cài thư viện lần đầu, đọc `dashboard.env`, tìm ffmpeg, mở cửa sổ kiểu app bằng Edge/Chrome; chạy lần 2 thì chỉ mở lại cửa sổ), `Stop-Dashboard.bat`, `tools/make_shortcut.ps1` tạo shortcut + icon `tools/icon.ico` ra Desktop; cấu hình không bí mật ở `dashboard.env` (mẫu `dashboard.env.example`), token vẫn ở biến môi trường; log ở `data/dashboard.log`. Lưu ý: shortcut đi qua junction ASCII `%LOCALAPPDATA%\AIVideoPipeline` vì WScript.Shell không lưu được ký tự tiếng Việt trong đường dẫn; chạy lại `tools/make_shortcut.ps1` nếu di chuyển thư mục repo (2026-09-20)
- [x] Dashboard chỉnh theo mockup: theme (`.streamlit/config.toml`, `dashboard/ui.py`), thanh đầu trang (thương hiệu, chế độ dạng segmented, threshold, Pause/Resume/Cancel màu), stepper 7 bước có dấu ✓ khi xong, Bước 1 hai cột (Character Bible + badge IP + bảng phân cảnh), Bước 2 lưới thẻ ảnh + chip lọc + panel chi tiết QC bên phải, Bước 3 hàng có ảnh nhỏ, Bước 4 thanh tiến độ + thẻ risk control + danh sách job có badge, Bước 5a 3 thẻ nháp, Bước 5b chia 2 cột, Lịch sử dạng lưới phiên bản. Công cụ dev: `tools/seed_demo.py` (dữ liệu demo, không tốn credit) + `tools/run_demo.ps1`; đã kiểm tra bằng trình duyệt; 128 test pass (2026-09-19)
- [x] Dashboard Bước 5b: tự nạp clip từ Bước 4 theo thứ tự cảnh (cảnh thiếu được cảnh báo), tick chọn clip, xem thử, độ dài đọc thật bằng ffmpeg (sửa được), crossfade + thời gian fade, âm lượng nhạc, kiểm tra trước khi render, xem/tải FINAL_VIDEO.mp4; sửa lỗi nhạc ngắn hơn video làm video bị cụt (thêm `apad`). Đã render thử thật với ffmpeg (crossfade 3s+4s + nhạc 2s → 6,0s đúng); 128 test pass (2026-09-19)
- [x] Repo GitHub đã chuyển private (2026-09-19)
- [x] Audio Clip AI: adapter `core/adapters/clipai_audio.py` (music_v2, SFX, TTS, danh sách giọng; không tự gửi lại khi lỗi) + `core/music.py` (mock, bản nháp, chọn nhạc) + Dashboard Bước 5a tạo 3 bản nháp/nghe thử/chọn (`AUDIO_PROVIDER=clipai|mock`, mặc định theo `VIDEO_PROVIDER=clipai`); 121 test pass. Chưa gọi API audio thật, chưa ghi credit audio vào sổ mức dùng (2026-09-19)
- [x] Lớp core Python: schema SQLite + state machine + luồng `auto`/`human_qc` + retry/escalate, 10 unit test pass (`core/`, `tests/`) (2026-09-19)

## ⏸ Tạm gác
- **Kiểm tra API Clip AI có trả trường chi phí không** (`py -m core.adapters.inspect_api`, chỉ đọc, không tốn credit; cần `CLIPAI_TOKEN` trong terminal) — tạm gác vì đang làm việc từ xa, không chạy lệnh được (2026-09-20). Đã xác nhận từ tài liệu chính thức: không có endpoint giá/số dư và phản hồi `video-list` không có trường chi phí; còn khả năng trường không công bố trong phản hồi thật. Trong lúc đó chép giá từ web vào 💲 Bảng giá.
- **Dùng chung nhiều người + quản lý người dùng (chỉ nhắc lại khi quy trình đã chạy ổn định, hoàn thiện — theo yêu cầu 2026-09-20).** Đã bàn, ghi lại để khỏi bàn lại từ đầu:
  - Hai mô hình: **A** mỗi người chạy trên PC mình (mỗi người 1 database + token riêng) — đề xuất bắt đầu bằng A; **B** một máy chủ chung, mọi người vào bằng địa chỉ web (1 database chung; cần đăng nhập SSO công ty — Streamlit có `st.login`, phân quyền, máy chủ luôn bật, database chịu nhiều người ghi, token nằm trên máy chủ).
  - Đăng ký tên người dùng: nên làm. Lần đầu mở hỏi tên/email, gắn vào `usage_events` (ai gửi API) và `review_log` (ai duyệt/từ chối); thêm màn "Chi tiêu" theo người/dự án/model; hạn mức theo người (mở rộng bước xác nhận batch `confirm_batch_at`).
  - Lưu ý: chi tiêu trong app chỉ là ước tính (cần `data/pricing.json`); nguồn chính xác là web Clip AI/Deepix, nếu mỗi người dùng token riêng thì nền tảng tự thống kê theo tài khoản. Tên đăng ký chỉ là ghi nhận, không phải bảo mật; muốn chặn/phân quyền thật cần đăng nhập (mô hình B).
  - Câu hỏi cần trả lời khi nhắc lại: số đồng nghiệp, cùng làm 1 dự án hay riêng, token riêng hay chung, công ty có máy chủ/VM nội bộ không.
  - Nếu cần phát cho nhiều người không cài Python: đóng gói `.exe` (PyInstaller) — chỉ làm khi thật cần.
- MCP Claude / V0 trong Claude Desktop (tạm gác từ 2026-09-19; tập trung build Dashboard). Các mục dry-run V0 và "mở lại Claude Desktop" bên dưới chờ mở lại.

## 🚧 Đang làm / kế tiếp (ưu tiên từ trên xuống)
- [ ] **Tối ưu giao diện Dashboard một thể** — đã kiểm kê khung từng bước ở `docs/UI_AUDIT.md` (+ ảnh `docs/images/audit_2026-09-20/`); chờ người dùng rà và chọn hướng (mục D), chưa sửa gì. Chưa kiểm tra màn hình điện thoại
- [ ] **Bạn làm:** thoát hẳn + mở lại Claude Desktop, rồi chạy thử V0 trong Chat theo `docs/V0_SETUP.md` mục 3 (config đã ghi sẵn, đã kiểm thử qua MCP stdio)
- [ ] **Bạn làm:** thử Bước 5a với API thật (`$env:AUDIO_PROVIDER="clipai"`, tốn credit) để xác nhận hợp đồng audio; nếu lệch thì báo lại để sửa adapter
- [ ] Dashboard: chạy thử với dữ liệu thật; đã đủ so với mockup
- [ ] **Bạn làm (khi có key):** chạy thử LLM runner với `ANTHROPIC_API_KEY` thật (Director / QC / motion trong Dashboard); nếu API trả khác dự kiến (tên model, giới hạn ảnh, định dạng JSON) thì báo để chỉnh `core/llm_runner.py`. Thử không tốn tiền bằng `LLM_PROVIDER=mock`
- [ ] Đối chiếu hành vi thật của API: negative prompt (`CLIPAI_NEGATIVE=append`?), thông điệp risk control từng model, thời hạn `video_url`, hạn mức credit; ghi vào `docs/api_notes.md`
- [ ] **Bạn duyệt tạm (không cần chuyên gia lúc này):** chạy vòng đánh giá đầu tiên theo `eval/README.md` (12 mẫu, 9 held-out), chấm phiếu thẩm mỹ, chỉnh `knowledge/`/`prompts/` theo lỗi lặp lại, rồi khóa version. Khi có chuyên gia miền thì bàn giao phần chấm thẩm mỹ
- [ ] Dry-run V0 với `samples/script_demo_1.docx`, `script_demo_2.docx` (đã có 2 kịch bản mẫu; qua Dashboard, hoặc Claude Desktop + MCP khi mở lại)
- [ ] Dry-run 2 mode, đo % đồng thuận QC Agent–người → hiệu chỉnh `qc_auto_pass_threshold`

## 👤 Việc cần người dùng quyết định / cung cấp
- [ ] **Chi phí (không cần chạy thử tốn credit):** web Clip AI hiện giá/token cho từng thiết lập **trước khi bấm gen** → mở **💲 Bảng giá** ở đầu Dashboard và chép lại: Kling (std/pro, 5s/10s), Seedance 2.0 (720p/1080p), Seedance 2.5, nhạc/SFX/giọng đọc. Deepix chưa biết giá thì để trống (vẫn đếm số ảnh). Có thể đối chiếu 1–2 giá bằng số tổng đã dùng trên web trước/sau khi chạy thật
- [ ] **Bạn làm:** thử Seedance ở 1080p (`$env:CLIPAI_RESOLUTION="1080p"`) để so công bằng với Kling; rồi chạy **1 cảnh thật qua Dashboard** (`IMAGE_PROVIDER=deepix`, `VIDEO_PROVIDER=clipai`). Gợi ý: thử thêm cảnh có nhân vật cận cảnh/hành động nhanh từ `eval/cases.json` để so 2 model
- [ ] **Lưu ý tài khoản (2026-09-20):** hiện đang dùng tài khoản Claude **cá nhân (email)**, chưa phải doanh nghiệp → hạn mức 400$ chưa áp dụng cho tài khoản này; API key có thể lấy từ Console cá nhân (tự nạp credit + tự đặt giới hạn chi tiêu) hoặc từ tổ chức khi chuyển sang tài khoản doanh nghiệp. Kiểm tra chính sách công ty trước khi đưa nội dung IP game lên tài khoản cá nhân.
- [ ] **API key Anthropic (chỉ khi muốn tự động hóa bằng LLM runner):** hạn mức cứng **400$/tháng của gói doanh nghiệp là cho Chat + Code của tài khoản cá nhân** (dùng chung với các phiên làm việc như phiên code này), **không phải ngân sách API**. Muốn dùng LLM runner cần admin cấp API key riêng (Console, Workspace riêng, giới hạn chi tiêu riêng, vd 200$) và xác nhận chính sách dữ liệu ảnh nhân vật. Cho tới lúc đó dùng cách dán JSON từ Claude Desktop (không cần key, chỉ tốn suất dùng của tài khoản)
- [x] `music_provider` = Clip AI (music_v2/ElevenLabs; đã có adapter, chờ thử thật) — Suno không có API chính thức (2026-09-20)
- [ ] Chọn `video_model` mặc định: `kling` (kling-v3-omni) hoặc `seedance` (MiniMax không có trong API) — sau khi thử thực tế cả hai
- [ ] Chốt framework Dashboard V1: hiện là Streamlit và đã sát mockup; xác nhận giữ nguyên (không cần frontend riêng)?
- [ ] Cấp danh sách nhân vật/IP dự kiến để build blocklist IP v1

## 🐞 Tồn đọng / cần sửa lại
- [ ] Figma: component **Stepper đang chồng lên Screen 1** trên canvas — dời vị trí (Figma MCP đang hết hạn mức Starter; sửa tay hoặc chờ reset)
- [ ] Figma: frame import từ html.to.design là layer tự động — tách từng màn, đặt tên, componentize nếu dùng làm design system
- [ ] Memory repo (`{{MEMORY_DIR}}`/bootstrap URL) trong `~/.claude/CLAUDE.md` chưa điền URL thật → chưa setup được memory sync

## 🗓 Mốc theo PLAN.md (Mục 7)
- [ ] V0 (~3–4 tuần): pipeline end-to-end qua Claude Desktop + MCP, threshold đã hiệu chỉnh
- [ ] V1 (~+3–4 tuần): Dashboard hợp nhất + Anthropic API + nhạc nền + đóng gói/runbook — **code đã xong**, còn chạy thật + hiệu chỉnh (cần key Anthropic và credit)
