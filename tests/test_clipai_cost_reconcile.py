"""Hồi quy offline Đ19v2: không cấu hình hay API thật."""
import importlib
import json
import os
import sqlite3
from unittest.mock import patch

import pytest

# Thay đối tượng trước khi import mã dự án; không đọc môi trường thật.
with patch.object(os, "environ", {"PYTHONUTF8": "1"}):
    tool = importlib.import_module("tools.clipai_cost_reconcile")
    cost = importlib.import_module("core.cost")
    adapter = importlib.import_module("core.adapters.clipai")
    http = importlib.import_module("core.adapters.http")

MODEL = "dreamina-seedance-2-5-260628"
PRICING = {"per_video_second": {MODEL + ":480p": .14, MODEL + ":1080p": .31}, "per_video_clip": {}}


@pytest.fixture(autouse=True)
def isolated():
    with patch.object(os, "environ", {"PYTHONUTF8": "1"}):
        yield


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "fake.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""CREATE TABLE jobs(id INTEGER, project_id INTEGER, external_id TEXT, quality_tier TEXT, draft_job_id INTEGER, type TEXT);
        CREATE TABLE usage_events(id INTEGER, job_id INTEGER, project_id INTEGER, kind TEXT, provider TEXT, model TEXT, tier TEXT, quantity REAL, unit TEXT);""")
        for i in range(1, 5):
            conn.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?)", (i, 33, "seedance:t" + str(i), "draft" if i < 4 else "final", None if i < 4 else 1, "video_gen"))
            conn.execute("INSERT INTO usage_events VALUES(?,?,?,?,?,?,?,?,?)", (i, i, 33, "video", "clipai", MODEL, "480p" if i < 4 else "1080p", 9, "second"))
    return path


def tasks():
    return [dict(task_id="t" + str(i), task_status=2, model_name=MODEL, duration=9, is_draft=i < 4,
                 extra_data=dict(usage=dict(total_tokens=179740 if i < 4 else 909225), has_video_input=True, resolution="480p" if i < 4 else "1080p"),
                 seedance_cost_usd=1.150336 if i < 4 else 6.364575,
                 request_params=dict(seedance_cost_usd=2.52 if i < 4 else 2.79936, content=[] if i < 4 else [{"type": "draft_task", "draft_task": {"id": "prl47"}}])) for i in range(1, 5)]


def report(database, rows=None):
    conn = tool.open_readonly(database)
    try:
        return tool.reconcile(conn, tasks() if rows is None else rows, PRICING)
    finally:
        conn.close()


def test_money_and_separate_upgrade(database):
    result = report(database)
    assert result["totals"][0]["actual_usd_known"] == 3.451008
    assert result["totals"][1]["actual_usd_known"] == 6.364575
    assert sum(r["actual_usd_known"] for r in result["totals"]) == pytest.approx(9.815583)
    final = result["tasks"][3]
    assert final["kind"] == "upgrade"
    assert final["request_estimate_usd"] == 2.79936
    assert final["ledger_usd"] == pytest.approx(2.79)
    assert final["token_usd"] == pytest.approx(cost.seedance_token_usd(MODEL, 909225, True))
    assert result["actual_1080p_points"] == 1
    assert result["calibration"][3]["difference_percent"] == pytest.approx(-8.571)


def test_connection_rejects_writes(database):
    conn = tool.open_readonly(database)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM jobs")
    conn.close()


def test_fake_transport_get_only():
    calls = []
    def transport(method, url, _headers, _body, _timeout):
        calls.append((method, url.partition("?")[0]))
        return http.HttpResponse(200, json.dumps({"code": 0, "data": {"data": tasks()}}).encode())
    provider = adapter.ClipAIVideoProvider("offline-placeholder", transport=transport)
    rows, warnings = tool.collect_tasks(provider, 2)
    assert len(rows) == 4 and not warnings
    assert calls == [("GET", adapter.DEFAULT_BASE + adapter.PATH_LIST)]


def test_duplicate_tasks_no_double_count(database):
    result = report(database, tasks() * 2)
    assert len(result["tasks"]) == 4
    assert len(result["warnings"]) == 5


def test_ambiguous_jobs_and_multiple_events(database):
    with sqlite3.connect(database) as conn:
        conn.execute("INSERT INTO jobs SELECT 99,project_id,external_id,quality_tier,draft_job_id,type FROM jobs WHERE id=1")
        conn.execute("INSERT INTO usage_events SELECT 99,job_id,project_id,kind,provider,model,tier,quantity,unit FROM usage_events WHERE id=2")
    rows = report(database)["tasks"]
    assert rows[0]["job_id"] is None and "ambiguous_job" in rows[0]["warnings"]
    assert rows[1]["ledger_usd"] is None and "ledger_multiple_events" in rows[1]["warnings"]


@pytest.mark.parametrize("field,value", [("extra_data", "{broken"), ("request_params", "{broken"), ("extra_data", [1])])
def test_malformed_nested_data_warns(database, field, value):
    rows = tasks()
    rows[0][field] = value
    assert "bad_type:" + field in report(database, rows)["tasks"][0]["warnings"]


@pytest.mark.parametrize("value", [True, -1, "909225", float("inf")])
def test_bad_numeric_not_zero(database, value):
    rows = tasks()
    rows[0]["extra_data"]["usage"]["total_tokens"] = value
    result = report(database, rows)
    assert result["tasks"][0]["token_usd"] is None
    assert result["totals"][0]["token_usd_missing"] == 1


def test_unmatched_missing_and_output_allowlist(database):
    rows = tasks()[1:]
    rows[0]["task_id"] = "web-only"
    rows[0]["prompt"] = "PRIVATE-FIXTURE-MARKER"
    rows[0]["extra_data"]["arbitrary"] = "PRIVATE-FIXTURE-MARKER"
    result = report(database, rows)
    assert result["tasks"][0]["project_id"] is None
    assert "job_missing_task:t1" in result["warnings"]
    output = tool.markdown(result) + json.dumps(result)
    assert "PRIVATE-FIXTURE-MARKER" not in output


def test_bounded_pagination_and_invalid_pages():
    class Fake:
        def __init__(self):
            self.calls = []
        def _page(self, family, page):
            self.calls.append((family, page))
            return (tasks() * 13)[:50]
    fake = Fake()
    _, warnings = tool.collect_tasks(fake, 2)
    assert fake.calls == [("seedance", 1), ("seedance", 2)]
    assert "coverage_incomplete:page_limit" in warnings
    with pytest.raises(ValueError):
        tool.collect_tasks(fake, 101)


def test_cli_offline_json_and_sanitized_error(database, tmp_path, capsys):
    taskfile, prices = tmp_path / "tasks.json", tmp_path / "prices.json"
    taskfile.write_text(json.dumps(tasks()), encoding="utf-8")
    prices.write_text(json.dumps(PRICING), encoding="utf-8")
    args = ["--db", str(database), "--pricing", str(prices)]
    assert tool.main(args + ["--tasks-json", str(taskfile), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["actual_1080p_points"] == 1
    with patch.object(adapter.ClipAIVideoProvider, "from_env", side_effect=ValueError("offline_only")):
        assert tool.main(args + ["--live"]) == 2
    # C-FIX-D19: không nuốt lỗi — loại lỗi + mã do công cụ đặt (chi tiết lạ vẫn không in, xem dấu PRIVATE bên dưới)
    assert capsys.readouterr().out.strip() == "Không đối soát được [provider_read]: ValueError offline_only — kiểm tra file đầu vào, schema và provider chỉ đọc."
    taskfile.write_text("{PRIVATE-FIXTURE-MARKER", encoding="utf-8")
    assert tool.main(args + ["--tasks-json", str(taskfile)]) == 2
    assert "PRIVATE-FIXTURE-MARKER" not in capsys.readouterr().out


def test_cli_db_mandatory():
    with pytest.raises(SystemExit) as exc:
        tool.main(["--live", "--pricing", "unused"])
    assert exc.value.code == 2


def test_incomplete_unknown_actual_direct_and_string_json(database):
    rows = tasks()
    rows[0].pop("seedance_cost_usd")
    rows[0]["task_status"] = 1
    rows[1]["extra_data"] = json.dumps(rows[1]["extra_data"])
    rows[1]["request_params"] = json.dumps(rows[1]["request_params"])
    rows[2]["is_draft"] = False
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE jobs SET quality_tier='direct' WHERE id=3")
    result = report(database, rows)
    assert result["tasks"][0]["actual_usd"] is None
    assert "task_incomplete_or_unknown_status" in result["tasks"][0]["warnings"]
    assert result["tasks"][1]["total_tokens"] == 179740
    assert result["tasks"][2]["kind"] == "direct"


def test_wrong_ledger_project_and_unit(database):
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE usage_events SET project_id=22 WHERE id=1")
        conn.execute("UPDATE usage_events SET unit='tokens' WHERE id=2")
    result = report(database)
    assert result["tasks"][0]["ledger_usd"] is None
    assert result["tasks"][1]["ledger_usd"] is None
    assert "ledger_project_mismatch" in result["tasks"][0]["warnings"]
    assert "bad_type:ledger_seconds" in result["tasks"][1]["warnings"]


def test_unknown_prices_are_not_zero_and_missing_db(tmp_path, database):
    with tool.open_readonly(database) as conn:
        result = tool.reconcile(conn, tasks(), {"per_video_second": {}, "per_video_clip": {}})
    assert result["totals"][0]["ledger_usd_known"] is None
    assert result["totals"][0]["ledger_usd_missing"] == 3
    absent = tmp_path / "absent.sqlite"
    with pytest.raises(FileNotFoundError):
        tool.open_readonly(absent)
    assert not absent.exists()


def test_import_never_loads_live_provider():
    for fake in ({"PYTHONUTF8": "1"}, {"PYTHONUTF8": "1", "CLIPAI_TOKEN": "offline-placeholder"}):
        with patch.object(os, "environ", fake), patch.object(adapter.ClipAIVideoProvider, "from_env", side_effect=AssertionError("unexpected_live")):
            importlib.reload(tool)


def test_conflicting_duplicate_excludes_money(database):
    rows = tasks()
    other = dict(rows[0], seedance_cost_usd=99)
    result = report(database, rows + [other])
    assert result["tasks"][0]["actual_usd"] is None
    assert result["totals"][0]["actual_usd_missing"] == 1
    assert "conflicting_duplicate_task" in result["tasks"][0]["warnings"]


def test_unknown_kind_and_zero_not_calibration(database):
    rows = tasks()
    rows[3]["seedance_cost_usd"] = 0
    rows[0].pop("is_draft")
    with sqlite3.connect(database) as conn:
        conn.execute("UPDATE jobs SET quality_tier=NULL WHERE id=1")
    result = report(database, rows)
    assert result["tasks"][0]["kind"] == "unknown"
    assert result["actual_1080p_points"] == 0


def test_numeric_overflow_and_bad_price(database):
    assert tool.number(10 ** 1000) is None
    assert tool.number(1e308) is None
    with tool.open_readonly(database) as conn:
        for value in (float("nan"), float("inf"), -1, True, 10 ** 1000, 1e308):
            with pytest.raises(ValueError, match="invalid_pricing"):
                tool.reconcile(conn, tasks(), {"per_video_second": {MODEL + ":480p": value}, "per_video_clip": {}})


def test_input_bounds(database, tmp_path):
    class Fake:
        def _page(self, family, page):
            return tasks() * 13
    with pytest.raises(ValueError, match="invalid_page"):
        tool.collect_tasks(Fake())
    with pytest.raises(ValueError, match="invalid_tasks"):
        report(database, [{}] * (tool.MAX_ROWS + 1))
    path = tmp_path / "oversized.json"
    path.write_bytes(b" " * 20)
    with patch.object(tool, "MAX_FILE_BYTES", 10), pytest.raises(ValueError, match="input_too_large"):
        tool.read_json(path)


def test_calibration_groups_do_not_pool_models_or_video(database):
    rows = tasks()[3:]
    for i in range(4):
        row = dict(rows[0], task_id="web-" + str(i))
        row["extra_data"] = dict(row["extra_data"], has_video_input=False)
        rows.append(row)
    result = report(database, rows)
    assert result["actual_1080p_points"] == 5
    assert sorted(g["count"] for g in result["calibration_groups"]) == [1, 4]
    assert "calibration_insufficient:need_at_least_5_1080p_points" in result["warnings"]


def test_computed_overflow_is_unknown_and_json_finite(database):
    rows = tasks()
    rows[0]["seedance_cost_usd"] = 1e308
    rows[1]["seedance_cost_usd"] = 1e308
    rows[3]["seedance_cost_usd"] = 5e-324
    result = report(database, rows)
    assert result["totals"][0]["actual_usd_missing"] == 2
    assert result["calibration"][-1]["difference_percent"] is None
    assert result["actual_1080p_points"] == 0
    json.dumps(result, allow_nan=False)


# ---- C-FIX-D19 (rà C-RA-D19, docs/RA_CLOUD_D19_2026-10-20.md) -------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_PRICING = os.path.join(ROOT, "data", "pricing.json")


def test_real_pricing_table_with_null_prices_runs(database, tmp_path, capsys):
    """CAO: data/pricing.json CỐ Ý có giá null (_note_null_prices) — công cụ phải chạy được với bảng giá thật."""
    rows = tmp_path / "tasks.json"
    rows.write_text(json.dumps(tasks()), encoding="utf-8")
    assert tool.main(["--db", str(database), "--pricing", REAL_PRICING, "--tasks-json", str(rows)]) == 0
    assert "Đối soát ClipAI" in capsys.readouterr().out


def test_null_price_is_unknown_not_zero_and_said(database):
    pricing = {"per_video_second": {MODEL + ":480p": None, MODEL + ":1080p": .31}, "per_video_clip": {}}
    conn = tool.open_readonly(database)
    try:
        result = tool.reconcile(conn, tasks(), pricing)
    finally:
        conn.close()
    draft = result["tasks"][0]
    assert draft["ledger_usd"] is None
    assert any(w.startswith("unpriced:") for w in draft["warnings"])
    with pytest.raises(ValueError):
        tool.validate_pricing({"per_video_second": {"x": "0.1"}, "per_video_clip": {}})     # kiểu sai vẫn bị từ chối


@pytest.fixture
def group_db(tmp_path):
    path = tmp_path / "group.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""CREATE TABLE jobs(id INTEGER, project_id INTEGER, external_id TEXT, quality_tier TEXT, draft_job_id INTEGER,
                              type TEXT, group_leader INTEGER, clip_span TEXT);
        CREATE TABLE usage_events(id INTEGER, job_id INTEGER, project_id INTEGER, kind TEXT, provider TEXT, model TEXT, tier TEXT, quantity REAL, unit TEXT);""")
        spans = {10: {"start": 0, "length": 6}, 11: {"start": 6, "length": 3}}
        for jid, leader in ((10, None), (11, 10)):
            conn.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)", (jid, 31, "seedance:tg", "draft", None, "video_gen", leader, json.dumps(spans[jid])))
            conn.execute("INSERT INTO usage_events VALUES(?,?,?,?,?,?,?,?,?)", (jid, jid, 31, "video", "clipai", MODEL, "480p", spans[jid]["length"], "second"))
    return path


def group_task():
    return [dict(task_id="tg", task_status=2, model_name=MODEL, duration=9, is_draft=True, seedance_cost_usd=0.9,
                 extra_data=dict(usage=dict(total_tokens=180000), has_video_input=False, resolution="480p"),
                 request_params=dict(seedance_cost_usd=1.0, content=[]))]


def test_group_task_belongs_to_its_leader_and_is_split_once(group_db):
    """VỪA: thành viên nhóm mang chung external_id của job dẫn (core/runner.py) — không còn 'ambiguous_job', không đếm trùng."""
    conn = tool.open_readonly(group_db)
    try:
        result = tool.reconcile(conn, group_task(), PRICING)
    finally:
        conn.close()
    assert len(result["tasks"]) == 1
    row = result["tasks"][0]
    assert (row["job_id"], row["project_id"]) == (10, 31)
    assert "ambiguous_job" not in row["warnings"]
    assert row["ledger_usd"] == pytest.approx(.14 * 9)                       # sổ chi của cả nhóm (6 s + 3 s)
    shares = {m["job_id"]: m["actual_share_usd"] for m in row["group_members"]}
    assert shares == {10: pytest.approx(0.6), 11: pytest.approx(0.3)}        # chia theo clip_span, tổng = tiền task một lần
    assert result["totals"][0]["actual_usd_known"] == pytest.approx(0.9)


def test_two_leaders_on_one_task_stay_ambiguous(group_db):
    with sqlite3.connect(group_db) as conn:
        conn.execute("UPDATE jobs SET group_leader=NULL")
    conn = tool.open_readonly(group_db)
    try:
        row = tool.reconcile(conn, group_task(), PRICING)["tasks"][0]
    finally:
        conn.close()
    assert row["job_id"] is None and "ambiguous_job" in row["warnings"]


def test_final_without_draft_task_is_a_new_generation_not_an_upgrade(database):
    """THẤP: bản cao không nâng được từ nháp (quality_tier.NEW_GEN) có draft_job_id nhưng gói không có draft_task → không phải bước nâng."""
    rows = tasks()
    rows[3]["request_params"]["content"] = []
    assert report(database, rows)["tasks"][3]["kind"] == "new_final"


def test_errors_are_said_with_their_code(database, tmp_path, capsys):
    bad = tmp_path / "p.json"
    bad.write_text(json.dumps({"per_video_second": {"x": "abc"}, "per_video_clip": {}}), encoding="utf-8")
    rows = tmp_path / "tasks.json"
    rows.write_text("[]", encoding="utf-8")
    assert tool.main(["--db", str(database), "--pricing", str(bad), "--tasks-json", str(rows)]) == 2
    out = capsys.readouterr().out
    assert "ValueError invalid_pricing" in out


def test_report_says_only_seedance_is_reconciled(database):
    result = report(database)
    assert result["scope"] == "seedance_only"
    assert "chỉ họ Seedance" in tool.markdown(result)
