"""V3.1 M6.1 (C-M61-M69): Role Registry CHỈ ĐỌC — data/crew_roles.json + core/crew.py. Sổ v31-ep-m6-pack-a-approved-2026-10-21.
Kiểm: schema đủ trường (kế hoạch M6 mục 2a), mỗi trường đúng MỘT vai chủ, writes ⊂ trường thật, owns_errors.stages ⊂ devsys/stages.json,
claude_stage là nhãn sổ chi có thật, tra cứu (vai của một đường ghi W1–W38, đường Kỹ sư K1–K16, lỗi gốc → vai chủ), module không ghi gì."""
import copy
import inspect
import json
import os
from unittest import mock

from core import crew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ON = mock.patch.dict(os.environ, {"FEATURE_CREW_REGISTRY": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_CREW_REGISTRY": ""})


def test_flag_registered_off_and_unverified():
    from core import features
    assert crew.FLAG == "crew_registry" and features.FEATURES[crew.FLAG]["verified"] is False
    with OFF:
        assert not crew.enabled()
        assert crew.active() is None                     # cờ TẮT: đường chạy (validator) không nhận registry


def test_flag_on_gives_the_registry():
    with ON:
        reg = crew.active()
    assert reg and reg["version"] == 1


def test_registered_in_areas_and_golden():
    areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    a = next(x for x in areas["areas"] if "core/crew.py" in x["code"])
    assert "tests/test_v31_m61_crew_registry.py" in a["tests"] and crew.FLAG in a["flags"]
    gold = json.load(open(os.path.join(ROOT, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
    blocks = [v["flags"] for v in gold.values() if isinstance(v, dict) and isinstance(v.get("flags"), dict)]
    assert len(blocks) == 2 and all(b.get(crew.FLAG) is False for b in blocks)


def test_real_registry_has_no_problems():
    assert crew.problems() == []


def test_cli_check_is_green(capsys):
    assert crew.main(["check"]) == 0
    assert "0 lỗi" in capsys.readouterr().out


def test_every_role_has_the_required_fields():
    for r in crew.roles():
        missing = [k for k in crew.REQUIRED if k not in r]
        assert not missing, (r.get("id"), missing)


def test_all_plan_roles_present():
    ids = {r["id"] for r in crew.roles()}
    assert {"executive_producer", "director", "scriptwriter", "cinematographer", "artist_3d", "storyboard_artist", "video_prompt_artist",
            "sound_designer", "editor_vfx", "continuity_validator", "engineer"} <= ids


def test_each_field_has_exactly_one_owner_and_owner_lists_it():
    reg = crew.load()
    for field, meta in reg["fields"].items():
        owners = [r["id"] for r in reg["roles"] if field in r["writes"]]
        assert owners == [meta["owner"]], (field, owners)


def test_ownership_table_of_the_plan():
    assert crew.owner_of("motion_prompts.motion_prompt") == "video_prompt_artist"
    assert crew.owner_of("scenes.data.end_state") == "director"            # VPA chỉ đọc end_state (mục 2a)
    assert crew.owner_of("scenes.data.lens_mm") == "cinematographer"
    assert crew.owner_of("scenes.data.stage_camera") == "artist_3d"
    assert crew.owner_of("scenes.data.image_prompt") == "storyboard_artist"
    assert crew.owner_of("scenes.data.byd") == "director"
    assert crew.owner_of("khong.co.truong") is None


def test_can_write():
    assert crew.can_write("video_prompt_artist", "motion_prompts.motion_prompt")
    assert not crew.can_write("video_prompt_artist", "scenes.data.end_state")
    assert not crew.can_write("engineer", "scenes.data.byd")              # Kỹ sư không ghi nội dung production
    assert not crew.can_write("continuity_validator", "scenes.data.image_prompt")
    assert crew.can_write("executive_producer", "scenes.data.byd")        # EP sửa được mọi thứ (quyền 1b)
    assert not crew.can_write("khong_co_vai", "scenes.data.byd")


def test_problems_catch_two_owners_and_unknown_field():
    reg = copy.deepcopy(crew.load())
    vpa = next(r for r in reg["roles"] if r["id"] == "video_prompt_artist")
    vpa["writes"].append("scenes.data.byd")                                # trường của Director
    vpa["writes"].append("scenes.data.khong_ton_tai_xyz")
    out = "\n".join(crew.problems(reg))
    assert "scenes.data.byd" in out and "scenes.data.khong_ton_tai_xyz" in out


def test_problems_catch_unknown_stage_claude_stage_and_missing_field():
    reg = copy.deepcopy(crew.load())
    r = next(r for r in reg["roles"] if r["id"] == "sound_designer")
    r["owns_errors"]["stages"].append("L99")
    r["claude_stage"].append("khong_co_khau")
    del r["acceptance"]
    out = "\n".join(crew.problems(reg))
    assert "L99" in out and "khong_co_khau" in out and "acceptance" in out


def test_problems_catch_validator_owning_errors_and_unowned_stage():
    reg = copy.deepcopy(crew.load())
    cv = next(r for r in reg["roles"] if r["id"] == "continuity_validator")
    cv["owns_errors"]["stages"].append("L13")                                # QC độc lập: vai kiểm không đứng tên lỗi
    out = "\n".join(crew.problems(reg))
    assert "continuity_validator" in out
    reg = copy.deepcopy(crew.load())
    for r in reg["roles"]:
        if "L6" in r["owns_errors"]["stages"]:
            r["owns_errors"]["stages"].remove("L6")
    assert any("L6" in x for x in crew.problems(reg))


def test_every_devsys_stage_has_one_owner():
    stages = [s["id"] for s in json.load(open(os.path.join(ROOT, "devsys", "stages.json"), encoding="utf-8"))["stages"]]
    for s in stages:
        owners = [r["id"] for r in crew.roles() if s in r["owns_errors"]["stages"]]
        assert len(owners) == 1, (s, owners)


def test_role_of_write_paths_w1_w38():
    reg = crew.load()
    assert [w["id"] for w in reg["write_paths"]] == [f"W{i}" for i in range(1, 39)]
    assert crew.role_of_write("core/camera_plan.py:apply")["role"] == "cinematographer"
    assert crew.role_of_write("camera_plan.apply")["id"] == "W7"
    assert crew.role_of_write("W16")["role"] == "video_prompt_artist"
    assert crew.role_of_write("core/llm_io.py:store_motion_prompts")["id"] == "W3"
    assert crew.role_of_write("core/khong_co.py:x") is None


def test_engineer_paths_k1_k16_readable_for_q1_q3():
    ks = crew.engineer_paths()
    assert [k["id"] for k in ks] == [f"K{i}" for i in range(1, 17)]
    assert all(k["decision"] and k["where"] and k["level"] in ("cao", "trung_binh", "thap") for k in ks)
    assert {k["id"] for k in ks if k["level"] == "cao"} == {"K1", "K2", "K3", "K4", "K5", "K7", "K13", "K14"}
    k3 = next(k for k in ks if k["id"] == "K3")
    assert k3["acts_as_user"] is True                                       # Q3: CLI giả "user"


def test_job_insert_points_for_q2():
    pts = crew.load()["job_insert_points"]
    assert "core/pipeline.py" in pts and "tools/redraw_compare.py" in pts and len(pts) == 5


def test_owner_of_error_by_registry_stage_category_and_code():
    assert crew.owner_of_error(registry_ids=["P31-G1"])["owner"] == "artist_3d"           # stage L6
    r = crew.owner_of_error(registry_ids=["P31-G51", "P31-G52"])
    assert r["owner"] == "video_prompt_artist" and r["via"].startswith("stage:L13")
    assert crew.owner_of_error(registry_ids=["P31-G3"])["owner"] == "cinematographer"      # category may
    assert crew.owner_of_error(registry_ids=["P31-G33"])["owner"] == "engineer"            # provider: hết tiền API → Kỹ sư
    assert crew.owner_of_error(qc_code="QC-L9-HORIZON_MISMATCH")["owner"] == "cinematographer"
    assert crew.owner_of_error(qc_code="QC-V3-LIP_SYNC")["owner"] == "sound_designer"
    fb = crew.owner_of_error(registry_ids=["KHONG-CO"])
    assert fb["owner"] == "director" and fb["via"] == "fallback"                           # không rõ → Director phân công


def test_module_is_read_only():
    src = inspect.getsource(crew)
    for bad in ("open(path, \"w\"", "'w'", "\"w\"", "\"a\"", ".write(", "json.dump(", "execute(", "os.makedirs"):
        assert bad not in src, bad


# ---- rà C-M61-M69 (VỪA-3, THẤP) ------------------------------------------------------------------------------------------------------
def test_every_error_item_and_qc_code_has_a_role():
    assert not [p for p in crew.problems() if "không vai nào nhận" in p]


def test_problems_catch_error_item_no_role_takes():
    errs = [{"id": "X-NEW-1", "stage": None, "category": "loai_moi_chua_gan"}]
    out = "\n".join(crew.problems(errors=errs))
    assert "X-NEW-1" in out and "không vai nào nhận" in out


def test_problems_catch_qc_code_no_role_takes():
    reg = copy.deepcopy(crew.load())
    for r in reg["roles"]:
        r["owns_errors"]["codes"] = [c for c in r["owns_errors"]["codes"] if c != "QC-V1-DRIFT"]
    assert any("QC-V1-DRIFT" in p and "không vai nào nhận" in p for p in crew.problems(reg))


def test_fallback_says_so():
    fb = crew.owner_of_error(registry_ids=["KHONG-CO"])
    assert fb["via"] == "fallback" and "không vai nào nhận" in fb["note"]


def test_problems_use_the_given_root_and_say_empty_sources(tmp_path):
    out = "\n".join(crew.problems(root=str(tmp_path)))
    assert "core/db.py" in out and "devsys/stages.json" in out          # nguồn kiểm rỗng → báo, không bỏ qua im lặng


def test_audit_paths_completed():
    w = {x["id"]: x for x in crew.load()["write_paths"]}
    assert "core/claude_tasks.py:dismiss_bible_flag" in w["W32"]["where"] and "core/subjects.py:unlink" in w["W32"]["where"]
    assert "core/assets.py:set_outfit" in w["W32"]["where"]
    assert "dashboard/steps/step1.py:reset_unworked_scenes" in w["W20"]["where"]
    assert "scenes.data.spatial_state" in w["W3"]["fields"]
