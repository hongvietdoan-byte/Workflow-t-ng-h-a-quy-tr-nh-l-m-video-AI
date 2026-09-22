# Dự án: Auto Pipeline sản xuất Video AI

Repo: `D:\AI-Video-Pipeline`, GitHub `hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI` (private), nhánh `main`. Nguồn kế hoạch: `PLAN.md` (Mục 5 = quyết định chốt/mở, Mục 7 = lộ trình, Mục 9 = trạng thái). Tiến độ + việc tồn đọng: `TODO.md`.

## Quy ước bắt buộc (từ CLAUDE.md của repo)
- Sửa `PLAN.md` → phải chạy `bash tools/build_docs.sh` để build lại `PLAN.docx`/`PLAN.pdf`, commit cùng lúc.
- Luôn cập nhật `TODO.md` trong cùng commit.
- Luôn commit + push lên `main`; message có dòng `Co-Authored-By`.
- Không commit secrets/API key; `deepix-*` và `data/manifest.sqlite` ngoài git.
- Đầu session mới: `git pull`, đọc `PLAN.md` Mục 5/7/9 và `TODO.md`.

## Trạng thái (2026-09-22)
Dashboard Streamlit là giao diện chính (V1). `operating_mode` mặc định `human_qc`, QC Agent = Claude Vision. Đã có: core + state machine, adapter thật Deepix (ảnh) + Clip AI (Kling/Seedance + audio), LLM runner Anthropic, ước tính chi phí, ghép/render, knowledge pack, Kho tài nguyên (FF 293+ mục), phân quyền theo email, autopilot, giám sát/chẩn đoán từng khâu.

**530 unit test pass** (`py -m unittest discover -s tests -t .` từ `D:\AI-Video-Pipeline`; Python `py` launcher chạy được trên Windows máy này).

## Việc Claude tự làm được vs. cần user
Phần lớn việc còn lại trong `TODO.md` (mục "Đang làm/kế tiếp", "Việc cần người dùng") đòi hỏi user tự thao tác: chạy thử tốn credit thật (Clip AI/Deepix), đăng nhập SSO xem Network tab, xem video YouTube xác minh nhân vật, quyết định `video_model` mặc định, điền bảng giá thật. Claude chỉ tự làm được việc code/test thuần túy — ví dụ chạy lại bộ test sau khi đổi schema DB, sửa test lỗi thời, sửa bug rõ ràng trong code.

## Lỗi/workaround đã gặp (tránh lặp lại)
- Token API (`CLIPAI_TOKEN`, `DEEPIX_TOKEN`, `ANTHROPIC_API_KEY`) chỉ đặt ở biến môi trường Windows của user, không bao giờ ghi vào repo/chat/log.
- Heredoc bash chứa ký tự đặc biệt/tiếng Việt dễ lỗi encoding → dùng Write/Edit tool thay vì heredoc khi tạo file có tiếng Việt.
- Python (`py`, bản Store) không thấy `%APPDATA%\Claude\...` → sửa config Claude Desktop bằng PowerShell/Read/Edit tool, không dùng Python.
- MiniMax không có trong API Clip AI (chỉ Kling Omni và Seedance).
- Repo đã chuyển private; dùng chung nhiều người vẫn tạm gác (xem TODO.md mục "Tạm gác").

## 2026-09-22 — Setup memory repo trong chính repo dự án
**Context**: User có hệ thống memory sync đa máy định nghĩa trong `~/.claude/CLAUDE.md` (global, mọi dự án) nhưng `{{GITHUB_RAW_BOOTSTRAP}}`/`{{MEMORY_DIR}}` chưa điền — placeholder rỗng, không tự đoán URL để chạy `irm | iex` (rủi ro thực thi mã lạ).
**Finding**: User chọn phương án lưu memory trong thư mục `.claude-memory/` ngay bên trong repo dự án này (thay vì repo riêng), đồng bộ qua git pull/push cùng code. `~/.claude/CLAUDE.md` đã được cập nhật trỏ `MEMORY_DIR` = `D:\AI-Video-Pipeline\.claude-memory`. Trên máy khác: chỉ cần `git clone` repo này vào đúng đường dẫn `D:\AI-Video-Pipeline` là dùng được ngay, không cần script bootstrap riêng.
**Source**: user nói trực tiếp trong chat.
