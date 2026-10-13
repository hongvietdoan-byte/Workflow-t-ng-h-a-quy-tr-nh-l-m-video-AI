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
