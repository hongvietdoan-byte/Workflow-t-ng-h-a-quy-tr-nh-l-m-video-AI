# Dự án: Auto Pipeline sản xuất Video AI

Kế hoạch chính nằm ở `PLAN.md` (nguồn tài liệu gốc: `Quy_Trinh_Auto_Pipeline_Full1.docx`). Mockup giao diện ở `mockup/`.

## Quy ước làm việc (áp dụng cho mọi session/tài khoản)
1. **Luôn commit và push** mọi thay đổi lên GitHub: https://github.com/hongvietdoan-byte/Workflow-t-ng-h-a-quy-tr-nh-l-m-video-AI (branch `main`).
2. **Mỗi khi `PLAN.md` thay đổi, phải build lại `PLAN.docx` và `PLAN.pdf`** rồi commit cùng lúc:
   ```
   bash tools/build_docs.sh
   ```
   (cần pandoc + Chrome/Edge; script tự tìm trình duyệt). Hai file này luôn phải khớp `PLAN.md` mới nhất để người khác/session khác theo dõi.
3. Sửa nội dung kế hoạch trong `PLAN.md` (nguồn duy nhất); không sửa tay `PLAN.docx`/`PLAN.pdf`.
4. Khi bắt đầu session mới: `git pull` trước, đọc `PLAN.md` (Mục 5 = quyết định đã chốt/còn mở, Mục 7 = lộ trình).
5. Commit message có dòng `Co-Authored-By` theo cấu hình session; không commit secrets/API key.

## Mockup
- `mockup/dashboard.html` — bản tương tác (bấm stepper; `#s2`… để mở thẳng bước).
- `mockup/dashboard_all.html` — tất cả màn xếp dọc (dùng import Figma bằng plugin html.to.design).
- Figma: https://www.figma.com/design/NjEZBllciYNbZwIntemWbd (gói Starter đã hết hạn mức MCP).
