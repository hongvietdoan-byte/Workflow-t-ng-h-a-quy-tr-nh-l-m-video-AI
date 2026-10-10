"""core/world_rules (T2 luật thế giới có phạm vi, A8 — K0b phần 2): tải + kiểm hợp lệ, tìm theo thứ tự cụ thể nhất, không áp ngầm cho
vật khác, hạn dùng, gỡ, ghi nguyên tử, đường dẫn neo theo gốc repo (không theo cwd)."""
import json
import os

import pytest

from core import world_rules as wr
from tests import golden


def _rule(**kw):
    r = {"id": "r1", "vat": "kho:418", "ngu_canh": "*", "dieu": "lơ lửng cách đất 0,3 m", "pham_vi": "du_an:24",
         "nguon": "nguoi_dung: trả lời 'cố ý' 10/10"}
    r.update(kw)
    return r


def test_general_file_loads_without_issues():
    rules, issues = wr.load_file(wr.GENERAL_PATH, required=True)
    assert issues == []
    assert rules and all(r["pham_vi"] == "chung" for r in rules)
    assert any(r["vat"] == "loai:xe" for r in rules)          # "xe FF không bay" (mục 5, T2)


def test_missing_fields_are_reported_not_silent():
    bad = {"id": "x", "vat": "kho:1"}
    got = " ".join(i["loi"] for i in wr.validate_rule(bad))
    for k in ("ngu_canh", "dieu", "pham_vi", "nguon"):
        assert k in got
    assert wr.validate_rule(_rule(pham_vi="moi_noi"))           # phạm vi lạ
    assert wr.validate_rule(_rule(vat="giếng"))                 # vat phải kho:<id> / loai:<tên>
    assert wr.validate_rule(_rule(nguon="nghe nói"))            # nguồn phải người dùng / tư liệu
    assert wr.validate_rule(_rule(het_han="mai"))               # ngày ISO
    assert wr.validate_rule(_rule(pham_vi={"du_an": 24, "shot": []}))
    assert wr.validate_rule(_rule()) == []


def test_missing_required_file_and_bad_json_are_reported(tmp_path):
    rules, issues = wr.load_file(str(tmp_path / "khong_co.json"), required=True)
    assert rules == [] and issues and issues[0]["muc"] == "do"
    rules, issues = wr.load_file(str(tmp_path / "khong_co.json"), required=False)
    assert rules == [] and issues == []                         # dự án chưa có luật nào: hợp lệ
    p = tmp_path / "hong.json"
    p.write_text("{không phải json", encoding="utf-8")
    rules, issues = wr.load_file(str(p), required=False)
    assert rules == [] and issues[0]["muc"] == "do"


def test_rule_for_item_x_never_applies_to_item_y_of_same_kind():
    rules = [_rule(id="yn1", vat="kho:418", loai="yeu_nu")]
    assert [r["id"] for r in wr.tim(rules, "kho:418", du_an=24)] == ["yn1"]
    assert wr.tim(rules, "kho:419", du_an=24, loai="yeu_nu") == []   # cùng loại, khác vật → KHÔNG áp
    kind = [_rule(id="xe", vat="loai:xe", pham_vi="chung", dieu="không bay")]
    assert [r["id"] for r in wr.tim(kind, "kho:77", loai="xe")] == ["xe"]   # luật theo loại thì nói rõ loại
    assert wr.tim(kind, "kho:77") == []                         # không khai loại → không đoán


def test_scope_project_shot_context_and_order():
    rules = [_rule(id="chung", vat="loai:xe", pham_vi="chung", nguon="tu_lieu: x"),
             _rule(id="duan", vat="loai:xe", pham_vi="du_an:24"),
             _rule(id="shot", vat="loai:xe", pham_vi={"du_an": 24, "shot": [5, 6]}),
             _rule(id="ky_nang", vat="loai:xe", ngu_canh="ky_nang:kelly_dash", pham_vi="du_an:24"),
             _rule(id="vat", vat="kho:77", pham_vi="du_an:24")]
    got = [r["id"] for r in wr.tim(rules, "kho:77", ngu_canh="ky_nang:kelly_dash", du_an=24, shot=5, loai="xe")]
    assert got == ["shot", "vat", "ky_nang", "duan", "chung"]
    got = [r["id"] for r in wr.tim(rules, "kho:77", du_an=8, shot=5, loai="xe")]
    assert got == ["chung"]                                     # dự án khác: chỉ luật chung
    got = [r["id"] for r in wr.tim(rules, "kho:77", du_an=24, loai="xe")]
    assert "shot" not in got and "ky_nang" not in got           # không biết shot / ngữ cảnh → luật hẹp không áp


def test_removed_and_expired_rules_do_not_apply():
    rules = [_rule(id="go", go=True), _rule(id="het", het_han="2026-10-01"), _rule(id="con", het_han="2026-12-31")]
    assert [r["id"] for r in wr.tim(rules, "kho:418", du_an=24, hom_nay="2026-10-10")] == ["con"]


def test_no_accent_folding_short_words():
    rules = [_rule(id="v", vat="loai:van")]
    assert wr.tim(rules, "kho:1", du_an=24, loai="vàng") == []


def test_add_and_remove_write_atomically(tmp_path):
    path = wr.project_path(24, str(tmp_path))
    assert os.path.isabs(path) and path.endswith(os.path.join("24", "world_rules.json"))
    assert wr.add(path, _rule(), du_an=24) == []
    assert wr.add(path, _rule(), du_an=24)                      # trùng id → báo, không ghi đè
    assert wr.add(path, _rule(id="r2", pham_vi="du_an:8"), du_an=24)   # luật dự án khác không vào tệp dự án này
    assert wr.add(path, _rule(id="r3", pham_vi="chung"), du_an=24)     # luật chung không vào tệp dự án
    assert wr.remove(path, "r1", "người dùng: thực ra là lỗi") == []
    data = json.load(open(path, encoding="utf-8"))
    r = data["luat"][0]
    assert r["go"] is True and r["go_ly_do"] and r["ngay_go"]   # gỡ = đánh dấu, giữ lịch sử
    assert wr.remove(path, "khong_co", "x")
    assert not os.path.exists(path + ".tmp")
    rules, issues = wr.load_project(24, str(tmp_path))
    assert issues == [] and wr.tim(rules, "kho:418", du_an=24) == []


def test_project_file_rejects_foreign_scope(tmp_path):
    path = wr.project_path(24, str(tmp_path))
    os.makedirs(os.path.dirname(path))
    json.dump({"version": 1, "luat": [_rule(pham_vi="du_an:8"), _rule(id="ok")]}, open(path, "w", encoding="utf-8"))
    rules, issues = wr.load_project(24, str(tmp_path))
    assert [r["id"] for r in rules] == ["ok"] and issues


def test_relative_data_dir_is_anchored_at_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    p = wr.project_path(24, os.path.join("data", "projects"))
    assert p == os.path.join(wr.ROOT, "data", "projects", "24", "world_rules.json")
    monkeypatch.delenv("PIPELINE_DATA", raising=False)
    assert wr.project_path(24) == p


def test_load_all_combines_general_and_project(tmp_path):
    path = wr.project_path(24, str(tmp_path))
    wr.add(path, _rule(id="xe_bay_24", vat="kho:77", dieu="xe bay nhờ kỹ năng"), du_an=24)
    rules, issues = wr.load_all(24, str(tmp_path))
    assert issues == []
    ids = [r["id"] for r in wr.tim(rules, "kho:77", du_an=24, loai="xe")]
    assert ids[0] == "xe_bay_24" and len(ids) >= 2


GOLDEN = [c for c in golden.load_cases() if "world_rules" in (c.get("ky_vong") or {})]


def test_golden_has_world_rule_case():
    assert GOLDEN


@pytest.mark.parametrize("case", GOLDEN, ids=[c["id"] for c in GOLDEN])
def test_golden_world_rules(case):
    exp = case["ky_vong"]["world_rules"]
    for r in exp["luat"]:
        assert wr.validate_rule(r) == []
    for q in exp["hoi"]:
        got = [r["id"] for r in wr.tim(exp["luat"], q["vat"], ngu_canh=q.get("ngu_canh"), du_an=q.get("du_an"), shot=q.get("shot"),
                                        loai=q.get("loai"), hom_nay=q.get("hom_nay"))]
        assert got == q["ra"], q


def test_project_path_uses_caller_data_dir(monkeypatch, tmp_path):
    """Người gọi (K3: ctx autopilot / DATA dashboard) truyền data_dir TUYỆT ĐỐI → thắng PIPELINE_DATA và neo ROOT (bản sao thử, cwd khác)."""
    monkeypatch.setenv("PIPELINE_DATA", os.path.join("data", "projects"))
    monkeypatch.chdir(tmp_path)
    mine = str(tmp_path / "copy" / "projects")
    assert wr.project_path(24, mine) == os.path.join(mine, "24", "world_rules.json")
    path = wr.project_path(24, mine)
    assert wr.add(path, _rule(id="xe_bay_24", vat="kho:77"), du_an=24) == []
    rules, issues = wr.load_project(24, mine)
    assert issues == [] and [r["id"] for r in rules] == ["xe_bay_24"]
    assert [r["id"] for r in wr.load_all(24, mine)[0]][-1] == "xe_bay_24"


def test_write_uses_unique_temp_file(tmp_path):
    """Ghi nguyên tử bằng tệp tạm TÊN DUY NHẤT trong cùng thư mục — tên cố định '<tệp>.tmp' đụng nhau khi hai người ghi."""
    path = wr.project_path(24, str(tmp_path))
    os.makedirs(path + ".tmp")                     # chỗ tên tạm cố định cũ bị chiếm → cách cũ hỏng
    assert wr.add(path, _rule(id="xe_bay_24", vat="kho:77"), du_an=24) == []
    assert sorted(os.listdir(os.path.dirname(path))) == ["world_rules.json", "world_rules.json.tmp"]   # không để rác tạm
