# Kế hoạch triển khai — Auto Pipeline sản xuất Video AI

Tài liệu này phân tích `Quy_Trinh_Auto_Pipeline_Full1.docx` (bao gồm 4 comment góp ý trong file) và đề xuất giải pháp + định hướng triển khai chi tiết.

## 1. Tóm tắt tài liệu gốc

**Kết luận đã chốt trong doc:** Hệ thống có thể auto 100% về mặt kỹ thuật (từ đọc kịch bản → xuất video), nhưng về nghệ thuật/chất lượng nên dùng mô hình **Hybrid Agentic Workflow** — tự động hóa qua MCP, có User duyệt (Human-in-the-Loop) tại 3 điểm chốt.

**Quy trình 5 bước:**

| Bước | Thành phần kỹ thuật | Điểm kiểm duyệt | Mức tự động |
|---|---|---|---|
| 1. Input kịch bản & phân tích | Claude Director + MCP Script Parser + SQLite | ĐIỂM 1: duyệt Character Bible & bảng phân cảnh | Bán tự động |
| 2. Sinh ảnh cảnh hàng loạt | MCP Deepix Connector (REST API) | ĐIỂM 2 (quan trọng nhất): duyệt ảnh Approve/Reject | Tự động 100% (can thiệp khi cần) |
| 3. QC ảnh & sinh video motion prompt | Claude Vision + Director Prompt | ĐIỂM 3: duyệt nhanh prompt video | Tự động 90% |
| 4. Sinh video từ ảnh | MCP Clip AI / Kling AI API | Không bắt buộc dừng | Tự động 100% |
| 5. Ghép & render video | MCP FFmpeg Studio (local) | Điểm chốt: nghiệm thu cuối | Tự động 100% |

**Lộ trình đề xuất trong doc (4 tuần):** (1) hạ tầng & API, (2) build 4 MCP servers (project-db, deepix, clipai, ffmpeg), (3) Streamlit dashboard + dry-run, (4) đóng gói 1-click startup + bàn giao prompt templates.

## 2. Phân tích các comment (rất quan trọng — đây là các gap chưa được giải trong bản doc)

### Comment 1 — Cần State Machine cho toàn bộ pipeline
> "Nên bổ sung State machine... queued/running/succeeded/failed/retryable(?)/rejected/cancelled — User ở khâu bắt buộc review có thể bắt kịp trạng thái và đưa ra quyết định hợp lý hơn."

**Gap:** Doc mô tả trạng thái rời rạc kiểu tự do (`READY`, `IMAGE_GENERATED`, `VIDEO_PROMPT_READY`) nhưng không có một state machine thống nhất, không có trạng thái lỗi/hủy/retry rõ ràng cho từng job (ảnh, video, render).

**Giải pháp:** Định nghĩa 1 bảng `job_state` dùng chung cho mọi loại tác vụ (scene, image_gen, video_gen, render), với state enum cố định:
`queued → running → succeeded | failed → retryable → (queued lại) | rejected (user reject) | cancelled`.
Mỗi transition được ghi log (audit trail) trong SQLite để Dashboard hiển thị real-time, và để Claude/MCP biết chính xác việc nào cần resume, retry, hay dừng hẳn.

### Comment 2 — Mâu thuẫn về mức độ auto ở bước QC ảnh
> "Đây là bước quan trọng nhất nên mức độ tự động không 100%... Trong trường hợp ưu tiên tự động 100%, user review không quan trọng. Trong trường hợp quan trọng thì cần can thiệp bắt buộc vì job phát sinh sau reject hủy/tạo lại như thế nào."

**Gap:** Doc ghi Bước 2 là "Tự động 100%" nhưng đồng thời gọi đây là "ĐIỂM KIỂM DUYỆT... QUAN TRỌNG NHẤT" — mâu thuẫn nội tại. Chưa định nghĩa rõ: reject thì job con (regenerate ảnh) được tạo lại như thế nào, ai sở hữu retry count, khi nào dừng hẳn.

**Giải pháp:** Tách rõ 2 chế độ vận hành (config theo project/khách hàng):
- **Chế độ Speed** (ưu tiên tốc độ, nội dung ít rủi ro thương hiệu): Claude Vision auto-pass theo ngưỡng, review là optional/async — pipeline không block.
- **Chế độ Quality** (nhân vật/IP quan trọng, video ra mắt chính thức): **bắt buộc** user approve trước khi qua Bước 3, pipeline block (trạng thái `pending_review`) cho tới khi có quyết định.
Khi Reject: tạo `job` mới `image_gen` với `parent_job_id` trỏ về job cũ + ghi `retry_reason` (note của user), tăng `retry_count`; nếu `retry_count` vượt ngưỡng (vd 3 lần) → tự động chuyển state `failed` và escalate cho user thay vì lặp vô hạn.

### Comment 3 — Ngưỡng auto-pass của Claude Vision chưa rõ
> "Có ngưỡng để Claude Vision cho auto-pass không? User có thể quy định/chỉnh sửa ngưỡng cho Claude hay quá trình ảnh hưởng này do lựa chọn mô hình?"

**Gap:** Chưa có cơ chế cấu hình ngưỡng QC (confidence score, checklist tiêu chí) — hiện tại là "hộp đen".

**Giải pháp:** Xây `qc_checklist` cấu hình được (YAML/DB) gồm các tiêu chí cụ thể Claude Vision chấm điểm (vd: đúng nhân vật theo Character Bible, không lỗi tay/mặt, đúng bố cục cảnh, đúng mood màu sắc) — mỗi tiêu chí trả về score 0-1. `auto_pass_threshold` là 1 con số user chỉnh được trong Dashboard (per-project), ví dụ ≥0.85 tự pass, 0.6–0.85 vào hàng chờ review, <0.6 tự động reject + note lỗi cụ thể. Việc chọn model (Claude Vision version) cũng ảnh hưởng độ chính xác score — nên version model dùng phải được pin (không auto-update) để ngưỡng không bị trôi.

### Comment 4 — Batch lớn (>100 video) & vấn đề bản quyền IP bị chặn (Kling AI)
> "Khi tạo 1 batch request lớn (>100 videos)... cần heartbeat check hoặc always allow... Mô hình Kling video 3.0 omni đang ban một số IP (vd Wonder Woman) → Failure to pass risk control system → User nên check trước nhân vật/IP trước khi request gen nhiều video bị fail."

**Gap kép:**
1. **Vận hành/polling:** batch lớn cần cơ chế polling dài hạn không cần user ngồi approve từng request.
2. **Rủi ro nội dung:** nhân vật có thể trùng IP bản quyền (superhero, celeb...) bị Kling AI content-moderation chặn → tốn credit, tốn thời gian mà không biết trước.

**Giải pháp:**
1. MCP Clip AI Connector chạy **heartbeat polling background** (interval cấu hình được, vd mỗi 60-120s) tự động check trạng thái job trên Kling/Clip AI, không cần user "allow" từng lần — chỉ cần approve 1 lần ở đầu batch (long-lived credential/session), Dashboard hiển thị tiến độ real-time (x/100 done).
2. Thêm bước **Pre-flight IP/Content Check** ngay ở Bước 1 (Character Bible): Claude quét mô tả nhân vật, cảnh báo nếu tên/mô tả trùng IP nổi tiếng đã biết bị risk-control chặn (duy trì 1 blocklist cập nhật thủ công/định kỳ từ thực tế fail logs). Nếu phát hiện, cảnh báo sớm cho user **trước khi** chạy batch gen ảnh+video hàng loạt, tránh gen hàng loạt rồi fail hàng loạt ở Bước 4.
3. Ghi log mọi lần fail vì risk-control vào bảng riêng (`content_moderation_failures`) để dần xây blocklist nội bộ từ dữ liệu thực tế.

## 3. Giải pháp & định hướng tổng thể (đã tích hợp comment)

### 3.1 Kiến trúc dữ liệu (SQLite schema đề xuất)
- `scenes` — 1 record/cảnh, cột `state` theo state machine chung (comment 1)
- `jobs` — mọi tác vụ async (image_gen, video_gen, render) đều là 1 job: `id, type, scene_id, parent_job_id, state, retry_count, retry_reason, created_at, updated_at`
- `qc_results` — điểm QC theo tiêu chí (comment 3): `job_id, criterion, score, threshold_at_time, auto_decision`
- `content_moderation_failures` — log fail vì IP/risk-control (comment 4)
- `review_log` — audit trail mọi quyết định của user (approve/reject/note) tại 3 điểm chốt

### 3.2 Cấu hình vận hành (theo project, chỉnh trong Dashboard)
- `operating_mode`: `speed` | `quality` (comment 2)
- `qc_auto_pass_threshold`: float, mặc định 0.85 (comment 3)
- `qc_model_version`: pin cố định
- `batch_poll_interval_seconds`: mặc định 90s (comment 4)
- `max_retry_count`: mặc định 3

### 3.3 MCP Servers cần build (theo lộ trình 4 tuần gốc, bổ sung chi tiết)
1. `mcp-server-project-db` — quản lý schema trên, expose state machine transitions dạng tool calls
2. `mcp-server-deepix` — gen ảnh + ghi `qc_results`
3. `mcp-server-clipai` — gửi request + **heartbeat polling** batch (comment 4) + pre-flight IP check
4. `mcp-server-ffmpeg` — concat/render local

### 3.4 Streamlit Dashboard — bổ sung yêu cầu
- Hiển thị pipeline theo state machine (Kanban theo state, không chỉ list)
- Cho phép chỉnh `qc_auto_pass_threshold` và `operating_mode` trực tiếp trên UI
- Cảnh báo Pre-flight IP/Content risk ngay ở màn hình Character Bible
- Progress bar real-time cho batch >100 video (heartbeat status)

## 4. Rủi ro & mitigation tổng hợp

| Rủi ro | Mitigation |
|---|---|
| Auto-reject/retry vô hạn tốn credit | `max_retry_count` + escalate to user |
| QC threshold "hộp đen", không giải trình được | `qc_checklist` theo tiêu chí + threshold config được |
| Batch lớn cần user túc trực approve | Heartbeat polling, approve 1 lần/batch |
| Gen hàng loạt rồi fail vì trùng IP bản quyền | Pre-flight check ở Character Bible + blocklist nội bộ |
| Không rõ trạng thái job khi lỗi nửa chừng | State machine chuẩn + audit trail `review_log` |

## 5. Next steps đề xuất (bổ sung lộ trình 4 tuần gốc)

- **Tuần 1:** Hạ tầng & API (giữ nguyên) + chốt `operating_mode` mặc định cho từng loại nội dung với team.
- **Tuần 2:** Build 4 MCP servers + **implement state machine & schema ở trên trước tiên** (nền tảng cho mọi server khác).
- **Tuần 3:** Dashboard (thêm Kanban theo state, config threshold, cảnh báo IP) + dry-run 2 kịch bản mẫu, đo thử ngưỡng QC thực tế để hiệu chỉnh `qc_auto_pass_threshold`.
- **Tuần 4:** Đóng gói, viết blocklist IP ban đầu (dựa trên case Wonder Woman + tra cứu thêm), bàn giao vận hành.

---
*Tài liệu nguồn: `Quy_Trinh_Auto_Pipeline_Full1.docx` (kèm 4 comment góp ý, đã phân tích ở Mục 2).*
