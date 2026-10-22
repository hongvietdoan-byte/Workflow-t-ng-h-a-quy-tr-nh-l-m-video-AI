"""Hồ sơ vai + liên kết sản phẩm (người dùng 22/10): bộ kiểm core/crew.link_problems bắt THIẾU / THỪA / không ai đáp ứng."""
import copy

import pytest

from core import crew


@pytest.fixture
def mini():
    reg = {"fields": {"scenes.data.byd": {"owner": "director"}},
           "roles": [{"id": "executive_producer", "reports_to": None, "outputs": ["brief"], "acceptance": []},
                     {"id": "director", "reports_to": "executive_producer", "outputs": ["byd"], "acceptance": ["byd_du"]},
                     {"id": "storyboard_artist", "reports_to": "director", "outputs": ["anh"], "acceptance": []}]}
    k = lambda i: {"id": i, "ten": i, "nguong": "100 %", "cach_do": "code:core/crew"}  # noqa: E731
    prof = {"external_consumers": ["ngoai:phat_hanh"], "products": {
        "brief": {"ten": "brief", "producer": "executive_producer", "fields": [], "kpi": [k("brief_du")],
                  "consumers": {"director": [{"yeu_cau": "đủ", "dap_ung": "brief_du"}]}},
        "byd": {"ten": "byd", "producer": "director", "fields": ["scenes.data.byd"], "kpi": [k("byd_du")],
                "consumers": {"storyboard_artist": [{"yeu_cau": "rõ", "dap_ung": "byd_du"}]}},
        "anh": {"ten": "ảnh", "producer": "storyboard_artist", "fields": [], "kpi": [k("anh_dung")],
                "consumers": {"ngoai:phat_hanh": [{"yeu_cau": "đẹp", "dap_ung": "anh_dung"}]}}},
        "profiles": {r: {"ban_la_ai": r, "vai_tro": r, "viec_lam": ["x"], "chiu_trach_nhiem": ["y"], "giam_sat": [],
                         "dau_vao": ins, "dau_ra": outs}
                     for r, ins, outs in (("executive_producer", [], ["brief"]), ("director", ["brief"], ["byd"]),
                                          ("storyboard_artist", ["byd"], ["anh"]))}}
    return reg, prof


def run(reg, prof):
    return crew.link_problems(reg, prof)


def test_consistent_mini_crew_passes(mini):
    assert run(*mini) == []


def test_input_without_source_is_missing(mini):
    reg, prof = mini
    prof["profiles"]["storyboard_artist"]["dau_vao"].append("kho")
    assert any("THIẾU nguồn" in b for b in run(reg, prof))


def test_product_nobody_receives_is_waste(mini):
    reg, prof = mini
    prof["products"]["byd"]["consumers"] = {}
    prof["profiles"]["storyboard_artist"]["dau_vao"] = []
    assert any("THỪA" in b for b in run(reg, prof))


def test_one_sided_link_is_caught_both_ways(mini):
    reg, prof = mini
    a = copy.deepcopy(prof)
    a["profiles"]["storyboard_artist"]["dau_vao"] = []                  # người nhận quên khai
    assert any("không khai trong dau_vao" in b for b in run(reg, a))
    b = copy.deepcopy(prof)
    b["profiles"]["executive_producer"]["dau_vao"] = ["byd"]             # khai nhận mà sản phẩm không gửi
    assert any("không ghi executive_producer là người nhận" in x for x in run(reg, b))


def test_requirement_must_point_to_a_real_kpi(mini):
    reg, prof = mini
    prof["products"]["byd"]["consumers"]["storyboard_artist"][0]["dap_ung"] = "khong_co"
    assert any("không chỉ ra KPI đáp ứng" in b for b in run(reg, prof))


def test_kpi_needs_threshold_and_a_real_measure(mini):
    reg, prof = mini
    prof["products"]["anh"]["kpi"][0]["nguong"] = ""
    prof["products"]["byd"]["kpi"][0]["cach_do"] = "code:core/khong_co_module"
    out = run(reg, prof)
    assert any("thiếu tên / ngưỡng" in b for b in out) and any("khong_co_module" in b for b in out)


def test_not_measured_yet_is_a_gap_not_an_error(mini):
    reg, prof = mini
    prof["products"]["anh"]["kpi"][0]["cach_do"] = "chua_co:đo bằng mắt"
    assert run(reg, prof) == []
    assert any("anh.anh_dung" in g for g in crew.profile_gaps(prof, reg))


def test_outputs_profile_and_registry_must_agree(mini):
    reg, prof = mini
    reg["roles"][1]["outputs"] = ["byd", "shot_plan"]
    assert any("outputs (crew_roles)" in b for b in run(reg, prof))


def test_acceptance_must_be_a_kpi_of_own_products(mini):
    reg, prof = mini
    reg["roles"][2]["acceptance"] = ["byd_du"]                           # KPI của vai khác
    assert any("acceptance 'byd_du'" in b for b in run(reg, prof))


def test_field_of_product_belongs_to_its_producer(mini):
    reg, prof = mini
    prof["products"]["anh"]["fields"] = ["scenes.data.byd"]
    assert any("thuộc vai director" in b for b in run(reg, prof))


def test_management_chain_reaches_ep_without_loops(mini):
    reg, prof = mini
    reg["roles"][1]["reports_to"] = "storyboard_artist"
    assert any("vòng" in b for b in run(reg, prof))


def test_real_registry_profiles_are_complete_and_linked():
    assert crew.link_problems() == []
    text = crew.hoso_text()
    for r in crew.roles():
        assert f"(`{r['id']}`)" in text
    for head in ("Bạn là ai", "Vai trò", "Làm gì", "Chịu trách nhiệm", "Dưới quyền", "giám sát", "Đầu vào", "Đầu ra", "KPI", "cần:"):
        assert head in text


def test_human_page_matches_the_registry():
    """docs/HO_SO_VAI_2026-10-22.md tạo bằng `py -m core.crew hoso` — sửa hồ sơ mà quên tạo lại trang thì đỏ."""
    import os
    page = open(os.path.join(crew.ROOT, "docs", "HO_SO_VAI_2026-10-22.md"), encoding="utf-8").read()
    assert crew.hoso_text() in page
