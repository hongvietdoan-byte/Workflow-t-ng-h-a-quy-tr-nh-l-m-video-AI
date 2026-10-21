# Kế hoạch sửa 20 cờ "SỬA rồi bật/khóa" + 2 cờ nguy hiểm — gói duyệt (21/10/2026)

> **Cấp 1 — CHỈ TÀI LIỆU, 0 USD, không sửa code.** Việc C-FLAGFIX-PLAN (làn cloud-E). Nền `origin/main` 245dc24c.
> Nguồn: `docs/DANH_GIA_HIEU_QUA_CO_2026-10-21.md` (mục 3 bảng 144 cờ, mục 4 nhóm "🔧 SỬA rồi bật/khóa", mục 4.2 cờ nguy hiểm), sổ lỗi
> `devsys/errors.json`, code `origin/main` (đọc 21/10), metadata `core/features.FEATURES` (`costs`, `verified`, `default_on`, `REQUIRES`).
> Trạng thái "máy chính" = cột máy chính của bảng mục 3 (không đọc lại `data/` máy chính — cloud không có).
> Cấp quyền theo sổ `v31-permission-tiers-2026-10-20`: **Cấp 2** = sửa code sau cờ, test đỏ→xanh, gộp được khi rà xong; **Cấp 3** = đổi trạng
> thái cờ ở máy chính (bật / tắt / khóa `verified`) hoặc thêm lời gọi tốn tiền — người dùng duyệt.

## 0. Tóm tắt — 3 gói để duyệt một lần

| Gói | Nội dung | Cờ | Cấp | Tiền | Xin duyệt |
|---|---|---|---|---|---|
| **G-A "chặn mất tiền / ghi đè người"** (làm NGAY, trước dự án #34) | đóng cổng khi rà lỗi, khai `costs` đúng, không ghi đè trường người khóa, tắt cờ QC Claude chưa đạt | change_review, hero_takes (+ end_frames, scene_qc_claude, voice_check_redo khai costs), director_rewrite, chat_prompts, scene_qc_claude | 2 code + **3**: tắt `scene_qc_claude`, bật cờ con mới mặc định BẬT cho `director_rewrite` | 0 USD (bớt tiền) | 1 lần: "Gói A" |
| **G-B "sửa báo nhầm / nhãn / giá rồi KHÓA"** | các cờ có ích đã chạy thật, chỉ còn 1 lỗi rõ | video_gate, two_tier_quality, motion_consistency_lint, end_frames, scene_qc, lip_sync + dialogue_take, bg_autoqc, travel_truth | 2 code + **3**: khóa `verified` từng cờ sau 1 dự án sạch | 0 USD (trừ 1 shot cận khớp môi thật ≈ giá 1 clip — xin riêng) | 1 lần: "Gói B" + 1 lần gen thử khớp môi |
| **G-C "cờ bật mà vô tác dụng: nối hoặc bỏ"** | cờ chỉ chạy trong autopilot / thiếu cờ cha | audio_first, story_check, voice_check_redo, stage_auto, stage_handheld_props, stage_crew_user_approve, continuity_layout | 2 code + **3**: bỏ (REMOVED) hoặc bật cha | 0 USD (stage_auto: Claude, có ước tính sẵn) | 1 lần: "Gói C" (chọn nối / bỏ từng cờ) |

Thứ tự trong G-A (theo đề): **change_review (cổng mở khi Claude lỗi → job tự gửi)** → **hero_takes + 3 cờ tốn tiền không khai costs** →
director_rewrite → scene_qc_claude → chat_prompts.

Phát hiện mới khi đọc code (không có trong bảng mục 3): ngoài `hero_takes`, **`end_frames`** (tốn 1 ảnh/shot đổi trạng thái, `why` tự ghi),
**`scene_qc_claude`** (gọi Claude mỗi cảnh) và **`voice_check_redo`** (gửi lại TTS khi đo sai) cũng KHÔNG khai `costs: True` và không có trong
`before_run.PAID_FLAGS` → `before_run.costly_fix_flag` (`core/before_run.py:134`) coi là 0 USD, nút "bật hàng loạt cờ sửa lỗi" có thể bật nhầm.

Đã có nhánh đang chờ gộp chạm vào cờ trong danh sách (không làm lại, chỉ nối):
`cloud/v31-m29` (C-M29: G17 `quality_tier.hard_signs`, G10/G15 lời dẫn, A11 thông điệp `end_frame_skill_object`) ·
`cloud/v31-dp9` (M2.7 bảng mã chung) · `cloud/v31-m25` (write guard M2.5 — nền cho "không ghi đè trường người khóa") · cờ `horizon_needs_sky`,
`send_estimate`, `qc_false_alarm_fix`, `video_qc_shadow` (đã có code, TẮT — bậc B mục 4.3 của đánh giá).

---

## 1. Gói A — chặn mất tiền / ghi đè người (ưu tiên 1)

### A1. `change_review` — cổng giữ phải ĐÓNG khi rà lỗi (đang BẬT, `costs: True`)
- **Lỗi:** P31-G35 (FIXED_UNVERIFIED) Claude hết tiền → `change_events.state='failed'` mà cổng `change_review.blocking` trả None → job 1061 tự gửi.
  P31-G56 (OPEN) diag `change_review_hold` 4 435–5 710 lượt. P31-G34 (OPEN) job kẹt `queued` do dữ liệu mâu thuẫn. #31: 80/162 mục ĐỎ bị bỏ qua (49 %),
  39 `review_fail` bị bỏ.
- **Gốc / hiện trạng code:** đã có sửa 19/10 `core/change_review.py:_hold_failed` (550) gọi trong `blocking` (579–594) + `except` "không biết thì
  không mở cổng" (594) — **chưa kiểm thật** (chưa có lần Claude lỗi nào sau sửa). Diag giữ ghi mỗi nhịp tim (không gộp theo (code, scene)).
- **Sửa (Cấp 2):** (1) test tích hợp đường thật: `change_events` failed mới hơn duyệt → `VideoRunner/ImageRunner.submit_pending` KHÔNG gửi, `held_reason`
  nói "rà lỗi — Bỏ qua ở 📥 hoặc chạy lại rà"; lỗi đọc bảng → giữ. (2) `change_review_hold` ghi qua `_diag_once`/`diag.record` gộp (code, scene) như
  `plate_stale` (G56). (3) Bỏ qua ĐỎ phải có lý do bắt buộc (ô chữ) — đo được tỉ lệ bỏ qua có lý do.
- **Test đỏ→xanh:** `tests/test_change_review.py` ca "Claude ném LlmError hết tiền → job queued + held_reason", "bảng change_events hỏng → giữ",
  "1 000 nhịp tim → ≤ 1 dòng diag/(scene, 10 phút)".
- **Tác động khi đang BẬT:** đúng hướng an toàn (giữ nhiều hơn, không gửi thêm). Người dùng thấy nhiều job "chờ rà" hơn khi provider Claude hết tiền.
- **Chặn mới / tiền:** thêm điểm GIỮ đúng thiết kế (fail-closed), không thêm lời gọi Claude. **Cấp:** 2. Sau 1 dự án sạch → Cấp 3 khóa.

### A2. `hero_takes` — gen thêm bản mà không khai tiền (đang BẬT)
- **Lỗi:** không mã sổ lỗi; `core/features.py` mục `hero_takes` không có `costs: True`, không có trong `before_run.PAID_FLAGS`; `core/hero_takes.py`
  (`hold_reason`, `solo`) tạo bản 2 cho shot ⭐ = thêm một clip trả tiền. `costly_fix_flag("hero_takes")` = False.
- **Sửa (Cấp 2):** khai `costs: True` + một dòng `PAID_FLAGS["hero_takes"] = {"text": "thêm 1 clip mỗi shot ⭐ — giá ở ước tính Bước 4"}`;
  ước tính Bước 4 (`cost.estimate_videos_by_scene`) cộng bản 2 khi cờ bật (kiểm có chưa — `core/cost.py` đã đọc `hero_takes`).
  **Cùng gói:** khai `costs: True` cho `end_frames` (1 ảnh/shot đổi trạng thái), `scene_qc_claude` (Claude/cảnh), `voice_check_redo` (TTS gửi lại).
- **Test:** `tests/test_fix_flags.py` thêm ca: mọi cờ có đường gọi provider trả phí (grep `provider.submit`/`llm_runner`/`tts` sau `features.on(<cờ>)`)
  phải `costly_fix_flag` = True — danh sách 4 cờ trên đỏ trước, xanh sau.
- **Tác động khi BẬT:** không đổi phim; nút bật hàng loạt ngừng bật 4 cờ này; ô 💰 có thêm dòng. **Cấp:** 2 (chỉ khai báo).

### A3. `director_rewrite` — không ghi đè trường người đã chỉnh (nguy hiểm, đang BẬT)
- **Lỗi:** P33-A4 (OPEN) Đạo diễn viết lại `image_prompt` shot 1–3 người đã chỉnh tay (dời tháp, thêm mặt đồng hồ); P31-G57 (IN_PROGRESS)
  `director_rewrite_fallback` "Chưa cấu hình Claude" ở tiến trình riêng.
- **Gốc:** `core/prompt_rewrite.py:_set_prompt` (≈ 92–99) ghi thẳng `scenes.data.image_prompt` / `motion_prompts.motion_prompt`, không đọc
  `_user_locked` (luật khóa đã có ở `core/camera_plan.py:494`, `core/dialogue.py:331`); đường gọi `rewrite_for_retry` (461).
- **Sửa (Cấp 2):** trước khi ghi: trường nằm trong `_user_locked` (hoặc write guard M2.5 báo USER_LOCKED khi cờ `field_guard` có) → KHÔNG ghi; lưu bản
  viết lại làm ĐỀ XUẤT (diag + ô "Đạo diễn đề xuất" ở Bước 2/3, nút Áp dụng) và gen lại dùng câu sửa (`fix=`) thay vì viết lại cả prompt. Lưu tay
  ở Bước 2/3 (người) → thêm trường vào `_user_locked` (nối C-M25B: sửa tay motion → USER_LOCKED). Tiến trình không có provider → không gọi, nói rõ (G57).
- **Test:** `tests/test_prompt_rewrite.py`: prompt có `_user_locked: ["image_prompt"]` → `rewrite_for_retry` không đổi CSDL + 1 diag đề xuất;
  không khóa → như cũ (byte); không provider → diag, không ném.
- **Tác động khi BẬT:** đổi hành vi (bớt ghi) — cần cờ con `director_rewrite_respect_lock` mặc định BẬT → **Cấp 3** (xin trong Gói A).
- **Tạm thời:** tắt `director_rewrite` cho dự án đang chỉnh tay (đánh giá 4.2) — người dùng đã làm thủ công ở #33.

### A4. `scene_qc_claude` — TẮT tới khi nghiệm thu lại (nguy hiểm)
- **Lỗi:** nghiệm thu duy nhất (#8, 27/09) KHÔNG đạt: bỏ lọt 6, báo nhầm 12/21 khung tốt; bật hàng loạt 15/10 không bằng chứng; mỗi cảnh tự gọi
  Claude (`core/qc_scene.py:claude_on` 573: `features.on("scene_qc_claude") or qc_agent.enabled() or qc_team.enabled()`); không khai `costs`.
- **Sửa:** (Cấp 3) tắt ở máy chính; (Cấp 2) khai `costs: True` (A2); đưa vào danh sách "cần nghiệm thu lại" với bộ benchmark M4.6 (DP7 đã gộp:
  khung chạy benchmark QC) — đạt ngưỡng (bỏ lọt ≤ 1/21, báo nhầm ≤ 2/21) mới bật lại.
- **Test:** `claude_on()` False khi cờ tắt và qc_agent/qc_team tắt (mới; `tests/test_qc_team_pipeline.py:41` chỉ thử chiều bật) + ca `costly_fix_flag` (A2). **Tác động:** bớt lời gọi Claude; QC
  lớp 0 (code) vẫn chạy trong runner ảnh.

### A5. `chat_prompts` (D6) — kiểm gói có D6 + lỗi hết tiền (đang BẬT, `costs: True`)
- **Lỗi:** P31-G29 (OPEN) `tools/pregen_check.py` / `tools/replay_payload.py` luôn TẮT D6 (`replay_payload.py:185` `box["chat_prompts"] = False`) → kiểm
  gói KHÔNG phải gói thật; P33-A4 (cùng nhóm ghi đè); 98 `chat_prompt_fail` + 32 `refused` + 14 vượt trần ở #29–#33.
- **Sửa (Cấp 2):** (1) `pregen_check --payload` có chế độ "D6 như máy chính" dùng bản đã lưu của lượt D6 gần nhất (cache `core/chat_prompt.py`) thay vì
  gọi Claude — nếu chưa có bản lưu thì nói rõ "gói thật sẽ do Claude viết lại lúc gửi, chưa xem được" (không im lặng). (2) Lỗi hết tiền / từ chối →
  dùng bản code ghép + 1 diag gộp (không thử lại mỗi nhịp). (3) Vượt trần → qua `prompt_budget` của M2.8b khi có.
- **Test:** `tests/test_chat_prompt.py`: LlmError hết tiền → gói = bản ghép, 1 diag; `pregen_check` với D6 bật nói rõ phần chưa xem được.
- **Tác động:** không đổi gói khi Claude chạy tốt. **Cấp:** 2.

## 2. Gói B — sửa báo nhầm / nhãn / giá rồi KHÓA (ưu tiên 2)

| Cờ | Lỗi (sổ) · file:hàm | Gốc | Sửa đề xuất (Cấp 2) | Test đỏ→xanh | Khi đang BẬT | Khóa (Cấp 3) khi |
|---|---|---|---|---|---|---|
| `video_gate` (dOn, BẬT) | P31-G20 OPEN: báo nhầm "lệch nền" khi ảnh ít trời (2 lần người dùng phải Bỏ qua — `video_gate_skips`) · `core/video_gate.py`, `core/plate_layout_qc.py` (`SKY_FLAG = "horizon_needs_sky"` 186) | so đường chân trời cả khi khung 7–14 % trời | bật `horizon_needs_sky` (code có sẵn, TẮT) — chỉ so chân trời khi đủ trời | phát lại 0 USD S22/S39 #31: không còn ĐỎ; ca lệch thật vẫn ĐỎ | bớt báo nhầm, không thêm chặn | 1 dự án 0 lần Bỏ qua sai |
| `two_tier_quality` (BẬT) | P33-A7 OPEN giá bản cao lệch +24 %, nháp ≈ 1,37× (phụ phí video ref); RA_QUYET_DINH A3 nhãn "MỌI shot nháp" · `core/quality_tier.py`, `core/cost.py` | bảng giá thiếu phụ phí ref / nâng bản cao | bật `send_estimate` (giá theo gói gửi) + sửa câu nhãn ở `dashboard/quality_ui.py` theo quyết định 15/10 (shot dễ đi thẳng 720p) | giá ước tính #33 6 bản cao trong ±5 % sổ chi; nhãn không còn "mọi shot" | không đổi phim | sau #34 giá khớp |
| `motion_consistency_lint` (dOn, BẬT) | 19/10 người dùng: clip #31 đơ / giữ tư thế mà lint không bắt (G51) · `core/prompt_formula.py` (nhóm `nhat_quan` 39; regex `_END` 71 coi `holds` là nhịp cuối hợp lệ) | luật chỉ kiểm nhất quán diễn ↔ hành động, chưa có luật "giữ yên quá lâu" | thêm luật VÀNG `giu_yen`: câu motion có hold/pause/poised/stays still/slowly kéo > 1,5 s (theo thời lượng) mà không có hành động kế → VÀNG trước gen (không chặn) | prompt shot 13 #31 → VÀNG; prompt có hành động sau "holds" → không | thêm VÀNG ở Bước 3 | sau 1 dự án: tỉ lệ VÀNG đúng ≥ 80 % |
| `end_frames` (🎓 học việc trong `why`, BẬT ở 🧪) | P33-A11 OPEN thông điệp "ném keo" sai 28 lần (đã sửa ở nhánh `cloud/v31-m29`, chờ gộp); `end_frame_missing` 9 lần #31; `why` còn ghi học việc; không khai costs | nhãn lệch trạng thái thật; thiếu khai tiền | sửa `why` theo trạng thái thật + `costs: True` (A2) + gộp m29 | `tests/test_fix_flags.py` (costs); test m29 A11 | không đổi phim | sau #34 0 thông điệp sai |
| `scene_qc` (🎓, BẬT) | #31 chấm 0,96 clip gần đứng hình (G51); P33-A5 FIXED_UNVERIFIED đo nhầm cỡ cảnh → tự gen lại thừa · `core/qc_scene.py`, QC lớp 0 | QC không đo đứng hình; đo cỡ theo mặt xa | bật `qc_false_alarm_fix` (A5/A6) + `video_qc_shadow` (M4.2 đo đứng hình, chỉ ghi) trước; sau benchmark M4.6 mới cho điểm đứng hình vào chấm | phát lại #33 S2: không tự gen lại; #31 shot 13: shadow ghi "đứng ≥ 1,5 s" | bớt gen lại thừa (tiết kiệm) | sau benchmark M4.6 |
| `lip_sync` (env) + `dialogue_take` (🔒 khóa giả) | P31-G17 OPEN (`quality_tier.hard_signs` coi `lip_sync is True` là khớp môi), P31-G10 FIXED_UNVERIFIED; #22 tương quan môi 0,03/0,44 < 0,65; `dialogue_take` khóa nhưng `REQUIRES ("lip_sync",)` → vô tác dụng khi máy không có `FEATURE_LIP_SYNC=1` | khóa con mà cha chỉ bật bằng env | gộp `cloud/v31-m29` (G17/G15 qua `lipsync.talking`); chuyển `lip_sync` từ env sang 🧪/baseline (mục 5 đánh giá); KHÓA `lip_sync` cùng `dialogue_take` (`features.unmet_all` đã báo cờ 🔒 có cha tắt — chỉ báo, không bật) | test: cờ 🔒 không được có cha trong `REQUIRES` chưa 🔒 (`tests/test_fix_flags.py`, đỏ với `dialogue_take`→`lip_sync`) | không đổi phim | **1 shot cận thật** (quyết định `lip-sync-lock-after-real-run`) — xin giá riêng |
| `bg_autoqc` (OPT_IN, BẬT, `costs`) | P31-G57 IN_PROGRESS: `bg_autoqc_stuck` 29 lần · `core/bg_poll.py` (≈ 225–238 `AUTOQC_TRIES`) | thử lại khi cảnh chưa đủ khung / Claude lỗi; tiến trình riêng không có provider | phân loại lý do kẹt (chưa đủ khung → chờ im; Claude lỗi/hết tiền → 1 diag + dừng tới khi provider đổi; không provider → không chạy) | ca hết tiền → 1 diag, 0 lần gọi lại trong N nhịp | bớt nhiễu + bớt gọi | **không khóa** (OPT_IN tự tiêu tiền) — giữ bật |
| `travel_truth` (BẬT) | P31-G41 OPEN hướng chạy shot 35 ngược mạch · `core/travel_truth.py`, `core/runner.py` ≈ 2162/2994 | chỉ tính từ độ cao 3D, không biết vị trí địch/đích | nối câu vị trí `world_map_sentences` (DP11, chờ gộp) cho hướng chạy theo đích; chưa khóa | replay #31 shot 35: câu hướng chạy "về phía máy / ra khỏi khung trái" | đổi prompt (Cấp 3 khi bật world_map_sentences) | sau G41 đạt |

## 3. Gói C — cờ bật mà vô tác dụng: nối hoặc bỏ (ưu tiên 3)

| Cờ | Vì sao vô tác dụng · file | Phương án 1: NỐI (Cấp 2 + 3) | Phương án 2: BỎ (Cấp 3 — đưa vào `features.REMOVED`) | Khuyến nghị |
|---|---|---|---|---|
| `audio_first` (env) | chỉ `core/autopilot.py:1704`; #24–#33 không chạy autopilot | gọi cùng hàm từ nút Bước 3/5 (giọng trước, cắt theo giọng) | bỏ | **hỏi người dùng** (Q2) — đổi thứ tự sản xuất |
| `story_check` (env) | chỉ `core/autopilot.py:1681` (cần `ctx.llm`); 1 diag `story_unclear` #31 | nút "Kiểm mạch truyện" Bước 1 (Claude — khai costs, báo giá) | bỏ | NỐI (có 1 phát hiện thật #31) |
| `voice_check_redo` (env) | chỉ `core/autopilot.py:1671`; resends 0; đo sai thì trả TTS; không khai costs | nối sau TTS ở Bước 3 + khai costs (A2) + trần 1 lần gửi lại/shot | bỏ | NỐI sau khi có số đo (chạy shadow 1 dự án) |
| `stage_auto` (TẮT, `costs`) | `fixes_projects [31]` đang ĐỎ 🧭 cho #34; G1/G3 IN_PROGRESS, G8 FIXED_UNVERIFIED; hỏng 2 lần 16/10 (0,68 USD) | sửa G1 (M2.4 `stage_props_byd` — C-M24), G3 (≤ 5° pitch + kiểm `depth.png`); preflight 0 USD #31 → bật cho #34 | — | NỐI (đường 3D chính); Cấp 3 bật sau preflight |
| `stage_handheld_props` (OPT, BẬT) | `REQUIRES ("stage_auto",)` — cha tắt (`unmet_all` báo) | theo `stage_auto` | — | để nguyên, tự có tác dụng khi `stage_auto` bật |
| `stage_crew_user_approve` (dOn) | `REQUIRES ("stage_crew",)` — cha tắt (bậc kiểm chứng nhanh) | theo `stage_crew` (C-STAGE-PLAN: bàn đạo diễn 3D) | — | để nguyên |
| `continuity_layout` (BẬT) | chỉ VÀNG, không mã đo riêng (`core/continuity.py:46`); G51/G52 không bắt được | — | thay bằng `continuity_state` + `continuity_shadow` (M3.4/M4.3) khi chúng bật; giữ tới lúc đó | thay thế (không xóa trước khi cờ mới bật) |

## 4. Bảng tổng 22 cờ (thứ tự làm)

| # | Cờ | Gói | Đang (máy chính) | Thêm chặn? | Tốn tiền? | Cấp | Việc code (ước) |
|---|---|---|---|---|---|---|---|
| 1 | change_review | A | BẬT | có — đúng thiết kế (fail-closed) | không thêm | 2→3 khóa | nhỏ (test + gộp diag) |
| 2 | hero_takes | A | BẬT | không | đang tốn, chưa khai | 2 | rất nhỏ |
| 3 | end_frames / scene_qc_claude / voice_check_redo (khai costs) | A | BẬT | không | đang tốn, chưa khai | 2 | rất nhỏ |
| 4 | director_rewrite | A | BẬT | không (bớt ghi) | không thêm | 2 + 3 (cờ con) | vừa |
| 5 | scene_qc_claude | A | BẬT → **TẮT** | không | bớt | 3 | — |
| 6 | chat_prompts | A | BẬT | không | không thêm | 2 | vừa |
| 7 | video_gate (+ horizon_needs_sky) | B | BẬT | bớt báo nhầm | 0 | 3 bật cờ con, 3 khóa | 0 code |
| 8 | two_tier_quality (+ send_estimate) | B | BẬT | không | 0 | 2 nhãn + 3 | nhỏ |
| 9 | motion_consistency_lint | B | BẬT | VÀNG mới (không chặn) | 0 | 2 | nhỏ |
| 10 | end_frames | B | BẬT | không | (đã khai ở A) | 2 + gộp m29 | rất nhỏ |
| 11 | scene_qc (+ qc_false_alarm_fix, video_qc_shadow) | B | BẬT | không | bớt gen lại | 3 bật 2 cờ con | 0 code |
| 12 | lip_sync + dialogue_take | B | env / 🔒 | không | 1 clip thử thật | 2 (gộp m29) + 3 | nhỏ |
| 13 | bg_autoqc | B | BẬT (OPT) | không | bớt gọi | 2 | nhỏ |
| 14 | travel_truth | B | BẬT | không | 0 | 3 (world_map_sentences) | 0 code (chờ DP11) |
| 15 | audio_first | C | env | — | — | hỏi người dùng | — |
| 16 | story_check | C | env | không | Claude (khai) | 2 + 3 | vừa |
| 17 | voice_check_redo | C | env | không | TTS (khai) | 2 + 3 | vừa |
| 18 | stage_auto | C | TẮT | không | Claude (đã khai) | 3 sau C-M24 + G3 | (việc riêng) |
| 19–20 | stage_handheld_props, stage_crew_user_approve | C | BẬT, vô tác dụng | — | — | theo cờ cha | 0 |
| 21 | continuity_layout | C | BẬT | — | — | 3 thay thế | 0 |

## 5. Câu hỏi người dùng chốt
1. **Gói A** — đồng ý: (a) tắt `scene_qc_claude` ở máy chính; (b) cờ con `director_rewrite_respect_lock` mặc định BẬT (Đạo diễn chỉ ĐỀ XUẤT cho trường
   người đã chỉnh, không ghi đè)?
2. `audio_first`: nối vào đường Dashboard thường (giọng trước rồi cắt hình theo giọng) hay bỏ?
3. `lip_sync`: duyệt 1 shot cận thật (≈ giá 1 clip Seedance 2.5 720p — số chính xác do `pregen_check`/ước tính Bước 4 in khi xin) để khóa cùng `dialogue_take`?
4. `two_tier_quality`: khóa sau #34 nếu giá ước tính khớp sổ chi ±5 %?
5. Cơ chế baseline cờ (mục 5 đánh giá) làm trước hay song song Gói B? (khóa cờ mà máy khác vẫn đọc mặc định code thì "khóa" không tới máy đó).

## 6. Giao việc đề xuất (sau khi duyệt)
- G-A code: 1 việc cloud (A1+A2+A5, cùng `core/change_review.py`/`core/features.py`/`core/chat_prompt.py`/`tools/pregen_check.py`), A3 nối sau M2.5 + C-M25B.
- G-B code: 1 việc nhỏ (motion lint + bg_autoqc + nhãn two_tier); phần còn lại là bật cờ con có sẵn (Cấp 3) + gộp `cloud/v31-m29`.
- G-C: chờ câu 2; `story_check` / `voice_check_redo` 1 việc vừa sau khi chọn NỐI.
- Mỗi việc: cờ con mới mặc định TẮT (trừ cờ người dùng duyệt BẬT), `tests/golden/package_inputs.json` thêm cờ = false, rà quy ước 7.
