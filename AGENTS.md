# AGENTS.md — hướng dẫn cho Codex (và agent khác ngoài Claude Code)

Dự án: Auto Pipeline sản xuất video AI (Streamlit dashboard + core Python). Trả lời / ghi chú / commit bằng **tiếng Việt**.

## Đọc trước khi làm (theo thứ tự)
1. `CLAUDE.md` — quy ước bắt buộc (commit + push `main`, build `PLAN.docx/pdf` khi đổi `PLAN.md`, cập nhật `TODO.md` cùng commit, không commit secret).
2. `TODO.md` — khối 📌 mới nhất ở đầu mục "🚧 Đang làm / kế tiếp" (bàn giao từ phiên Claude: bước kế, nhánh dở, quyết định người dùng).
3. `docs/CHUAN_XAY_DUNG.md` — 8 luật xây dựng + luật chi phí (không im lặng khi thiếu đầu vào; "đã sửa" kèm bằng chứng chạy thật; gen lại phải đổi đầu vào; mọi lời gọi tốn tiền qua sổ chi + ước tính trước).
4. `.claude/skills/vong-lam-viec-theo-plan/SKILL.md` — vòng làm việc theo kế hoạch (thứ tự việc, mức rà RÀ KỸ / RÀ NHẸ, gộp, ghi trạng thái). Bỏ qua phần riêng của Claude Code (get_usage, Agent, PushNotification); giữ phần quy trình.
5. Kế hoạch: `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` (dòng `> Đợt ưu tiên:`; `py tools/plan_progress.py` cho việc kế) + file kế hoạch chi tiết mà tiêu đề đợt trỏ tới.

## Luật cứng
- **Tiền:** KHÔNG tự chạy gì tốn tiền (ClipAI, Deepix, Kling, Claude API, TTS, Apify…). Liệt kê trần từng việc, hỏi người dùng trước.
- **Dữ liệu:** `data/`, `data/manifest.sqlite`, `dashboard.env` chỉ có ở máy chính `D:\AI-Video-Pipeline`; không commit, không in khóa/token. Sửa dữ liệu thật → sao lưu trước.
- **Test:** đỏ trước, xanh sau; không nới test để che lỗi. Cả bộ: `py -m pytest -q -p no:cacheprovider` (≈ 15–19 phút, Windows). Dùng `py`, đặt `PYTHONUTF8=1`.
- **Git:** làm trên nhánh riêng; gộp vào `main` chỉ sau khi cả bộ test xanh; tăng `devsys/areas.json` `version` một lần ở nhánh tích hợp; file mã mới khai vào `devsys/areas.json`.
- **Sau khi gộp:** `git pull --ff-only` ở `D:\AI-Video-Pipeline`; đổi code `dashboard/` hoặc `core/` → khởi động lại Dashboard (`tools/stop_dashboard.ps1` + `tools/launch_dashboard.ps1`); đổi `devsys/` → khởi động lại cả AI Dev System cổng 8502 (`tools/launch_devsys.ps1`); kiểm `http://localhost:8501/_stcore/health` và `:8502`.
- Ghi trạng thái sau MỖI việc gộp xong: đổi trạng thái trong kế hoạch (✅ + mã commit + bằng chứng) → `py tools/plan_progress.py --write` → `TODO.md` → commit → push.

## Chạy LOCAL trên máy chính `D:\AI-Video-Pipeline` (thư mục này đang chạy Dashboard 8501 + AI Dev System 8502)
- **KHÔNG đổi nhánh / checkout trong `D:\AI-Video-Pipeline`** (Dashboard đang chạy từ đó, luôn ở `main`). Làm mỗi việc trong worktree riêng: `git worktree add D:\AI-Video-Pipeline\.codex-wt\<việc> -b codex/<việc> origin/main`; xong thì gộp vào `main` từ worktree (`git push origin HEAD:main`) rồi `git pull --ff-only` ở `D:\AI-Video-Pipeline`.
- **KHÔNG BAO GIỜ** chạy `git clean`, `git reset --hard`, `git checkout -- .`, `git stash` ở `D:\AI-Video-Pipeline`: có thư mục dữ liệu chưa theo dõi (`KHO TÀI NGUYÊN/`, `_plates3d/`, `data/backup/`, `data/ab_test/`…) và `data/` thật. Dùng `git stash` thì phải `push -m <tên riêng>` và `apply <sha>`.
- Test cần dữ liệu thật (`data/`, `dashboard.env`) chạy ở `D:\AI-Video-Pipeline`; test thường chạy trong worktree. Cả bộ trên Windows bắt buộc trước khi gộp.
- Khóa API nằm ở biến môi trường User + `dashboard.env`: không in, không ghi log, không commit.
- Dừng và hỏi người dùng trước: mọi lời gọi tốn tiền; xóa/ghi đè dữ liệu thật (sao lưu vào `data/backup/` trước); force-push; đổi `dashboard.env`.
