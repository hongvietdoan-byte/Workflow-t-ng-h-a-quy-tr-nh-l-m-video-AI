# C-FLAGTEST8 — Test không phụ thuộc mặc định 8 cờ đề nghị khóa (cloud-C, 21/10)

- Nhánh: `cloud/v31-flagtest8`, tạo từ origin/main.
- **Chỉ sửa TEST**: không đổi một dòng code `core/` / `dashboard/`, không nới assert nào.
- 8 cờ: `send_claim`, `video_pregen`, `framing_guard`, `plate_view_sentence`, `stage_camera`, `seedance_ref_groups`, `back_view_guard`, `chat_first`.
- Plugin dùng: `tools/testing/flagforce.py` (FLAGMATRIX_MODE=soft = `verified: True`).

## Kết quả
| Lượt (cloud Linux, Py 3.13, `-m "not slow" -n auto`) | Trước | Sau |
|---|---|---|
| Mặc định | 30 đỏ: 25 golden + 4 lỗi nền + plan_map | **25 đỏ = toàn bộ golden** (cần Python 3.14). Không đỏ mới |
| 8 cờ BẬT (soft) | 186 đỏ: 25 golden + 155 do cờ + 6 lỗi nền / chập chờn | **30 đỏ = 25 golden + 5 nhóm C** |

- **Nhóm B (lỗi thật của code khi cờ BẬT): 0.**
- Đã kiểm kỹ 3 ca nghi ngờ; cả 3 đều là hành vi chủ đích:
  - `chat_first` → "Duyệt tất cả" một click: `dashboard/design/components.py:267` `ONE_CLICK`, quyết định người dùng 07/10.
  - `framing_guard` → `qc_framing_cap` giữ điểm gốc: `core/claude_tasks.py:211`, clip đã bị `_framing_hold` giữ.
  - `video_pregen` → job giữ `queued`: cổng đỏ khi fixture thiếu ảnh duyệt / dữ liệu, đúng luật "thiếu đầu vào → ĐỎ". 2 ca `TypeError` trong test (`probe_size(None)`) là hệ quả clip không được gửi, không phải lỗi code.

## Phân bố 155 test đỏ do cờ (ép từng cờ một trên tập đỏ: mỗi test đỏ vì đúng MỘT cờ)
| Cờ | Số test |
|---|---|
| `video_pregen` | 66 |
| `seedance_ref_groups` | 47 |
| `chat_first` | 37 |
| `framing_guard` | 5 |
| `stage_camera` | 4 |
| `plate_view_sentence` | 1 |
| `send_claim` | 0 |
| `back_view_guard` | 0 |

5 test đỏ với hai cờ: `test_lipsync`, `test_locomotion_end_frame` ×2, `test_subjects`, `test_v3::ConsistencyTests`.

## Cách sửa (nhóm A — test ngầm dựa vào cờ TẮT mặc định)
- **`tests/_flags.pin_off(tc, *names)`**:
  - đặt `FEATURE_<NAME>=0` (mock.patch.dict, gỡ bằng addCleanup);
  - không dùng `flags_off` (tệp 🧪) vì tệp cài đặt thắng biến môi trường: test nào trong lớp tự bật cờ bằng `FEATURE_X=1` sẽ bị đè. Với `pin_off`, test / lớp con tự bật vẫn thắng.
- Đặt ở **đầu `setUp` các lớp test** có test đỏ (trước `super().setUp()`, để Base tự bật vẫn thắng). Lớp không có `setUp` thì thêm `setUp` gọi `super()`.
- Test dạng hàm (pytest): `monkeypatch.setenv("FEATURE_X", "0")`.
- `test_stage_auto` (3 test): test vốn đặt `FEATURE_STAGE_CAMERA=""` với nghĩa TẮT. Nhưng `""` rơi về mặc định → đổi thành `"0"` (TẮT tường minh).
- Mỗi file test một commit (45 commit).

## Nhóm C — 5 test khẳng định CHÍNH mặc định của cờ (phải đổi trong commit khóa cờ, không sửa trước)
| Test | Assert |
|---|---|
| `test_video_pregen.py::Registry::test_flag_default_off_and_declared` | `FEATURES["video_pregen"]["verified"]` là False |
| `test_framing_guard.py::FlagTests::test_flag_declared_and_off_by_default` | `verified` False |
| `test_plate_camera_stage.py::test_flag_declared_off_by_default` | `stage_camera` `verified` False |
| `test_seedance_refs.py::SeedanceRefTests::test_off_by_default` | bỏ FEATURE env → không nhóm ref (mặc định TẮT) |
| `test_fix_flags.py::FixesProjectsDeclared::test_p27_flags_default_on_by_user_decision` | `plate_view_sentence` bật theo quyết định nhưng `verified` False |

Khi khóa: đổi các assert này cùng lúc với `verified: True`; test thứ tư đổi thành "mặc định BẬT"; test p27 bỏ `plate_view_sentence` khỏi `P27_FLAGS` (hoặc kiểm `locked`).

## Bảng đầy đủ (155 test nhóm A + 5 nhóm C; test đỏ với 2 cờ có 2 dòng)
| Test | Nhóm | Cờ | Cách sửa |
|---|---|---|---|
| `test_adapters.py::FactoryAndRunnerTests::test_end_to_end_success_writes_ordered_file` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_adapters.py::FactoryAndRunnerTests::test_network_errors_keep_job_queued_or_running` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_adapters.py::FactoryAndRunnerTests::test_risk_control_at_create_is_logged_and_job_fails_without_retry` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_batch_a_0910.py::VideoHeroAndQcLine::test_hero_counts_tiers_and_hides_the_shared_trial_budget` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_camera_setups.py::CameraSetupTests::test_off_by_default` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_camera_setups.py::CameraSetupTests::test_one_continuous_clip_is_sent_for_the_set_up` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_camera_setups.py::CameraSetupTests::test_the_set_up_group_shares_the_first_picture` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_concurrency_v4.py::OnePollerTests::test_the_lock_is_per_database` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost.py::CostTests::test_video_ledger_uses_billed_seconds` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::TransientDraftReadTests::test_a_failed_expiry_read_keeps_the_final_queued_and_does_not_lock_the_upgrade` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeCutsTheDraftPartTests::test_a_follower_final_asked_meanwhile_waits_and_is_not_paid_twice` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeCutsTheDraftPartTests::test_follower_whose_motion_changed_is_not_cut_silently` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeCutsTheDraftPartTests::test_followers_get_their_1080p_part_from_the_group_clip` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeCutsTheDraftPartTests::test_leader_final_is_cut_at_the_drafts_part` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeCutsTheDraftPartTests::test_ledger_records_the_group_clip_seconds_once` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeLoneTrimmedDraftTests::test_final_is_cut_where_the_draft_was_cut_and_billed_on_the_whole_clip` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_a_follower_final_asked_meanwhile_waits_and_is_not_paid_twice` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_follower_whose_motion_changed_is_not_cut_silently` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_followers_get_their_1080p_part_from_the_group_clip` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_leader_final_is_cut_at_the_drafts_part` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_leader_final_whose_cut_fails_is_red_and_failed` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_ledger_records_the_group_clip_seconds_once` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_cost_route_e1.py::UpgradeReviewFixTests::test_recut_by_hand_moves_where_the_final_is_cut` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_dashboard.py::DashboardSmokeTests::test_a_new_pending_image_cancels_a_question_already_asked` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_dashboard.py::DashboardSmokeTests::test_approve_all_asks_yes_or_no_once` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_dashboard.py::DashboardSmokeTests::test_the_script_card_has_its_summary_and_the_input_folds_into_an_expander` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_dashboard.py::DashboardSmokeTests::test_video_step_with_mock_provider_runs_to_completion` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_director_two_pass.py::DashboardTests::test_the_button_shows_the_estimate_runs_two_passes_and_shows_the_review` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::EndFrameFlowTests::test_drawn_from_the_start_picture_and_outdated_by_a_new_one` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::EndFrameFlowTests::test_off_by_default_nothing_waits` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::EndFrameFlowTests::test_the_clip_waits_for_its_end_frame_then_goes_out_first_plus_last` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_a_new_end_frame_request_ends_the_choice` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_budget_refused_end_frame_reason_shows_the_cap` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_dashboard_poll_skips_autopilot_queued_rows` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_manual_video_send_waits_for_needed_end_frame` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_manual_video_send_without_end_frame_is_said` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_ready_end_frame_says_nothing` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_rejected_end_frame_is_said_not_silent` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::ManualSendTests::test_stopped_autopilot_clip_can_be_sent_without_its_end_frame` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::SkillObjectEndFrameTests::test_end_frame_prompt_says_the_wall_is_standing` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_end_frames.py::SkillObjectSkipTests::test_queue_skips_skill_object_rising_shot` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_fix_flags.py::FixesProjectsDeclared::test_p27_flags_default_on_by_user_decision` | C | plate_view_sentence | khẳng định mặc định TẮT — sửa CÙNG commit khóa cờ |
| `test_framing_guard.py::FlagTests::test_flag_declared_and_off_by_default` | C | framing_guard | khẳng định mặc định TẮT — sửa CÙNG commit khóa cờ |
| `test_framing_guard.py::RunnerEndFrameTests::test_card_says_dropped_end_frame` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_end_frame_at_another_distance_is_not_sent_and_said_once` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_flag_off_sends_the_drawn_end_frame_as_before` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_pregen_says_it_yellow` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_same_distance_end_frame_is_sent` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_skill_object_appearing_shot_gets_no_drawn_end_frame` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_unmeasured_end_frame_of_a_moving_person_is_not_sent` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_framing_guard.py::RunnerEndFrameTests::test_unmeasured_end_frame_of_a_shooting_person_is_sent_yellow` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_gd1_fixes.py::RecoverToolRelinkTests::test_the_tool_reopens_a_written_off_job_on_its_real_task` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_gd1_fixes.py::RefusedThenSwitchedTests::test_the_switched_shot_is_sent_again_on_kling` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_image_progress.py::StatusTableTests::test_the_per_scene_status_table_lists_every_scene_with_its_state` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_job_lifecycle_b1a.py::PausedOrCancelledWhileSubmitting::test_a_failed_send_still_ends_failed_without_queued_to_failed` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_job_lifecycle_b1a.py::PausedOrCancelledWhileSubmitting::test_job_cancelled_while_submit_is_in_flight_keeps_the_paid_task_on_record` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_job_lifecycle_b1a.py::PausedOrCancelledWhileSubmitting::test_project_paused_while_submit_is_in_flight_is_not_paid_twice` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_lipsync.py::RunnerTests::test_a_marked_close_up_goes_to_seedance_with_its_voice` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_lipsync.py::RunnerTests::test_a_marked_close_up_goes_to_seedance_with_its_voice` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_a_run_as_long_as_its_clip_keeps_the_end_frame` | A | framing_guard | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_a_run_as_long_as_its_clip_keeps_the_end_frame` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_a_short_run_generated_at_3_s_goes_without_the_drawn_end_frame_and_says_so` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_flag_off_sends_the_drawn_end_frame_as_before` | A | framing_guard | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_flag_off_sends_the_drawn_end_frame_as_before` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_pregen_says_it_yellow` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_same_ground_ignores_matching_person_on_new_background` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_same_ground_needs_a_followed_run` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_locomotion_end_frame.py::RunnerEndFrameTests::test_sprint_end_frame_same_scale_dropped` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_new_skills.py::PanelTests::test_style_panel_is_in_step_1` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_next_step.py::NextStepTests::test_step1_walks_from_script_to_lock` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::NotCreatedTest::test_a_dropped_order_leaves_the_ledger_and_is_sent_again_without_using_a_retry` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::NotCreatedTest::test_a_provider_that_keeps_dropping_stops_after_three_resends` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::NotCreatedTest::test_a_running_task_below_the_first_page_is_still_found` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::PersistentCountersTest::test_a_dropped_order_leaves_the_ledger_and_is_sent_again_without_using_a_retry` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::PersistentCountersTest::test_a_new_provider_on_every_poll_still_reaches_the_verdict` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::PersistentCountersTest::test_a_provider_that_keeps_dropping_stops_after_three_resends` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::PersistentCountersTest::test_a_running_task_below_the_first_page_is_still_found` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::PersistentCountersTest::test_a_task_hidden_under_newer_tasks_is_not_resent` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::RequeuedTaskTest::test_a_dropped_order_leaves_the_ledger_and_is_sent_again_without_using_a_retry` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::RequeuedTaskTest::test_a_job_already_written_off_is_reopened_on_its_real_task` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::RequeuedTaskTest::test_a_provider_that_keeps_dropping_stops_after_three_resends` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::RequeuedTaskTest::test_a_running_task_below_the_first_page_is_still_found` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_not_created.py::RequeuedTaskTest::test_the_real_task_is_followed_instead_of_resent` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_plate_camera_stage.py::test_flag_declared_off_by_default` | C | stage_camera | khẳng định mặc định TẮT — sửa CÙNG commit khóa cờ |
| `test_qc_video.py::FramingCap::test_framing_flag_caps_score` | A | framing_guard | pin_off(self, cờ) trong setUp lớp |
| `test_quality_tier.py::RunnerTierTests::test_expired_draft_is_not_resent_unasked` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_quality_tier.py::RunnerTierTests::test_final_from_a_live_2_5_draft_uses_draft_task_at_1080p` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_references.py::ChoiceTests::test_the_character_bible_shows_the_pictures_and_saves_a_change` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_concurrency_limit` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_full_success_downloads_ordered_files` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_paused_project_submits_nothing_and_cancel_hits_provider` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_project_video_model_is_passed_to_provider` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_risk_control_is_logged_and_not_retried` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_transient_error_is_retried_and_then_succeeds` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_runner.py::RunnerTests::test_transient_errors_exhaust_retries_and_escalate` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_box_inside_the_v2_replace_panel_has_no_nested_expander` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_pasted_script_is_read_as_script_and_goes_to_the_full_text_box` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_s14_38_chat_is_the_centre_no_paste_popover_no_attach_popover` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_s14_38_full_script_over_one_in_use_asks_once_then_replaces_or_cancels` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_s14_38_read_only_view_with_copy_and_view_only_is_blocked` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::ScriptBoxTests::test_s14_38_short_paste_over_one_in_use_asks_add_or_replace` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::SparseChatS1443::test_request_alone_takes_the_text_in_the_box_and_says_what_it_took` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_s1443_screenwriter.py::SparseChatS1443::test_sparse_script_asks_in_the_chat_and_yes_goes_to_the_writer_without_paying` | A | chat_first | lớp import từ test_ui_script (ghim ở đó) |
| `test_scene_regen.py::GeneratedAudioOptionTests::test_runner_passes_the_flag_only_when_the_project_asks` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_scene_regen.py::RegenerateVideoTests::test_can_regenerate_more_times_than_max_retry` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_screens_dashboard.py::ScreensTests::test_script_screen_has_the_inputs_and_references_panel` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_seedance_refs.py::SeedanceRefTests::test_off_by_default` | C | seedance_ref_groups | khẳng định mặc định TẮT — sửa CÙNG commit khóa cờ |
| `test_seedance_refs.py::SeedanceRefTests::test_runner_follower_cost_provenance` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::EndFrameTests::test_end_frame_package_matches_the_call` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::FinalFromDraftTests::test_final_from_sample_package` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::RaSuaTests::test_a_failing_package_diag_never_skips_the_ledger` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::VideoPathTests::test_package_failure_never_blocks_the_send` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::VideoPathTests::test_package_guard_outside_safe_build_keeps_the_task_id` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_sent_package.py::VideoPathTests::test_video_package_matches_args_and_kwargs` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_spend_gate.py::EndFrameGateTests::test_a_locked_project_budget_warns_and_the_end_frame_is_sent` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_stage_auto.py::ReviewFixTests::test_needs_stage_camera_and_place_refs` | A | stage_camera | FEATURE_STAGE_CAMERA "" → "0" (TẮT tường minh) |
| `test_stage_auto.py::RunTests::test_g0_skips_staged_shots_when_stage_auto_off` | A | stage_camera | FEATURE_STAGE_CAMERA "" → "0" (TẮT tường minh) |
| `test_stage_auto.py::RunTests::test_stage_report_does_not_hold_a_staged_scene` | A | stage_camera | FEATURE_STAGE_CAMERA "" → "0" (TẮT tường minh) |
| `test_step1_flow.py::Step1LayoutTests::test_script_comes_first_then_the_choice_between_automatic_and_step_by_step` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_subjects.py::RunnerSubjectTests::test_subjects_are_sent_only_for_seedance_and_only_when_switched_on` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_subjects.py::RunnerSubjectTests::test_subjects_are_sent_only_for_seedance_and_only_when_switched_on` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_trainee_plans.py::TraineePlanTests::test_plans_recorded_group_of_unchanged_no_end_frame_drawn` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_trash.py::SweepAndRunnerTests::test_regenerated_video_moves_the_old_clip_to_the_trash` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_trial_fixes.py::EndFrameTests::test_sent_pictures_are_kept_a_missing_start_picture_is_said_and_redos_are_capped` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_trial_fixes.py::EstimateTests::test_the_picture_estimate_counts_end_frames_and_the_run_estimate_has_usd` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_box_inside_the_v2_replace_panel_has_no_nested_expander` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_pasted_script_is_read_as_script_and_goes_to_the_full_text_box` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_s14_38_chat_is_the_centre_no_paste_popover_no_attach_popover` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_s14_38_full_script_over_one_in_use_asks_once_then_replaces_or_cancels` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_s14_38_read_only_view_with_copy_and_view_only_is_blocked` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptBoxTests::test_s14_38_short_paste_over_one_in_use_asks_add_or_replace` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_lock_row_has_no_second_primary_button` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_locked_bible_leaves_every_panel_of_card_two_closed` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_new_project_shows_empty_state_hero_and_the_input_panel` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_primary_action_follows_the_state` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_project_with_scenes_characters_and_locked_bible_keeps_every_old_key` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_s14_28_references_after_scene_analysis_folded_with_recognised_names` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_script.py::ScriptScreenV2Tests::test_s14_28_script_first_and_no_reference_form_before_analysis` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_storyboard.py::StoryboardV2Tests::test_approve_all_asks_then_approves` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_storyboard.py::StoryboardV2Tests::test_hero_and_sticky_bar_are_there` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_v2_default.py::LightScreensAlwaysV2Tests::test_script_screen_is_v2_without_the_flag` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_ui_video.py::VideoV2Tests::test_hero_shows_stats_and_progress` | A | chat_first | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::BudgetAndCompareTests::test_a_job_over_the_limit_is_sent_with_a_warning` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::BudgetAndCompareTests::test_a_seedance_real_person_refusal_moves_the_continuity_group_to_kling` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::BudgetAndCompareTests::test_cheap_test_mode_never_asks_for_1080p_or_kling_pro` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::ConsistencyTests::test_a_continuing_shot_waits_for_the_previous_picture_and_ends_on_the_next_one` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::ConsistencyTests::test_a_continuing_shot_waits_for_the_previous_picture_and_ends_on_the_next_one` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_v3.py::ShotLayerTests::test_video_jobs_of_shots_ask_for_whole_seconds_not_below_the_plan` | A | seedance_ref_groups | pin_off(self, cờ) trong setUp lớp |
| `test_v31_m13_pause_before_submit.py::test_pause_stops_the_model_switched_retry` | A | video_pregen | monkeypatch.setenv FEATURE_X=0 |
| `test_v31_m47a_send_preview.py::PackagePreviewTests::test_preview_is_the_package_the_gen_button_sends` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_v31_t12_m12_m13_gaps.py::test_pause_pressed_while_the_end_frame_is_being_prepared_sends_nothing` | A | seedance_ref_groups | monkeypatch.setenv FEATURE_X=0 |
| `test_v31_t12_m12_m13_gaps.py::test_paused_project_sends_no_end_frame[0]` | A | seedance_ref_groups | monkeypatch.setenv FEATURE_X=0 |
| `test_v31_t12_m12_m13_gaps.py::test_paused_project_sends_no_end_frame[1]` | A | seedance_ref_groups | monkeypatch.setenv FEATURE_X=0 |
| `test_video_pregen.py::EndFrame::test_pass_ready_end_frame_matching_byd` | A | framing_guard | pin_off(self, cờ) trong setUp lớp |
| `test_video_pregen.py::FlagOff::test_flag_off_sends_like_before` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_video_pregen.py::Registry::test_flag_default_off_and_declared` | C | video_pregen | khẳng định mặc định TẮT — sửa CÙNG commit khóa cờ |
| `test_video_references.py::VideoRunnerWiringTests::test_a_chosen_character_asset_reaches_the_seedance_job_without_any_subject_library_setup` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_video_references.py::VideoRunnerWiringTests::test_a_reference_picture_deleted_from_disk_does_not_crash_the_submit` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_video_references.py::VideoRunnerWiringTests::test_kling_gets_no_image_references` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
| `test_workflow.py::FullSequenceTests::test_script_to_final_clips_step_by_step` | A | video_pregen | pin_off(self, cờ) trong setUp lớp |
