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

## 2026-09-22 — Quyết định về tính năng ClipAI/Deepix (sau khi rà slide chính thức)
**Context**: User có bộ ảnh slide chính thức ClipAI/Deepix ở `Get this Skill to Claude/Tài nguyên tham khảo để AI làm tốt hơn/` — luôn kiểm tra thư mục này trước khi hỏi lại về giá/model/tính năng, có thể câu trả lời đã nằm sẵn trong đó.
**Finding**:
- **Bàn đạo diễn** (3D director's desk ClipAI) — tạm gác, không điều tra thêm.
- **Không dùng Kho chủ thể Seedance** (`core/adapters/clipai_subjects.py`, panel "🧩 Kho chủ thể" Bước 1) — user thấy không hiệu quả. Ưu tiên: ảnh tài nguyên đã gắn cho cảnh (`assets.scene_references`) làm tham chiếu cho CẢ Deepix lẫn Clip AI (cơ chế này đã có sẵn, không cần Kho chủ thể). Code cũ vẫn giữ, không xoá, nhưng đừng đề xuất user thử/dùng nó nữa.
- **Video tham chiếu chuyển động** (`reference_video`) — hạ ưu tiên thử thật; ưu tiên `knowledge/ff_character_skills_visual.md` (mô tả skill bằng chữ). Nhưng code ĐÃ hỗ trợ gửi đồng thời ảnh tham chiếu + video tham chiếu chuyển động cùng lúc (không loại trừ nhau) — dùng khi cần.
- **Lip-sync (Đồng bộ môi) trên ClipAI còn Beta** — user không muốn đầu tư, ưu tiên gen video có thoại bằng prompt trực tiếp (Kling `sound`/Seedance `generate_audio`).
- **Blocklist IP thu hẹp**: hiện tại chỉ dùng nhân vật Free Fire (đã có bản quyền), chưa cần blocklist IP khác.
- **`video_model` mặc định — có gợi ý nhưng CHƯA chốt**: theo slide chính thức, Kling 3.0 Omni ghi rõ "tái sử dụng nhân vật, đối thoại nhiều nhân vật" — khớp nhu cầu dự án (nhân vật FF lặp lại + hội thoại nhiều người) và rẻ nhất ($0.08/s). Đã đề xuất với user, đang chờ họ xác nhận lần cuối trước khi đặt làm mặc định.
**Source**: user nói trực tiếp trong chat kèm 6 ảnh chụp slide + 1 ảnh chụp UI lip-sync beta của ClipAI.

## 2026-09-22 — Đối chiếu + bổ sung dữ liệu 65 nhân vật FF từ Google Sheet nội bộ
**Context**: User chia sẻ Google Sheet nội bộ ("Data for Viet Mabu", cần đăng nhập Google — Claude in Chrome không kết nối được trong phiên này, phải nhờ user tự đăng nhập trong browser pane của Claude vì Claude không được phép tự nhập email/mật khẩu).
**Finding**: (1) Sheet có tab `char_Skill` (id/key/name/isActive/hardId/roleIds/sex/age/birthday + link ảnh icon), `char_Role` (1=Tấn công,2=Thông tin,3=Sinh tồn,4=Đồng đội), `char_Hard` (1=Dễ,2=Trung bình,3=Khó). Đối chiếu 65 nhân vật: khớp 100% với Kho tài nguyên, 24 `isActive:TRUE` khớp đúng danh sách đã xác nhận qua API `wiki.ff.garena.vn` trước đó — không phát hiện khác biệt (2 lần tưởng thấy khác biệt hoá ra do đọc nhầm ảnh chụp màn hình ở zoom 100%, phải đọc lại kỹ hơn). (2) Giới tính/tuổi/sinh nhật trong sheet **trùng lặp** với dữ liệu đã đồng bộ sẵn từ ff.garena.com (core/ff_site.py) — không cần bổ sung lại. (3) Đã bổ sung độ khó + vai trò gameplay (dữ liệu MỚI, chưa có) vào mô tả cả 65 nhân vật qua `tools/enrich_ff_role_difficulty.py` (script re-run an toàn, tự skip nếu đã có block `[Độ khó & vai trò gameplay]`).
**Bài học quan trọng — xác minh video qua trình duyệt của Claude KHÔNG hiệu quả**: thử với A124, trình duyệt chỉ chụp được khung hình tĩnh theo thời gian thực (không tua/seek chính xác), tốn ~15 thao tác mà vẫn lỡ đúng khoảnh khắc kích hoạt skill. User đã quyết định (2026-09-22): tạm gác cách Claude tự xem video, quay về cách cũ hiệu quả hơn — user tự xem rồi báo lại mô tả cho Claude ghi vào file (đã dùng thành công với Kenta trước đó). **Áp dụng cho tương lai**: đừng đề xuất Claude tự "xem video" để lấy thông tin chính xác — chỉ hữu ích cho việc đọc trang web/dữ liệu tĩnh, không phải xem chuyển động/video.
**Nguồn**: user chia sẻ link Google Sheet trực tiếp trong chat + tự đăng nhập trong browser pane.

## 2026-09-22 — Setup memory repo trong chính repo dự án
**Context**: User có hệ thống memory sync đa máy định nghĩa trong `~/.claude/CLAUDE.md` (global, mọi dự án) nhưng `{{GITHUB_RAW_BOOTSTRAP}}`/`{{MEMORY_DIR}}` chưa điền — placeholder rỗng, không tự đoán URL để chạy `irm | iex` (rủi ro thực thi mã lạ).
**Finding**: User chọn phương án lưu memory trong thư mục `.claude-memory/` ngay bên trong repo dự án này (thay vì repo riêng), đồng bộ qua git pull/push cùng code. `~/.claude/CLAUDE.md` đã được cập nhật trỏ `MEMORY_DIR` = `D:\AI-Video-Pipeline\.claude-memory`. Trên máy khác: chỉ cần `git clone` repo này vào đúng đường dẫn `D:\AI-Video-Pipeline` là dùng được ngay, không cần script bootstrap riêng.
**Source**: user nói trực tiếp trong chat.
