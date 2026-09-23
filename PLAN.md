# Kế hoạch triển khai — Auto Pipeline sản xuất Video AI

Tài liệu này phân tích `Quy_Trinh_Auto_Pipeline_Full1.docx` (bao gồm 4 comment góp ý trong file) và đề xuất giải pháp + định hướng triển khai chi tiết.

## 1. Tóm tắt tài liệu gốc

**Kết luận đã chốt trong doc:** Hệ thống có thể auto 100% về mặt kỹ thuật (từ đọc kịch bản → xuất video), nhưng về nghệ thuật/chất lượng nên dùng mô hình **Hybrid Agentic Workflow** — tự động hóa qua MCP, có User duyệt (Human-in-the-Loop) tại 3 điểm chốt.

**Quyết định kiến trúc đã chốt (2026-09-19): điều khiển hợp nhất qua 1 tool duy nhất.** Toàn bộ pipeline (5 bước) được điều khiển từ **một Dashboard web duy nhất**, sắp xếp theo đúng thứ tự bước, mỗi khâu có bộ nút điều khiển riêng; người dùng không phải chạy qua lại giữa nhiều công cụ (xem Mục 3.4). Triển khai 2 giai đoạn: V0 (thử nghiệm qua Claude Desktop + MCP) rồi V1 (Dashboard hợp nhất) — xem Mục 7.

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

### 3.3 Kiến trúc & MCP Servers (6 server + lớp core dùng chung)

**Kiến trúc lớp (để chuyển V0 → V1 không phải làm lại):**
- **Core Python dùng chung** — toàn bộ logic nghiệp vụ (state machine, gọi Deepix/Clip AI/FFmpeg/nhạc, retry, ghi log) nằm ở đây.
- **MCP servers** — chỉ là vỏ mỏng bọc core, phục vụ V0 (gọi từ Claude Desktop).
- **Dashboard (V1)** — gọi cùng core; là **frontend orchestrator duy nhất**, không có đường thao tác nào khác (không mở SQLite tay, không gọi API tay, không chạy script CLI riêng).
- **LLM runner hoán đổi được** — bước cần Claude (Director Bước 1/3, QC Bước 2, Music Brief) đi qua 1 lớp runner: V0 = chạy thủ công qua chat Claude Desktop, V1 = Anthropic API; dùng chung prompt template + JSON schema đầu ra.

| # | Server | Nhiệm vụ | API/tool bên ngoài cần |
|---|---|---|---|
| 1 | `mcp-server-project-db` | SQLite, state machine, parse script.docx, Character Bible, pre-flight IP check | Local; thư viện đọc docx |
| 2 | `mcp-server-deepix` | Gen ảnh hàng loạt, tải ảnh, ghi kết quả | REST API + key Deepix (nội bộ) |
| 3 | `mcp-server-qc-agent` | Chấm ảnh theo `qc_checklist`, cả 2 mode; Claude Vision + system prompt QC riêng (xem 3.2.1), provider swap được | Claude (V0: chat; V1: Anthropic API, pin version) |
| 4 | `mcp-server-clipai` | Gửi/poll gen video, **heartbeat polling** batch, parse lỗi risk-control (comment 4); chọn model theo dự án (`video_model`: seedance / kling / minimax) | REST API (+webhook) Clip AI (nền tảng tích hợp nhiều model) |
| 5 | `mcp-server-ffmpeg` | Concat, transition, mux nhạc, render | FFmpeg local |
| 6 | `mcp-server-music` | Music Brief, gen 3 bản nháp, thư viện/upload nhạc (xem 3.5) | API nhạc có license thương mại (chọn sau) |

Ngoài ra: Claude Director (Bước 1, 3, Music Brief), Streamlit Dashboard (V1), Figma (mockup giao diện).

### 3.3b Thông tin về Clip AI (bổ sung 2026-09-19)
Clip AI là nền tảng tạo video và âm thanh AI tích hợp cho team (all-in-one), gộp nhiều model: **Seedance, Kling, MiniMax** (video), **Seed Audio, ElevenLabs** (âm thanh/giọng), kèm thư viện game asset. Tính năng: tạo/chỉnh video đa phương thức, đạo diễn 3D, thoại, âm thanh và nhạc, thiết kế và nhân bản giọng nói.

Hệ quả cho thiết kế:
1. **Không chỉ Kling:** bộ chạy Bước 4 có cấu hình `video_model` theo dự án (`kling`, `kling-o1`, `seedance`, `seedance-fast`, `seedance-2.5`), truyền vào provider. **Hợp đồng API thực tế chỉ có Kling Omni và Seedance; MiniMax không có trong API** (xem `docs/api_notes.md`). Bộ lọc kiểm duyệt (risk control) và cú pháp prompt khác nhau theo model → blocklist IP và `content_moderation_failures` nên ghi kèm model; bộ đánh giá `eval/` cần chạy lại khi đổi model.
2. **Âm thanh (đã xác nhận có endpoint):** API có tạo TTS, sound effect và **nhạc** (`music_v2`, dài 3–600 giây, có tùy chọn instrumental) qua `/api/sound/generate`, bất đồng bộ; Bước 5a dùng chính Clip AI, giảm một nhà cung cấp. Còn cần xác nhận điều khoản thương mại và viết adapter audio.
3. **Giọng/thoại:** tạo thoại, thiết kế/nhân bản giọng là tính năng có thể thêm ở giai đoạn sau (lồng tiếng nhân vật); chưa nằm trong V0/V1.
4. **Thư viện game asset:** phù hợp trailer game; xét dùng làm nguồn tham chiếu nhân vật/bối cảnh nhất quán khi API cho phép.
5. **Đã có trong tài liệu API (2026-09-19, xem `docs/api_notes.md`):** model chọn được, cách gửi ảnh (multipart cùng lệnh tạo), quét `video-list` để poll (không có endpoint 1 tác vụ), thời lượng/độ phân giải theo model, endpoint audio. **Còn cần xác nhận khi chạy thật:** hạn mức/credit theo model, thời hạn link `video_url`, cách API xử lý negative prompt (hiện không có trường riêng), và thông điệp lỗi risk control thực tế của từng model.

### 3.4 Giao diện điều khiển hợp nhất (Unified Control Dashboard)

**Nguyên tắc:**
1. **Một tool duy nhất** — mọi hành động (upload script, gen ảnh, duyệt, gen video, nhạc, render) thực hiện từ Dashboard; user không phải chuyển qua lại giữa công cụ.
2. **Bố cục Stepper/Wizard theo đúng thứ tự Bước 1 → 5**, mỗi bước là 1 màn hình riêng, đầu trang luôn hiển thị tiến độ theo state machine. Cho phép quay lại xem/sửa bước trước bất kỳ lúc nào; không cho vào bước sau khi bước trước chưa đủ điều kiện (vd chưa Approve & Lock Character Bible thì chưa vào Bước 2).
3. **Mỗi khâu có bộ nút điều khiển tác vụ riêng** (bảng dưới), mỗi nút map vào state machine: Run → `queued`→`running`; Retry → `retryable`→`queued` (tăng `retry_count`, ghi `retry_reason`); Cancel → `cancelled`; Approve/Reject → ghi `review_log` (`reviewer_type`).
4. **Chỉ chạy lại phần thay đổi** (học từ ComfyUI): Reject 1 ảnh và sửa mô tả thì chỉ re-run đúng job đó (qua `parent_job_id`), không re-run các bước/cảnh không đổi.
5. **Tab Lịch sử:** xem lại các phiên bản ảnh/video đã reject của cùng 1 scene để so sánh.
6. Giữ giao diện tuyến tính (không dùng node-graph tự do như ComfyUI) vì yêu cầu sắp xếp đúng thứ tự bước.

**Thanh điều khiển toàn cục (luôn hiển thị):** chọn project/kịch bản; switch `operating_mode` (`auto`/`human_qc`); slider `qc_auto_pass_threshold`; Kanban tổng quan scenes theo state; nút khẩn cấp **Pause toàn bộ / Resume toàn bộ / Cancel tất cả job đang chạy**.

**Bộ nút điều khiển theo từng bước:**

| Bước | Nút điều khiển |
|---|---|
| 1. Kịch bản & phân tích | Upload script.docx · Chạy phân tích · Sửa Character Bible/bảng cảnh inline · Lưu · **Duyệt & khóa** · Hủy/Reset bước · Cảnh báo Pre-flight IP risk |
| 2. Gen ảnh + QC | Gen ảnh hàng loạt (tất cả/chọn scene) · mỗi ảnh: Approve · Reject + ghi chú · Gen lại · hàng loạt: Approve tất cả PASS · Gen lại tất cả FAIL · hiển thị mode đang áp dụng + QC score |
| 3. Video Motion Prompt | Sinh prompt hàng loạt · Sửa prompt · Duyệt từng cái · Duyệt tất cả |
| 4. Gen video | Bắt đầu gen batch · thanh tiến độ heartbeat (x/y) · Pause/Resume polling · Retry job fail · Cancel job đang chạy · cảnh báo IP risk |
| 5a. Nhạc nền | Sinh/sửa Music Brief · Gen 3 bản nháp · Nghe thử · Chọn 1 · Gen lại · Upload nhạc · Không dùng nhạc |
| 5b. Ghép & render | Chọn transition · Render Final · Preview · Tải xuống · Render lại với option khác · **Nghiệm thu (Done)** |

**Bản xem trước bằng Figma:** mockup chi tiết (control bar, stepper, màn hình từng bước 1–5b, tab Lịch sử, trạng thái empty/loading/error, badge theo state machine) — user duyệt trước khi build. **Trạng thái mockup (2026-09-19):**
- **HTML tương tác (đầy đủ):** [mockup/dashboard.html](mockup/dashboard.html) — mở bằng trình duyệt; đủ 6 màn hình (Bước 1, 2, 3, 4, 5a, 5b) + tab Lịch sử, control bar toàn cục, đổi `operating_mode`/threshold thấy tác động lên Bước 2. Dữ liệu giả.
- **Figma:** [file Figma](https://www.figma.com/design/NjEZBllciYNbZwIntemWbd) — có component TopBar, Stepper (6 biến thể), Màn hình Bước 1 (dựng bằng Figma MCP) và **bản import đầy đủ 7 màn** từ [mockup/dashboard_all.html](mockup/dashboard_all.html) bằng plugin html.to.design (frame "dashboard_all.html", các màn xếp dọc). Các màn 2–6 chỉ được dựng qua import HTML vì gói Figma Starter hết hạn mức MCP; layer là kết quả import tự động nên cần tách frame/đặt tên/componentize thủ công nếu muốn dùng làm design system. Việc tồn đọng: Stepper component đang chồng lên Screen 1 trên canvas (cần dời vị trí).

Lưu ý Streamlit khó khớp 100% pixel với Figma; nếu cần UI sát mockup thì cân nhắc frontend web riêng (quyết định mở).

### 3.5 Bước 5a — Nhạc nền
AI đề xuất, user quyết định: (1) Claude Director đọc Visual Mood + tổng thời lượng → sinh Music Brief (thể loại, tempo, cảm xúc, nhạc cụ, instrumental), user sửa hoặc tự viết prompt; (2) gen **3 bản nháp cho cả video** (1 track xuyên suốt, tránh đứt giữa cảnh), nghe thử và chọn/gen lại; (3) hoặc upload nhạc có sẵn/thư viện nội bộ/không dùng nhạc; (4) FFmpeg ghép (fade, ducking, căn độ dài) → preview → render.
- **Suno:** hiện **không có API chính thức** (07/2026 mới mở intake form cho partner, chưa có self-serve; gói Pro/Premier chỉ dùng web/app); các "Suno API" bên thứ ba là wrapper không chính thức → rủi ro ToS/ổn định/bản quyền, không đưa vào pipeline. Dùng Suno thủ công: tạo trên web rồi upload vào slot.
- **Cập nhật 2026-09-21:** nhạc nền là **nhánh phụ của Bước 5 (Ghép & render)**, cùng cấp với phụ đề (không còn là khối riêng phía trên). **Nhạc chính do AI tạo** (Clip AI `music_v2`, nhà cung cấp ElevenLabs bên trong Clip AI, đã có endpoint `/api/sound/generate` type `music` nên **không cần tài khoản ElevenLabs riêng**; gói Free của ElevenLabs chỉ dùng phi thương mại nên không phù hợp video công ty). Kho nhạc/âm thanh của người dùng chỉ **hỗ trợ**: nghe thử, chọn tay, thêm hiệu ứng, và dự phòng tự động khi AI tạo nhạc lỗi hoặc chưa cấu hình; muốn ưu tiên kho thay AI thì bật riêng theo dự án.
- `music_provider` swap được. **Ứng viên số 1 nay là chính Clip AI** (nền tảng tích hợp ElevenLabs và Seed Audio, có tạo nhạc/âm thanh) — nếu API Clip AI mở phần audio thì dùng chung 1 nhà cung cấp, 1 hợp đồng, 1 API key; nếu không thì dùng nhà cung cấp riêng có license thương mại rõ. **Chọn sau khi xác nhận API Clip AI** (chưa chặn V0).

### 3.6 Knowledge Base & Prompt Library (nền chất lượng Bước 1 và Bước 3)
Nguyên tắc: **không train/fine-tune model** — xây knowledge pack có cấu trúc + ví dụ mẫu + JSON schema đầu ra + bộ đánh giá, nạp vào system prompt Director; rẻ, sửa ngay được, đổi model được.
- **Bước 1 (biên kịch/đạo diễn):** cấu trúc cảnh (slugline, beat, mục tiêu), bối cảnh, nhân vật/trang phục (= Character Bible), ánh sáng/màu sắc/mood, ngôn ngữ ống kính (cỡ cảnh, góc máy, tiêu cự), continuity giữa cảnh. Đầu ra JSON: scene, location, time, characters, wardrobe, mood, lighting, shot list, image prompt.
- **Bước 3 (video motion prompt):** thư viện theo thể loại (hành động, kinh dị, drama, game trailer…), từ vựng chuyển động camera (push/pull/pan/tilt/orbit/handheld), tốc độ, hành động nhân vật trong 5s, cú pháp Kling image-to-video; mỗi thể loại có few-shot tốt/xấu + negative prompt.
- **Nguồn tham khảo (chưa kiểm định — review chất lượng/license trước; chỉ lấy tri thức, không chạy code lạ tùy tiện):** [awesome-ai-video-prompts](https://github.com/geekjourneyx/awesome-ai-video-prompts), [ai-shortfilm-prompts](https://github.com/jnMetaCode/ai-shortfilm-prompts), [visual-skills](https://github.com/smixs/visual-skills), [SKRIPTON](https://github.com/NAMDIE/SKRIPTON), [OpenStory](https://openstory.so/docs/developer-guide/workflow), [awesome-llm-story-generation](https://github.com/Picrew/awesome-llm-story-generation), [Kling Prompt Guide](https://kling.ai/blog/kling-ai-prompt-guide); cộng sách/giáo trình biên kịch-đạo diễn-quay phim do team nội dung chọn và kịch bản/storyboard các dự án đã làm.
- **Quy trình:** thu thập + lọc → chưng cất knowledge pack → viết system prompt + schema → **eval set** 10–20 mẫu có đáp án do chuyên gia phim/nội dung chấm → lặp cải thiện → khóa version. Cần 1 "chuyên gia miền" duyệt. Ước tính +8–12 ngày công, chạy song song với build MCP ở V0; bộ mẫu dùng luôn để hiệu chỉnh QC checklist (Bước 2).

### 3.7 Nhất quán nhân vật – bối cảnh – bố cục (rà soát 2026-09-23)
Bối cảnh: kịch bản thật dài ~60 giây, 3–5 nhân vật, bối cảnh là map Free Fire. Hiện mỗi cảnh = 1 ảnh gen độc lập (không phải storyboard), nên cần biết video có giữ nhất quán nhân vật, bối cảnh và vị trí nhân vật giữa các cảnh không.

**Hiện trạng (đọc code + mô phỏng, không tốn credit):**

- `assets.scene_references` gửi tối đa 8 ảnh/cảnh, **nhân vật lấy trước (2 ảnh/người), bối cảnh xét sau**. Mô phỏng: 2–3 nhân vật → có ảnh bối cảnh; **4 nhân vật → mất ảnh bối cảnh; 5 nhân vật → mất bối cảnh và nhân vật thứ 5 không có ảnh**. Chế độ Storyboard cũng tự tắt khi hết chỗ.
- Ảnh bối cảnh chỉ được gửi khi tên tài nguyên nằm nguyên văn trong trường `location` do Director viết (ví dụ Director viết "abandoned factory rooftop" thay vì tên trong kho → không gửi) và tài nguyên phải được tick vào dự án.
- Mỗi bối cảnh chỉ dùng **1 ảnh ngang lớn nhất** cho mọi cảnh; các góc chụp khác trong kho không được dùng.
- Director không có trường **vị trí nhân vật** (trái/phải, hướng nhìn, tiền/hậu cảnh) → vị trí đứng ngẫu nhiên giữa các shot, trục 180° dễ bị đảo.
- Chế độ Storyboard nối với **cảnh liền trước theo số thứ tự**, không theo nhóm cùng bối cảnh.
- Bước 4: **Kling chỉ nhận ảnh khung đầu**; ảnh nhân vật/bối cảnh chỉ gửi kèm khi dùng Seedance.
- Bằng chứng tích cực (chạy thật 2026-09-23, dự án "Kenta xuyên tường", 3 nhân vật): gắn tài nguyên địa điểm "Đảo Quân Sự" (6 ảnh in-game) → 5/6 cảnh gen lại đúng bối cảnh FF ngay; thêm "đặc điểm neo tương phản" cho mỗi người → hết nhầm Kelly/Maxim. Tức là cơ chế tham chiếu **có hiệu quả khi còn đủ chỗ** — vấn đề chính là cảnh đông người và chọn góc/bố cục.

**Kết luận:** mỗi cảnh 1 ảnh giữ được mặt/trang phục (khi ≤3 người) nhưng **không giữ được không gian**: bối cảnh, vị trí đứng, tỉ lệ người/cảnh, hướng nhìn. AI vẽ lại toàn bộ khung hình nên dễ ra nhân vật quá to, đứng lơ lửng, bối cảnh lệch so với in-game.

**Ưu tiên đã chốt (2026-09-23):** mục 1–4 và 6 dưới đây thuộc **hướng chính (ảnh + text)**, làm ngay. Mục 5 (previz 3D) là **hướng nghiên cứu cho tương lai** (xem `docs/RESEARCH_3D_PREVIZ.md`). Bàn đạo diễn Clip AI là hướng 2, dò lại ở lần dùng API tiếp theo (`docs/CLIPAI_FEATURES.md`). Bổ sung cho hướng chính: ảnh nền chung cho mỗi nhóm cảnh (gen 1 ảnh bối cảnh trống từ ảnh in-game, duyệt 1 lần, mọi shot trong nhóm dùng lại), tự gắn nhãn góc/cỡ cảnh/mốc cho ảnh bối cảnh bằng Claude Vision để chọn đúng ảnh góc theo shot, tách vai trò ảnh tham chiếu mặt/tóc và trang phục + gen bảng nhân vật (trước/nghiêng/sau) khi đổi trang phục.

**Previz 2D — dựng cảnh bằng lớp ảnh trước khi gen (chốt 2026-09-23, thay cho "ảnh nền chung cần người duyệt"):** không thêm bước duyệt nào. (1) *Phân tích ảnh nền* 1 lần/ảnh, lưu lại: Claude Vision đọc góc máy so với mặt đất, đường chân trời, vùng mặt đất đứng được, vật mốc + kích thước thật, hướng sáng. (2) *Layout từng shot*: Claude chọn ảnh nền hợp góc, đặt chân từng người + hướng mặt, đánh dấu "cần vẽ lại nền" khi không có ảnh đúng góc; **code** (`core/layout.py`) tính chiều cao theo phối cảnh (từ đường chân trời + vật mốc), kéo chân về mặt đất, vẽ người xa trước, bóng tiếp xúc; dùng ảnh nhân vật tách nền nếu có, không thì ma-nơ-canh màu. (3) *Storyboard* ghép mọi layout thành 1 tấm (không tốn credit), Claude tự rà lỗi liên tục (trục 180°, hướng di chuyển); người dùng xem nếu muốn, không chặn. (4) *Gen từng cảnh*: Deepix nhận ảnh layout làm tham chiếu chính (giữ bố cục/vị trí/cỡ/góc máy) + ảnh nhân vật/bối cảnh; QC so với layout. (5) Sau này thay nguồn layout bằng render map 3D hoặc Bàn đạo diễn mà không đổi các bước sau. **Chạy bằng `claude_cli` trước** (qua `llm_runner.ask_json`, cùng code với API): mỗi ảnh nền 1 lần (lưu lại), mỗi dự án thêm 1 lần dựng layout + 1 lần rà storyboard; chuyển sang API key khi chất lượng video đạt. Rủi ro chính: Deepix có bám layout không (API không có tham số khoá bố cục); Claude ước lượng chân trời/mặt đất có thể sai với một số ảnh.

**Hướng giải quyết (theo thứ tự):**

1. **Sửa nhanh cách chọn ảnh tham chiếu (A):** luôn giữ 1 chỗ cho bối cảnh (và 1 cho Storyboard); cảnh ≥4 người → 1 ảnh/người.
2. **Chọn bối cảnh theo ID (B):** Director chọn `location_asset` từ danh sách tài nguyên của dự án; Bước 1 có ô chọn background từng cảnh để sửa tay.
3. **Blocking + nhóm cảnh (C):** Director thêm `blocking` (vị trí trái/giữa/phải, hướng nhìn, tiền/trung/hậu cảnh) và `sequence` (nhóm cảnh cùng bối cảnh liên tục, giữ trục 180°). Storyboard nối theo nhóm, không theo số thứ tự.
4. **Hồ sơ model video:** Bước 1–3 và 5 dùng chung cho mọi model; chỉ Bước 4 khác theo khả năng từng model (số ảnh tham chiếu, âm thanh, xung đột tùy chọn, giá). Mặc định Kling; tự đề xuất Seedance khi cảnh ≥3 người, có nhân vật đi vào khung hình giữa clip, hoặc hành động mạnh. Không cần dựng quy trình riêng cho từng model — chỉ cần bộ test cố định 3 cảnh chạy trên mỗi model.
5. **Previz 3D từ map Free Fire (D, hướng chính cho độ chân thực):** thay vì để AI vẽ lại toàn bộ khung hình, dựng bố cục bằng 3D trước rồi mới cho AI "render đẹp":
   - Nhập model 3D của map (GLB/FBX) vào **Blender chạy tự động bằng script** (miễn phí, chạy trên máy người dùng). Script tự đọc tên object, tự tìm mặt đất, tự kiểm tra đơn vị bằng vật mốc (cửa/xe/container), xuất bản đồ nhìn từ trên + danh sách khu vực — **người dùng không phải đánh dấu tay ảnh nào**.
   - Director viết blocking bằng lời (khu vực, vị trí so với mốc, cỡ cảnh, độ cao camera) → code đặt **ma-nơ-canh cao ~1,75 m đúng trên mặt đất** (dò mặt đất bằng raycast → không lơ lửng, đúng tỉ lệ) và camera theo cỡ cảnh; góc cao/thấp/ngang mắt đều được, không cần ảnh chụp sẵn.
   - Render ảnh layout (màu + độ sâu) → Deepix vẽ ảnh cuối từ layout + ảnh nhân vật trong kho. Vị trí nhân vật lưu trong 3D nên đổi góc máy vẫn nhất quán, shot ngược góc tự đúng.
   - Video: ảnh cuối làm khung đầu; chuyển động camera render từ Blender làm video tham chiếu (`reference_video`) khi cần; nếu không, chỉ cho camera chuyển động nhỏ (push-in/pan/tilt) để model không phải bịa phần bối cảnh ngoài khung.
   - Tạm dùng **map fan dựng trên mạng** (Sketchfab/CGTrader, vd "Free Fire Old Bermuda Three 3D Places") để thử nội bộ; video phát hành nên chuyển sang asset chính thức từ team game. File map không đưa lên GitHub (để trong `data/`). Tải chỉ file model (`.glb/.gltf/.fbx/.obj`); mở `.blend` thì tắt "Auto Run Python Scripts".
   - Dự phòng khi không có 3D cho một map: ước lượng độ sâu từ 1 ảnh bằng model chạy cục bộ để tự tìm mặt đất/tỉ lệ (kém chính xác hơn).
   - **Rủi ro lớn nhất cần thử trước:** API Deepix không có tham số khoá bố cục (mask/strength/ControlNet) → phải thử 3–5 ảnh xem Deepix có bám layout không, trước khi đưa vào Dashboard.
6. **QC bổ sung 3 tiêu chí:** tỉ lệ người/cảnh, chân chạm đất/có bóng, độ lệch bối cảnh so với ảnh gốc (đo vùng ngoài nhân vật, không cần AI chấm).

### 3.7b Hậu kiểm 1 video thật đã chạy xong (2026-09-23) — 2 nguyên nhân gốc chưa nằm trong mục 3.7 ở trên — ĐÃ SỬA CẢ HAI (2026-09-23)

Khác với mục 3.7 (mô phỏng code cho kịch bản TƯƠNG LAI 60s/3-5 người), mục này là **hậu kiểm (post-mortem)** một video đã chạy thật xong ("FF: Kenta xuyên tường cướp kill", dự án id 1, 8 cảnh) — đọc lại `manifest.sqlite` thật (Character Bible, ảnh tham chiếu gốc, lịch sử retry của QC, file mix âm thanh) để tìm đúng nơi lỗi bắt đầu, theo yêu cầu "nhất quán thấp / bối cảnh lệch / nhân vật không đồng nhất / voice hỗn loạn". Phát hiện 2 nguyên nhân gốc **không trùng** với P0 (A)(B)(C), Previz 2D, hay QC 3 tiêu chí đã làm — cần làm THÊM, không thay thế; có thể làm song song, không phụ thuộc nhau.

**Nguyên nhân gốc #4 — Character Bible (Director viết) chưa từng được đối chiếu với ảnh tham chiếu thật:**
`core/prompts.py::build_director_bundle()` chỉ gửi Director `assets.context_text()` (CHỮ), không gửi ảnh nhân vật thật → Director tự bịa mô tả "nghe hợp lý" nhưng sai với ảnh gốc (Kelly: viết "tóc đen đuôi ngựa, vệt cam" — ảnh thật là bob nâu hạt dẻ + choker; Maxim: viết "tóc đen" — ảnh thật tóc bạc; Kenta: viết "vệt xám, sẹo" — ảnh thật không có). Bằng chứng đo được qua lịch sử `retry_reason` của Cảnh 1: job 9 lặp lại đúng mô tả sai của Director, job 16 QC tự nhìn ảnh kỹ hơn và sửa lại đúng, job 24 (retry 4/5, hết ngân sách) vẫn thiếu 1 chi tiết (choker) khi được duyệt — Cảnh 7 (ngân sách retry khác) hội tụ đúng hơn, nên cùng 1 nhân vật trông như 2 người ở 2 cảnh. Đây là lỗi ở TẦNG DỮ LIỆU GỐC, ảnh hưởng mọi cảnh của mọi dự án dùng Director tự động, không phải lỗi model gen ảnh/video. **Đã sửa (2026-09-23):** `core/llm_runner.py::run_director()` giờ gửi kèm ảnh tham chiếu thật (`_director_references`, dùng `assets.best_reference`/`thumbnail`) của mọi nhân vật/thú cưng đã gắn cho dự án — cùng cơ chế QC đã dùng; `prompts/01_director_scene_analysis.md` dặn: có ảnh đính kèm thì viết `description`/`wardrobe` đúng theo ảnh, không suy đoán. 2 test mới ở `tests/test_llm_runner.py`.

**Nguyên nhân gốc #5 — Không đối chiếu thời lượng giọng đọc TTS thật với lịch mix (giọng chồng tiếng):**
`core/dialogue.py::needed_seconds()` (ước lượng 3,5 âm tiết/giây, quyết định độ dài clip TRƯỚC khi có giọng thật) và `core/subtitles.py::build_cues()` (chia đều thời lượng clip đã cố định cho từng dòng thoại) đều chỉ là ước lượng; ElevenLabs trả `duration_ms` THẬT (thường dài hơn) nhưng không có bước nào đối chiếu lại. `core/audio_lib.py::set_mix()` nhận `start` tùy ý không kiểm tra chồng lấn; `core/ffmpeg_studio.py::build_extras_mix_cmd()` dùng `amix=normalize=0` (cộng thẳng, không ducking). Đo được trên video thật: 8/13 điểm nối giữa các câu thoại bị chồng lên nhau (tới 1,29 giây). **Đã sửa (2026-09-23):** `core/audio_lib.py` thêm `overlapping_tts()` (phát hiện) và `schedule_by_cues()` (tính lại lịch mix TUẦN TỰ theo thời lượng thật: start_mới = max(ước lượng cũ, kết thúc thật của dòng trước + khoảng nghỉ tối thiểu), khớp dòng theo đúng nội dung thoại của `subtitles.build_cues`). Dashboard Bước 5a tự cảnh báo + nút "🗓 Xếp lại theo thoại". 4 test mới (`tests/test_audio_lib.py`, `tests/test_dashboard.py`). 600 test pass.

### 3.8 Dashboard v2 (2026-09-23) — nhất quán giữa các bước + kho kỹ năng thành luật trong code

Nguồn: báo cáo rà soát `docs/DASHBOARD_REVIEW_2026-09-23.md` và kiểm kê kho kỹ năng `Get this Skill to Claude/` (mới dùng ~50%, chủ yếu dán tài liệu vào prompt). Quyết định của người dùng: tỉ lệ khung theo dự án (mặc định 9:16), thoại tiếng Việt bằng TTS là chính, kho kỹ năng → luật + cổng kiểm tra trong code, **model video chọn theo từng cảnh** theo slide ClipAI (bỏ Kling mặc định), làm hết rồi test 1 lượt.

| Nền tảng | Làm gì | File |
|---|---|---|
| "⚠ cũ" (lineage) | ảnh/motion/video/bản giao lưu dấu vân tay đầu vào; sửa cảnh, bỏ duyệt ảnh, đổi tỉ lệ khung → phần làm từ đầu vào cũ hiện ⚠ và có nút làm lại đúng phần đó; video không gen từ prompt cũ | `core/lineage.py`, `core/batch.py` |
| Director JSON v2 | thể loại, Character Lock, ý đồ cảm xúc, beat, độ phức tạp máy, vai trò cảnh (then chốt/chuyển tiếp), thoại có cấu trúc, thời lượng; chạy lại không ghi đè trường sửa tay (🔒), null không xóa Background | `core/llm_io.py`, `prompts/01` |
| Tỉ lệ khung | 16:9 / 9:16 / 1:1 → kích thước Deepix, ratio Clip AI, khung layout, render, xuất bản (cắt khung thay viền đen) | `core/formats.py` |
| Model theo cảnh | 3 mức ưu tiên (Chất lượng / Cân bằng / Tiết kiệm) = 2 thang của slide; luật: then chốt/phức tạp/video tham chiếu → Seedance 2.5, ≥3 nhân vật → Seedance, đối thoại nhiều người/chuyển tiếp → Kling, cảnh thường → Seedance 2.0 / Fast; đổi được từng cảnh; MiniMax H3 và Seedance Mini chỉ có trên web | `core/model_router.py`, `data/video_models.json` |
| Giọng thoại | giọng từng nhân vật (Character Bible), TTS mỗi câu, độ dài giọng thật đặt thời lượng clip, xếp không chồng tiếng, phụ đề lấy giờ từ giọng | `core/voice.py` |
| Bản giao | dựng (thiết lập lưu theo dự án) → phụ đề (màu theo nhân vật, kiểm mật độ, .xlsx) → card cuối → các kích thước; animatic trước khi gen video | `core/delivery.py` |
| QC | chính sách 3 mức; tiêu chí chặn cứng; QC video tự động (4 tiêu chí); QC đồng bộ cả bộ ảnh; gen thử trước lô | `core/qc_policy.py`, `core/claude_tasks.py`, `core/pilot.py`, `core/autoqc.py` |
| Kho kỹ năng → luật | film-director (thể loại, JSON), narration-writer (rà thoại, persona), consistency designer (Character Lock, ảnh mốc), asset-set (pilot, QC đồng bộ), seedance25 (rà motion prompt + 4 kiểm tra mơ hồ của slide), style-analyst (mẫu phong cách), auto-dialogue (phụ đề); chỉ gửi mục kỹ năng FF của nhân vật có trong dự án | `knowledge/genre/*`, `knowledge/*.md`, `prompts/10-15` |
| Giao diện | tách `app.py` thành module; 1 thanh đầu trang, 1 nút ⚙; mỗi bước có đầu bước; nhãn tiếng Việt thống nhất; Bước 1 sắp theo thứ tự dữ liệu cần; Bước 5 thành "Âm thanh & xuất bản" | `dashboard/*` |
| Chế độ tự động | cổng duyệt Character Bible (mặc định bật), gen thử trước lô, rà storyboard, QC đồng bộ, rà prompt, giọng thoại, QC video, brief nhạc, bản giao; trả lại cách duyệt khi dừng | `core/autopilot.py` |
| Thử nghiệm (tắt mặc định) | Deepix cutout cho layout (`PREVIZ_CUTOUT=1`); Kling multi-shot cho một nhóm cảnh (không vào bản ghép) | `core/previz.py`, `core/experiments.py` |

Kết quả test và danh sách lỗi: `docs/V2_TEST_REPORT.md`.

### 3.9 Kế hoạch v3 — tổng hợp mọi đề xuất, chốt việc cần làm (2026-09-23)

Tổng hợp từ: báo cáo rà soát `docs/DASHBOARD_REVIEW_2026-09-23.md`, kế hoạch/kết quả v2 (3.8, `docs/V2_TEST_REPORT.md`), câu trả lời 4 câu hỏi về nhất quán/Director/giọng/storyboard, và phân tích `docs/PHAN_TICH_2026-09-23_NHAT_QUAN_DIRECTOR_LIPSYNC_STORYBOARD.md`. **Nguyên tắc người dùng chốt: tính năng nào API chưa có thì tạm bỏ qua.**

**Bảng đối chiếu tính năng (tra tài liệu skill + API thật, chỉ đọc):**

| Tính năng | API (token) | Dùng trong v3 |
|---|---|---|
| Kling 3.0 Omni multi-shot (`multi_shot` + `multi_prompt`, mỗi shot 1 prompt + thời lượng) | Có | **Có** |
| Seedance khung đầu + **khung cuối** (`first_frame` / `last_frame`), ảnh tham chiếu, video tham chiếu, âm thanh tham chiếu | Có | **Có** (âm thanh tham chiếu: chỉ thử nghiệm) |
| TTS ElevenLabs (`eleven_v3`, `eleven_multilingual_v2`), danh sách giọng có trường `languages` | Có | **Có** — chỉ 5 giọng ghi hỗ trợ `vi` (4 nam, 1 nữ) |
| Kling Elements (`element_list` có trong lệnh gen, nhưng **tạo** Element chỉ trên web) | Không đủ | Bỏ qua |
| Lip Sync, Voice Design / Clone, Director Workspace (3D), Motion Control, Storyboard của Deepix | Không (web; token bị `LoginErr`) | Bỏ qua |

**Vấn đề gốc phải giải (từ bản chạy thử kịch bản Kenta):** 1 cảnh = 1 shot = 1 ảnh = 1 clip → 56 giây chỉ có 3 shot (15/15/26s), trong khi video Free Fire chính thức: phim ngắn "Kenta's Obsession" 75,7s ≈ 43 shot (~1,8s/shot), video kỹ năng Kenta OB55 38,8s ≈ 12 shot (1–5s/shot). Ảnh chỉ là trạng thái đầu của một cảnh dài nên nhân vật/vị trí trôi; prompt ảnh và prompt video viết ở hai lúc; Kling chỉ nhận khung đầu.

**Việc cần làm — theo thứ tự:**

| GĐ | Việc | Chi tiết | Credit |
|---|---|---|---|
| **C** (làm trước, ngắn) | **Director hiểu Free Fire** | Công cụ phân tích video tham khảo (cắt shot + Claude gắn nhãn cỡ cảnh/góc/chuyển động/vai trò; đã thử được ngay trong trình duyệt với kênh [Garena Free Fire VN](https://www.youtube.com/@GarenaFreeFireVN/videos)); bộ 10–20 video: phim ngắn CGI (Kenta's Obsession, Eclipse Rises, Free Fire x Gintama, Pitch Party, Thánh Nữ Tái Sinh), tiểu phẩm **Kelly Show**, video kỹ năng (Kenta Rework OB55), VFX; ra `knowledge/ff_directing.md` + 3 khuôn mẫu: **video kỹ năng**, **tiểu phẩm hài**, **phim ngắn CGI**; thêm cỡ cảnh "camera game" (góc thứ ba sau lưng) và lựa chọn "look" dự án (trong game / anime CGI / CGI thực) | Không (chỉ hạn mức Claude) |
| **A** (lớn nhất) | **Phân shot + "hợp đồng shot"** | Director chia mỗi cảnh thành shot 1,5–6s theo khuôn mẫu thể loại; mỗi shot một bản ghi: cỡ cảnh, góc, chuyển động máy, thời lượng, vai trò (hook/hành động/phản ứng/chèn/thoại/chuyển), khung đầu, khung cuối (nếu đổi trạng thái), 1 hành động chính, người nói + câu thoại, tài nguyên + vai trò (@Hình), điều QC phải kiểm. Kiểm tra nhịp + đa dạng cỡ cảnh + trục 180° + shot/đáp cho thoại. Đơn vị của ảnh, motion, video, giọng, phụ đề, "⚠ cũ", timeline chuyển từ **cảnh** sang **shot**; Bước 1 thành bảng storyboard theo shot | Không |
| **B** | **Nhất quán ảnh ↔ prompt ↔ video** | Prompt ảnh và prompt video cùng sinh từ hợp đồng shot; một bảng nhãn tài nguyên dùng chung cho Deepix và Seedance; ảnh khung cuối + Seedance `last_frame` cho shot đổi trạng thái; shot liền mạch cùng nhóm: khung cuối shot trước làm khung đầu shot sau; **cùng model trong một nhóm cảnh**; nhóm cảnh nhiều shot ngắn dùng **Kling multi-shot** (1 lần gọi, tránh thời lượng tối thiểu 3–4s mỗi clip); shot cận/trung của nhân vật chính ưu tiên Seedance (có ảnh tham chiếu nhân vật); QC đồng bộ cả bộ clip; cân màu khi dựng | Không (code); thử thật ở F |
| **D** | **Giọng tiếng Việt (chỉ API)** | Chỉ đề xuất giọng có `vi`; cảnh báo khi số nhân vật nữ > số giọng nữ; so `eleven_v3` với `eleven_multilingual_v2`; bảng cách đọc từ game (loot, skill, Booyah, tên nhân vật); nút nghe thử câu mẫu tiếng Việt | Rất ít (vài câu TTS) |
| **E1** | **Storyboard theo shot** | Ảnh khung đầu từng shot (Deepix, rẻ) chính là storyboard để duyệt trước khi gen video; previz 2D chạy theo từng shot (cỡ người theo cỡ cảnh); Claude tự gắn nhãn góc/cỡ cho ảnh bối cảnh trong kho | Ảnh Deepix |
| **F** | **Kiểm chứng thật** (cần duyệt ngân sách) | 1 dự án 2–3 cảnh (~10–15 shot) ở Đảo Quân Sự: Deepix 9:16, Kling multi-shot + Seedance khung đầu/cuối, TTS tiếng Việt; đo giá thật, nghe giọng, so với bản 3 shot; chạy chế độ tự động qua giao diện; hiệu chỉnh ngưỡng QC | Có |
| E2 (nghiên cứu dần) | Storyboard 3D kiểu Blender (khung camera trong không gian 3D, nhiều lớp) | Vì Director Workspace của ClipAI chỉ có trên web: nghiên cứu Blender chạy nền (bpy) — cần mô hình 3D map/nhân vật; làm sau khi A–F ổn (`docs/RESEARCH_3D_PREVIZ.md`) | — |

**Chi phí khi chuyển sang nhiều shot:** giá tính theo giây nên tổng giây gần như không đổi; phần phát sinh là shot ngắn hơn thời lượng tối thiểu (Kling 3s, Seedance 4s) phải gen dài rồi cắt → dùng Kling multi-shot cho nhóm shot ngắn để tránh.

**Bỏ qua cho tới khi API có:** Lip Sync, Kling Elements, Voice Design/Clone, Director Workspace, Motion Control, Storyboard Deepix. Ghi nhận để hỏi team ClipAI mở API.

**Cần người dùng chốt trước khi code:** (1) mặc định gen từng shot riêng hay Kling multi-shot theo nhóm cảnh; (2) "look" mặc định cho video Free Fire; (3) nhịp mục tiêu cho video ngắn (đề xuất 2–3s/shot); (4) ngân sách credit cho GĐ F; (5) đồng ý dùng video kênh chính thức làm tư liệu phân tích (chỉ phân tích nội bộ, không dùng lại hình).

## 4. Rủi ro & mitigation tổng hợp

| Rủi ro | Mitigation |
|---|---|
| Auto-reject/retry vô hạn tốn credit | `max_retry_count` + escalate to user |
| QC threshold "hộp đen", không giải trình được | `qc_checklist` theo tiêu chí + threshold config được |
| Batch lớn cần user túc trực approve | Heartbeat polling, approve 1 lần/batch |
| Gen hàng loạt rồi fail vì trùng IP bản quyền | Pre-flight check ở Character Bible + blocklist nội bộ |
| Không rõ trạng thái job khi lỗi nửa chừng | State machine chuẩn + audit trail `review_log` |

## 5. Quyết định đã chốt & còn mở

**Đã chốt:**
- `qc_agent_provider` = Claude Vision (system prompt QC riêng) — xem 3.2.1 (2026-09-18)
- Schema state machine, retry logic, `review_log.reviewer_type` — xem Mục 2, 3.1
- Điều khiển hợp nhất qua 1 Dashboard duy nhất, stepper theo thứ tự bước, nút điều khiển riêng từng khâu — xem 3.4 (2026-09-19)
- Triển khai 2 giai đoạn: **V0** (thử nghiệm qua Claude Desktop + MCP, phương án B) rồi **V1** (Dashboard hợp nhất + Anthropic API) — xem Mục 7 (2026-09-19)
- Kiến trúc core dùng chung + MCP vỏ mỏng + LLM runner hoán đổi được — xem 3.3
- Không train/fine-tune model; dùng Knowledge Base + eval set — xem 3.6
- **Chỉ dùng tính năng có trong API**; tính năng chỉ có trên web ClipAI/Deepix (Lip Sync, Kling Elements, Voice Design/Clone, Director Workspace, Motion Control, Storyboard Deepix) tạm bỏ qua — xem 3.9 (2026-09-23)
- Đơn vị sản xuất chuyển từ **cảnh** sang **shot** (phân shot + hợp đồng shot), Director học ngữ pháp dựng Free Fire từ video kênh chính thức — xem 3.9 (2026-09-23, chờ chốt 5 điểm cuối 3.9)

**Đã chốt cho V0 (2026-09-19):**
- `operating_mode` mặc định V0 = **`human_qc`** (mọi ảnh chờ người duyệt; an toàn credit khi chưa có dữ liệu QC). Chuyển `auto` sau khi dry-run cho thấy % đồng thuận QC Agent–người đủ cao.
- Ngân sách credit thử nghiệm V0: **nhỏ** (~2 kịch bản, 10–20 cảnh) — đủ dry-run tối thiểu; nếu cần hiệu chỉnh threshold sâu hơn thì xin thêm.
- **Deepix:** đã kiểm tra, **có API lấy được**. **Clip AI:** **đã có API (2026-09-19)** — bước tiếp theo là đọc tài liệu API để viết adapter `VideoProvider` (và audio nếu có), nắm response schema lỗi risk-control. Nếu chỉ có webhook mà không có endpoint truy vấn trạng thái thì cần thêm điểm nhận callback.

**Đã chốt (2026-09-22, sau khi đối chiếu slide chính thức ClipAI/Deepix với API thật):**
- **"Bàn đạo diễn" (ClipAI 3D director's desk) — tạm gác** *(cập nhật 2026-09-23: chuyển thành hướng 2 — dò lại ở lần dùng API tiếp theo, xem bên dưới)*. Không phải sản phẩm giả — có thật trên web ClipAI — nhưng không dò được endpoint qua các đường dẫn đoán mù; không đầu tư thêm thời gian trừ khi có URL/payload thật từ tab Network.
- **Không dùng Kho chủ thể Seedance (upload nhân vật riêng lên Subject Library của Clip AI).** Chưa thấy hiệu quả rõ rệt so với công sức. Ưu tiên: ảnh tham chiếu lấy thẳng từ **tài nguyên đã gắn cho cảnh trong Kho tài nguyên dự án** (`assets.scene_references`) — cơ chế này đã dùng cho Deepix (Bước 2) và từ 2026-09-22 cũng dùng cho Clip AI Seedance (Bước 4), không cần bước upload/chờ `active` riêng của Kho chủ thể. Panel "🧩 Kho chủ thể" ở Bước 1 và tuỳ chọn "🧩 Gắn ảnh chủ thể" ở Bước 4 vẫn giữ trong code (không xoá) nhưng không còn là hướng ưu tiên.
- **Video tham chiếu chuyển động (`reference_video`) — chưa ưu tiên thử nghiệm.** Ưu tiên hoàn thiện dictionary "kỹ năng nhân vật → hình ảnh" (`knowledge/ff_character_skills_visual.md`) làm nguồn chính mô tả chuyển động skill bằng chữ trong prompt, thay vì cần video mẫu thật. Code đã hỗ trợ gửi ĐỒNG THỜI ảnh tham chiếu nhân vật + video tham chiếu chuyển động trong cùng một lần gen (`core/adapters/clipai.py::submit()` nhận cả `image_references` và `reference_video`, không loại trừ nhau trừ khi bật audio sinh trên Kling) — khi nào thật sự cần độ chính xác chuyển động cao hơn chữ mô tả thì kết hợp cả hai, không phải chọn một trong hai.
- **Đồng bộ môi (Lip Sync) trên ClipAI — không ưu tiên vì còn Beta** (yêu cầu tải video có sẵn + chọn giọng lồng tiếng riêng, quy trình 2 bước cồng kềnh). Tập trung vào việc gen video có thoại ngay từ prompt (tuỳ chọn "🔊 Model tự tạo âm thanh/lời thoại" ở Bước 4 dùng Kling `sound`/Seedance `generate_audio`) — không cần hỏi team Clip AI về lip-sync/voice design nữa.
- **Blocklist IP — thu hẹp phạm vi:** hiện tại hầu như chỉ dùng nhân vật Free Fire (đã có thoả thuận bản quyền), chưa dùng nhân vật IP khác. Không cần xây blocklist rộng ngay; danh sách nhân vật FF đã có sẵn (từ `ff.garena.com`, xem Kho tài nguyên) là đủ cho giai đoạn này.
- **Giá + gợi ý chọn model** theo slide chính thức ClipAI ("Hôm nay tôi chọn mô hình video như thế nào") đã điền vào `data/pricing.json` (`listed_usd_per_video_second`, `model_choice_guide`).
- ~~**`video_model` mặc định = `kling-v3-omni`.**~~ **Thay bằng quyết định 2026-09-23 (Dashboard v2): chọn model THEO TỪNG CẢNH dựa trên slide "Hôm nay tôi chọn mô hình video như thế nào" — xem 3.8.** Lý do cũ (giữ để tham khảo): theo gợi ý chính thức của slide, Kling 3.0 Omni ghi rõ thế mạnh "tái sử dụng nhân vật, đối thoại nhiều nhân vật" — đúng nhu cầu dự án (nhân vật FF lặp lại nhiều cảnh, nhiều nhân vật đối thoại) và cũng rẻ nhất trong 2 model thật đang dùng (`$0.08/giây` so với Seedance `$0.15–0.23/giây`). Không cần sửa code — `resolve_model(None)` đã mặc định về `kling-v3-omni` từ trước. `seedance`/`seedance-2.5` vẫn chọn thủ công được cho cảnh cần chất lượng điện ảnh cao hơn.
- **"📽 Chế độ Storyboard" (ảnh cảnh trước làm tham chiếu liên tục) — vẫn giữ trong kế hoạch thử nghiệm**, không gộp vào quyết định bỏ Kho chủ thể ở trên: đây là hai vấn đề khác nhau (Storyboard = liên tục phong cách/ánh sáng giữa các cảnh; Kho chủ thể = khoá nhận diện nhân vật).

**Đã chốt hướng (2026-09-23, rà soát nhất quán — xem 3.7):**

- Workflow hiện **chạy được** (đã ra video 8 cảnh ~46 giây) nhưng **chưa chứng minh hiệu quả**: chưa đạt cổng chuyển V1 (threshold QC chưa hiệu chỉnh bằng dữ liệu, prompt chưa khóa version qua `eval/`), chưa có số liệu so với làm tay. Cần báo cáo 5 chỉ số: thời gian/giây video, chi phí/giây video, tỉ lệ đạt lần đầu, đồng thuận QC–người, số lần can thiệp tay/cảnh.
- Không dựng quy trình riêng cho từng model video; chỉ có hồ sơ khả năng từng model ở Bước 4 + bộ test cố định 3 cảnh.
- **CHỐT 3 hướng theo thứ tự ưu tiên (người dùng, 2026-09-23):**
  1. **Hướng chính — tối ưu cách dùng ảnh + text** (đơn giản nhất, giữ linh hoạt thay trang phục khi không có file 3D). Làm ngay: sửa chọn ảnh tham chiếu (A), chọn bối cảnh theo ID (B), blocking + nhóm cảnh (C), ảnh nền chung cho mỗi nhóm cảnh, tự gắn nhãn góc ảnh bối cảnh bằng Claude Vision, tách ảnh tham chiếu mặt/trang phục + bảng nhân vật khi đổi trang phục, QC 3 tiêu chí mới, báo cáo 5 chỉ số.
  2. **Bàn đạo diễn của Clip AI — dò lại ở lần dùng API tiếp theo, để build sau.** Lần tới làm việc với API Clip AI: đọc kỹ toàn bộ tính năng API cho phép (gói skill mới nhất nếu có, danh sách video/`task_type`, trường mới), kiểm tra video lưu từ Bàn đạo diễn có hiện trong API không, hỏi team Clip AI. Kết quả của nó (video white model) đã dùng được qua `reference_video` của Seedance theo tài liệu API. Xem `docs/CLIPAI_FEATURES.md`.
  3. **Combo Deepix + Blender + Meshy + Clip AI (previz 3D) — nghiên cứu dần, dùng trong tương lai.** Mới và khó; ghi chép nghiên cứu ở `docs/RESEARCH_3D_PREVIZ.md`, không chặn hướng 1.

**Còn mở (2026-09-23):**

| Quyết định | Ghi chú |
|---|---|
| ~~API Clip AI có cho dùng Bàn đạo diễn không~~ | **Đã kiểm (2026-09-23): không** — Director Workspace chỉ có trên web (token bị `LoginErr`) → bỏ qua theo 3.9; hỏi team Clip AI mở API |
| Deepix có bám ảnh layout từ 3D không | Hướng 3 (nghiên cứu) — cổng quyết định trước khi đầu tư previz 3D |
| Nguồn map 3D / model 3D nhân vật FF | Hướng 3 — map fan chỉ để thử nội bộ; bản phát hành cần asset chính thức |

**Còn mở, KHÔNG chặn V0 (chốt trước V1):**
| Quyết định | Ghi chú |
|---|---|
| Nguồn truy cập Claude cho V1 | Gói Claude (seat Enterprise/Pro/Max) và Anthropic API (Console, API key, tính tiền theo token) là 2 sản phẩm/billing tách biệt; seat không tự sinh API key. Dashboard tự gọi Claude bằng code nên V1 cần API key từ Console org công ty (không nên dùng đăng nhập seat cho ứng dụng tự động — cần xác nhận với admin/điều khoản Anthropic). Việc cần làm: hỏi admin Enterprise (a) có Console org không, (b) hạn mức token, (c) chính sách data cho ảnh nhân vật. |
| `music_provider` | Suno không có API chính thức. Ưu tiên dùng audio của Clip AI (ElevenLabs/Seed Audio tích hợp) nếu API cho phép; xác nhận license thương mại. Xem 3.5 |
| Framework Dashboard | Streamlit (mặc định) hay web frontend riêng nếu cần UI sát mockup Figma |

**Còn mở — cần chốt trước khi code V0 (chặn Tuần 1-2):**
| Quyết định | Vì sao cần | Ai chốt |
|---|---|---|
| `operating_mode` mặc định (`auto` hay `human_qc`) cho từng loại nội dung/dự án | Quyết định luồng review có block hay không — ảnh hưởng thiết kế Dashboard & MCP QC Agent | Bạn + team sản xuất nội dung |
| Deepix và Clip AI/Kling có REST API + Webhook thật không, hay chỉ có giao diện Web | Nếu chỉ có Web, Bước 2 & 4 phải dùng Playwright automation thay vì gọi API — kiến trúc MCP server khác hẳn (chậm hơn, dễ vỡ hơn khi UI đổi) | Team dev nội bộ giữ API Deepix/Clip AI |
| `qc_auto_pass_threshold` khởi điểm (0.85 là giả định, chưa có dữ liệu thật) | Threshold sai (quá lỏng/chặt) làm hỏng hiệu quả cả 2 mode ngay từ đầu | Chốt tạm ở dry-run, hiệu chỉnh bằng dữ liệu thật Tuần 3 |
| Ngân sách credit cho giai đoạn thử nghiệm (Deepix + Clip AI/Kling) | Dry-run + retry loop đều tốn credit thật; cần biết giới hạn trước khi chạy batch | Bạn / người giữ ngân sách |

## 6. Checklist chuẩn bị — cần có gì trước khi bắt đầu Tuần 1

**Truy cập & tài liệu:**
- [x] API endpoint + API Key/Authentication của **Deepix** (REST): có API; cần tài liệu chi tiết để viết adapter
- [x] API của **Clip AI** (đa model): **đã có**; còn thiếu tài liệu endpoint/auth để viết adapter (key đặt trong biến môi trường, không đưa vào repo)
- [ ] Xác nhận rate limit / quota của cả 2 API (ảnh hưởng trực tiếp `batch_poll_interval_seconds`)
- [ ] Tài liệu response schema của Kling AI khi bị content-moderation chặn (để `mcp-server-clipai` parse đúng lỗi "Failure to pass the risk control system" — Comment 4)

**Hạ tầng vận hành:**
- [ ] Máy chạy pipeline (PC vận hành) cài **Claude Desktop App** + Python runtime
- [ ] File `claude_desktop_config.json` trỏ tới các MCP servers local
- [ ] Môi trường Python cho lớp core + 6 MCP servers (`project-db`, `deepix`, `qc-agent`, `clipai`, `ffmpeg`, `music`) — venv/dependencies
- [ ] (V1) API key Anthropic Console cho Director/QC gọi bằng code — xem Mục 5
- [ ] FFmpeg cài local, kiểm tra version + codec cần dùng (transition, re-encode)
- [ ] Ổ đĩa đủ dung lượng cho `/images/`, `/videos/` khi chạy batch lớn

**Dữ liệu & nội dung:**
- [ ] 2 kịch bản mẫu (5-10 cảnh/kịch bản) để dry-run Tuần 3
- [ ] Danh sách IP/nhân vật dự kiến dùng trong dự án thật — để build blocklist ban đầu trước khi chạy batch thật (Comment 4)
- [ ] Bộ tiêu chí `qc_checklist` cụ thể (không chỉ "đúng nhân vật" chung chung — cần liệt kê rõ: góc mặt, trang phục, tỉ lệ khung hình, độ phân giải tối thiểu...) để Claude Vision QC Agent chấm điểm nhất quán

**Con người / vai trò:**
- [ ] Người build 5 MCP servers (dev)
- [ ] Người thiết kế & build Streamlit Dashboard
- [ ] Người review thẩm mỹ thật (đóng vai "User" ở 3 điểm kiểm duyệt) trong dry-run — cần người này để đo % Claude Vision QC Agent đúng/sai thực tế
- [ ] "Chuyên gia miền" biên kịch/đạo diễn để duyệt Knowledge Base và chấm eval set (Mục 3.6)
- [ ] Nguồn tri thức nền: sách/giáo trình biên kịch-đạo diễn-quay phim, kịch bản + storyboard các dự án cũ (Mục 3.6)
- [ ] Người giữ quan hệ với team dev nội bộ cấp API Deepix/Clip AI

## 7. Lộ trình triển khai: V0 → V1

### Giai đoạn V0 — Thử nghiệm (Claude Desktop + MCP, ≈ 3–4 tuần)
Mục tiêu: chứng minh pipeline end-to-end chạy được, đo chất lượng QC, hiệu chỉnh threshold, chốt Knowledge Base/prompt. Các bước cần Claude (Director Bước 1/3, QC Bước 2, Music Brief) chạy qua chat Claude Desktop với prompt template chuẩn; các thao tác còn lại gọi qua MCP tool. Dashboard V0 tối giản (xem trạng thái + duyệt ảnh) hoặc bỏ qua.

**Tuần 1 — Hạ tầng & chốt quyết định mở**
- Đã có API Deepix và Clip AI; đọc tài liệu API để viết adapter (nếu chỉ có Web thì Playwright, +1–2 tuần).
- Cài Claude Desktop + Python; test kết nối MCP cơ bản ("hello world").
- Chốt `operating_mode` mặc định, ngân sách credit thử nghiệm.
- Khởi động Knowledge Base (Mục 3.6): thu thập + lọc nguồn, chọn chuyên gia miền.
- **Deliverable:** API access hoạt động, môi trường sẵn sàng, các quyết định chặn V0 đã chốt.

**Tuần 2 — Core + MCP servers**
- Implement schema SQLite + state machine **trước tiên** trong lớp core dùng chung.
- Build MCP `project-db`, `deepix`, `qc-agent` (cả 2 nhánh `auto`/`human_qc`), `clipai` (heartbeat polling, parse lỗi moderation), `ffmpeg`; `music` có thể để sau (upload nhạc thủ công ở V0).
- Song song: viết system prompt + JSON schema cho Director/QC, tạo eval set.
- **Deliverable:** chạy được end-to-end 1 cảnh qua 5 bước bằng tool call.

**Tuần 3–4 — Dry-run & hiệu chỉnh**
- Dry-run 2 kịch bản mẫu (5–10 cảnh) ở cả 2 mode; người review thật chấm song song với QC Agent → tính % đồng thuận → hiệu chỉnh `qc_auto_pass_threshold` (0.85 chỉ là giả định).
- Lặp cải thiện prompt theo eval set; build blocklist IP v1 (case Wonder Woman + danh sách nhân vật dự kiến).
- **Cổng chuyển V1:** ≥1 video hoàn chỉnh end-to-end, threshold đã hiệu chỉnh bằng dữ liệu, prompt/checklist khóa version.

### Giai đoạn V1 — Hợp nhất trên 1 Dashboard (≈ +3–4 tuần, cần API key Anthropic)
- **Song song đầu V1:** Figma mockup chi tiết (Mục 3.4) → user duyệt trước khi build.
- Build Dashboard theo Mục 3.4 (stepper 5 bước, control bar toàn cục, nút điều khiển từng khâu, Kanban, tab Lịch sử, cảnh báo IP, tiến độ heartbeat) gọi lớp core.
- Thay LLM runner từ chat thủ công sang Anthropic API (cùng prompt template + schema).
- Build `mcp-server-music` + Bước 5a (Music Brief, 3 bản nháp) sau khi chọn `music_provider`.
- Đóng gói 1-Click Startup, runbook (xử lý job `failed` bị escalate, chỉnh threshold an toàn), Prompt Templates bàn giao.
- **Deliverable:** hệ thống bàn giao vận hành được từ 1 giao diện duy nhất, có tài liệu.

### Ước tính nỗ lực (giả định đã có đủ API key/docs/môi trường/kịch bản mẫu; dev Python có Claude Code hỗ trợ)
| Hạng mục | Ngày công |
|---|---|
| Schema + state machine + project-db | 3–4 |
| deepix | 2–3 |
| qc-agent (+ checklist prompt) | 3–4 |
| clipai (heartbeat, moderation, retry) | 4–5 |
| ffmpeg | 2–3 |
| music | 2–3 |
| Knowledge Base + eval set (Mục 3.6) | 8–12 |
| Dashboard Streamlit (màn hình 5 bước + control bar + lịch sử) | 8–10 |
| Figma mockup (song song) | 2–3 |
| Tích hợp E2E + dry-run + hiệu chỉnh threshold | 4–5 |
| Đóng gói 1-click + runbook + prompt templates | 3 |
| **Tổng** | **~41–55 ngày công** |

→ **1 dev: ≈ 8–11 tuần; 2 dev (1 backend/MCP + Knowledge Base, 1 dashboard): ≈ 5–7 tuần.** Rủi ro kéo dài: chờ API Deepix/Clip AI; Deepix/Clip AI chỉ có Web (Playwright, +1–2 tuần); hiệu chỉnh QC threshold cần nhiều vòng; chất lượng Knowledge Base phụ thuộc chuyên gia miền.

## 8. Định nghĩa "Hoàn thành" (Definition of Done) cho toàn dự án
- [ ] Chạy được ít nhất 1 video hoàn chỉnh end-to-end từ script.docx đến FINAL_VIDEO.mp4 qua Dashboard (V1), không cần chỉnh code tay
- [ ] Cả 2 `operating_mode` đều test được và cho kết quả đúng như thiết kế ở Mục 3.2
- [ ] `max_retry_count` + escalate hoạt động đúng khi cố tình cho 1 job fail liên tục
- [ ] Pre-flight IP check cảnh báo đúng với ít nhất 1 case đã biết (Wonder Woman) trước khi chạy batch thật
- [ ] Batch >100 video chạy được qua heartbeat polling mà không cần user approve từng cái
- [ ] Runbook + Prompt Templates đã bàn giao cho bộ phận sản xuất nội dung

## 9. Trạng thái triển khai (cập nhật 2026-09-23, khuya)

**Adapter thật đã viết (`core/adapters/`):** Deepix (gen ảnh Seedream 5.0 Pro) và Clip AI (video Kling Omni + Seedance) theo hợp đồng API của skill chính thức; kiểm thử bằng giao thức giả (chưa gọi API thật vì token phải do bạn đặt trong biến môi trường). Kiểm tra kết nối chỉ đọc: `py -m core.adapters.check`. Chạy thử thật: `py -m core.adapters.trial --yes`. Chi phí: ước tính trước khi chạy + sổ mức dùng trong Dashboard theo bảng giá `data/pricing.json` (xem `docs/api_notes.md`).

**Đã build (168 unit test pass, không cần API ngoài):**
- `core/` — schema SQLite, state machine job, luồng QC `auto`/`human_qc`, retry/escalate, Pause/Resume/Cancel-all, script parser (docx → cảnh/nhân vật), validators + lưu JSON của Director/QC, Character Bible + khóa, Pre-flight IP check + blocklist seed, motion prompt (Bước 3), FFmpeg command builders, prompt bundles.
- `mcp_servers/` — `project-db`, `qc-agent`, `ffmpeg-studio`, `clipai` (vỏ mỏng bọc core; `clipai` mới chạy bản giả lập); hướng dẫn `docs/V0_SETUP.md`.
- `dashboard/app.py` + `dashboard/ui.py` — Dashboard Streamlit theo mockup: stepper 7 tab có dấu ✓, control bar toàn cục, nút điều khiển từng khâu, lịch sử; các bước cần Claude chạy bằng API (`core/llm_runner.py`) hoặc dán JSON tay khi chưa có key. Mở như phần mềm bằng `Start-Dashboard.bat`/shortcut Desktop; vận hành xem `docs/RUNBOOK.md`.
- `prompts/`, `knowledge/` (v0.2: nền tảng đạo diễn, hướng dẫn 7 thể loại, lỗi ảnh AI, từ vựng motion; người duyệt tạm là chủ dự án), `data/qc_checklist.json`, `samples/` (2 kịch bản mẫu cho dry-run).
- `eval/` + `core/evalset.py` — bộ đánh giá Director: 12 mẫu (3 golden làm few-shot, 9 held-out), bộ chấm tự động phần khách quan, phiếu duyệt thẩm mỹ; hướng dẫn ở `eval/README.md`.

**Audio (Bước 5a):** adapter Clip AI audio (`core/adapters/clipai_audio.py`: nhạc `music_v2`, SFX, TTS) + `core/music.py`; Dashboard Bước 5a tạo nhiều bản nháp từ Music Brief, nghe thử, chọn để mix. `music_provider` = Clip AI (đã chốt). Chưa xác nhận bằng API thật.

**Bước 5b (Ghép & Render):** `core/final_cut.py` — tự nạp clip theo thứ tự cảnh từ Bước 4, đọc độ dài thật bằng ffmpeg, cảnh báo cảnh thiếu, chọn clip/transition/âm lượng nhạc, kiểm tra trước khi render, xem và tải bản cuối. Đã render thử thật với ffmpeg.

**Giao diện Dashboard:** đã chỉnh theo `mockup/dashboard.html` (theme, stepper có ✓, lưới thẻ ảnh + panel QC, badge trạng thái, thanh tiến độ). Xem thử không tốn credit: `py tools/seed_demo.py` rồi `powershell -File tools/run_demo.ps1`.

**Cập nhật 2026-09-20:** `knowledge/seedance_prompting.md` (nối tự động vào motion prompt khi model là Seedance); vùng chờ review của QC ở auto mode (`qc_review_floor`); transition Dip to black; sửa Character Bible trong Dashboard; sổ mức dùng có âm thanh; SFX + giọng đọc (TTS) trộn vào bản cuối (Bước 5a/5b); LLM runner gọi API Anthropic cho Director/QC/motion (code xong, chờ key thật); waveform nhạc.

**Chi phí & ngân sách (2026-09-20):** Dashboard có 💲 Bảng giá để chép giá hiển thị trên web Clip AI (giá theo từng thiết lập model/mức/độ dài); ước tính từng clip theo giá riêng. Claude: gói doanh nghiệp có hạn mức cứng 400$/tháng cho Chat + Code của tài khoản cá nhân (không phải ngân sách API); LLM runner cần API key riêng, chưa có thì dán JSON tay.

**Duyệt và dọn dẹp (2026-09-20):** duyệt tất cả có hỏi Có/Không; ảnh điểm thấp (mặc định < 0,50) tự loại + xếp hàng gen mới ở cả hai chế độ; thùng rác tách ảnh/video, tự xóa sau 30 ngày, khôi phục được.

**Kho kiến thức (2026-09-20):** tab "Kho kiến thức" trong Cài đặt: xem tổng quan và upload thêm tài liệu để nâng cấp Director/QC/Motion; tài liệu bật được nối vào prompt của bước tương ứng.

**Cập nhật 2026-09-22:** đã chạy thật 1 cảnh đầy đủ Bước 1→5 qua Dashboard (Deepix + Clip AI video/audio + render, xem `docs/api_notes.md`) — xác nhận `claude_cli` hoạt động được nhưng dùng chung hạn mức chi tiêu tháng với phiên Claude Code, không phải ngân sách riêng. `data/pricing.json` đã có giá ƯỚC TÍNH (USD, từ slide niêm yết ClipAI) để Dashboard tính chi phí thay vì luôn báo "chưa có giá". Tab "📊 Theo dõi hiệu suất" nay có bảng tổng quan **mọi** dự án (không chỉ dự án tự động hoàn toàn), kèm bước hiện tại và video hoàn tất xem/tải ngay (`core/perf.py::portfolio_rows`). Thêm tính năng **phân tích video kỹ năng bằng Claude** (bản MVP theo tài liệu "AI Video Analysis & Prompt Generation Standard" người dùng cung cấp): tải video gameplay → Claude viết nhận dạng nhân vật + kỹ năng/VFX thành chữ có gắn nhãn OBSERVED/EXPLICIT/INFERRED/UNKNOWN, người dùng duyệt trước khi lưu vào Kho tài nguyên (`core/video_analysis.py`, panel trong nút "⚙" → Kho tài nguyên). **Thiết kế lại đầu trang Dashboard** (tham khảo skill `uiux-pro-max`): nút "⚙" cạnh Đăng xuất gộp Kho tài nguyên/Bảng giá/Kho kiến thức/Lịch sử/Bài học/Phân quyền — mỗi mục mở một modal riêng (`st.dialog`, có nút ✕) thay cho `st.tabs` lồng trong `st.expander` cũ; nút "+ Dự án mới" tách ra cạnh tên người dùng; thanh bước chính chỉ còn 5 bước + Theo dõi hiệu suất. Deep link cũ (`?step=history/lessons/users`) vẫn hoạt động. Chi tiết + phần chưa làm xem `TODO.md`.

**Cập nhật 2026-09-23:** đã chạy thật 1 video hoàn chỉnh 8 cảnh (~46 giây, 3 nhân vật, thoại TTS + phụ đề + nhạc + card cuối) qua Dashboard; sửa lỗi rate-limit bị hiểu là lỗi vĩnh viễn và job kẹt do `external_id` lệch; thêm "đặc điểm neo" chống nhầm nhân vật; 548 test pass. Rà soát nhất quán nhân vật/bối cảnh/bố cục và lên kế hoạch previz 3D — xem 3.7 và Mục 5.

**Cập nhật 2026-09-23 (cuối ngày):** xong phần code P0 của hướng 1 — giữ chỗ ảnh bối cảnh + bối cảnh theo ID + ô Background; blocking + nhóm cảnh (Storyboard nối theo nhóm); **Previz 2D** (`core/layout.py`, `core/previz.py`: Claude đọc ảnh nền 1 lần, dựng layout cả kịch bản 1 lần, code đặt người theo phối cảnh, storyboard + Claude rà; Bước 2 gen theo layout; chạy bằng `claude_cli`); QC thêm `scale`/`grounding`/`set_match` và so với layout; thay trang phục bằng ảnh + bộ ảnh nhân vật 2 ảnh (`core/costume.py`); báo cáo 5 chỉ số hiệu quả (`core/effectiveness.py`, tab 📊). 588 test pass. **Chưa kiểm chứng thật** — bước tiếp theo là người dùng thử trên máy (Deepix + `claude_cli`), rồi P2 chạy kịch bản 60 giây và đọc báo cáo hiệu quả. Lưu ý: điểm QC tổng giờ là trung bình 8 tiêu chí, có thể phải chỉnh ngưỡng.

**Cập nhật 2026-09-23 (khuya) — Dashboard v2 xong và đã test một lượt:** làm hết GĐ0–8 theo 3.8 trên nhánh `dashboard-v2`, rồi test một lượt: toàn bộ unit test (lần đầu 66 lỗi) + chạy thử qua trình duyệt bằng kịch bản Kenta của người dùng (3 cảnh, 9:16, nhà cung cấp giả lập) từ tách cảnh đến bản giao (dựng 56s có 14 câu thoại → phụ đề → card cuối → bản vuông). Tìm và sửa 29 lỗi, trong đó 3 lỗi nặng: thanh bước nhảy về Bước 1 khi nhãn tiến độ đổi, bảng trộn âm tắt mất giọng thoại vừa xếp, bản xuất cắt khung mất phụ đề. 632 test pass. Chi tiết: `docs/V2_TEST_REPORT.md`. **Chưa chạy API thật** — bước tiếp theo cần người dùng đồng ý (tốn credit): 1 dự án 2–3 cảnh với Deepix 9:16, Clip AI theo model từng cảnh, TTS tiếng Việt.

**Kế hoạch tiếp theo (chốt 2026-09-23, chi tiết từng việc ở `TODO.md`):**

| Hướng | Giai đoạn | Việc | Ai | Credit |
|---|---|---|---|---|
| 1 — Ảnh + text (chính) | P0 | (A) giữ chỗ ảnh bối cảnh/Storyboard; (B) chọn bối cảnh theo ID + ô chọn ở Bước 1; (C) `blocking` + `sequence`, Storyboard nối theo nhóm; skip 3 test `sound_lib` khi thiếu ffmpeg | Claude | Không |
| 1 | P0 | **Previz 2D** (thay "ảnh nền chung"): phân tích ảnh nền (góc máy, chân trời, mặt đất, vật mốc) → layout từng shot do code dựng theo phối cảnh → storyboard + Claude rà liên tục → Deepix gen từ layout; chạy bằng `claude_cli` | Claude | Hạn mức `claude_cli`; thử thật ~6 ảnh |
| 1 | P0 | Ảnh tham chiếu mặt/trang phục + bảng nhân vật khi đổi trang phục; QC 3 tiêu chí (tỉ lệ, chân chạm đất, lệch layout) | Claude | Không |
| 1 | P0 | Báo cáo "Hiệu quả workflow" 5 chỉ số từ `manifest.sqlite` | Claude | Không |
| 1 | P1 | Hồ sơ model video + tự đề xuất model từng cảnh; bộ test 3 cảnh × Kling/Seedance | Claude + người dùng | ~$3,5 |
| 1 | P2 | Chạy lại 1 kịch bản 60 giây, đo 5 chỉ số, so với làm tay | Người dùng | Theo kịch bản |
| 2 — Bàn đạo diễn | Lần dùng API tới | Đọc kỹ toàn bộ tính năng API; kiểm tra video Bàn đạo diễn có trong API không; hỏi team Clip AI; thử `reference_video` Seedance thật (~$1–2) | Claude + người dùng | ~$2 |
| 3 — Previz 3D | Nghiên cứu dần | Blender + map FF + Meshy (rig/tư thế) + Deepix/Clip AI; ghi ở `docs/RESEARCH_3D_PREVIZ.md` | Khi có thời gian | — |

**Tạm gác (2026-09-19):** MCP Claude/V0 qua Claude Desktop; ưu tiên hoàn thiện Dashboard.

**Đang chờ điều kiện bên ngoài (đều cần người dùng):**
- Đo giá credit thật để đối chiếu với giá ước tính đã điền (model video chọn theo từng cảnh từ Dashboard v2, xem 3.8 và Mục 5).
- Vòng đánh giá `eval/` (người duyệt tạm = chủ dự án) và dry-run 2 mode để hiệu chỉnh prompt/threshold.
- Thử tải video thật qua panel "Phân tích video kỹ năng" (chưa tự động hóa được việc chọn file qua trình duyệt để test).

---
*Tài liệu nguồn: `Quy_Trinh_Auto_Pipeline_Full1.docx` (kèm 4 comment góp ý, đã phân tích ở Mục 2).*
