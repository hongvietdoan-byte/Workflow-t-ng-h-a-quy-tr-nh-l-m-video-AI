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

**Giải pháp:** Tách rõ 2 chế độ vận hành qua `operating_mode` (config theo project/khách hàng), dùng chung 1 bước QC scoring — khác nhau ở **ai có quyền quyết định chuyển state**:

- **`auto`** — QC Agent (model AI chuyên duyệt ảnh, tách biệt với Claude Director viết prompt) tự chấm điểm và **tự quyết định** pass/fail theo `auto_pass_threshold`. Score đạt → job tự chuyển `APPROVED_AUTO` → tự động sang Bước 3/4, không ai cần bấm gì.
- **`human_qc`** — QC Agent vẫn chấm điểm như trên, nhưng chỉ mang tính gợi ý/pre-filter (sort ảnh theo score để user duyệt nhanh hơn). Mọi ảnh dừng ở state `pending_human_review`; chỉ khi **user bấm Approve** job mới được phép đi tiếp.

Khi Reject (dù do QC Agent tự động hay user): tạo `job` mới `image_gen` với `parent_job_id` trỏ về job cũ + ghi `retry_reason`, tăng `retry_count`. Nếu `retry_count` vượt `max_retry_count` (vd 3 lần) → tự động chuyển state `failed` và **escalate cho user** — đây là van an toàn bắt buộc ngay cả ở mode `auto`, tránh lặp vô hạn tốn credit.

Mọi quyết định (AI hay người) đều ghi vào `review_log` với cột `reviewer_type` (`ai_agent` | `user`), để sau này so sánh QC Agent quyết định đúng bao nhiêu % so với user thật — dữ liệu này dùng để tinh chỉnh `auto_pass_threshold` hoặc làm căn cứ chuyển hẳn project sang mode `auto` khi đã đủ tin cậy.

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
- `review_log` — audit trail mọi quyết định (comment 2): `job_id, reviewer_type (ai_agent|user), decision, note, decided_at`

### 3.2 Cấu hình vận hành (theo project, chỉnh trong Dashboard)
- `operating_mode`: `auto` | `human_qc` (comment 2) — xem bảng so sánh dưới đây
- `qc_auto_pass_threshold`: float, mặc định 0.85 (comment 3)
- `qc_agent_provider`: **Claude Vision** (system prompt QC riêng, tách biệt system prompt của Claude Director) — quyết định 2026-09-18, xem lý do so sánh ở dưới
- `qc_model_version`: pin cố định (version cụ thể, không auto-update) để ngưỡng không bị trôi
- `batch_poll_interval_seconds`: mặc định 90s (comment 4)
- `max_retry_count`: mặc định 3

**So sánh 2 giá trị `operating_mode`:**

| | `auto` | `human_qc` |
|---|---|---|
| QC Agent chấm điểm | Có | Có (chỉ để gợi ý/pre-filter) |
| Ai quyết định pass/fail | QC Agent (theo `auto_pass_threshold`) | User |
| Pipeline có block chờ Bước 3 không | Không (trừ khi escalate sau `max_retry_count`) | Có, luôn chờ user Approve |
| Khi nào cần user can thiệp | Chỉ khi retry vượt ngưỡng (safety net) | Mọi ảnh |

#### 3.2.1 Vì sao chọn Claude Vision làm `qc_agent_provider` (so với GPT-6 Astra)

Đã cân nhắc GPT-6 Astra (OpenAI, ra mắt 09/2026, $10/$50 mỗi 1M token input/output) nhưng chọn Claude Vision vì:
1. **Đồng bộ vendor** — Claude Director (Bước 1, 3) đã dùng Claude Enterprise; dùng chung Claude cho QC Agent giảm số vendor, đơn giản vận hành, đúng tinh thần "1-Click Startup" trong lộ trình gốc.
2. **Chi phí phù hợp bài toán** — QC checklist là tác vụ phân loại/so khớp (đúng nhân vật, lỗi tay, bố cục), không cần model reasoning nặng như GPT-6 Astra; chạy hàng trăm-nghìn ảnh/ngày ở mức giá reasoning cao sẽ đội chi phí không cần thiết.
3. **Data governance** — không phát sinh thêm đường dữ liệu ảnh ra vendor thứ 2, quan trọng vì pipeline xử lý nội dung có rủi ro bản quyền IP (Comment 4).

`qc_agent_provider` vẫn để dạng config swap được — nếu sau này `review_log.reviewer_type` cho thấy Claude Vision chấm sai lệch nhiều so với quyết định thật của user, có thể A/B test model khác mà không phải đổi kiến trúc.

### 3.3 MCP Servers cần build (theo lộ trình 4 tuần gốc, bổ sung chi tiết)
1. `mcp-server-project-db` — quản lý schema trên, expose state machine transitions dạng tool calls
2. `mcp-server-deepix` — gen ảnh + ghi kết quả vào `qc_results`
3. `mcp-server-qc-agent` — model AI chuyên duyệt ảnh theo `qc_checklist` (tách biệt Claude Director), chạy cho cả 2 mode; mặc định dùng **Claude Vision với system prompt QC riêng** (xem 3.2.1), provider vẫn thiết kế swap được qua config `qc_agent_provider` để A/B test sau này
4. `mcp-server-clipai` — gửi request + **heartbeat polling** batch (comment 4) + pre-flight IP check
5. `mcp-server-ffmpeg` — concat/render local

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
