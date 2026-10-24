"""Ràng buộc phía máy và vật phụ: hình học thuần, không UI/Blender/model."""
import math
import os
from unittest import mock

import pytest

with mock.patch.object(os,"environ",{}):
    from core import stage_grid as sg, stage_solver as ss


@pytest.fixture(autouse=True)
def isolated(tmp_path):
    with mock.patch.object(os,"environ",{"HOME":str(tmp_path),"USERPROFILE":str(tmp_path)}):
        yield


@pytest.mark.parametrize("side,point",[("front",[0,5,1]),("back",[0,-5,1]),("left",[-5,0,1]),("right",[5,0,1])])
def test_side_uses_directed_axis_without_changing_left_right(side,point):
    axis=[[0,-1,0],[0,1,0]]
    assert sg.camera_side_error(axis,point,side) is None
    assert sg.camera_side_error(axis,[-point[0],-point[1],1],side)
    if side in ("left","right"):
        assert sg.axis_side(*axis,point) == side


@pytest.mark.parametrize("angle",[0,45,135,270])
def test_rotating_and_translating_axis_preserves_local_side(angle):
    a=math.radians(angle)
    def move(p):
        return [12+p[0]*math.cos(a)-p[1]*math.sin(a),-7+p[0]*math.sin(a)+p[1]*math.cos(a),p[2]]
    axis=[move([0,-1,0]),move([0,1,0])]
    assert sg.camera_side_error(axis,move([0,5,1]),"front") is None
    assert sg.camera_side_error(axis,move([-5,0,1]),"left") is None


@pytest.mark.parametrize("axis",[None,[[0,0,0],[0,0,0]]])
def test_selected_side_requires_real_axis(axis):
    objects=ss.objects_from_blocking({"objects":[{"key":"a","kind":"nguoi","at":[0,0],"H":1.7,"facing":0}]})
    result=ss.solve_shot({"co":"WS","camera_side":"front","thanh_phan":[{"vat":"a","vai":"chinh"}]},objects,9/16,axis=axis)
    assert result["errors"] and not result["cams"]
    assert any("trục" in e for e in result["errors"])


def test_user_selected_side_seeds_camera_without_guessing_view():
    objects=ss.objects_from_blocking({"objects":[{"key":"a","kind":"nguoi","at":[0,0],"H":1.7,"facing":0}]})
    result=ss.solve_shot({"co":"WS","camera_side":"left","thanh_phan":[{"vat":"a","vai":"chinh"}]},objects,9/16,
                         axis=[[0,-1,0],[0,1,0]],fallback=False)
    assert not result["errors"] and result["cams"]
    assert any(c["check"]["ok"] and c["at"][0] < 0 for c in result["cams"])


def test_measured_check_cannot_pass_wrong_side():
    result=sg.check_spec({"at":[4,0,1]}, {"camera_side":"left","thanh_phan":[]},{},axis=[[0,-1,0],[0,1,0]])
    assert not result["ok"] and "C2" in result["fail"]


@pytest.mark.parametrize("seen,expected",[(24,False),(25,True),(90,True)])
def test_auxiliary_minimum_is_a_constraint(seen,expected):
    result=sg.check_spec({"obj":{"b":{"seen_pct":seen,"uv":[.5,.5]}}},
                         {"thanh_phan":[{"vat":"b","vai":"phu","thay_min":25}]},{"b":{"kind":"dao_cu"}})
    assert result["ok"] is expected
    assert ("S1" in result["fail"]) is (not expected)


def test_auxiliary_without_explicit_min_keeps_soft_behavior():
    result=sg.check_spec({"obj":{"b":{"seen_pct":0}}},{"thanh_phan":[{"vat":"b","vai":"phu"}]},{"b":{"kind":"dao_cu"}})
    assert result["ok"] and result["phu"]["b"] is False


@pytest.mark.parametrize("value",[-1,101,float("nan"),True,"invalid"])
def test_invalid_minimum_is_rejected_by_solver(value):
    objects={"a":{"kind":"nguoi","xy":[0,0],"H":1.7},"b":{"kind":"dao_cu","xy":[1,0],"h":1}}
    errors=ss.validate({"co":"WS","thanh_phan":[{"vat":"a","vai":"chinh"},{"vat":"b","vai":"phu","thay_min":value}]},objects)
    assert errors
