"""Hộp thư 13/10 việc 3 (test song song -n 8): core.runner keeps per-process memory keyed by job id (WAIT_REASONS, PREGEN_HELD …);
tests use `:memory:` databases whose job ids restart at 1, so a reason left by one test held a job of the next one in the same worker
(test_layout_follow failed only under -n 8). tests/conftest.py empties that memory before every test."""
import time

from core import runner
from tests import test_layout_follow


def test_a_left_over_hold_reason_does_not_reach_the_next_test():
    runner.WAIT_REASONS[1] = ("chờ khung cuối (còn sót từ test trước)", time.time())
    runner.PREGEN_HELD[1] = ("ĐỎ còn sót", time.time())


def test_runner_memory_is_empty_at_the_start_of_a_test():
    assert runner.WAIT_REASONS == {} and runner.PREGEN_HELD == {}
    test_layout_follow.test_the_shot_waits_while_its_layout_shot_is_being_drawn()
