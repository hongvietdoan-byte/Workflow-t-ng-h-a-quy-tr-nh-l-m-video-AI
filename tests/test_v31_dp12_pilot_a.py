"""DP12 — V3.1 M5.3 pilot vòng A OFFLINE (docs/V3_1_M0_11_PILOT_3_VONG_2026-10-20.md mục 1): khung chạy 5 nhóm ca (payload, continuity, QC,
lineage, phục hồi) lấy từ sổ lỗi devsys/errors.json (một nguồn), chạy test bằng chứng dưới lớp chặn (mạng ra ngoài, ghi vào data/), chấm 5 tiêu
chí đạt/rớt mục 1.3. Kết quả cao nhất = "DAT_OFFLINE" — không bao giờ VERIFIED (cần vòng B chạy thật). 0 USD."""
import json
import os
import socket
import sys
from unittest.mock import patch

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
_IMPORT_ENV = {"PATH": "fixture-path", "SYSTEMROOT": "fixture-system", "TEMP": "fixture-temp", "PYTHONUTF8": "1"}
with patch.object(os, "environ", _IMPORT_ENV):
    import pilot_a as P  # noqa: E402
    import pilot_a_guard as GD  # noqa: E402


def _item(id_, status, category="goi_video", tests=()):
    return {"id": id_, "status": status, "category": category, "stage": "L12", "tests": list(tests), "title": id_}


def test_categories_map_to_the_five_groups():
    assert set(P.GROUPS) == {"payload", "continuity", "qc", "lineage", "phuc_hoi"}
    assert P.group_of({"category": "goi_video"}) == "payload"
    assert P.group_of({"category": "vi_tri"}) == "continuity"
    assert P.group_of({"category": "bao_nham"}) == "qc"
    assert P.group_of({"category": "vong_doi_job"}) == "phuc_hoi"
    assert P.group_of({"category": "chua_co"}) == "khac"


def test_cases_from_registry():
    reg = {"items": [_item("A", "FIXED_UNVERIFIED", tests=["tests/test_a.py"]), _item("B", "OPEN", tests=["tests/test_b.py::t"]),
                     _item("C", "OPEN"), _item("D", "WONT_FIX", tests=["tests/test_d.py"]),
                     _item("E", "IN_PROGRESS", tests=["tests/test_e.py::t"])]}
    got = {c["id"]: c["kind"] for c in P.cases(reg)}
    assert got == {"A": "phai_xanh", "B": "phai_do", "E": "dang_lam"}


def test_real_registry_has_cases_in_every_group_and_files_exist():
    reg = json.load(open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8"))
    cs = P.cases(reg)
    assert {c["group"] for c in cs if c["kind"] == "phai_xanh"} >= {"payload", "qc", "phuc_hoi"}
    assert P.missing_tests(cs, ROOT) == []


def test_node_status_from_junit(tmp_path):
    xml = tmp_path / "j.xml"
    xml.write_text('<testsuites><testsuite>'
                   '<testcase classname="tests.test_a" name="test_ok"/>'
                   '<testcase classname="tests.test_a.K" name="test_bad"><failure message="x"/></testcase>'
                   '<testcase classname="tests.test_b" name="test_x"><skipped type="pytest.xfail" message="P31-G9"/></testcase>'
                   '</testsuite></testsuites>', encoding="utf-8")
    res = P.junit(str(xml))
    assert P.node_status("tests/test_a.py::test_ok", res) == "passed"
    assert P.node_status("tests/test_a.py::K::test_bad", res) == "failed"
    assert P.node_status("tests/test_a.py", res) == "failed"                       # cả tệp: một ca đỏ → đỏ
    assert P.node_status("tests/test_b.py::test_x", res) == "xfailed"
    assert P.node_status("tests/test_c.py", res) == "missing"


def _verdict(**over):
    base = {"cases": [{"id": "A", "kind": "phai_xanh", "status": "passed"}, {"id": "B", "kind": "phai_do", "status": "xfailed"}],
            "golden": "passed", "network": 0, "data_writes": []}
    base.update(over)
    return P.evaluate(base)


def test_all_good_is_offline_pass_never_verified():
    v = _verdict()
    assert v["ket_qua"] == "DAT_OFFLINE" and "VERIFIED" not in json.dumps(v)


@pytest.mark.parametrize("over,why", [
    ({"cases": [{"id": "A", "kind": "phai_xanh", "status": "failed"}]}, "c1"),
    ({"network": 2}, "c3"),
    ({"data_writes": ["data/ref_padded/x.png"]}, "c4"),
    ({"cases": [{"id": "B", "kind": "phai_do", "status": "passed"}]}, "c5"),
])
def test_any_failed_criterion_fails(over, why):
    v = _verdict(**over)
    assert v["ket_qua"] == "ROT" and v["tieu_chi"][why]["dat"] is False


def test_golden_not_measurable_is_not_a_pass():
    v = _verdict(golden="khong_do_duoc")
    assert v["ket_qua"] == "CHUA_DO_DU" and v["tieu_chi"]["c2"]["dat"] is None


def test_open_case_without_xfail_but_red_is_still_red():
    assert _verdict(cases=[{"id": "B", "kind": "phai_do", "status": "failed"}])["tieu_chi"]["c5"]["dat"] is True


def test_main_machine_capture_list_is_written():
    assert P.MAY_CHINH and all(x.get("nhom") in P.GROUPS for x in P.MAY_CHINH)


# ---- lớp chặn (plugin pytest) --------------------------------------------------------------------------------------------------
def test_guard_blocks_outbound_and_counts(tmp_path):
    g = GD.Guard(str(tmp_path / "data"))
    with g:
        s = socket.socket()
        with pytest.raises(GD.Blocked):
            s.connect(("93.184.216.34", 443))
        s.close()
    assert g.network == 1


def test_guard_lets_local_sockets_through():
    g = GD.Guard("/nonexistent")
    with g:
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        c = socket.socket()
        c.connect(srv.getsockname())
        c.close()
        srv.close()
    assert g.network == 0


def test_guard_records_writes_under_data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    g = GD.Guard(str(data))
    with g:
        with open(data / "x.txt", "w") as f:
            f.write("x")
        with open(tmp_path / "ok.txt", "w") as f:
            f.write("y")
    assert [os.path.basename(p) for p in g.data_writes] == ["x.txt"]
