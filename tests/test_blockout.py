"""Nhánh C chỉ kiểm số và chuyển props, không dùng Blender/API/dữ liệu thật."""
from copy import deepcopy

import pytest

from core import blockout as bo


def box(key="a", xy=(3, 3), size=(1, 1, 2), **kw):
    return {"id": key, "loai": "hop", "tam": list(xy), "kich_thuoc": [[v, v] for v in size],
            "nguon": "anh", "huong": 0, "mo_ta_ngan": key, **kw}


def plan(*blocks):
    return {"san": {"kich_thuoc": [20, 20], "z": 0}, "khoi": list(blocks), "loi_mo": [], "huong_sang": 90}


def test_props_translate_to_model_without_changing_legacy():
    p = plan(box())
    old = bo.to_props(p)
    result = bo.to_props(p, stage={"origin_model": [10, -20, 7]})
    assert result[0]["at"] == [13, -17, 7]
    assert old[0]["at"] == [3, 3, 0]
    assert {k: v for k, v in result[0].items() if k != "at"} == {k: v for k, v in old[0].items() if k != "at"}


def test_block_library_identity_survives_props():
    props = bo.to_props(plan(box(mo_ta_ngan="tường gỗ", vat_kho=123)))
    assert props[0]["vat_kho"] == 123


def test_valid_plan_has_no_issue():
    p = plan(box())
    assert bo.validate(p) == []
    assert bo.check_geometry(p, cho_dung=[[0, 0]], vat_kich_ban=["a"]) == []


@pytest.mark.parametrize("field,value", [("loai", "gieng"), ("tam", [1]), ("huong", float("nan")),
                                       ("kich_thuoc", [[2, 1], [1, 1], [2, 2]]),
                                       ("kich_thuoc", [[-1, 1], [1, 1], [2, 2]]),
                                       ("nguon", "doan"), ("mo_ta_ngan", "")])
def test_invalid_schema_is_red_with_path(field, value):
    b = box()
    b[field] = value
    issues = bo.validate(plan(b))
    assert any(i["muc"] == "do" and field in i["path"] and i["loi"] for i in issues)


def test_missing_fields_and_duplicate_ids_are_reported():
    assert bo.validate({})
    assert any(i["path"] == "khoi[1].id" for i in bo.validate(plan(box(), box())))
    p = plan(box())
    del p["khoi"][0]["tam"]
    assert any(i["path"] == "khoi[0].tam" for i in bo.validate(p))


def test_overlap_is_red_but_roof_on_wall_is_supported():
    assert any(i["code"] == "overlap" and i["muc"] == "do" for i in bo.check_geometry(plan(box(), box("b"))))
    wall = box("wall", (0, 0), (4, .3, 2), loai="tuong")
    roof = box("roof", (0, 0), (4, 2, .2), loai="mai", z=2)
    assert bo.check_geometry(plan(wall, roof)) == []


def test_floating_block_is_red():
    assert any(i["code"] == "floating" for i in bo.check_geometry(plan(box(z=.5))))


def test_narrow_walkway_and_standing_inside_block():
    p = plan(box("left", (-.8, 0)), box("right", (.8, 0)))
    assert any(i["code"] == "walkway" for i in bo.check_geometry(p, cho_dung=[[0, 0]]))
    assert not bo.check_geometry(p, cho_dung=[[0, 6]])
    assert any(i["code"] == "standing_blocked" for i in bo.check_geometry(p, cho_dung=[[-.8, 0]]))


def test_missing_script_object_uses_exact_unicode_match():
    p = plan(box(mo_ta_ngan="vàng"))
    assert not bo.check_geometry(p, vat_kich_ban=["vàng"])
    assert any(i["code"] == "missing_object" for i in bo.check_geometry(p, vat_kich_ban=["van"]))
    p["khoi"][0]["vat_kho"] = "263"
    assert not bo.check_geometry(p, vat_kich_ban=["263"])


def test_reference_size_deviation_is_yellow_and_missing_reference_is_not_pass():
    p = plan(box(size=(1.3, 1, 2), nguon="kho", kich_thuoc_chuan=[1, 1, 2]))
    assert any(i["code"] == "size_reference" and i["muc"] == "vang" for i in bo.check_geometry(p))
    del p["khoi"][0]["kich_thuoc_chuan"]
    assert any(i["code"] == "reference_missing" for i in bo.check_geometry(p))


def test_rotated_footprints_and_floor_limits():
    p = plan(box("a", (0, 0), (4, .2, 1), huong=45), box("b", (0, 0), (4, .2, 1), huong=-45))
    assert any(i["code"] == "overlap" for i in bo.check_geometry(p))
    assert any(i["code"] == "outside_floor" for i in bo.check_geometry(plan(box(xy=(10, 0)))))


def test_walkway_boundary_opening_and_piercing_roof():
    p = plan(box("left", (-.9, 0)), box("right", (.9, 0)))
    assert not bo.check_geometry(p, cho_dung=[[0, 0]])  # đúng 0,8 m
    p["loi_mo"] = [{"tam": [-.9, 0], "kich_thuoc": [1, 1]}]
    assert any(i["code"] == "opening_blocked" for i in bo.check_geometry(p))
    roof = box("roof", (0, 0), (4, 2, .2), loai="mai", z=1)
    wall = box("wall", (0, 0), (4, .3, 2), loai="tuong")
    assert any(i["code"] == "overlap" for i in bo.check_geometry(plan(wall, roof)))


@pytest.mark.parametrize("bad", [None, [], {"san": []}, plan(None)])
def test_malformed_input_reports_issues_instead_of_crashing(bad):
    assert bo.validate(bad)
    assert bo.check_geometry(bad)


def test_to_props_preserves_dimensions_rotation_and_source_without_mutating():
    p = plan(box(huong=30, kich_thuoc=[[1, 3], [2, 4], [3, 5]]))
    before = deepcopy(p)
    props = bo.to_props(p)
    assert props == [{"kind": "block", "id": "a", "shape": "box", "at": [3, 3, 0], "size": [2, 3, 4],
                      "rotation_deg": 30, "label": "a", "source": "anh", "stand_in": True}]
    assert p == before
    with pytest.raises(ValueError, match="khoi"):
        bo.to_props(plan(box(loai="invalid")))


def _render_add_props():
    """Nạp CHÍNH hàm add_props bằng AST, mock bpy; không import script hay mở Blender."""
    import ast
    import math
    from pathlib import Path
    from types import SimpleNamespace as NS
    tree = ast.parse((Path(__file__).resolve().parents[1] / "tools/render_plates.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "add_props")
    made, ops = [], []

    class Obj(dict):
        pass

    ctx = NS(active_object=None)

    def primitive(kind, **kw):
        ob = Obj()
        ob.data = NS(materials=[])
        ob.rotation_euler = [0, 0, 0]
        ob.location = kw["location"]
        ctx.active_object = ob
        made.append(ob)
        ops.append((kind, kw))

    def material(name):
        inputs = {k: NS(default_value=None) for k in ("Base Color", "Roughness")}
        return NS(use_nodes=False, node_tree=NS(nodes={"Principled BSDF": NS(inputs=inputs)}))

    bpy = NS(context=ctx, ops=NS(mesh=NS(primitive_cube_add=lambda **kw: primitive("box", **kw),
                                       primitive_cylinder_add=lambda **kw: primitive("cylinder", **kw))),
             data=NS(materials=NS(new=material)))
    ns = {"bpy": bpy, "math": math}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "add_props-under-test", "exec"), ns)
    return ns["add_props"], made, ops


@pytest.mark.parametrize("kind,shape", [("hop", "box"), ("cot", "cylinder"), ("tru", "cylinder")])
def test_props_are_actually_consumed_by_add_props(kind, shape):
    add_props, made, ops = _render_add_props()
    props = bo.to_props(plan(box(loai=kind, huong=30)))
    result = add_props(props)
    assert len(result) == len(made) == 1  # bản cũ bỏ qua kind=block
    assert ops[0][0] == shape
    assert made[0].location == (3, 3, 1)
    assert list(made[0].dimensions) == [1, 1, 2]
    assert made[0].rotation_euler[2] == pytest.approx(.5235987756)
    assert made[0]["stand_in"] is True and made[0]["label"] == "a"


def test_add_props_keeps_existing_well_and_rejects_bad_blocks():
    add_props, made, ops = _render_add_props()
    assert len(add_props([{"kind": "well", "at": [0, 0, 0], "radius": .75, "height": .9}])) == 2
    assert all(kind == "cylinder" for kind, _ in ops)
    with pytest.raises(ValueError, match="block"):
        add_props([{"kind": "block", "size": [-1, 1, 1]}])


from tests import golden

GOLDEN = [c for c in golden.load_cases() if "blockout" in (c.get("ky_vong") or {})]


@pytest.mark.parametrize("case", GOLDEN, ids=lambda c: c["id"])
def test_blockout_golden(case):
    expected = case["ky_vong"]["blockout"]
    issues = bo.check_geometry(expected["plan"], expected.get("cho_dung"), expected.get("vat_kich_ban"))
    assert expected["codes"] == sorted({i["code"] for i in issues})
    assert all(i["muc"] == "do" for i in issues)
    assert not golden.problems(case)
