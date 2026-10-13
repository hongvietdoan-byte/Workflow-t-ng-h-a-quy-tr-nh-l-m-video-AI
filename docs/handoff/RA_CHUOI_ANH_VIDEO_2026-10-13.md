# Rà chuỗi ảnh → video chất lượng cao (trước tập 2 #27) — 13/10

Phiên con RÀ (chỉ đọc, 0 USD). Code: worktree `danh-gia-devsys-2026-491348` @ `cdc88399`. Dữ liệu thật đọc `mode=ro`.
Test liên quan chạy 1 lần: `test_change_review, test_end_state_fresh, test_quality_tier, test_regen_draft_route,
test_update_scene_end_state, test_ui_quality_tier` → **83 passed** (các bản sửa lỗi 5/6/7/8 đã có test xanh).

## Trạng thái 4 lỗi đã biết (handoff P27 mục 6)
| Lỗi | Trạng thái | Bằng chứng |
|---|---|---|
| #5 sửa tay motion → Tổ rà soát giữ oan | **Sửa một nửa** — agent giờ đọc `motion_prompts` (1a880bd0), nhưng mục đỏ CŨ không bao giờ được rà lại khi sửa prompt → xem **C4** | `core/change_review.py:258-268` |
| #6 end_state | **Code đã sửa (3e68addd) nhưng cờ `end_state_fresh` TẮT** trong `data/feature_settings.json` → ô sửa end_state ẩn, motion_en.end_state cũ vẫn gửi → **C8** | `core/features.py:47` |
| #7 bản cao nháp cũ chặn nháp mới | **Đã gộp** (ea39a36b + `superseded_by`/`retire_superseded_finals`, job 855/895 đã rejected/failed) — nhưng chỉ cho final CHƯA duyệt; final ĐÃ duyệt của nháp cũ vẫn chặn → **C1** (thấy trên dữ liệu thật shot 17) | `core/quality_tier.py:305-384` |
| #8 gen lại ra direct 480p | **Đã sửa** (36640a4c: tuyến nháp dính, runner đổi direct→draft lúc gửi, follower theo leader) | `tests/test_regen_draft_route.py` xanh |

## Danh sách lỗi

### C1 — Bản cao ĐÃ DUYỆT của nháp cũ chặn nâng nháp mới + bản giao 480p không cảnh báo · **CHẶN** · Nhóm A
- **file:dòng**: `core/quality_tier.py:354-383` (`state`), `:305-320` (`superseded_by` chỉ xét `_RETIRABLE`), `:453-454` (`request_final`), `dashboard/quality_ui.py:77-80` (`draft_scenes`).
- **Triệu chứng** (dữ liệu thật #27 shot 17, scene 285): final 905 (từ nháp 903) `approved`; sau đó người duyệt nháp mới 915 (06:44) và `takes.used` = 915.
  `state()` vẫn ra `final_ok` (905 approved, ≥720p) → thẻ hiện "Bản cao ✓", KHÔNG có nút "⬆ Gen bản cao" (chỉ hiện khi `draft_ok`), bấm qua nút gom/
  script thì `request_final` từ chối "Shot đã có bản cao". Bản dựng dùng take 915 (nháp 480p) nhưng `draft_scenes` theo `state` → không gắn `_DRAFT`,
  không có `delivery_warning` → **480p ra bản giao im lặng** (trái luật "480p không bao giờ là bản giao").
- **Gốc**: lỗi 7 chỉ xử lý final chưa gửi/chờ duyệt; final đã duyệt luôn thắng, không so với nháp người duyệt mới nhất / take đang dùng.
- **Sửa**: trong `state()` bỏ qua final `approved` có `draft_job_id` < `approved_draft().id` (nháp người duyệt SAU nó) — coi như shot đang `draft_ok`
  của nháp mới; giữ final cũ làm take (không xóa). `request_final` dùng cùng bộ lọc. `draft_scenes` thêm điều kiện: take đang dùng (`takes.used`) có
  `quality_tier='draft'` → tính là nháp trong bản dựng.
- **Test**: `test_quality_tier::test_newer_approved_draft_reopens_final_after_old_final_approved` (đỏ: state=='final_ok', request_final ValueError →
  xanh: 'draft_ok', job final mới gắn nháp mới); `test_ui_quality_tier::test_used_draft_take_marks_cut_draft_even_if_old_final_approved`.

### C2 — Autopilot duyệt NHÁP bằng `ai_agent` → shot kẹt "Nháp · chờ duyệt" không lối ra · **CHẶN** (khi chạy autopilot/Dashboard autopilot cho video) · Nhóm B
- **file:dòng**: `core/autopilot.py:993-1002` (`_approve_unflagged`), gọi ở `:1054`; đối chiếu `core/quality_tier.py:243-253` (`approved_draft` chỉ nhận `reviewer_type='user'`), `dashboard/steps/step4.py:501` (`reviewable` chỉ `pending_review/succeeded`).
- **Triệu chứng**: QC đặt nháp về `pending_review` (đúng, `_draft_suggest`), rồi vòng autopilot duyệt luôn nháp không cờ bằng `ai_agent` → job `approved`;
  `quality_tier.state` = `draft_review` ("Nháp · chờ duyệt") nhưng nút "✔ Duyệt clip" tắt (job đã approved), `request_final` báo "bản nháp chưa được
  người duyệt". Không có nút nào cho người duyệt lại. Hộp thư không báo (không còn `pending_review`). Dữ liệu hiện tại: 61 lượt duyệt nháp đều `user`
  (autopilot chưa chạy video) → lỗi tiềm ẩn, sẽ nổ khi bật autopilot #27 (quyết định 13/10).
- **Sửa**: `_approve_unflagged` bỏ qua job `quality_tier='draft'` (khi `quality_tier.enabled()`); nếu còn nháp chờ → `_Wait("drafts", "N nháp chờ bạn duyệt …")`.
  Phòng thủ thêm: `Pipeline.approve` từ chối `reviewer_type != 'user'` cho nháp hai bậc (trả False + ghi chú) — giống cách chặn final bị thay.
- **Test**: `test_autopilot::test_video_phase_never_approves_draft_as_ai` (đỏ: review_log ai_agent approve → xanh: vẫn pending_review + _Wait).

### C3 — "↻ Xếp hàng lại từ đầu vào mới" biến bản cao chờ xác nhận thành NHÁP mới tốn tiền · **NẶNG** · Nhóm C
- **file:dòng**: `core/runner.py:808-813` + `:1129-1131` (final không nâng được → fail `stale_input: bản cao bị chặn: cần xác nhận gen MỚI…`),
  `core/batch.py:203-247` (`_input_failed`/`input_failures`/`requeue_input_failures` coi mọi `stale_input` là đầu vào cũ), `dashboard/steps/step4.py:543-547`.
- **Triệu chứng**: nháp hết hạn ở ClipAI lúc gửi bản cao → job final hỏng với lý do "cần xác nhận"; thẻ ghi "Hỏng vì đầu vào đã cũ / thiếu — dùng ↻ Xếp hàng
  lại…" (sai lý do). Bấm nút đó → `create_job` không cha → `tier_for_new_job` → **job nháp 480p mới** (trả tiền) dù nháp đã duyệt còn nguyên; cũng áp cho
  final bị chặn "superseded".
- **Gốc**: lý do "chờ người xác nhận" và "đầu vào cũ" cùng tiền tố `stale_input`.
- **Sửa**: runner fail các chặn bản cao bằng tiền tố riêng (vd. `final_hold:`); `input_failures` bỏ job `quality_tier='final'` (hoặc tiền tố đó); thẻ Bước 4 với
  `final_hold` hiện "Bản cao chờ bạn xác nhận gen mới" + trỏ nút "⬆ Gen MỚI bản cao" (đã có ở `quality_ui.card_block`).
- **Test**: `test_quality_tier::test_requeue_input_failures_skips_final_needing_confirm` (đỏ: created==1 job draft → xanh: created==0, final vẫn được đề xuất).

### C4 — Sửa tay motion prompt không làm Tổ rà soát rà lại; mục đỏ cũ giữ gen tới khi bấm tay · **NẶNG** · Nhóm D
- **file:dòng**: `core/db.py:631-636` (trigger chỉ `UPDATE OF data ON scenes`), `core/llm_io.py:970-1007` (`store_motion_prompts` ghi `motion_prompts`, không tạo
  change_event), `core/change_review.py:337-343` (chỉ đóng mục Claude cũ khi có thay đổi `scene` mới), `:449-468` (`blocking`).
- **Triệu chứng**: mục đỏ khâu `motion` (vd. "motion tả trạng thái cuối cũ") → người sửa prompt ở Bước 3 → job video vẫn "chưa gửi: Tổ rà soát…" mãi (đúng
  kịch bản shot 16). Bước 3 không hiện khung Rà soát (`change_review_ui` chỉ render ở Bước 2 và 4) nên người sửa không thấy nút "✓ Đã sửa".
- **Gốc**: lỗi 5 mới sửa nội dung agent đọc, chưa sửa thời điểm rà: sự kiện chỉ sinh từ `scenes.data`.
- **Sửa**: thêm trigger `AFTER UPDATE OF motion_prompt ON motion_prompts` (kind `scene`, before/after = `{"motion_prompt": …}`) và thêm `motion_prompt` vào
  `WATCH` (khâu motion/video/khung_cuoi); hoặc gọn hơn: `store_motion_prompts` sau commit đóng `change_findings` mở khâu `motion` của shot bằng
  `resolved_by='prompt sửa — chờ rà lại'` rồi chèn change_event để agent rà bản mới. Render `change_review_ui` ở Bước 3 (tab Motion).
- **Test**: `test_change_review::test_editing_motion_prompt_requeues_review_and_lifts_old_red` (đỏ: blocking() còn lý do sau store_motion_prompts → xanh:
  có change_event pending, sau process_pending với Claude giả trả 'khop' → blocking None).

### C5 — Luồng Dashboard tay không bao giờ vẽ khung cuối; clip gửi thiếu khung cuối im lặng · **NẶNG** · Nhóm E
- **file:dòng**: `core/end_frames.py:77-102` (`queue`) chỉ gọi từ `core/autopilot.py:733`; `core/runner.py:1631-1634` (`_wait` chỉ chờ khi hàng `queued/running`),
  `:1229-1234` (`_end_frame` trả None không diag); `core/cost.py:150-170` (báo giá ảnh vẫn cộng khung cuối).
- **Triệu chứng**: cờ `end_frames` BẬT trong dữ liệu thật; người bấm "▶ Gen video" ở Bước 4 → shot có `end_state` (per_shot) gửi chỉ ảnh đầu, không dòng ⚙ nào
  nói thiếu khung cuối; khung cuối cũ (`ready`) bị coi cũ vì end_state đổi cũng rơi im lặng. Dashboard không có chỗ xem/duyệt/vẽ lại khung cuối
  (Grep `end_frames` trong `dashboard/` = 0).
- **Sửa**: (1) `_wait`: `end_frames.needed(...)` mà `usable_path` None → gọi `end_frames.queue` cho shot đó và giữ job với lý do "đang vẽ khung cuối" (hoặc
  `_diag_once` VÀNG "gửi không kèm khung cuối: …" nếu cố ý cho đi); (2) `queue_videos`/nút Gen video gọi `end_frames.queue` + `tick` trước khi gửi, có giá
  trên nút; (3) thẻ Bước 3/4 hiện khung cuối + nút vẽ lại (`end_frames.redo`).
- **Test**: `test_end_frames::test_manual_video_send_waits_for_needed_end_frame` (đỏ: provider giả nhận submit không `last_frame` → xanh: job queued + diag).

### C6 — `end_state_changed` so chuỗi con: end_state bị `looks.clean_prompt` sửa → khung cuối mãi "cũ", vẽ lại lặp tốn tiền · **NẶNG (điều kiện hẹp)** · Nhóm E
- **file:dòng**: `core/end_frames.py:56-63` (`now not in row["prompt"]`), `:118-130` (`prompt_for` đưa end_state qua `build_image_prompt` → `looks.clean_prompt`
  `core/looks.py:119-144` bỏ từ "cinematic/realistic/bokeh…", gộp khoảng trắng trước dấu câu).
- **Triệu chứng**: dự án FF_INGAME, end_state có từ bị lọc (hoặc " ," / khoảng trắng đôi) → khung cuối vừa vẽ đã bị coi cũ → `usable_path` None (clip gửi
  thiếu khung cuối) và `queue` chèn hàng mới mỗi lượt autopilot → vẽ lại liên tục (mỗi lần 1 ảnh trả tiền), không trần.
- **Sửa**: lưu dấu `end_state_src = sha1(end_state.strip())` vào hàng `end_frames` lúc gửi (cột mới hoặc trong `note` JSON), so dấu thay vì chuỗi con; hàng
  cũ không có dấu → so như hiện tại.
- **Test**: `test_update_scene_end_state::test_end_state_with_filtered_word_is_not_stale` (đỏ với "cinematic slow fade" → xanh).

### C7 — Job video bị giữ (Tổ rà soát / kiểm trước gen ĐỎ / bản cao chờ) không hiện lý do trên thẻ Bước 4 và hộp thư · **NẶNG** · Nhóm F
- **file:dòng**: `core/runner.py:403-406` (change_review hold), `:845-873` (`_pregen`), `:446-451` (`_wait` bản cao) ghi `WAIT_REASONS` + `_diag_once`;
  `dashboard/steps/step4.py:722-723` chỉ vẽ shimmer cho `queued`; `runner.wait_reason` chỉ dùng ở `dashboard/steps/step2.py:139` (ảnh);
  `core/inbox.py:48-80` không có mục video bị giữ (pregen ĐỎ, chờ khung cuối, nháp đã duyệt chờ nâng bản cao).
- **Triệu chứng**: thẻ clip "đang chờ" vô hạn; người chỉ thấy lý do khi mở ⚙ Chẩn đoán. Hộp thư không có "N nháp đã duyệt — bấm Gen bản cao".
- **Sửa**: thẻ Bước 4 khi `queued`: `st.caption("⏸ " + R.wait_reason(jid))` (giống Bước 2) + gom lý do ở thanh trên; `inbox` thêm mục từ `PREGEN_HELD`/
  diag `video_pregen`/`change_review_hold` gần nhất của job queued, và mục `draft_ok` (quality_tier.final_estimate scenes) "N cảnh chờ gen bản cao".
- **Test**: `test_ui_storyboard`/`test_step4::test_queued_video_shows_wait_reason` (AppTest: WAIT_REASONS[jid] set → caption có lý do);
  `test_inbox::test_lists_drafts_waiting_for_final`.

### C8 — Cờ `end_state_fresh` TẮT trên dữ liệu thật → lỗi 6 vẫn còn trong sản xuất · **NẶNG (cấu hình)** · Nhóm G
- **file:dòng**: `core/features.py:47-49` (verified False), `data/feature_settings.json` (không có khóa) ; hành vi cũ ở `core/seedance_refs.py:856-863`.
- **Triệu chứng**: sửa end_state (chỉ được qua `update_scene`/chat — ô Bước 1/3 bị ẩn khi cờ tắt) → prompt Seedance code viết vẫn dùng `motion_en.end_state` cũ.
- **Sửa**: bật `end_state_fresh` trong 🧪 trước tập 2 (0 USD; bản dịch lại qua sổ chi có giá ở nút Bước 3); sau 1 lần chạy thật thì `verified=True`.
- **Test**: đã có `tests/test_end_state_fresh.py` (7) — chỉ cần bật cờ; thêm kiểm tay ở kịch bản bấm thử bước 5.

### C9 — Tổ rà soát giữ cả lệnh NÂNG từ nháp (không dùng lại đầu vào) vì mục đỏ khâu ảnh/nền · **NHẸ** · Nhóm D
- **file:dòng**: `core/runner.py:396-406` (kiểm `change_review.blocking` trước mọi job, kể cả final `_from_sample`).
- **Triệu chứng**: nháp đã duyệt, mục đỏ mới (vd. shot kề đổi) → bản cao bị giữ "Tổ rà soát…" dù nâng từ nháp không gửi prompt/ảnh mới; dữ liệu thật đang
  có 1 mục đỏ mở (scene 287 khâu `anh`).
- **Sửa**: với job final nâng từ nháp, chỉ giữ khi mục đỏ mới hơn thời điểm người duyệt nháp VÀ khâu ∈ {video, motion, khung_cuoi}; còn lại ghi VÀNG.
- **Test**: `test_change_review::test_old_red_image_finding_does_not_hold_upgrade_from_approved_draft`.

## Tổng hợp theo nhóm file (gom một vòng sửa mỗi nhóm)
| Nhóm | File | Lỗi |
|---|---|---|
| A | `core/quality_tier.py`, `dashboard/quality_ui.py` | C1 |
| B | `core/autopilot.py`, `core/pipeline.py` (approve) | C2 |
| C | `core/batch.py`, `core/runner.py` (fail tiền tố bản cao), `dashboard/steps/step4.py` (caption) | C3 |
| D | `core/db.py` (trigger), `core/llm_io.py`, `core/change_review.py`, `dashboard/steps/step3.py`, `core/runner.py:396` | C4, C9 |
| E | `core/end_frames.py`, `core/runner.py` (`_wait`/`_end_frame`), `core/batch.py`, Dashboard Bước 3/4 | C5, C6 |
| F | `dashboard/steps/step4.py`, `core/inbox.py` | C7 |
| G | `data/feature_settings.json` (🧪) | C8 |

Mức: **chặn 2** (C1, C2) · **nặng 6** (C3–C8; C6 điều kiện hẹp, C8 cấu hình) · **nhẹ 1** (C9).

## Kịch bản bấm thử Dashboard (nhà cung cấp giả, bản sao CSDL — xem memory `reference_safe_copy_testing`)
1. Bước 2: tạo/duyệt ảnh shot A (per_shot, có `end_state`) và shot B. Bật cờ `end_state_fresh`, `end_frames`, `two_tier_quality`, `change_review`.
2. Bước 3: "Viết motion prompt" → duyệt. Kiểm thẻ có ô "🏁 Trạng thái cuối shot" (C8). Sửa end_state shot A → motion hiện ⚠ cũ, lý do "bản dịch cũ của end_state không dùng".
3. Bước 4: "▶ Gen video" shot A → xem job có đi kèm khung cuối không / có dòng chờ "đang vẽ khung cuối" không (C5). Xem thẻ clip queued có ghi lý do giữ không (C7).
4. Tạo mục đỏ khâu motion cho shot B (sửa `action` shot B trong Bước 1 → Claude giả trả `lech`/`do`), sửa tay motion prompt shot B ở Bước 3 → quay Bước 4: job B còn bị giữ không? Bước 3 có hiện khung Rà soát không? (C4).
5. Nháp shot A về `pending_review` → duyệt ✔ (người) → "⬆ Gen bản cao" → final xong → duyệt. Sau đó "↻ Gen lại video" trên nháp → nháp mới → duyệt → kiểm thẻ còn nút "⬆ Gen bản cao" không, pill có "Bản cao ✓" sai không, xuất bản dựng có `_DRAFT` không (C1).
6. Nhà cung cấp giả trả `task_usage(... is_draft=False)` (nháp hết hạn) → bấm Gen bản cao → job hỏng: đọc caption thẻ, rồi bấm "↻ Xếp hàng lại từ đầu vào mới" ở thanh trên → kiểm có sinh job NHÁP mới không (C3).
7. Chạy autopilot (Dashboard) tới pha video với QC giả chấm đạt → kiểm nháp có thành `approved` bởi ai_agent và nút ✔ Duyệt bị tắt không (C2).
8. Hộp thư (⌂): sau bước 3, 5, 6 xem có dòng "nháp chờ duyệt / chờ gen bản cao / bản cao chờ xác nhận / video bị giữ" không (C7).
