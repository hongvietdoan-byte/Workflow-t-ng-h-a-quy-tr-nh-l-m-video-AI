"""Rà gộp Đ15v1 (12/10): final_cut.measured_size probed every clip with a new ffmpeg process on every rerun (~10× per shot) —
remembered per file version; a changed file is probed again."""
import os
import time
from unittest import mock

from core import ffmpeg_studio, final_cut


def test_same_file_is_probed_once_and_again_after_it_changes(tmp_path):
    clip = tmp_path / 'a.mp4'
    clip.write_bytes(b'x')
    probe = mock.Mock(side_effect=[(1080, 1920), (720, 1280)])
    with mock.patch.object(ffmpeg_studio, 'probe_size', probe):
        assert final_cut.measured_size(str(clip)) == (1080, 1920)
        assert final_cut.measured_size(str(clip)) == (1080, 1920)
        assert probe.call_count == 1
        clip.write_bytes(b'xy')
        os.utime(clip, (time.time() + 5, time.time() + 5))
        assert final_cut.measured_size(str(clip)) == (720, 1280)
        assert probe.call_count == 2


def test_missing_file_is_not_cached(tmp_path):
    probe = mock.Mock(return_value=None)
    with mock.patch.object(ffmpeg_studio, 'probe_size', probe):
        final_cut.measured_size(str(tmp_path / 'none.mp4'))
        final_cut.measured_size(str(tmp_path / 'none.mp4'))
    assert probe.call_count == 2
