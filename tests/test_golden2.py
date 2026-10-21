"""C-GOLDEN2 (cloud-C 21/10): nghiệm thu golden #24/#27 lần 2 vẫn 68/68 INSUFFICIENT_INPUT — sửa tools/golden_capture.py + tools/golden_db_replay.py.
Fixture tổng hợp, không dữ liệu / provider thật; các phần thuần chạy được ở cloud (worker dựng gói vẫn cần native Python 3.14 → (g) skipif).
(a) video final: lần theo draft_job_id (source_job_id trỏ job ẢNH) · (b) COMPAT theo baseline_flags (cờ sản xuất lúc chụp) + experimental_flags TẮT
(c) model theo jobs.model của chính job · (d) pregen_fingerprint so riêng · (e) builder đòi tệp nền/Kho khác refs → DATA_CHANGED · (f) --help utf-8."""
import importlib
import io
import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_golden_replay import golden  # noqa: F401  (fixture CSDL tổng hợp)

ROOT = Path(__file__).resolve().parents[1]


def _mods():
    with patch.object(os, "environ", {}):
        return importlib.import_module("tools.golden_capture"), importlib.import_module("tools.golden_db_replay")


def _capture(golden, **kw):  # noqa: F811
    module, db, flags, root, _ = golden
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        return module.capture(db=db, project=24, shot=7, flags_file=flags, ref_root=root, purpose="compat", **kw)


# ---- (a) final video → bản nháp video theo draft_job_id ----------------------------------------------------------------------------
def test_a_video_final_follows_draft_job_id(golden):  # noqa: F811
    module, db, _, _, raw = golden
    final = dict(json.loads(raw), prompt="")                                    # submit_final_from_sample: prompt rỗng
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE jobs ADD COLUMN source_job_id INTEGER")
        conn.execute("ALTER TABLE jobs ADD COLUMN draft_job_id INTEGER")
        conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,model,quality_tier,sent_package,source_job_id,draft_job_id,"
                     "created_at,updated_at) VALUES(3,24,7,'video_gen','succeeded','fake-image','final',?,1,2,'x','x')", (json.dumps(final),))
    got = _capture(golden, latest_per_type=True)["jobs"]
    video = next(j for j in got if j["type"] == "video_gen")
    assert (video["id"], video["selected_job_id"]) == (2, 3)


def test_a_image_still_follows_source_job_id(golden):  # noqa: F811
    module, db, _, _, raw = golden
    up = dict(json.loads(raw), prompt=None)
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE jobs ADD COLUMN source_job_id INTEGER")
        conn.execute("ALTER TABLE jobs ADD COLUMN draft_job_id INTEGER")
        conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,model,quality_tier,sent_package,source_job_id,created_at,updated_at)"
                     " VALUES(4,24,7,'image_gen','succeeded','fake-image','final',?,1,'x','x')", (json.dumps(up),))
    image = next(j for j in _capture(golden, latest_per_type=True)["jobs"] if j["type"] == "image_gen")
    assert (image["id"], image["selected_job_id"]) == (1, 4)


# ---- (b) COMPAT theo cờ sản xuất ---------------------------------------------------------------------------------------------------
def _baseline(module, on=()):
    values = {k: False for k in module.feature_catalog()}
    for k in on:
        values[k] = True
    return values


def test_b_production_flags_on_are_compat_when_experimental_off(golden):  # noqa: F811
    module, _, flags, _, _ = golden
    prod_on = ["project_prop_lock", "video_pregen", "two_tier_quality"]
    flags.write_text(json.dumps({"baseline_flags": _baseline(module, prod_on), "experimental_flags": ["continuity_state", "whitebox_height_dummy"]}),
                     encoding="utf-8")
    got = _capture(golden)
    assert got["flags_mode"] == "baseline" and all(got["flags"][k] for k in prod_on)
    assert got["experimental_flags"] == ["continuity_state", "whitebox_height_dummy"]
    assert got["flags_provenance"] == "baseline_production_at_capture"


@pytest.mark.parametrize("change", ["experimental_on", "missing_catalog_flag", "unknown_experimental", "not_bool"])
def test_b_fail_closed(golden, change):  # noqa: F811
    module, _, flags, _, _ = golden
    base, exp = _baseline(module), ["whitebox_height_dummy"]
    if change == "experimental_on":
        base["whitebox_height_dummy"] = True
    elif change == "missing_catalog_flag":
        del base["video_pregen"]
    elif change == "unknown_experimental":
        exp = ["khong_co_co_nay"]
    else:
        base["video_pregen"] = 1
    flags.write_text(json.dumps({"baseline_flags": base, "experimental_flags": exp}), encoding="utf-8")
    with pytest.raises(module.GoldenError):
        _capture(golden)


def test_b_build_validates_baseline_mode():
    module, replay = _mods()
    base = _baseline(module, ["video_pregen"])
    module.validate_baseline_flags(base, ["whitebox_height_dummy"])                      # không ném
    with pytest.raises(module.GoldenError):
        module.validate_baseline_flags(dict(base, whitebox_height_dummy=True), ["whitebox_height_dummy"])
    with pytest.raises(module.GoldenError):
        module.validate_compat_flags(base)                                      # định nghĩa cũ vẫn chặt như trước


def test_b_readme_states_the_new_definition():
    text = (ROOT / "tests" / "golden" / "README.md").read_text(encoding="utf-8")
    assert "baseline_flags" in text and "experimental_flags" in text and "C-GOLDEN2" in text


# ---- (c) model theo job --------------------------------------------------------------------------------------------------------------
def test_c_model_is_pinned_from_the_job():
    _, replay = _mods()
    choice = {"model": "seedance-fast", "reason": "thử rẻ", "resolution": None}
    assert replay.pinned_choice(choice, {"model": "seedance-2.5"})["model"] == "seedance-2.5"
    assert replay.pinned_choice(choice, {"model": None}) == choice
    src = (ROOT / "tools" / "golden_db_replay.py").read_text(encoding="utf-8")
    assert "pinned_choice(" in src.split("def _worker", 1)[1] and "image_models" in src.split("def _worker", 1)[1]


# ---- (d) pregen_fingerprint so riêng -----------------------------------------------------------------------------------------------
def test_d_fingerprint_only_difference_is_compat_with_note():
    _, replay = _mods()
    body = {"v": 1, "prompt": "p", "refs": [], "external_id": "x"}
    sent = json.dumps(dict(body, pregen_fingerprint="abc"), ensure_ascii=False)
    built = json.dumps(body, ensure_ascii=False)
    got = replay.compare_database_job({"sent_package_raw": sent}, {"status": "BUILT", "raw": built})
    assert got["status"] == "COMPAT" and got["pregen_fingerprint"] == "so_rieng" and got["fingerprint_sent"] == "abc"
    other = json.dumps(dict(body, prompt="q", pregen_fingerprint="abc"), ensure_ascii=False)
    assert replay.compare_database_job({"sent_package_raw": other}, {"status": "BUILT", "raw": built})["status"] != "COMPAT"


def test_d_exact_bytes_still_plain_compat():
    _, replay = _mods()
    raw = json.dumps({"v": 1, "prompt": "p"})
    assert replay.compare_database_job({"sent_package_raw": raw}, {"status": "BUILT", "raw": raw}) == {"status": "COMPAT"}


# ---- (e) tệp nền / Kho khác refs → DATA_CHANGED ----------------------------------------------------------------------------------
@pytest.mark.parametrize("diag", [{"kind": "data", "path": "data/_plates3d/cache/abc/shot_7.png"},
                                  [{"kind": "read", "path": "data/assets/41/new.png"}]])
def test_e_builder_needing_other_plate_or_asset_is_data_changed(diag):
    _, replay = _mods()
    got = replay.classify_answer({"status": "INSUFFICIENT_INPUT", "reason": "x", "diagnostic": diag})
    assert got["status"] == "DATA_CHANGED" and "nền/Kho" in got["reason"] and got["paths"]


@pytest.mark.parametrize("diag", [{"kind": "network", "path": "<outside-root>"}, {"kind": "data", "path": "data/manifest.sqlite"},
                                  {"kind": "ValueError", "positions": []}, None])
def test_e_other_blocks_stay_insufficient(diag):
    _, replay = _mods()
    ans = {"status": "INSUFFICIENT_INPUT", "reason": "x", **({"diagnostic": diag} if diag is not None else {})}
    assert replay.classify_answer(ans)["status"] == "INSUFFICIENT_INPUT"


def test_e_classification_is_applied_after_the_worker():
    src = (ROOT / "tools" / "golden_db_replay.py").read_text(encoding="utf-8")
    body = src.split("def build_from_database", 1)[1].split("\ndef ", 1)[0]
    assert "classify_answer(" in body


# ---- (f) --help không vỡ khi stdout cp1252 -------------------------------------------------------------------------------------
@pytest.mark.parametrize("which", ["capture", "replay"])
def test_f_help_on_cp1252_console(which):
    module, replay = _mods()
    target = module if which == "capture" else replay
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    with patch.object(sys, "stdout", out), patch.object(sys, "stderr", out), pytest.raises(SystemExit) as stop:
        target.main(["--help"])
    assert stop.value.code == 0


# ---- (g) test cần worker 3.14 được skipif có lý do --------------------------------------------------------------------------------
def test_g_worker_tests_are_skipped_with_a_reason_off_314():
    for name in ("test_golden_db_replay.py", "test_golden_replay.py"):
        src = (ROOT / "tests" / name).read_text(encoding="utf-8")
        assert "needs_native_314" in src and "Python 3.14" in src
