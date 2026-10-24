"""Biến lựa chọn Dashboard thành JSON N4, không import Streamlit/runtime."""
import copy
import ast
import json
import os
from pathlib import Path
from unittest import mock

import pytest

with mock.patch.object(os,"environ",{}):
    from dashboard.stage_camera_controls import apply_camera_controls, answer_specs


@pytest.fixture(autouse=True)
def isolated():
    with mock.patch.object(os,"environ",{}):
        yield


def test_controls_only_copy_requested_side_and_auxiliary_minimum():
    answer={"shot_specs":[{"shot":1,"co":"WS","thanh_phan":[{"vat":"a","vai":"chinh"},{"vat":"b","vai":"phu"}]}]}
    before=copy.deepcopy(answer)
    result=apply_camera_controls(answer,{1:{"camera_side":"left","minimums":{"b":70}}})
    assert answer == before
    assert result["shot_specs"][0]["camera_side"] == "left"
    assert result["shot_specs"][0]["thanh_phan"][1]["thay_min"] == 70
    assert result["shot_specs"][0]["co"] == "WS"


def test_review_controls_only_apply_to_explicit_sua_may_spec():
    answer={"shots":[{"shot":1,"ket_luan":"sua_may","shot_spec":{"shot":1,"thanh_phan":[]}},
                     {"shot":2,"ket_luan":"khop"}]}
    assert [s["shot"] for s in answer_specs(answer)] == [1]
    result=apply_camera_controls(answer,{1:{"camera_side":"front"}})
    assert result["shots"][0]["shot_spec"]["camera_side"] == "front"
    assert result["shots"][1] == answer["shots"][1]


@pytest.mark.parametrize("changes",[{99:{"camera_side":"front"}},{1:{"camera_side":"invented"}},
                                  {1:{"minimums":{"absent":50}}},{1:{"minimums":{"b":float("nan")}}}])
def test_stale_or_invalid_selection_cannot_be_silently_applied(changes):
    with pytest.raises(ValueError):
        apply_camera_controls({"shot_specs":[{"shot":1,"thanh_phan":[{"vat":"b","vai":"phu"}]}]},changes)


def test_no_selection_preserves_json_contract():
    answer={"blocking":{"axis":["a","b"]},"shot_specs":[{"shot":1,"camera_side":"right","thanh_phan":[]}]}
    assert apply_camera_controls(answer,{}) == answer


class FakeControls:
    def caption(self,*args,**kwargs): pass
    def selectbox(self,*args,**kwargs): return "left"
    def checkbox(self,*args,**kwargs): return True
    def number_input(self,*args,**kwargs): return 70.0


def controls_function(fake=None):
    source=(Path(__file__).resolve().parents[1]/"dashboard/stage_desk_ui.py").read_text(encoding="utf-8")
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name == "_camera_controls")
    namespace={"json":json,"st":fake or FakeControls()}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),"camera_controls_fixture","exec"),namespace)
    return namespace["_camera_controls"]


def test_mock_widget_choices_are_applied_through_answer_copy():
    answer={"shot_specs":[{"shot":1,"thanh_phan":[{"vat":"b","vai":"phu"}]}]}
    choices=controls_function()(json.dumps(answer),"fixture",False)
    assert choices == {1:{"camera_side":"left","minimums":{"b":70.0}}}
    assert apply_camera_controls(answer,choices)["shot_specs"][0]["camera_side"] == "left"


@pytest.mark.parametrize("answer",[{"shots":None},{"shot_specs":[{"shot":1},{"shot":1}]},
                                  {"shot_specs":[{"shot":1,"thanh_phan":[{"vat":"b","vai":"phu"},{"vat":"b","vai":"phu"}]}]}])
def test_invalid_preview_never_renders_duplicate_widget_keys(answer):
    assert controls_function()(json.dumps(answer),"fixture",False) == {}


class StatefulControls(FakeControls):
    def __init__(self):
        self.state={}
        self.keys=[]
    def selectbox(self,*args,**kwargs):
        self.keys.append(kwargs["key"])
        return self.state.get(kwargs["key"])
    def checkbox(self,*args,**kwargs):
        self.keys.append(kwargs["key"])
        return self.state.get(kwargs["key"],False)
    def number_input(self,*args,**kwargs):
        self.keys.append(kwargs["key"])
        return self.state.get(kwargs["key"],kwargs["value"])


def test_changed_json_never_reuses_old_side_or_minimum():
    a={"shot_specs":[{"shot":1,"camera_side":"back","thanh_phan":[{"vat":"b","vai":"phu","thay_min":25}]}]}
    fake=StatefulControls(); controls=controls_function(fake)
    assert controls(json.dumps(a),"fixture",False) == {}
    for key in fake.keys:
        fake.state[key] = "front" if "_camera_side_" in key else True
    selected=controls(json.dumps(a),"fixture",False)
    number_key=next(k for k in fake.keys if "_min_1_b" in k)
    fake.state[number_key]=70.0
    assert controls(json.dumps(a),"fixture",False)[1]["minimums"]["b"] == 70
    b=copy.deepcopy(a); b["shot_specs"][0]["camera_side"]="right"
    b["shot_specs"][0]["thanh_phan"][0]["thay_min"]=20
    assert controls(json.dumps(b),"fixture",False) == {}
    assert apply_camera_controls(b,{}) == b


def test_whitespace_and_key_order_keep_same_semantic_widget_namespace():
    fake=StatefulControls(); controls=controls_function(fake)
    raw='{"shot_specs":[{"shot":1,"thanh_phan":[{"vat":"b","vai":"phu"}]}]}'
    controls(raw,"fixture",False)
    first=list(fake.keys); fake.keys=[]
    equivalent=' { "shot_specs": [ { "thanh_phan": [{"vai":"phu","vat":"b"}], "shot": 1 } ] } '
    controls(equivalent,"fixture",False)
    assert fake.keys == first


@pytest.mark.parametrize("container",[None,{},"invalid"])
def test_direct_helper_reports_malformed_component_container(container):
    with pytest.raises(ValueError):
        apply_camera_controls({"shot_specs":[{"shot":1,"thanh_phan":container}]},{1:{"minimums":{"b":70}}})
