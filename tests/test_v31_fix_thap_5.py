"""C-FIX-THAP-5 (cloud-C 21/10, các THẤP rà 21/10 — cờ giữ TẮT), mỗi mục đỏ → xanh:
(1) final_qc.intended_holds / _shot_at: chuyển cảnh chồng (crossfade / dip_to_black, OVERLAP_STYLES) làm bản dựng ngắn hơn tổng timeline
    `fade` × (số shot − 1) — mốc giữ khung cố ý lệch → báo freeze_frame nhầm (như final_cut.total_seconds).
(2) world_map.build → build_3d không truyền BYĐ vào sources() → BYĐ đổi không làm map 3D hết hiệu lực; entities_at(m, None) với valid_from
    số → TypeError.
(3) send_preview_ui: shadow_of đọc 3 tệp + bảng ở MỖI rerun trên mọi thẻ clip → bộ nhớ đệm theo (dự án, job, shot, mtime tệp, qc_run lớn nhất).
(4) devsys/areas.json: tests/test_v31_g36b_refusal_skip.py trong "tests" của core_infra."""
import json
import os
from unittest import mock

import pytest

from core import final_qc as F
from core import send_preview as SP
from core import world_map as W
from tests.test_v31_dp8_world_map import BYD_C6, _stage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = [{"idx": 1, "seconds": 4.0}, {"idx": 2, "seconds": 4.0}, {"idx": 3, "seconds": 4.0}]


# ---- (1) ---------------------------------------------------------------------------------------------------------------------
def _freeze_issues(spans, manifest, total):
    with mock.patch.object(F, "black_freeze_spans", return_value={"black": [], "freeze": spans}), \
         mock.patch.object(F.ffmpeg_studio, "probe_duration", return_value=total):
        return [i for i in F.check_black_freeze("v.mp4", TL, manifest) if i["code"] == "freeze_frame"]


def test_crossfade_end_hold_is_not_a_freeze():
    man = {"transition": "crossfade", "fade": 1.0, "end_hold": {"held_s": 1.7}}
    assert F.intended_holds(man, TL, 10.0) == [(pytest.approx(8.3), pytest.approx(10.0))]
    assert _freeze_issues([(8.3, 9.9)], man, 12.0) == []           # 12 s probe: không coi là mờ dần kết phim


def test_cut_keeps_the_old_positions():
    man = {"transition": "cut", "fade": 1.0, "end_hold": {"held_s": 1.7}}
    assert F.intended_holds(man, TL, 12.0) == [(pytest.approx(10.3), pytest.approx(12.0))]


def test_editor_fit_hold_and_shot_label_follow_the_overlap():
    man = {"transition": "dip_to_black", "fade": 1.0, "editor_fit": [{"idx": 2, "how": "hold", "from_s": 2.0, "to_s": 4.0}]}
    assert F.intended_holds(man, TL, 10.0) == [(pytest.approx(5.0), pytest.approx(7.0))]   # shot 2 kết ở 8 − 1 = 7 s
    assert F._shot_at(TL, 7.5, man) == "3"                       # cắt thẳng: 7,5 s còn là shot 2; chồng 1 s: đã sang shot 3
    assert F._shot_at(TL, 7.5) == "2"


# ---- (2) ---------------------------------------------------------------------------------------------------------------------
def test_byd_change_invalidates_the_3d_map(tmp_path):
    k1, seg = _stage(tmp_path)
    data = str(tmp_path / "data")
    first = W.save(data, 31, W.build(4, k1_dir=k1, seg_dir=seg, byd=BYD_C6))
    assert first["kind"] == "3d" and first["sources"]["byd"]
    changed = {**BYD_C6, 27: {**BYD_C6[27], "vat": []}}
    second = W.save(data, 31, W.build(4, k1_dir=k1, seg_dir=seg, byd=changed))
    assert second["map_revision"] == first.get("map_revision", 1) + 1
    hist = os.listdir(os.path.join(W.world_dir(data, 31), "history"))
    old = json.load(open(os.path.join(W.world_dir(data, 31), "history", hist[0]), encoding="utf-8"))
    assert old["invalidated"]["why"] == "byd_changed"


def test_entities_at_none_returns_everything(tmp_path):
    k1, seg = _stage(tmp_path)
    m = W.build(4, k1_dir=k1, seg_dir=seg)
    assert len(W.entities_at(m, None)) == len(m["entities"])


# ---- (3) ---------------------------------------------------------------------------------------------------------------------
def _job(jid=5):
    return {"id": jid, "project_id": 7, "scene_id": 1}


def test_shadow_is_read_once_until_a_file_changes(tmp_path):
    SP.SHADOW_CACHE.clear()
    with mock.patch("core.video_qc_shadow.read", return_value=[]) as read:
        SP.shadow_cached(None, str(tmp_path), 7, _job(), 1)
        SP.shadow_cached(None, str(tmp_path), 7, _job(), 1)
        assert read.call_count == 1
        d = tmp_path / "7" / "qc_shadow"
        d.mkdir(parents=True)
        (d / "video_qc.jsonl").write_text("{}\n", encoding="utf-8")
        SP.shadow_cached(None, str(tmp_path), 7, _job(), 1)
        assert read.call_count == 2
        SP.shadow_cached(None, str(tmp_path), 7, _job(6), 1)       # job khác: khóa khác
        assert read.call_count == 3


def test_new_qc_run_in_the_table_refreshes(tmp_path):
    from core import qc_evidence
    from core.db import connect
    SP.SHADOW_CACHE.clear()
    conn = connect(":memory:")
    qc_evidence.migrate_up(conn)
    with mock.patch("core.video_qc_shadow.read", return_value=[]) as read:
        SP.shadow_cached(conn, str(tmp_path), 7, _job(), 1)
        conn.execute("INSERT INTO qc_runs (qc_run_id, project_id, scope, job_ids, qc_path, qc_version, mode, started_at, finished_at, status) "
                     "VALUES ('r1', 7, 'clip', '[5]', 'x', 'v', 'shadow', 'a', 'a', 'ok')")
        SP.shadow_cached(conn, str(tmp_path), 7, _job(), 1)
    assert read.call_count == 2


def test_ui_uses_the_cache():
    src = open(os.path.join(ROOT, "dashboard", "send_preview_ui.py"), encoding="utf-8").read()
    assert "send_preview.shadow_cached(" in src and "send_preview.shadow_of(" not in src


# ---- (4) ---------------------------------------------------------------------------------------------------------------------
def test_g36b_test_is_registered():
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    core_infra = next(a for a in areas["areas"] if a["id"] == "core_infra")
    assert "tests/test_v31_g36b_refusal_skip.py" in core_infra["tests"]
    assert "tests/test_v31_fix_thap_5.py" in core_infra["tests"]
