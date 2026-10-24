"""Nhãn ảnh từ project/provider giả, không import UI hay khởi tạo adapter."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {}):
    from core import image_models
    from dashboard.image_model_label import image_provider_label


@pytest.fixture(autouse=True)
def isolated():
    with mock.patch.object(os, "environ", {}), mock.patch.object(image_models,"models",return_value={
        "fake-a":{"label":"Model A"},"fake-b":{"label":"Model B"}}):
        yield


def test_two_projects_show_selected_model_not_provider_default():
    provider=SimpleNamespace(name="deepix",supports_model=True,model="wrong-default")
    first=image_provider_label({"image_model":"fake-a"},provider)
    second=image_provider_label({"image_model":"fake-b"},provider)
    assert "fake-a" in first and "Model A" in first and "fake-b" not in first
    assert "fake-b" in second and "Model B" in second and "fake-a" not in second
    assert "deepix" in first and "wrong-default" not in first


def test_nonselectable_provider_uses_its_actual_model():
    provider=SimpleNamespace(name="fixed-fixture",supports_model=False,model="fake-b")
    label=image_provider_label({"image_model":"fake-a"},provider)
    assert "fake-b" in label and "fake-a" not in label


@pytest.mark.parametrize("provider",[None,SimpleNamespace(),SimpleNamespace(name="fixture",supports_model=False)])
def test_missing_metadata_reports_unknown(provider):
    label=image_provider_label({"image_model":"fake-a"},provider)
    assert "chưa xác định" in label and "fake-a" not in label


def test_missing_project_does_not_invent_selected_model():
    label=image_provider_label(None,SimpleNamespace(name="deepix",supports_model=True,model="fake-a"))
    assert "chưa xác định" in label and "fake-a" not in label


def test_pipeline_default_selection_is_resolved_by_shared_source():
    provider=SimpleNamespace(name="deepix",supports_model=True,model="wrong-default")
    with mock.patch.object(os,"environ",{"DEEPIX_MODEL":"fake-b"}):
        assert "fake-b" in image_provider_label({"image_model":None},provider)


def test_mock_provider_never_claims_real_api():
    label=image_provider_label({"image_model":"fake-a"},SimpleNamespace(name="mock",supports_model=False))
    assert "giả lập" in label and "API thật" not in label and "fake-a" not in label


def test_step2_both_layouts_reuse_same_label_without_importing_ui():
    source=(Path(__file__).resolve().parents[1]/"dashboard/steps/step2.py").read_text(encoding="utf-8")
    nodes=ast.walk(ast.parse(source))
    calls=[n for n in nodes if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id == "image_provider_label"]
    assert calls and all(isinstance(n.args[0],ast.Name) and n.args[0].id == "proj" for n in calls)
    assert 'f"Ảnh: {runner.provider.name}"' not in source
    assert 'f"Nhà cung cấp ảnh: {runner.provider.name}"' not in source
