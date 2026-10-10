"""Nhãn `slow` cho test chậm (người dùng 10/10 duyệt "cách 3"; số đo `--durations=30` cả bộ 10/10: 30 test chậm nhất ≈ 8,5 phút / 28,5).

Mặc định `pytest` VẪN chạy tất cả (không đổi hành vi). Bước gộp thường: `-m "not slow"`; `py tools/related_areas.py` báo khi thay đổi đụng
khu vực có test chậm → BẮT BUỘC chạy thêm `-m slow`. Danh sách theo node id; `tests/test_slow_marker.py` đỏ khi một id không còn tồn tại.
Cập nhật danh sách: chạy cả bộ với `--durations=30`, lấy các test ≥ ~8 s.
"""

SLOW_TESTS = (
    "tests/test_v3.py::ConsistencyTests::test_kling_multishot_makes_one_clip_per_group_and_gives_each_shot_its_part",
    "tests/test_devsys.py::AppTests::test_every_page_renders_without_an_exception",
    "tests/test_throttle.py::LearningTests::test_a_service_that_allows_three_is_learned_without_losing_a_job",
    "tests/test_v3.py::BudgetAndCompareTests::test_the_automatic_run_makes_one_picture_per_multishot_group",
    "tests/test_devsys_v2.py::RealRepoMeasureTests::test_every_area_of_the_real_repo_can_be_measured_and_its_evidence_exists",
    "tests/test_ui_v2_acceptance.py::AcceptanceTests::test_dynamic_keys_only_documented_renames_missing",
    "tests/test_ui_v2_acceptance.py::AcceptanceTests::test_click_count_new_project_to_first_video_not_more_than_old",
    "tests/test_editor_apply.py::ApplyTests::test_limits_old_reviews_and_nothing_to_apply",
    "tests/test_editor_apply.py::ApplyTests::test_a_review_of_another_intent_is_not_applied",
    "tests/test_editor_apply.py::RealRenderTests::test_cut_segment_drops_the_middle_of_the_clip",
    "tests/test_access.py::CoreEntryPointMatrix::test_every_entry_point_for_every_role",
    "tests/test_editor_apply.py::RealRenderTests::test_a_join_cover_is_drawn_at_that_cut_without_changing_the_length",
    "tests/test_perf_queue.py::QueueTests::test_more_projects_than_slots_wait_in_line_and_all_finish",
    "tests/test_rough_cut.py::RoughCutTests::test_sheets_cover_every_cut_and_never_exceed_twelve_images",
    "tests/test_group_cut.py::RefineTests::test_p24_group_is_cut_at_the_real_cut",
    "tests/test_perf_queue.py::QueueTests::test_stopping_a_queued_project_removes_it_from_the_line",
    "tests/test_editor_apply.py::ApplyTests::test_the_person_can_go_back_to_the_old_cut",
    "tests/test_editor_apply.py::RealRenderTests::test_shorter_shots_get_a_shorter_clip_and_the_music_edit_reaches_the_film",
    "tests/test_editor_review.py::RunTests::test_sheets_cover_every_cut_and_never_exceed_twelve_images",
    "tests/test_editor_apply.py::ApplyTests::test_at_most_two_applications_per_review",
    "tests/test_editor_apply.py::ApplyTests::test_lines_say_what_happened",
    "tests/test_editor_apply.py::ApplyTests::test_a_worse_cut_is_not_kept_the_old_one_is_put_back",
    "tests/test_editor_review.py::Fixture::test_sheets_cover_every_cut_and_never_exceed_twelve_images",
    "tests/test_group_cut.py::RefineTests::test_cut_near_a_part_edge_moves_the_bound_before_qc",
    "tests/test_editor_apply.py::ApplyTests::test_a_failed_render_puts_the_old_cut_back_and_says_so",
    "tests/test_editor_apply.py::ApplyTests::test_a_kept_application_renders_with_the_new_numbers_and_keeps_the_old_cut",
    "tests/test_ui_v2_acceptance.py::AcceptanceTests::test_no_widget_key_pattern_lost_in_source",
    "tests/test_clip_measure.py::ClipMeasureTests::test_the_next_shots_frames_at_the_end_are_found_and_dropped",
    "tests/test_group_cut.py::RefineTests::test_no_clear_cut_keeps_the_plan_and_says_so",
    "tests/test_subtitles.py::AutopilotSubtitleTests::test_when_switched_on_the_automatic_run_adds_subtitles_after_the_render_and_a_failure_never_loses_the_video",
)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: test chậm (render ffmpeg / Blender / dựng mọi trang) — xem conftest.py")


def pytest_collection_modifyitems(config, items):
    import pytest
    slow = set(SLOW_TESTS)
    for it in items:
        if it.nodeid.replace("\\", "/") in slow:
            it.add_marker(pytest.mark.slow)
