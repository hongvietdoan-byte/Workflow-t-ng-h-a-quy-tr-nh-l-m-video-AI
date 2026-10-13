# HANDOFF S3 — Khung cuối + kiểm bố cục (13/10)

Nhánh `claude/sua-s3-khung-cuoi` (base `9da6e9ce`, sau gộp S1+S2). Nguồn: `docs/handoff/DANH_SACH_SUA_CHUOI_2026-10-13.md` dòng S3;
C5, C6 (`RA_CHUOI_ANH_VIDEO_2026-10-13.md`); V2, V3, V5 (fallback runner), V12 (`RA_GOC_VIDEO_P27_2026-10-13.md`); `_skill_reserve`
(`RA_S1_S2_2026-10-13.md` mục 7) + việc S2 giao S3 (`HANDOFF_S2.md` cuối: khung cuối dùng câu "đứng sẵn", `starts=`).

## Đã xong (test đỏ commit `df47d232` → xanh)
| Lỗi | Sửa | Test |
|---|---|---|
| C5 | `end_frames.missing_reason`; `runner._end_frame` VÀNG 1 lần "clip gửi KHÔNG kèm khung cuối: <lý do>" (`end_frame_missing`); `_wait` giữ job khi khung cuối đang vẽ CÓ lý do (`WAIT_REASONS`); thẻ Bước 4 `dashboard/end_frame_ui.py`: ảnh khung cuối + lý do + nút 🖼 Vẽ / 🔁 Vẽ lại có giá (`end_frames.redo`); vòng tự cập nhật Bước 4 (`widgets._poll_running`) vẽ khung cuối đang chờ (khi autopilot không chạy) rồi `submit_pending` | `test_end_frames::ManualSendTests` (5) |
| C6 | `stamp_end_state` lưu sha1(end_state) vào `app_settings` khóa `end_frame_src:<row>` lúc gửi; `end_state_changed` so dấu, hàng cũ không dấu → so chuỗi như cũ (không đổi CSDL) | `test_update_scene_end_state::test_end_state_with_filtered_word_is_not_stale` |
| S2→S3 (1) | `end_frames.tick` cho prompt khung cuối qua `skill_objects.guard_prompt` (cờ skill_object_guard): tường "already standing at full height" | `test_end_frames::SkillObjectEndFrameTests` |
| V2 | `framing_guard._end_drift`: khung CUỐI clip vs ảnh đầu khi máy đứng yên (nửa đầu clip góc lệch < 10 %) — khớp < max(3 %, 0,3 × khớp khung 0) → ĐỎ `frame_end` + gợi ý | `test_framing_guard::test_end_frame_architecture_drift_flags`, `::test_end_frame_drift_not_flagged_on_kept_clips` |
| V3 | `end_frame_distance`: không so được cỡ người → `ok=None` (trước: True); runner: ok None + shot có người cử động/di chuyển → KHÔNG gửi khung cuối (VÀNG); shot vật kỹ năng xuất hiện (`skill_objects.rises`) → không gửi khung cuối vẽ, gợi ý GHÉP (`end_frame_skill_object`) | `::test_end_frame_without_face_is_not_ok` (thay test cũ coi end21 là đạt), `::test_unmeasured_end_frame_of_a_moving_person_is_not_sent`, `::test_skill_object_appearing_shot_gets_no_drawn_end_frame`, `::test_same_distance_end_frame_is_sent` (sửa: đo được mặt → gửi; không đo + không cử động → gửi + VÀNG) |
| V5 runner | Kho chủ thể từ chối (Kho đầy): khung cuối vẽ (bản sạch chuẩn bị cho Kho) giờ được đánh dấu như các ảnh khác — cả đường gửi thẳng lẫn đường hoãn `_finish_kwargs` | `test_ref_mark_off_face::test_kho_full_fallback_marks_the_end_frame_like_the_other_pictures`, `::test_start_frame_never_eye_marked` (khóa, xanh từ đầu nhờ S2) |
| V12 | `motion_physics.same_ground`: chạy/đi máy bám theo, khung cuối nền × [0,95–1,05] và góc lệch ≤ 5 % → không gửi khung cuối (`runner._same_ground`) | `test_locomotion_end_frame::test_sprint_end_frame_same_scale_dropped`, `::test_same_ground_needs_a_followed_run` |
| `_skill_reserve` | `runner._reserve_text`: chữ cho `reserve` gồm motion + tên ảnh danh tính + tên/tệp render + câu sửa | `test_skill_objects::test_runner_reserve_counts_the_names_of_the_pictures` |
| V1 (S2→S3 (3)) | `place_pictures(..., starts=)` ở chỗ dựng prompt Seedance (chỉ khi cờ plate_view_sentence) | (đường cờ của S2, chưa test riêng) |

## Cờ
Không thêm cờ mới. V3 (ok None → bỏ khung cuối, vật kỹ năng xuất hiện) và V12 nằm sau `framing_guard` (TẮT, verified False); V12 cần
thêm `locomotion_end_frame`. Đổi hành vi với người đang bật cờ: C6 + prompt khung cuối qua guard vật kỹ năng (skill_object_guard đang BẬT)
+ V5 đánh dấu khung cuối khi Kho chủ thể từ chối + `_reserve_text` (dành chỗ khi tên vật kỹ năng chỉ nằm ở tên ảnh) — đều là sửa lỗi.

## Đang dở / việc mở
- V2: chưa có fixture thật 858 (đồng hồ) — ngưỡng chỉ kiểm bằng clip giả + 903/915/907; chưa che hộp người (YuNet) khi so nền; phần
  "đưa khung đầu + khung cuối clip cạnh nhau cho QC" thuộc `core/claude_tasks.py` (vùng S4) — chưa làm.
- V3: chưa đo cỡ người khi mặt khuất (hộp thân / mask) — hiện chỉ "không đo được → không gửi nếu người cử động".
- C5 (2): nút "▶ Gen video" chưa tự xếp vẽ khung cuối trước khi gửi (đang VÀNG + nút trên thẻ); thẻ Bước 3 chưa hiện khung cuối
  (`dashboard/steps/step3.py` là vùng S4).
- S2→S3 (2) `deployed_pictures` vào `_reference_pictures`/`_ref_lint` + `objects=`: chưa làm. V1 chưa ghi diag khi view None/"other".
- `end_frame_ui.poll` vẽ cả hàng khung cuối autopilot xếp sẵn khi autopilot đã dừng (đã có trần sổ chi + chặn dự án tạm dừng ở spend_gate).
- Chưa có agent rà khâu liên quan (quy ước 7) — đề bài: `py tools/related_areas.py core/end_frames.py core/framing_guard.py
  core/motion_physics.py core/runner.py dashboard/end_frame_ui.py dashboard/widgets.py dashboard/steps/step4.py`.

## Test
45 file liên quan (`-n 8`): 693 passed, 4 skipped. Chưa chạy cả bộ / test chậm (`test_access`, `test_ui_v2_acceptance`) — để bước gộp.

## Vùng S4
Không sửa `db.py`, `llm_io.py`, `change_review.py`, `step3.py`, `runner.py:~396`, `plate_anchor.py`, `claude_tasks.py`. `runner.py` sửa:
`_finish_kwargs`, `_base_submit_kwargs` (nhánh ref-only khung cuối), `_end_frame`/`_end_frame_off_distance` + hàm mới, `_wait` (khung
cuối), `_submit_args` (place_pictures + reserve), hàm module `_reserve_text`.

## Vòng sửa sau rà (RA_S3_S4 R1–R8, 13/10)
Test đỏ commit `876f9a5d` (13 test đỏ) → xanh. R12 để bước gộp (vùng S4 `claude_tasks.py`).
| Lỗi | Sửa | Test |
|---|---|---|
| R1 CHẶN | `end_frames.redo` (người bấm, `auto=False`) ghi `app_settings` `end_frame_asked:<row>` (`mark_asked`, không đổi CSDL); `tick(..., only_ids=)`; `end_frame_ui.poll` chỉ vẽ `asked_ids`, bỏ qua khi `dashboard.common.read_only`, vẽ xong `submit_pending(pid, only=[clip đang xếp của đúng shot đó])`; hàng chạy tự động xếp khi chạy tự động không chạy → `missing_reason` = `AUTO_WAITING` (thẻ hiện lý do + nút có giá = đường thoát) | `test_end_frames::ManualSendTests::test_dashboard_poll_skips_autopilot_queued_rows`, `::test_dashboard_poll_draws_nothing_for_a_read_only_viewer`, `::test_dashboard_poll_draws_the_asked_end_frame_then_the_clip_goes` (sửa: `only=[job]`) |
| R2 | `tick` bọc khóa `runner._turn(pid, "end_frame")` không chờ; `_claim` nguyên tử `note='đang gửi'` (cũ > 120 s thì lấy lại), nhả khi lỗi tạm, xóa khi gửi xong | `ConcurrentPollTests::test_two_concurrent_polls_send_once`, `::test_claimed_row_is_not_sent_again_until_the_claim_is_stale` |
| R3 | `end_frames.skip_reason` (vật kỹ năng xuất hiện, cờ framing_guard + skill_object_guard) dùng chung: `queue` bỏ qua, `tick` loại hàng đang xếp (0 USD), `redo` báo lỗi, `usable_path` None, `missing_reason` = `SKILL_SKIP` (thẻ không có nút), `_wait` không giữ, `runner._end_frame` nói `end_frame_skill_object` 1 lần; `end_frames.dropped_reason` đọc diag "KHÔNG kèm" có tên tệp → thẻ "đã vẽ nhưng KHÔNG gửi: <lý do>" | `SkillObjectSkipTests::test_queue_skips_skill_object_rising_shot`, `test_framing_guard::test_card_says_dropped_end_frame` |
| R4 | `framing_guard.person_boxes` (YuNet mặt → hộp thân xuống đáy khung), `similarity(..., boxes=)` che hộp; `end_frame_distance` thêm `ground` (nền đã che người); `same_ground` đọc `ground` + chỉ phán khi ≥ 20 điểm khớp và ≥ 15 % | `test_locomotion_end_frame::test_same_ground_ignores_matching_person_on_new_background` |
| R5 | `_end_drift`: máy chuyển động = cộng dồn góc lệch giữa các mẫu liên tiếp trên CẢ clip (`_camera_travel`); che hộp người cả hai phía khi so khung cuối; `clip_framing/measure(..., camera_move=)` (pan/follow/orbit… → không phán) | `test_framing_guard::test_end_drift_not_flagged_when_camera_pans_in_second_half`, `::test_end_drift_not_flagged_when_person_walks_toward_camera` |
| R6 | `_person_acts` chỉ `moves_through_space` (bắn/đánh tại chỗ → vẫn gửi + VÀNG); shot không `characters` mà đo được nền → không ghi VÀNG cỡ người. TODO spec: đo hộp thân | `test_framing_guard::test_unmeasured_end_frame_of_a_shooting_person_is_sent_yellow` |
| R7 | hàng `queued` có `note 'chờ:%'` → "chưa vẽ được khung cuối: chờ: <trần>"; `end_frames.drawing` (thay `pending` trong `widgets.video_busy`) không tính hàng bị sổ chi chặn / hàng không ai vẽ | `ManualSendTests::test_budget_refused_end_frame_reason_shows_the_cap` |
| R8 | `_wait` ghi diag `end_frame_wait` (lý do thật từ `missing_reason`), thêm vào `HOLD_CODES` | `ManualSendTests::test_end_frame_hold_survives_in_held_reason` |

Kết quả: 119 file liên quan (`related_areas` + file nhắc end_frames/framing_guard/autopilot, trừ 5 file chậm) `-n 8`: 1898 passed, 1 đỏ
(`test_skill_object_appearing_shot_gets_no_drawn_end_frame` — sửa: `_end_frame` nói GHÉP khi `skip_reason`) → chạy lại 6 file sát: 136 passed.

Việc cho bước gộp: (1) `core/claude_tasks.py:_measure_clip` (vùng S4) truyền `camera_move=data.get("camera_move")` vào
`clip_measure.measure` (tham số đã có, mặc định None — phần cộng dồn chuyển động máy đã chạy không cần nó); (2) R12. Rủi ro: hàng khung
cuối chạy tự động xếp mà chạy tự động dừng hẳn thì clip của shot đó chờ tới khi người bấm 🖼 Vẽ (có giá) hoặc chạy tự động chạy lại —
chưa có nút "gửi clip KHÔNG kèm khung cuối"; ngưỡng hộp thân / GROUND_* chỉ kiểm bằng ảnh tổng hợp.
