# V3.1 — Gói sửa M1.1 / M1.4 / M1.5, ma trận 6 rủi ro, bảng chuyển kế hoạch S (20/10/2026)

> **Trạng thái: CHỈ AUDIT + CHUẨN BỊ, CHƯA SỬA CODE PIPELINE.** Theo chỉ đạo người dùng 20/10 ("CHỈ ĐẠO XỬ LÝ RỦI RO V3.1 VÀ KẾ HOẠCH S"):
> được audit, cập nhật tài liệu, lập bảng, chuẩn bị gói; KHÔNG triển khai code pipeline, migration, đổi provider đang chạy, gọi API trả phí.
> Mọi số liệu đọc CHỈ ĐỌC trên máy chính (`data/manifest.sqlite` mở `mode=ro`, danh sách task ClipAI bằng GET, 0 USD). Mốc code: `main` = `89939658`.

---

## 1. Gói sửa khẩn cấp M1.1 — QC crash vì `BYĐ.vat` (CHỜ DUYỆT PHẠM VI)

### 1.1 Bằng chứng
- Dữ liệu thật: mọi `byd.vat` khác rỗng đều là **chuỗi** (v1), không có dạng object: #30 4 shot (vd shot idx 3 `["BOM_KEO"]`), #31 1 shot
  (idx 33 `["AWM"]` — là "shot 30" cũ, đánh số lại sau khi chèn 3 shot 18/10). #24, #28, #29, #33: rỗng.
- Đọc `byd.vat` dạng object: **chỉ một chỗ** — `core/qc_observe.py:62–66` (`compile_checks`): phần tử không phải dict → `raise ValueError("BYĐ.vat
  thiếu vật chuẩn")`. Chạy khi cờ `qc_observe_enum` BẬT (máy chính: BẬT) qua 2 đường gọi:
  `core/qc_scene.py:619–620` (`qc_observe.review_scene`, QC theo cảnh) và `core/llm_runner.py:927–929` (`qc_observe.run`, QC từng ảnh).
- Đọc khác (không crash): `core/shot_intent.py:207` `_kho_ids` (chỉ lấy `kho_id` khi phần tử là dict — chuỗi bị bỏ qua đúng), `core/shot_intent.py`
  `validate` không kiểm hình dạng `vat`; `prompts/31_director_byd.md:22` mẫu `"vat": []`. Mọi chỗ `get("vat")` khác trong code là khóa
  `thanh_phan[].vat` / dàn cảnh sân khấu (khác nghĩa), không đụng.

### 1.2 Phạm vi sửa đề xuất (giới hạn đúng lỗi)
| File | Thay đổi |
|---|---|
| `core/shot_intent.py` | thêm MỘT parser `vat_items(byd) -> List[dict]`: phần tử chuỗi (v1) → `{"vat": <chuỗi>, "_v": 1}`; dict có `vat` → giữ nguyên; giá trị `vat` là một chuỗi đơn (không phải list) → coi như list một phần tử; `None` / thiếu → `[]`. Phần tử khác (số, dict thiếu `vat`…) → **giữ nguyên để nơi gọi báo lỗi như cũ** (không âm thầm ép kiểu). |
| `core/qc_observe.py` | dòng 62: đọc qua `shot_intent.vat_items(...)` thay vì `(byd or {}).get('vat') or []`. Hành vi với dict đúng chuẩn và với dữ liệu sai giữ nguyên (vẫn `ValueError`). |
| `core/shot_intent.py` `_kho_ids` | đọc qua cùng parser (không đổi kết quả: chuỗi không có `kho_id`). |

Không đổi: tiêu chí QC, ngưỡng, câu hỏi gửi Claude, mức `set_match`, cờ. Ngữ nghĩa sau sửa: một vật v1 `"AWM"` sinh đúng một câu hỏi
`set_match` "AWM" (nguồn `byd.vat[0].vat`) — y như vật v2 cùng tên.

### 1.3 Test (regression)
- `tests/test_shot_intent.py`: parser — list chuỗi, list dict, trộn, chuỗi đơn, `None`, rỗng, phần tử số / dict thiếu `vat` (trả nguyên để báo).
- `tests/test_qc_observe_d14.py`: `compile_checks` với BYĐ **chép nguyên từ CSDL thật** #31 idx 33 (`["AWM"]`) và #30 idx 3 (`["BOM_KEO"]`) — fixture
  `tests/fixtures/byd_vat_v1_p30_p31.json` (chỉ trường `byd` + `characters`, đọc `mode=ro`) → không raise, sinh 1 check `set_match`; dict v2 → như cũ;
  dict thiếu `vat` → vẫn `ValueError` (khóa ngữ nghĩa cũ).
- Chạy: 2 file trên + vùng quy ước 7 (`py tools/related_areas.py core/qc_observe.py core/shot_intent.py` → step1, step2, step3, step4, plates3d) +
  `-m "not slow"`; agent rà quy ước 7 trước commit.

### 1.4 Nghiệm thu / rollback / chi phí
- Nghiệm thu: test trên xanh; chạy lại QC (code, provider giả) cho #31 idx 33 trên **bản sao CSDL** không còn `ValueError`. Không gọi Claude thật.
- Rollback: revert một commit (không migration, không cờ mới, không đổi dữ liệu).
- Biện pháp tạm khi chưa sửa (Cấp 3 — chỉ khi người dùng muốn): tắt `qc_observe_enum` trên máy chính → QC về đường cũ; không khuyến nghị nếu
  M1.1 được duyệt nhanh. Chi phí: 0 USD.

---

## 2. M1.4 — Provider Claude: biện pháp kiểm soát tạm thời + gói theo D02

### 2.1 Kết quả audit (chỉ đọc; agent rà toàn repo + kiểm máy chính)

**Một điểm chọn client:** `core/llm_runner.py:1312 client_from_env` — `LLM_PROVIDER` = `claude_cli` → `ClaudeCliClient`; `anthropic` →
`AnthropicClient`; **rỗng mà môi trường có `ANTHROPIC_API_KEY` → vẫn ra `AnthropicClient` (dòng 1320, fallback ngầm)**. Ngoại lệ duy nhất:
`devsys/scorer.py:471–488` luôn tạo `AnthropicClient` (có ô xác nhận + `--max-usd`).

**Máy chính (kiểm 20/10, chỉ có/không, không đọc giá trị):** biến môi trường **User có `ANTHROPIC_API_KEY`**; `dashboard.env` `LLM_PROVIDER=anthropic`;
Dashboard 8501 (pid khởi động 19/10 19:40) và 8503 (19/10 19:45) chạy qua launcher **chép key từ User vào tiến trình**
(`tools/launch_dashboard.ps1:74–79`, `.claude/launch.json` dòng 42); devsys tương tự (`tools/launch_devsys.ps1:46–48`).

**Vì sao hiện chưa mất tiền:** tài khoản API hết tiền 19/10 01:08 → `budget.halt(anthropic)` đang BẬT → mọi `AnthropicClient` CÓ sổ chi bị từ
chối trước khi lên mạng (`core/budget.py:284`, `llm_runner.py:603`). → **Nếu nạp tiền / bấm "mở lại" ở 💵 Ngân sách, các đường tự chạy dưới đây
trả phí ngay, không ai bấm:**

| Đường gọi tự chạy | file:hàm | Điều kiện phát sinh phí | Tạm ngừng ĐÚNG đường đó (không đổi env) |
|---|---|---|---|
| Tổ rà soát vòng nền (mỗi 30 s, ≤ 5 nhóm/lượt) | `core/bg_poll.py:256 change_review_round` → `core/change_review.py:339 claude_review` | có thay đổi dữ liệu shot đang chờ rà | cờ `change_review` (+`change_review_motion`); `BG_POLL=0` dừng cả hỏi/gửi job — không khuyến nghị |
| Tổ rà soát tại chỗ sau khi Đạo diễn viết lại motion | `core/prompt_rewrite.py:412 _review_now` → `change_review.review_scene_now` | mỗi lần viết lại motion | `change_review_motion` |
| Tự QC ảnh / clip khi trang dự án đang mở | `core/autoqc.py:102 start`, `:182 start_video` (khung poll `dashboard/widgets.py:66`) | ảnh/clip mới xong, dự án không ở chế độ auto | **không có cờ** cho nhánh trang; QC lớp 1: `scene_qc_claude` / `qc_team` / `qc_agent`; công tắc dự án `qc_video` |
| Tự QC nền | `core/bg_poll.py:199` | cờ `bg_autoqc` | `bg_autoqc` |
| D6 viết lại prompt lúc gửi (cả gửi nền `send_ready`) | `core/runner.py:2966` → `core/chat_prompt.py:302` | mỗi lần gửi ảnh/clip | `chat_prompts` |
| Đạo diễn viết lại prompt khi gen lại (kể cả QC tự từ chối) | `core/prompt_rewrite.py:520 before_retry` (hook `pipeline.py:292, 886`) | mỗi lần gen lại có "Fix" | `director_rewrite` |
| Nghiên cứu hằng tháng tự chạy khi mở Dashboard | `dashboard/app.py:171–173`, `core/research.py:96–116` | meta `research_monthly=1` và tới hạn | meta `research_monthly` |
| Chạy tự động | `core/autopilot.py:1513` (Đạo diễn, QC, motion, sân khấu, sơ đồ máy) | người bấm bật | dừng dự án |

**Lỗ hổng `claude_cli`** (đúng sự cố #33): `ClaudeCliClient.clean_env` (`llm_runner.py:1338`) KHÔNG bỏ `ANTHROPIC_API_KEY` → `claude -p` dùng key API
(trả phí) thay vì gói; nhánh CLI **không ghi sổ chi, không kiểm `budget.halt`**, và lỗi "credit balance too low" bị xếp `cli_error` (không halt);
chuỗi "You've hit your limit" không khớp `usage_limit` (`llm_runner.py:70–81`). Script dùng `tools/experiments/group_test.load_env` (đọc key từ
registry User) hoặc `core/adapters/check.load_dashboard_env` (nạp `LLM_PROVIDER=anthropic` bằng `setdefault`) dễ dính nhất.

**Khác:** `change_review.claude_review` hiện `cost_usd` theo giá API kể cả khi chạy CLI (`change_review.py:353–357`) — số USD sai (thực 0);
`autoqc` không dừng khi `usage_limit` / `out_of_credit` (`autoqc.py:146, 221`) → từng ảnh chuyển sang chờ người thay vì dừng cả lượt;
`jobs` / `llm_calls` không có cột provider; client tạo mới mỗi lượt → đổi env giữa chừng đổi provider giữa job (trái D02).

### 2.2 Biện pháp kiểm soát tạm thời (không sửa code — người dùng chọn; mỗi mục là Cấp 3 hoặc thao tác của người dùng)

1. **GIỮ cờ chặn "hết tiền Anthropic" đang bật** — không bấm "mở lại" ở ⚙ → 💵 Ngân sách và **không nạp tiền / tắt tự nạp** ở Anthropic Console
   tới khi M1.4 xong. Đây là lớp chặn đang giữ toàn bộ đường tự chạy ở 0 USD. (Không cần làm gì — chỉ đừng mở.)
2. **Khi chạy bất kỳ script / phiên Claude CLI nào:** chạy trong shell đã gỡ `ANTHROPIC_API_KEY` (PowerShell: `Remove-Item Env:ANTHROPIC_API_KEY`)
   — tránh `claude -p` dùng key API như #33 (A3). Phiên Claude của tôi đã làm vậy ở #33 (`os.environ.pop`).
3. **(Mạnh hơn, người dùng tự làm khi sẵn sàng):** xóa / đổi tên `ANTHROPIC_API_KEY` khỏi biến môi trường User. Hệ quả: Dashboard sau khi khởi động
   lại không còn client Claude (Tổ rà soát chỉ chạy luật code, tự QC tắt, chạy tự động không khởi động) cho tới khi `LLM_PROVIDER=claude_cli`
   được đặt cho dự án (M1.4). Không cần sửa `dashboard.env`.
4. Nếu muốn giữ Dashboard chạy mà tuyệt đối không gọi Claude nền: tắt cờ `change_review`, `bg_autoqc`, `chat_prompts`, `director_rewrite` (Cấp 3 —
   ảnh hưởng workflow) — chỉ khi người dùng duyệt.

### 2.3 Gói M1.4 theo D02 (CHỜ DUYỆT PHẠM VI; cột CSDL mới = migration Cấp 3)

| File | Thay đổi |
|---|---|
| `core/llm_runner.py` | `client_from_env` → `client_for_project(conn, pid)`: provider của dự án (`projects.llm_provider`, rỗng = env) ; **bỏ fallback ngầm** rỗng+key → anthropic (rỗng = theo env đã khai rõ, không khai → không có client); `ClaudeCliClient.clean_env` bỏ `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`; CLI ghi sổ chi (token, provider `claude_cli`, 0 USD) + kiểm `budget.halt`; phân loại thêm "hit your limit", "credit balance" → `usage_limit` / `out_of_credit` có giờ mở lại nếu đọc được |
| `core/db.py` | cột `projects.llm_provider` (rỗng = env cũ — tương thích dự án cũ); `jobs.llm_provider` + `llm_config_ver` snapshot lúc tạo job; `llm_calls.provider` |
| `core/bg_poll.py`, `core/change_review.py`, `core/prompt_rewrite.py`, `core/chat_prompt.py`, `core/autoqc.py`, `core/autopilot.py`, `dashboard/common.py`, `core/camera_plan.py` | lấy client theo dự án / theo snapshot job; job đang chạy giữ provider đã snapshot dù Dashboard đổi cấu hình; `change_review` tính USD = 0 khi CLI |
| `core/autoqc.py`, `core/llm_runner.py:966`, `core/claude_tasks.py:379` | dừng cả lượt khi `usage_limit` / `out_of_credit` (không đẩy từng ảnh sang người) |
| `devsys/scorer.py` | giữ API (có xác nhận + trần), thêm lựa chọn `claude_cli` |
| Không đụng | `dashboard.env`, provider của job đang chạy |

Test: 2 dự án (anthropic giả / claude_cli giả) cùng tiến trình; job tạo trước khi đổi cấu hình giữ provider cũ; hết quota CLI → dừng có giờ mở,
0 lời gọi API; môi trường có key + provider claude_cli → subprocess không nhận key; `LLM_PROVIDER` rỗng + key → KHÔNG tự ra anthropic.
Rollback: cột trống = hành vi env; revert code. Chi phí: 0 USD (provider giả).

---

## 3. Gói M1.5 — Kho chủ thể ClipAI (D03 sửa: `v31-d03b-subject-library-auto-clean-2026-10-20`)

### 3.1 Hiện trạng (bằng chứng)
- Biết Kho đầy chỉ **sau khi** tải lên thất bại (`core/subjects.py:189–196`, `clipai_subjects.is_library_full` theo chữ lỗi); khi đó gói video gửi ảnh
  đánh dấu → Seedance chặn "người thật" → lùi Kling (#31 G30/G32; #33 lặp 13 lần 20/10).
- Đếm được sức chứa thật trước khi gửi: `ClipAISubjectLibrary.list_assets()` (GET `/api/kling/seedance-user-asset-list`, miễn phí) +
  `LIBRARY_LIMIT = 100` (`core/adapters/clipai_subjects.py:28`); `subjects.library_overview` đã phân loại asset `in_use / rejected / orphan /
  done_project / unknown` (`core/subjects.py:251`) — **chưa được gọi trước khi gửi**.
- **Xung đột đã ghi:** cờ `subject_auto_cleanup` (người dùng 13/10; máy chính BẬT, khóa) tự xóa khung bị loại của dự án NGAY khi giao / cất
  (`core/subjects.py:396–460`, gọi từ `core/delivered.py:67`, `core/archive.py:65`). Chỉ đạo 20/10 cho phép tự xóa nhưng với **mốc trên 3 ngày** và
  thêm **dự án đã xong / đã cất** → M1.5 thay luật này.
- **Lỗi phát hiện thêm (G59):** lần tự dọn 13/10 không chạy được — `RuntimeError: chưa cấu hình Kho chủ thể (SUBJECT_PROVIDER / VIDEO_PROVIDER)`
  (diag 1860/1861): luồng nền tạo `factory.subject_library()` không nạp env → 10 khung #22 vẫn nằm trong Kho. Tự dọn hiện **không hoạt động**.

### 3.1b Kho chủ thể dùng khi nào — vì sao quá tải khi chạy song song (người dùng hỏi 20/10)

- **Khi nào dùng:** cờ `seedance_subjects` BẬT + provider ClipAI → MỌI ảnh gửi kèm job video Seedance (`core/runner.py:1640–1680`
  `_subject_refs`) được tải lên Kho (mỗi ảnh một asset, nhận lại theo sha256 — `core/subjects.py:111–208`). Lý do: ảnh "active" trong Kho đã
  qua kiểm duyệt người thật của ClipAI → Seedance không chặn `real_person`; thay cách cũ "ảnh đánh dấu chữ thập đỏ". Ảnh không có asset → gửi
  ảnh đánh dấu → dễ bị chặn → lùi Kling (G30/G32/G58).
- **Đo thật (sổ `seedance_subject_pictures`, máy chính):** 185 ảnh từng vào Kho — **95 là khung đầu từng shot** (`P31_S…_frame_…`), còn lại ảnh
  nhân vật / dạng / vật Kho và cả **ảnh nền 3D** (`P33_place_1_…` — ảnh không có người vẫn đi qua Kho). Theo dự án: #31 = 84, #24 = 44, #22 = 29,
  #29 = 10, #33 = 10. → Một dự án ~40 shot đã gần 100 chỗ; hai dự án song song chắc chắn đầy.

**Phương án (đề xuất cho M1.5 — chờ người dùng chọn):**
1. **Chỉ ảnh CÓ MẶT NGƯỜI mới vào Kho** (ảnh nhân vật, dạng nhân vật, khung đầu có người). Nền 3D, ảnh vật, ảnh không có mặt (đo bằng YuNet đã có ở
   `qc_measure`) gửi thẳng như ảnh thường. Ước giảm ≈ 20–30 % số asset (cần đo lại trên #31).
2. **Hai loại asset — BỀN và TẠM:** BỀN = ảnh nhân vật / dạng / vật Kho dùng chung NHIỀU dự án (Kelly #31 và #33 cùng một asset nhờ sha) — giữ;
   TẠM = khung đầu / ảnh nháp của một shot — giải phóng ngay khi job video dùng nó đã xong và clip được duyệt hoặc bị loại hẳn (không đợi
   giao dự án). Đây là phần lớn (≈ 50 %) và là nguyên nhân quá tải khi chạy song song.
3. **Bộ cấp chỗ chung cho mọi dự án** (như `send_claim`): trước khi gửi, job **giữ chỗ** N asset mới trong một bảng dùng chung; hết chỗ → tự dọn
   asset TẠM cũ nhất không thuộc job đang chạy (LRU); vẫn thiếu → job **chờ trong hàng** tới khi job khác xong và trả chỗ — KHÔNG gửi ảnh đánh dấu,
   KHÔNG đổi model. Chia hạn mức: ví dụ 60 chỗ BỀN + 40 chỗ TẠM luân phiên (số chốt sau khi đo).
4. **Tự dọn theo chỉ đạo 20/10** (`v31-d03b`): khung / nháp cũ + asset chỉ thuộc dự án đã giao / đã cất > 3 ngày.
5. **Dự phòng (cần quyết định riêng):** thêm token / tài khoản ClipAI thứ hai = Kho thứ hai (100 chỗ) cho dự án song song — chỉ khi 1–3 chưa đủ.

Thứ tự khuyến nghị: 2 + 3 (giải quyết song song) → 1 (giảm tải) → 4 (dọn dài hạn); 5 chỉ khi cần.

### 3.2 Phạm vi đề xuất
| File | Thay đổi |
|---|---|
| `core/subjects.py` | `capacity(conn, library)` = số asset / 100 + số có thể dọn theo luật 3 ngày; `auto_clean_candidates(conn, now)`: (a) khung bị loại / không thành video, (b) asset chỉ thuộc dự án đã giao hoặc đã cất ≥ 3 ngày; loại trừ asset có `in_use` / `unknown` / nhân vật liên kết; `run_auto_cleanup` dùng danh sách này |
| `core/runner.py` (~1657, trước `picture_refs`) | preflight: chỉ khi gói video THẬT cần tải ảnh mới lên Kho — thiếu chỗ sau khi dọn được → dừng job đó với lý do + cách xử lý (không gửi ảnh đánh dấu, không đổi model); không xác định được sức chứa → báo VÀNG, giữ job |
| `core/delivered.py`, `core/archive.py` | thôi xóa ngay; ghi mốc thời gian để dọn sau 3 ngày (luồng nền `bg_poll` hoặc lúc preflight) |
| `core/adapters/factory.py` / luồng nền | sửa G59: tiến trình nền nạp cấu hình như Dashboard |

### 3.3 Test / nghiệm thu / rollback
- Provider giả: Kho 100/100 có 5 khung bị loại + 3 asset dự án cất 4 ngày + 2 asset dự án cất 1 ngày + 1 asset dùng chung với dự án đang làm →
  chỉ xóa 8, giữ 3; Kho đầy không dọn được → job dừng, KHÔNG có job Kling lùi; list lỗi mạng → VÀNG, không xóa gì.
- Nghiệm thu: 0 lần lùi Kling vì Kho đầy; mọi lần xóa có diag ghi asset / dự án / lý do. Rollback: cờ M1.5 TẮT = hành vi hiện tại.
- Chi phí: 0 USD (list/delete Kho không tính tiền). Xóa asset là thao tác ngoài, không hoàn tác — chạy đúng luật đã chốt.

---

## 4. G10 / G53 — bộ regression lời dẫn (giữ ở M2.9)

Chỗ còn coi lời dẫn như người nói: `core/seedance_refs.py:546–552` (`speaker_no_identity` báo LỜI DẪN tới 19/10 13:52), `core/claude_tasks.py:323`
(`speaking = bool(dialogue)`), `core/quality_tier.py` (`lip_sync is True` trước `method_for`), `core/lipsync.py:116` `mark` (mục cũ không dọn).
Đã đúng: `core/lipsync.py` `_method` / `_take_segments` / `shot_audio` (G10, `ed612528`), `core/speaker_lint.py:46 is_narrator`.

**Bộ regression chung** `tests/test_narration_regression.py` (một bảng ca, chạy qua MỌI hàm trên):
| Ca | Mong đợi |
|---|---|
| shot chỉ lời dẫn, không cast (POV) | không khớp môi, không cảnh báo thiếu ảnh định danh, QC không coi "đang nói", không tính shot khó |
| shot lời dẫn + nhân vật trong khung không nói | như trên; nhân vật vẫn có ảnh định danh nhưng không gắn giọng |
| shot nhân vật nói thật (thoại) | khớp môi như cũ |
| thoại trộn: lời dẫn + một câu nhân vật | chỉ đoạn của nhân vật được khớp môi; đoạn lời dẫn giữ vị trí thời gian |
| tên người dẫn biến thể (`LỜI DẪN`, `Lời dẫn`, `NARRATOR`, `người dẫn chuyện`) | `is_narrator` nhận đủ |
| method đổi từ lipsync → skip | `lipsync.mark` dọn mục cũ, `synced_scene_ids` đúng |

---

## 5. Giá ClipAI 1080p — đối soát 2,80 ↔ 6,36 USD

Nguồn: danh sách task ClipAI (GET, 0 USD) — trường `seedance_cost_usd` (tiền ClipAI ghi cho task, chỉ có ở task gửi từ WEB), `request_params.seedance_cost_usd`
(ước tính lúc gửi), `extra_data.usage.total_tokens`, `has_video_input`; sổ chi pipeline `usage_events` (giây, không có USD).

| Task (web, thay nền video) | Loại | Token | Ước tính lúc gửi | Tiền ghi trên task | USD / 1k token |
|---|---|---|---|---|---|
| `cgt-20261019235412-7dpf3`, `…235413-vu8rc`, `…20000044-4m3rb` | nháp 480p, có video vào, 9 s (mỗi task) | 179 740 | 2,52 (cho lần gửi `video_num: 2`) | **1,150336** mỗi task | 0,00640 |
| `cgt-20261020000346-zyeku` | **chỉ bước nâng** 1080p (`draft_task` → prl47), 9 s | 909 225 | 2,80 | **6,364575** | 0,00700 |

Kết luận (có giới hạn):
1. **6,36 USD là tiền của riêng bước nâng 1080p**, tính theo token (909 225 × 0,0070 / 1k); KHÔNG gồm bản nháp. Bản nháp tính riêng (1,15 USD mỗi
   task 480p; thấy 3 task nháp → ≈ 3,45 USD). Tổng thử nghiệm thay nền ≈ **9,8 USD** (3,45 + 6,36), chưa tính task prl47 nếu được tính riêng
   (không thấy dòng riêng trong danh sách).
2. **2,80 là ước tính ClipAI hiện lúc gửi**, lệch 2,27× so với tiền thật — không dùng được để dự toán. Ước tính nháp của ClipAI (2,52 / 2 bản = 1,26)
   lệch +10 %.
3. Bảng giá token của pipeline (`core/cost.py` `SEEDANCE_USD_PER_1K_TOKENS`, video vào = 0,0064) **khớp đúng 480p**; với 1080p lệch −8,6 % trên
   **một** điểm dữ liệu → **chưa đủ để đổi giá** (đúng chỉ đạo: không kết luận từ một task).
4. Task gửi qua API (mọi job #31/#33) **không có trường tiền** trong danh sách, chỉ có token → đối soát sổ chi phải tính bằng token × giá; sổ
   `usage_events` hiện ghi GIÂY nên không đối soát trực tiếp được với ClipAI.

Việc đề xuất (vào M1.6, 0 USD): công cụ đối soát đọc token từ danh sách task cho mọi job → so với sổ chi theo giây; thu ≥ 5 điểm 1080p có tiền thật
(task web / hóa đơn ClipAI do người dùng cung cấp) trước khi đổi giá; ghi `tokens` vào sổ chi khi poll xong.

---

## 6. Ma trận 6 rủi ro

| # | Rủi ro | Owner | File / hàm | Mức ảnh hưởng | Gói | Điều kiện nghiệm thu |
|---|---|---|---|---|---|---|
| R1 | QC crash `vat` chuỗi | Claude (code) · người dùng duyệt gói | `core/qc_observe.py:62` `compile_checks`; gọi từ `core/qc_scene.py:620`, `core/llm_runner.py:929`; parser mới `core/shot_intent.py` | CAO — 5 shot (#30 ×4, #31 ×1) QC luôn lỗi khi cờ BẬT; dự án mới có `vat` sẽ lỗi tiếp | M1.1 | 2 ca thật #30/#31 không raise; dict sai vẫn báo; vùng quy ước 7 xanh |
| R2 | Gọi Anthropic API ngoài ý muốn / Tổ rà soát lỗi | Claude (audit, gói) · người dùng (env máy chính, không mở chặn hết tiền) | `core/llm_runner.py:1312` `client_from_env` (fallback ngầm :1320), `:1338` `clean_env`; launcher chép key `tools/launch_dashboard.ps1:74–79`; 8 đường tự chạy mục 2.1 | **CAO** — key User có thật; chỉ đang an toàn nhờ cờ chặn hết tiền; nạp tiền = trả phí ngay | M1.4 (+ biện pháp tạm 2.2) | 0 lời gọi API trả phí ngoài ý muốn trong test 2 dự án 2 provider; job giữ provider lúc tạo; hết quota dừng |
| R3 | Kho chủ thể đầy → lùi Kling; tự dọn hỏng (G59) | Claude · người dùng xác nhận "bản nháp cũ" | `core/subjects.py:168–460`, `core/runner.py:1657–1667`, `core/delivered.py:67`, `core/archive.py:65` | VỪA — đổi model ngoài quyết định video-route, chất lượng giảm | M1.5 | 0 lùi Kling vì Kho đầy; dọn đúng luật 3 ngày; không xóa asset đang dùng |
| R4 | Lời dẫn bị coi là người nói (G10 chưa phủ, G53) | Claude | `core/seedance_refs.py:546`, `core/claude_tasks.py:323`, `core/quality_tier.py`, `core/lipsync.py:116` | THẤP–VỪA — cảnh báo sai, QC chấm sai, tính shot khó sai (tiền) | M2.9 | bộ `test_narration_regression.py` xanh qua mọi hàm |
| R5 | Giá 1080p / ước tính lệch | Claude (công cụ) · người dùng (số liệu hóa đơn) | `core/cost.py` (`seedance_token_usd`, `clip_price`), `usage_events` (ghi giây) | VỪA — chạm trần giữa đợt (#33) | M1.6 | ≥ 5 điểm 1080p đối soát; lệch ≤ 10 % |
| R6 | Việc dở của kế hoạch S bị bỏ quên | người dùng duyệt bảng mục 7 | `docs/KE_HOACH_SUA_SAU_DU_AN_8.md` | THẤP | — | 14/14 việc có quyết định giữ / chuyển / bỏ |

---

## 7. Bảng chuyển việc còn mở của kế hoạch S sang V3.1

**Sửa số liệu:** kế hoạch S còn **14** việc chưa xong (2 ⏸, 8 🔄, 4 ⬜), không phải 16 như tôi báo trước đó (con số "3 ⏸ + 13" lấy từ
báo cáo agent rà mà tôi chưa kiểm lại). Đợt K (K.1–K.3) đã ✖ từ 30/09.

| Việc S | Trạng thái | Bằng chứng hiện có (máy chính, chỉ đọc) | Milestone V3.1 nhận | Đề xuất |
|---|---|---|---|---|
| S4.11 Bản mẫu Seedance 2.5 → 1080p; so A+/B #22 | 🔄 | Đường B chạy thật ở #33: 7 job nâng từ nháp (`draft_job_id`), cờ `seedance_sample_mode` BẬT; A+ (phóng AI) đã bỏ theo quyết định 07/10 không phóng AI | M1.6 (giá nâng 1080p) | **Đóng**: B ✅ (bằng chứng #33), A+ ✖ (quyết định 07/10) |
| S14.13 Dọn cờ `qc_agent`, `scene_qc_claude`, `scene_qc_trusted` khi `qc_team` đạt | ⏸ | `qc_team` = học việc (quyết định `qc-team-off-2026-10-14`, 49 % < 75 %); 3 cờ còn BẬT/học việc | M4.6 (benchmark) → dọn cờ khi nhóm luật qua benchmark | **Chuyển** |
| S14.14 `ui_v2` mặc định + gỡ giao diện cũ + tách file lớn | 🔄 | `ui_v2` BẬT khóa; G-a xong (`12d2779`); G-b (gỡ cờ cũ trong header/step2/3/5…), G-c (tách file lớn), S13.3/S13.10 chưa | G-b → M4.7 (trước khi thêm thẻ Dashboard mới); G-c → tồn đọng ngoài V3.1 | **Chuyển G-b; giữ G-c tồn đọng** |
| S14.51 Bảng màu nhân vật + QC `uncertain` | 🔄 | Cờ `palette_check` nay BẬT (settings); chưa có calibrate trên frame thật | M4.1 + M4.6 | **Chuyển** |
| S14.15 Tài liệu khớp trạng thái + chấm lại AI Dev System | ⬜ | — | M0.6 (AS-IS/TO-BE) | **Bỏ ở S** (thay bằng M0.6) |
| S15.5 7 thay đổi P1 KLD-1…7 — chờ kiểm Dashboard thật | 🔄 | Cờ sửa #22 `kld_lessons_prompts`, `outfit_strip_model` BẬT; #24–#33 chạy sau đó nhưng chưa có biên bản kiểm từng KLD | M5.3 (pilot vòng A replay) | **Chuyển** (lập biên bản từng KLD bằng replay) |
| S15.6 Nút "Viết motion prompt" ref-only bằng code | 🔄 | `ui_actions`: `viet_motion` bấm 1 lần (18/10); chưa rõ shot ref-only | M5.3 | **Chuyển** |
| S15.9 Học việc B3–B8 (luật 8: ✅ sau một dự án thật có `trainee_log`) | 🔄 | `trainee_log` 366 dòng 08/10 → 19/10 (dự án thật) | M4.6 dùng `trainee_log` làm dữ liệu benchmark | **Đóng ✅** (điều kiện luật 8 đã đạt) + chuyển dữ liệu sang M4.6 |
| S15.13 P3 (9 mục KLD) "để sau khi có bằng chứng" | ⏸ | — | M0.5 (nhập 9 mục vào sổ lỗi, OPEN) | **Chuyển vào sổ lỗi**, đóng ở S |
| S15.19 2 bậc chất lượng + nhạc theo cung cảm xúc | 🔄 | `two_tier_quality` BẬT, `music_story_arc` BẬT khóa; #33 nâng 1080p qua `quality_tier` (lần gen bản cao thật) | phần nhạc → M5.4 (pilot B) | **Đóng phần 2 bậc ✅ (#33); chuyển phần nhạc** |
| S15.20 Ngân sách riêng từng dự án | 🔄 | `project_reserve_log` có #29–#33; #33 lộ A14 (trích 0) | M1.7 (thông điệp ngân sách, D01) | **Đóng ✅** (đã chạy thật) + A14 sang M1.7 |
| S8.0 Chấm 16 khu vực (2 agent, 0 USD) | ⬜ | — | M0.6 + chấm lại sau M1 (đo tiến bộ) | **Chuyển** (thêm việc "chấm lại sau M1") |
| S8.2 Báo cáo đánh giá + danh sách việc theo điểm | ⬜ | — | gộp S8.0 | **Bỏ ở S** (gộp) |
| S8.4 Rút việc nên học vào TODO | ⬜ | — | thay bằng sổ lỗi (M0.5) + `project_error_report` (M1.8) | **Bỏ** |

Sau khi người dùng duyệt bảng: cập nhật từng dòng S (✅ / ✖ có lý do / "→ V3.1 Mx.y"), thêm việc mới vào V3.1 nếu cần (vd. "chấm lại 16 khu vực sau
M1", "S14.14 G-c tồn đọng"), rồi mới đóng kế hoạch S.

---

## 8. Đề xuất thứ tự build các gói tiếp theo

| Thứ tự | Gói | Lý do | Chạy song song được với | Chi phí |
|---|---|---|---|---|
| 1 | **M1.1** QC `vat` | lỗi đang xảy ra, nhỏ, rủi ro thấp | 2, 3 (khác file) | 0 |
| 2 | **M1.4** provider Claude theo dự án + snapshot theo job + quota (D02) | chặn nguy cơ tiền; gỡ lỗi Tổ rà soát | 1, 3 — đụng `llm_runner`, `change_review`, `bg_poll`, `db` (migration cột: Cấp 3) | 0 (provider giả) |
| 3 | **M1.5** Kho chủ thể + tự dọn 3 ngày + G59 | lỗi lặp mỗi dự án | 1, 2 — đụng `subjects`, `runner` (vùng trước gửi video), `delivered`, `archive` | 0 |
| 4 | M1.2 + M1.3 (poll nguyên tử, tạm dừng trước submit) | đụng `runner`/`bg_poll` — làm SAU 2–3 để không chồng file | — | 0 |
| 5 | M1.6 + M1.7 (giá + đối soát + thông điệp) | cần dữ liệu đối soát mục 5 | 6 | 0 |
| 6 | M0.4–M0.5 + M1.8 (sổ lỗi + báo cáo lỗi dự án; nhập S15.13) | nền theo dõi | 5 | 0 |
| 7 | M1.9 golden (D08) | trước M2 | — | 0 |
| 8 | M2.x theo thiết kế M0.9 / M0.10 | sau golden | — | 0 code; backfill Cấp 3 |

Nhánh song song (1, 2, 3) mỗi nhánh một worktree, commit thường xuyên để đổi tài khoản khi gần giới hạn; mỗi nhánh qua quy ước 7 trước khi gộp.
