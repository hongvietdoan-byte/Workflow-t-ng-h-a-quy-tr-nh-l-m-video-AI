"""C-M71-FIX (cloud-C 22/10, rà kỹ đợt gộp tich-hop-2210): D6 tạm ngừng theo NGUỒN Claude của job (không chung mọi dự án); bản đệm ảnh
tham chiếu của test không ghi vào data/ref_padded THẬT của repo."""
import os
import time
from unittest import mock

from core import chat_prompt as CP
from core import llm_runner


def _conn():
    from core.db import connect
    return connect(":memory:")


def test_quota_pause_is_per_claude_source_not_global():
    """VỪA 1: dự án A (Claude chung) báo out_of_credit → D6 dừng 600 s CHO A; dự án B có Claude riêng (nguồn khác) vẫn chạy."""
    conn = _conn()
    a, b = {"id": 1, "project_id": 1}, {"id": 2, "project_id": 2}
    src = {1: ("anthropic", "env"), 2: ("claude_cli", "project")}
    with mock.patch("core.llm_provider.job_provider", side_effect=lambda c, j: src[j["project_id"]]):
        sa, sb = CP.quota_scope(conn, a), CP.quota_scope(conn, b)
        assert sa != sb
        CP._pause(conn, llm_runner.LlmError("credit", code="out_of_credit"), sa)
        assert CP._quota_paused(conn, sa) and not CP._quota_paused(conn, sb)
        assert not CP._quota_paused(conn, None)                       # khóa chung cũ không còn được ghi
        c = {"id": 3, "project_id": 3}
        with mock.patch("core.llm_provider.job_provider", return_value=("anthropic", "env")):
            assert CP.quota_scope(conn, c) == sa                       # cùng nguồn (cùng key môi trường) → cùng tạm ngừng


def test_quota_pause_expires():
    conn = _conn()
    CP._pause(conn, llm_runner.LlmError("credit", code="out_of_credit"), "anthropic:x")
    with mock.patch.object(time, "time", return_value=time.time() + CP.QUOTA_PAUSE_S + 1):
        assert not CP._quota_paused(conn, "anthropic:x")


def test_rewrite_path_checks_and_sets_the_job_scope():
    import inspect
    src = inspect.getsource(CP)
    assert "_quota_paused(conn, scope)" in src and src.count("_pause(conn, e, scope)") == 2
    assert "_pause(conn, e)\n" not in src


def test_padded_copies_of_tests_never_land_in_the_repo_data_folder():
    """Mục 5: CSDL `:memory:` + PIPELINE_DATA mặc định → bản đệm từng ghi vào data/ref_padded THẬT của repo (đã lọt vào git)."""
    from PIL import Image
    from core import seedance_refs
    import tempfile
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_pad = os.path.join(root, "data", "ref_padded")
    before = set(os.listdir(repo_pad)) if os.path.isdir(repo_pad) else set()
    narrow = os.path.join(tempfile.mkdtemp(), "narrow.png")
    Image.new("RGB", (100, 400), (40, 40, 40)).save(narrow)
    out = seedance_refs.pad_to_rule(narrow, _conn())
    assert out and not os.path.abspath(out).startswith(os.path.abspath(repo_pad))
    after = set(os.listdir(repo_pad)) if os.path.isdir(repo_pad) else set()
    assert after == before


def test_a_test_that_popped_pipeline_data_does_not_leak_into_the_next_one():
    """Gốc rò data/ref_padded: test trước `os.environ.pop("PIPELINE_DATA")` ở tearDown → test sau ghi data/ THẬT. conftest đặt lại mỗi test."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = os.environ.get("PIPELINE_DATA")
    assert data and not os.path.abspath(data).startswith(os.path.join(root, "data"))
    from core import seedance_refs
    assert not os.path.abspath(seedance_refs.pad_dir(_conn())).startswith(os.path.join(root, "data"))
    os.environ.pop("PIPELINE_DATA", None)              # như tearDown của test_dashboard / test_users… (test kế được conftest đặt lại)


def test_zz_after_a_pop_the_next_test_still_writes_outside_the_repo():
    """Chạy SAU test trên (cùng tệp, cùng worker): PIPELINE_DATA đã bị pop — conftest phải đặt lại; bản đệm không vào data/ THẬT."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from core import seedance_refs
    assert os.environ.get("PIPELINE_DATA")
    assert not os.path.abspath(seedance_refs.pad_dir(_conn())).startswith(os.path.join(root, "data"))
