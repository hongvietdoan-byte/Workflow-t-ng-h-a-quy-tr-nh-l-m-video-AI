# Phân tích vòng chạy trọn một dự án của Dashboard — vì sao gen lỗi nhiều và tốn tiền (2026-09-24)

**Câu hỏi của người dùng:** để hạn chế chi phí tràn lan, cần xem lại cả quy trình chạy trọn 1 vòng của Dashboard — hiện chưa đủ hiệu
quả, gen lỗi nhiều.

**Phạm vi:** đọc code vòng tự động (`core/autopilot.py`), quyết định QC (`core/pipeline.py`), gửi job (`core/runner.py`), QC ảnh/clip
(`core/llm_runner.py`, `core/claude_tasks.py`) + số liệu GĐ6 trong `docs/PHAN_TICH_LOI_GD6_2026-09-24.md`. Bổ sung cho kế hoạch
"Tối ưu chi phí Claude API → Chuẩn xây dựng → Sửa gốc GĐ6 → Dọn tồn đọng": kế hoạch đó sửa **từng lỗi** (F1–F11, C1–C8); tài liệu này
xem **cấu trúc của vòng**, tức là vì sao một lỗi nhỏ ở đầu biến thành nhiều lần trả tiền ở cuối.

## 1. Vòng hiện tại (chế độ tự động)

```
Director ─► [cổng Bible: bật mặc định, GĐ6 đã tắt] ─► layout/previz ─► ảnh + QC ảnh (tự duyệt) ─► QC đồng bộ (tự gen lại)
        ─► motion prompt (tự duyệt) ─► giọng ─► VIDEO + QC video (tự duyệt / tự gen lại) ─► nhạc ─► SFX ─► xuất bản
```

Cổng người duy nhất bật mặc định là **Character Bible** (`GATE_DEFAULTS = {"bible": True, "pilot": False}`, autopilot.py:693).
Sau cổng đó **không người nào nhìn thấy ảnh hay clip trước khi tiền video được chi**: `start()` đặt `review_floor=None`
(autopilot.py:147) và mọi ảnh/clip `pending_review` đều bị tự duyệt (autopilot.py:312, :437).

**Tiền đi đâu:** video là khoản lớn nhất (GĐ6: $42,88 video so với ~$2,5–3 Claude/dự án và 53 ảnh). Nên câu hỏi hiệu quả thực chất là:
*có bao nhiêu lần gửi video, và bao nhiêu trong số đó được gửi từ đầu vào đã sai?* GĐ6: V2 gửi Kling 19 lần để có 21/26 shot;
V0 gửi 8 lần cho 3 cảnh.

## 2. Tám lỗ hổng cấu trúc của vòng (có bằng chứng trong code + số liệu GĐ6)

### V1 — Không có "cổng duyệt khung hình" trước bước đắt nhất
Ảnh khung đầu quyết định gần như toàn bộ chất lượng clip (GĐ6: clip ngắn bám ảnh giữ nhân vật 0/5 lỗi; phần không có ảnh bám lỗi
6/12). Nhưng ảnh chỉ qua QC của Claude — ngưỡng **chưa từng hiệu chỉnh với mắt người** — rồi đi thẳng vào video. Cổng `pilot`
(3 ảnh mẫu) có sẵn nhưng tắt mặc định và chỉ xem 3 ảnh, không xem cả bộ.
→ Mọi lỗi R1–R4, R7 của GĐ6 (Bible sai, phong cách sai, cỡ cảnh sai, tỉ lệ sai) đều **nhìn thấy được bằng mắt trên ảnh** — chỉ cần
một người lướt 26 ảnh là chặn được trước khi trả tiền video.

### V2 — Gen lại video không thay đổi đầu vào ("quay xổ số")
`qc_video` (claude_tasks.py:141) yêu cầu Claude viết `issues` "để đưa thẳng vào lần gen lại" (prompts/12_video_qc.md:9), và
`apply_qc` → `reject` → `_spawn_retry` lưu nó vào `retry_reason`. Nhưng `VideoRunner._submit_args` (runner.py:302) **không đọc
`retry_reason`**: gửi lại đúng ảnh, đúng motion prompt, đúng model. `retry_reason` chỉ được dùng ở ảnh (runner.py:496).
→ Mỗi lần QC video loại = trả thêm một clip với **đầu vào y hệt**. Đây là cơ chế cụ thể đằng sau R6 ("V2 nhóm S35–S38: 0,55 → gen
lại vẫn loại"). Multi-shot còn tệ hơn: một shot sai → gen lại cả nhóm 15s.

### V3 — Gen lại ảnh chỉ "vá thêm câu" vào prompt cũ, và câu vá có rác
Ảnh gen lại = prompt cũ + `". Fix: " + retry_reason` (runner.py:496–497). `retry_reason` là nguyên văn ghi chú loại, dạng
`"QC 0.71 < 0.82 — Tiêu chí chặn cứng dưới mức sàn: character 0.40 < 0.60. Kelly must wear…"` → prompt gửi Deepix chứa **điểm số và
câu tiếng Việt**. Mỗi lần gen lại chỉ mang lý do của lần gần nhất (lần vá trước bị mất → dễ dao động giữa hai lỗi). Không lần nào
đi ngược lên lớp sai (Bible, layout, ảnh tham chiếu) — nếu gốc sai ở đó, gen lại bao nhiêu cũng sai y như cũ.

### V4 — QC đồng bộ chạy SAU khi đã duyệt ảnh, rồi mở lại ảnh đã duyệt
`_setcheck_phase` (autopilot.py:752) chạy khi mọi ảnh đã được duyệt, sau đó `redo_from_set_check` (:767) mở lại từng ảnh "lệch" và
gen lại với câu sửa của Claude — không người xem, không kiểm câu sửa (R3: câu sửa gọi nhầm Kenta thành Maxim). Kiểm tra đồng bộ vốn
nên nằm **trước** khi gen hàng loạt (chốt "chuẩn" ở pilot), không phải sau.

### V5 — Dây chuyền "đầu vào đổi → tự làm lại" tự chi tiền
`lineage` đánh dấu cũ: ảnh đổi → motion prompt cũ → clip cũ. Ở pha video, clip cũ được **tự tạo job mới** qua
`regen.regenerate_video` (autopilot.py:425) — job mới có `retry_count=0`, nên **không bị `max_retry` chặn**, chỉ chặn bởi trần tổng.
Một câu sửa của QC đồng bộ có thể kéo theo: ảnh mới → Claude viết lại motion → clip mới, không ai được hỏi.

### V6 — Trần chi tính bằng SỐ JOB chung cả dự án, không theo tiền và không theo cảnh
`_job_caps` (autopilot.py:201–204): trần = số cảnh × (`max_retry` + 2), đếm chung. Một cảnh hỏng gốc có thể ăn hết phần của các cảnh
khác trước khi dừng. Job 4s và job multi-shot 15s đếm như nhau. Trần tiền ($50 đợt thử, $5 Claude) có, nhưng không có "ngân sách
theo cảnh" hay "dừng khi một cảnh trượt 2 lần cùng lỗi".

### V7 — Quyết định QC bằng điểm trung bình, ngưỡng chưa hiệu chỉnh
`overall = sum(scores)/len(scores)` (pipeline.py:313), đạt khi ≥ 0,82 và không dính mức sàn. 8 tiêu chí ảnh ngang nhau; `scale`,
`set_match`, `composition` không có mức sàn → ảnh sai cỡ cảnh vẫn qua nếu ánh sáng đẹp (R7). Ngược lại lỗi nhỏ motion_match vẫn kéo
trung bình clip dưới 0,82 → gen lại trả tiền. Chưa có số đo "QC đồng ý với người bao nhiêu %" → không biết ngưỡng nào đúng.

Nhỏ hơn: ảnh thất bại nào cũng được autopilot thử lại (autopilot.py:305) kể cả lỗi không tạm thời; Claude QC chấm ảnh từng cái một
(mỗi lần gửi lại toàn bộ Bible + ảnh tham chiếu — chi phí Claude, đã có C2 trong kế hoạch).

### V8 — Không kiểm đầu vào trước khi gửi; lỗi API được sửa SAU khi đã hỏng, autopilot thử lại mù *(số liệu thật GĐ6)*
Phiên trước (máy người dùng, đọc CSDL GĐ6 chỉ đọc) đếm được **khoảng 40 lần gen video hỏng/phải thử lại do lỗi đầu vào kiểm được
trước khi gửi** — không phải do chất lượng — và autopilot tự "thử lại" **21 lần**:

| Lỗi | Số lần | Trạng thái trong code hiện tại | Lỗ hổng còn lại |
|---|---|---|---|
| Sai tham số khung đầu/cuối Seedance (khung đầu đi cùng ảnh tham chiếu bị từ chối) | 9 | Đã sửa trong lúc chạy (`SEEDANCE_REFS_WITH_FIRST_FRAME = False`, commit aa27dd9) | Luật API chỉ được biết **sau khi** bị từ chối; không có bảng "luật từng model" kiểm trước khi gửi |
| Seedance chặn ảnh "giống người thật" | 8 | Sau khi bị chặn mới chuyển cả nhóm sang Kling (`_on_refused`, runner.py:366) | Mỗi nhóm vẫn phải **hỏng một lần** mới chuyển; biết trước được (phong cách CGI tả thực + Seedance) nhưng `model_router` không dùng |
| Prompt vượt 512 ký tự (Kling multi-shot) | 3 | Đã cắt ≤ 512 (commit a3f14f2) | Cắt âm thầm, không báo phần bị mất |
| Dò trạng thái báo `not_found` | 13 | `status()` chỉ quét **trang đầu 50 task** của `video-list` (clipai.py:277), 12 lần không thấy → `failed`, **không tạm thời** (clipai.py:287) | Task rơi khỏi trang 1 khi nhiều dự án chạy song song → job bị đánh hỏng → autopilot **gửi job mới** trong khi task cũ có thể vẫn chạy và **vẫn bị tính tiền** (nguy cơ trả 2 lần) |

Điểm chung: cả 4 loại đều **biết được trước khi chi tiền** (luật API, giới hạn độ dài, rủi ro người thật, cách dò trạng thái) nhưng
pipeline chỉ phát hiện bằng cách gửi thật rồi hỏng. Autopilot lại coi mọi lỗi không phải kiểm duyệt là "thử lại được"
(autopilot.py:430), nên lỗi cấu hình lặp lại cho tới khi hết trần hoặc có người sửa code giữa chừng.

## 2b. Số liệu thật GĐ6 — tiền và lỗi dồn ở bước nào

Nguồn: `tools/audit_run.py` chạy **chỉ đọc** trên `manifest.sqlite` thật (2026-09-24 15:37). Tổng video 3 dự án GĐ6
(#2 V1 từng shot, #3 V2 multi-shot, #4 V0 mỗi cảnh một clip) = **$42,88** — khớp đúng số đã chi, nên sổ chi đáng tin. Giá là ước
tính trong `data/pricing.json`; ảnh Deepix chưa có giá (chỉ đếm); Claude chạy qua CLI (gói thuê bao) nên không có dòng tiền Claude.

### Tiền video theo LÝ DO tạo từng lần gửi

| Lý do gửi | V1 từng shot | V2 multi-shot | V0 mỗi cảnh | **Tổng** | **%** |
|---|---|---|---|---|---|
| Lần đầu | $11,88 (21) | $5,52 (5) | — | **$17,40** | 41% |
| Gửi lại sau lỗi kỹ thuật / nhà cung cấp | — | $8,24 (8) | $3,60 (3) | **$11,84** | 28% |
| Người bấm gen lại | — | $5,84 (6) | $3,00 (2) | **$8,84** | 21% |
| QC video loại → tự gen lại | — | — | $4,80 (3) | **$4,80** | 11% |
| **Cộng** | $11,88 | $19,60 | $11,40 | **$42,88** | |

→ **59% tiền video ($25,48) trong sổ là gửi lại**, chỉ 41% là lần gửi đầu (lưu ý: ~$15 trong sổ là task ClipAI không hề tạo — phát hiện 1). Theo phương án: V1 **không gửi lại lần nào** (rẻ nhất, $11,88
cho 21 clip); V2 tốn gấp 3,5 lần tiền gửi đầu; V0 không có lần gửi đầu nào thành công ngay (xem lỗi 1.3).

### Phát hiện 1 — "Gửi" nhưng ClipAI KHÔNG có task: sổ chi ghi thừa, Dashboard chờ rồi gửi lại (khoản lớn nhất, chưa có trong F1–F11)
- V2: **12 job đã ghi sổ ($11,68 = 60% tiền V2) bị đánh `not_found`** ("task not found in the first list page"), autopilot gửi
  lại 8 lần. V0: 1 job `not_found` ($1,20). Dự án #1 (trước GĐ6): 4 job gửi lúc ClipAI đang báo `Too many requests`.
- **Đối chiếu với ClipAI** (`tools/recover_clips.py`, 2026-09-24 15:50): danh sách Kling của tài khoản **đã quét hết — 136 task từ
  07/01 đến 24/09**, trong đó **không có task nào** trong 16 task Kling bị đánh `not_found`/lỗi dò trạng thái (V2, V0, #1). Tức là
  ClipAI **đã trả task_id khi nhận lệnh nhưng không tạo task** — không phải task trôi xuống trang 2, cũng không phải clip xong mà
  chưa tải. Không có clip nào để lấy lại, và **nhiều khả năng không bị tính tiền** (cần đối chiếu lịch sử số dư ClipAI để khẳng định).
- Hệ quả thật:
  1. **Sổ chi Dashboard ghi thừa ~$15** (ghi tiền ngay lúc gửi, không đối chiếu ClipAI): $11,68 (V2) + $1,20 (V0) + ~$2 (#1),
     cộng $1,20 cho clip Seedance bị chặn bản quyền mà ClipAI ghi `cost=0`. **Tiền video GĐ6 thực tế ước ~$28–29, không phải
     $42,88** → trần $50 bị chạm sớm vì tiền "ma".
  2. Mỗi task "ma" làm shot đó **chờ 12 lần dò (~vài phút) rồi mới gửi lại**, và nhiều lần gửi lại cũng thành "ma" (V2 S22 3 lần,
     S01/S05/S14/S18 mỗi shot 2 lần) → chậm, dễ chạm trần số job.
  3. Các task "ma" dồn vào lúc gửi dồn dập (V2: 11 task trong 31 phút, 00:35–01:06 UTC; #1: 3 task cùng phút 16:41 lúc đang bị
     giới hạn tốc độ) → giả thuyết: ClipAI **nhận rồi bỏ** lệnh khi quá tải/giới hạn đồng thời. Cần hỏi ClipAI hoặc đo lại.
- Chi tiết từ trường `cost` của ClipAI: task Kling multi-shot hỏng vì prompt > 512 ký tự vẫn ghi **`cost=90`** (có thể **bị tính
  tiền dù hỏng** — đối chiếu số dư theo task_id 139299143209, 400512879984); task Seedance bị chặn bản quyền ghi `cost=0`.
- **Clip bị chặn bản quyền (V0 S03, job 115, Seedance 2.0 Fast, 15s):** ClipAI chỉ trả câu chung "The request failed because the
  output video may be related to copyright restrictions" + Request id, **không nói nhân vật/chi tiết nào**. Bộ lọc chạy trên
  **video đầu ra** (không phải ảnh đầu vào) → nhân vật Free Fire trong clip Seedance có nguy cơ bị chặn bất kỳ lúc nào; Kling chưa
  chặn lần nào trong GĐ6 → căn cứ cho W11 (nhân vật game → ưu tiên Kling).

### Phát hiện 2 — Gen lại video không đổi đầu vào: 100% trường hợp, 0% được dùng
- V0: 3/3 lần QC loại → tự gen lại đều **cùng ảnh + cùng motion prompt** (khẳng định V2 ở mục 2). $4,80, **0/3 clip được dùng**.
- V0 S03 một mình tốn **$6,60 (4 clip 15s), không clip nào vào bản cuối**; lý do QC: "Maxim đâm tường sai tư thế ở giây 12" —
  lỗi nhiều nhịp trong clip dài (R5), gen lại bao nhiêu cũng vậy.

### Phát hiện 3 — QC ảnh THẤY lỗi bố cục/tỉ lệ nhưng không chặn; QC video chặn nhưng người lại giữ
- V1 ảnh (38 lần chấm): `set_match` TB **0,52 (36/38 dưới 0,7)**, `composition` TB **0,52 (31/38)** — tức là QC đã nhìn thấy lỗi
  layout/cỡ cảnh R7 ở gần như mọi ảnh, nhưng hai tiêu chí này không có mức sàn → vẫn qua. Chỉ 3/38 ảnh bị loại.
- V1: `character` có **15/38 ảnh dưới mức sàn 0,6** nhưng chỉ 3 ảnh bị loại → cần xác minh đường đi. Nghi vấn trong code:
  QC chạy ở chế độ `human_qc` chỉ "gợi ý" → ảnh ở `pending_review` → autopilot **tự duyệt mọi `pending_review`**
  (autopilot.py:312), kể cả ảnh đã dính mức sàn (W15).
- V2 video (16 lần chấm): `motion_match` TB **0,49**, `identity` TB **0,58** (7 dưới sàn) — đúng R4 (shot sau trong nhóm không có
  ảnh bám). Người **giữ lại 15 clip QC đã loại** → hoặc ngưỡng QC video lệch mắt người, hoặc giữ để khỏi trả tiền; cả hai đều
  cho thấy **QC video chưa hiệu chỉnh** (W8).
- Dự án #1 (trước GĐ6): QC ảnh loại **68%**, `character` TB 0,57 — và câu sửa của QC đòi "Kelly **high ponytail** with orange
  streak": QC đang **ép theo Character Bible sai** (R1) → 19 ảnh tự gen lại để đuổi theo một mô tả sai. R1 có từ trước GĐ6.

### Phát hiện 4 — Lỗi gửi (tham số) và chặn nội dung
- V0: **15 lần gửi bị từ chối** `[InvalidParameter] first/last frame…` (Seedance không nhận khung đầu kèm ảnh tham chiếu), 2
  `real_person`, 1 bản quyền → autopilot **tự thử lại 13 lần**. Lần gửi bị từ chối ngay có lẽ không tốn tiền nhưng tốn lượt thử,
  thời gian và làm cảnh 3 dừng "cần bạn xử lý".
- V2: 3 lần `multiPrompt[0].prompt: size must be between 0 and 512`.

### Phát hiện 5 — Nhiễu làm che lỗi thật
- `cli_error` "hit your session limit": **1.516 (V1) + 1.625 (V2) + 20 (V0) lần** — autopilot hỏi lại Claude mỗi nhịp khi hết hạn
  mức (đã sửa: dừng hẳn, `_stop_if_claude_blocked`). Hệ quả còn lại: V1 chỉ **5/21 clip được QC video**.
- `dialogue_length` **1.092 lần** ở V2: dự án tắt tiếng video nên cổng thoại chỉ ghi cảnh báo mỗi nhịp và **không kéo dài clip**
  (autopilot.py `_dialogue_gate`) → giọng TTS dài hơn clip ở S23; cảnh báo lặp làm nhật ký khó đọc (W16).

### Ước lượng: bao nhiêu trong $25,48 gửi lại là tránh được

| Nhóm | Tiền | Sửa bằng |
|---|---|---|
| Gửi lại do task "ma" / lỗi gửi | $11,84 (phần lớn là tiền ghi thừa, xem phát hiện 1) | W12 (xác nhận task có thật trước khi ghi sổ + gửi lại ngay khi không có) + W10 (luật từng model) — **tránh gần hết** |
| QC tự gen lại cùng đầu vào | $4,80 | W3 (đổi đầu vào hoặc không gen) + F5 (chẩn đoán) — **tránh gần hết** |
| Người bấm gen lại | $8,84 | Phần lớn do ảnh/nhóm sai từ đầu (R1–R4, R7) → cổng storyboard W1 + F1–F4, F7–F10 — **tránh phần lớn** |

→ Theo sổ, **~$20–23 trong $42,88 (≈ 50%) là tránh được**; trong đó ~$15 là tiền ghi thừa (không chi thật). Tính trên tiền
  thật (~$28–29), phần tránh được chủ yếu là người bấm gen lại ($8,84) + QC gen lại cùng đầu vào ($4,80) ≈ **$13–14 (≈ 45–50%)**.

## 3. Vì sao tổng hợp lại thành "gen lỗi nhiều"

```
lỗi gốc ở đầu (Bible/layout/phong cách)  ──không ai xem ảnh──►  video gửi từ ảnh sai
        ▲                                                             │ QC video loại
        └──── không có bước chẩn đoán ◄── gen lại với ĐẦU VÀO Y HỆT ◄──┘  (lặp tới khi hết trần)
```

Vòng hiện tại **tự động hoá việc trả tiền cho lỗi** nhưng **không tự động hoá việc tìm lỗi**: mọi vòng lặp sửa đều nằm ở lớp cuối
(gen lại), không vòng nào quay về lớp gốc. Đây cũng là lý do "đã định hướng tránh lỗi" mà vẫn gặp: biện pháp đặt ở đầu vòng, nhưng
không có điểm kiểm nào xác nhận biện pháp đã có tác dụng trước khi đi tiếp.

## 4. Đề xuất: vòng mới "rẻ trước, đắt sau, người duyệt ở 2 điểm"

Nguyên tắc: **mỗi bậc tiêu tiền nhiều hơn bậc trước ~10 lần thì phải có một điểm kiểm trước nó.**
Chữ (Claude, ~cent) → ảnh (Deepix) → video (~$0,5–6/clip).

| Bậc | Việc | Ai quyết | Tốn |
|---|---|---|---|
| 0. Kiểm đầu vào | Ảnh tham chiếu đọc được; Bible ↔ ảnh tham chiếu (F1); phong cách ↔ tham chiếu (F2); ước tính chi phí cả dự án (C6) | Máy — **chặn** khi lệch | Claude ~cent |
| 1. Kịch bản → shot | Director + Character Bible + bảng shot | **Người duyệt** (cổng Bible, luôn bật) | Claude |
| 2. Ảnh mẫu | 1 ảnh/nhân vật chính + 1 ảnh/bối cảnh + 1 shot cận + 1 shot rộng (≈4–6 ảnh) → chốt "chuẩn" cho QC đồng bộ | **Người duyệt** (pilot, luôn bật lần chạy đầu) | vài ảnh |
| 3. Cả bộ ảnh | Gen phần còn lại; QC từng ảnh; gen lại tối đa 1 lần và **viết lại prompt** (không vá câu); QC đồng bộ so với chuẩn ở bậc 2, **chỉ báo** | Máy | ảnh |
| 4. **Storyboard** | Xem cả bộ khung đầu trên một màn (đã có contact sheet), kèm cờ QC; sửa/đổi ảnh từng shot | **Người duyệt — cổng mới, bắt buộc trước tiền video** | 0 |
| 5. Motion | Viết + rà motion prompt | Máy | Claude |
| 6. Video mẫu | 1 clip đại diện mỗi model/kiểu (vd 1 shot đơn Seedance + 1 nhóm multi-shot) | **Người xem** (tùy chọn, bật khi dự án mới/model mới) | 1–2 clip |
| 7. Cả bộ video | QC video → **chẩn đoán** (F5): lỗi đầu vào → dừng shot đó, báo lớp cần sửa; lỗi ngẫu nhiên của model → gen lại 1 lần, **có đưa `issues` vào motion prompt**; lỗi nhỏ → chỉ báo | Máy | video |
| 8. Âm thanh + xuất bản | như hiện tại | Máy | |

Thay đổi cụ thể trong code (không tốn credit):

| # | Sửa | File | Chặn lỗ hổng |
|---|---|---|---|
| W1 | Cổng **storyboard** mới giữa ảnh và motion/video (`_Wait("storyboard")`), bật cứng; Bước 2 có nút "Duyệt cả bộ khung" | core/autopilot.py, dashboard/steps/step2.py | V1 |
| W2 | Pilot bật mặc định lần chạy đầu của dự án; chọn ảnh mẫu theo nhân vật/bối cảnh/cỡ cảnh thay vì 3 cảnh đầu; kết quả pilot = chuẩn cho QC đồng bộ | core/pilot.py, core/autopilot.py | V1, V4 |
| W3 | Gen lại video phải **đổi đầu vào**: đưa `issues` vào motion prompt (có kiểm độ dài, đúng tên nhân vật); cùng đầu vào → không tự gen lại | core/runner.py (VideoRunner), core/pipeline.py | V2 |
| W4 | Gen lại ảnh: tách `retry_reason` (ghi chú cho người) khỏi `fix_prompt` (câu tiếng Anh sạch, cộng dồn các lần sửa); bỏ điểm số/tiếng Việt khỏi prompt Deepix | core/pipeline.py, core/runner.py, core/db.py | V3 |
| W5 | QC đồng bộ chạy sau pilot + trước cổng storyboard; chỉ báo, không tự `redo_from_set_check` | core/autopilot.py | V4 |
| W6 | Clip cũ do đầu vào đổi → **không tự gen lại**; liệt kê ở cổng storyboard/Bước 4 để người bấm | core/autopilot.py (_videos_phase) | V5 |
| W7 | Trần theo cảnh: mỗi shot tối đa 1 lần tự gen lại ảnh + 1 lần video; cùng tiêu chí trượt 2 lần → dừng shot đó (`needs_attention`), các shot khác chạy tiếp; trần tiền theo dự án (C6) thay cho trần số job | core/autopilot.py, core/budget.py | V6 |
| W8 | QC: mức sàn cho `scale`, `set_match`, `composition` (F11); `motion_match` thấp mà `identity/physics/artifacts` đạt → chỉ báo, không gen lại; ghi quyết định người vs QC để đo đồng thuận, chỉ tăng tự động khi đồng thuận ≥ 80% | data/qc_checklist.json, core/pipeline.py | V7 |
| W9 | Autopilot chỉ thử lại job thất bại **tạm thời** (mạng, hết lượt); lỗi tham số/nội dung → dừng shot đó, báo rõ | core/autopilot.py:305, :430 | V8 |
| W10 | **Kiểm đầu vào trước khi gửi** theo bảng luật từng model (`data/provider_rules.json`: khung đầu/cuối + ảnh tham chiếu có được đi cùng không, độ dài prompt, thời lượng, tỉ lệ khung); vi phạm → sửa hoặc chặn trước khi tốn tiền; mỗi lỗi API mới gặp → thêm 1 dòng luật + test | core/adapters/clipai.py, core/runner.py, data/ | V8 |
| W11 | **Chọn model biết trước rủi ro**: phong cách CGI tả thực / ảnh bị chặn trước đó → xếp Kling ngay từ đầu, không đợi Seedance từ chối | core/model_router.py | V8 |
| W12 | ✅ **ĐÃ LÀM (2026-09-24)** — **Xác nhận task có thật**: sau khi gửi, kiểm task xuất hiện trong `video-list` (quét nhiều trang); chỉ ghi sổ chi khi thấy task (hoặc ghi "tạm" rồi hủy); không thấy sau vài lần → đánh "ClipAI không tạo task", gửi lại ngay (không tốn tiền) thay vì chờ 12 lần; gửi giãn cách, giới hạn số task đồng thời để tránh bị bỏ lệnh | core/adapters/clipai.py:274–288, core/runner.py | V8 |
| W13 | Cắt prompt > 512 ký tự thì **báo** phần bị cắt (diag + Bước 3), ưu tiên rút gọn bằng Claude trước khi gửi | core/adapters/clipai.py, core/runner.py | V8 |
| W14 | **Đối chiếu với ClipAI** (công cụ `tools/recover_clips.py` đã có — GĐ6: 0 clip để lấy lại; thêm: sổ chi lấy `cost` thật của ClipAI thay vì ghi lúc gửi): công cụ quét các trang `video-list` theo `external_id` của job bị đánh `not_found`/lỗi dò trạng thái; task xong thì tải về, gắn lại vào job (không gửi lại) | tools/, core/adapters/clipai.py | 2b-1 |
| W15 | Autopilot **không tự duyệt** ảnh/clip `pending_review` có tiêu chí dưới mức sàn; để lại cho người ở cổng storyboard | core/autopilot.py:312, :437 | 2b-3 |
| W16 | Cổng thoại: tắt tiếng video vẫn kéo dài clip cho vừa giọng TTS; cảnh báo ghi **một lần** mỗi shot, không mỗi nhịp | core/autopilot.py (_dialogue_gate) | 2b-5 |

## 5. Tác động ước tính (phải đo lại ở GĐ4)

**Thứ tự làm theo tiền (số liệu 2b):** W12 + W14 (dò trạng thái, lấy lại clip — 28% tiền video GĐ6) → W1 + F1–F4 (cổng storyboard,
Bible đúng — 21% người bấm gen lại) → W3 + F5 (gen lại phải đổi đầu vào — 11%) → W10/W11 (luật từng model) → W7/W8/W15 (trần, QC).

- **Lỗi đầu vào (V8):** ~40 lần gen hỏng/thử lại + 21 lần autopilot tự thử lại trong GĐ6 thuộc loại chặn được trước khi gửi
  (W9–W13) → mục tiêu **0 lần hỏng do tham số** ở đợt sau; riêng W12 bịt nguy cơ trả tiền 2 lần cho một clip.

- Lấy GĐ6 V2 làm ví dụ: 19 lần gửi Kling cho 21/26 shot. Nếu cổng storyboard chặn được các nhóm có ảnh/nhóm sai (R4, R7) và gen lại
  video chỉ xảy ra khi đổi đầu vào, số lần gửi ước ~8–10 (bằng số nhóm) + 1–2 lần gen lại → **giảm ~40–50% tiền video**.
- Tiền Claude giảm theo: bớt QC lặp lại do bớt gen lại, cộng C2–C5 của kế hoạch chi phí.
- Chi phí đổi lại: người dùng mất ~5–10 phút ở 2 cổng (ảnh mẫu, storyboard). Đó là thời gian rẻ nhất trong toàn vòng.

## 6. Ghép vào kế hoạch hiện có

Đề xuất thêm **W1–W16** làm một giai đoạn "Sắp xếp lại vòng chạy" đặt **sau GĐ2 (lưới an toàn), trước/cùng GĐ3 (F1–F11)**, vì:
- W3/W4/W7/W8 trùng hướng với F5 (chẩn đoán) và F11 (mức sàn) → làm chung.
- W1/W2/W5/W6 là điều kiện để bậc kiểm thật GĐ4 (chữ → ảnh → 1 cảnh video) diễn ra đúng trong Dashboard thay vì làm tay.
- Tất cả không tốn credit; có test bằng MockLlm + provider giả (luồng) và fixture GĐ6 (nội dung).

Cần người dùng chốt:
1. Cổng storyboard **bắt buộc** (không tắt được) hay bật mặc định nhưng tắt được cho dự án đã quen?
2. Mức gen lại tự động: tối đa 1 lần/ảnh và 1 lần/clip có ổn không?
3. Video mẫu (bậc 6) bật mặc định hay chỉ khi đổi model/kiểu gen?
