import importlib.util
import json
import os
import socket
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(params=[{}, {"ANTHROPIC_API_KEY": "gia-lap"}])
def audit(request, monkeypatch):
    # Thay toàn bộ env trước import; tự khôi phục khi rời context.
    with patch.object(os, "environ", dict(request.param)):
        monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Cấm mạng"))
        for name in ("transformers", "onnxruntime", "core.db", "core.providers", "core.credentials", "core.registry"):
            monkeypatch.setitem(sys.modules, name, None)
        spec = importlib.util.spec_from_file_location("audit_offline", Path(__file__).parents[1] / "tools/audio_mood_audit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


def fixture(labels, rows=None, complete=False):
    return {"labels": labels, "windows": rows or [], "complete_scores": complete}


def test_full_labels_zero_valid(audit):
    labels = list(audit.MOODS)
    result = audit.analyse(fixture(labels, [[{"label": label, "score": 0} for label in labels]], True))
    assert result["covered_moods"] == 7
    assert result["candidates"] == 0
    assert result["below_threshold_windows"] == 1
    assert result["unobserved_mood_scores"] == 0


def test_candidate_counts_and_not_covered(audit):
    result = audit.analyse(fixture(["Music", "Scary music"], [[{"label": "Scary music", "score": .1}]]))
    assert result["candidates"] == 1
    assert result["not_covered"] == 6
    assert result["candidate_counts"]["Scary music"] == 1


def test_mismatch_not_ontology_absence(audit):
    result = audit.analyse(fixture(["sad music"], [[{"label": "sad music", "score": .9}]]))
    assert result["case_mismatch_moods"] == 1
    assert result["ontology_has_no_mood"] is False
    assert result["candidates"] == 0


def test_truncated_scores_not_zero(audit):
    result = audit.analyse(fixture(["Music", "Sad music"], [[{"label": "Music", "score": .9}]]))
    assert result["unobserved_mood_scores"] == 1
    assert result["below_threshold_windows"] == 0
    assert result["truncated_windows"] == 1


@pytest.mark.parametrize("payload", [{}, {"labels": []}, {"labels": ["Music"], "windows": [[{"label": "Other", "score": .2}]]}, {"labels": ["Music"], "windows": [[{"label": "Music"}]]}, {"labels": ["Music"], "windows": [[{"label": "Music", "score": True}]]}, {"labels": ["Music"], "windows": [[{"label": "Music", "score": float("nan")}]]}, {"labels": ["Music", "Sad music"], "windows": [[{"label": "Music", "score": .2}]], "complete_scores": True}])
def test_invalid_explicit(audit, payload):
    with pytest.raises(ValueError):
        audit.analyse(payload)


def test_csv_and_cli_readonly_no_path_echo(audit, tmp_path, capsys):
    ontology = tmp_path / "ontology.csv"
    ontology.write_text('index,mid,display_name\n0,/m/a,Music\n1,/m/b,Sad music\n', encoding="utf-8")
    source = tmp_path / "private-name.json"
    source.write_text(json.dumps({"windows": [[{"label": "Sad music", "score": .1}]]}), encoding="utf-8")
    assert audit.main(["--input", str(source), "--ontology", str(ontology)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["candidates"] == 1
    assert set(out) == set(audit.analyse(fixture(["Music", "Sad music"])))
    assert audit.main(["--input", str(tmp_path / "missing-private.json")]) == 2
    assert capsys.readouterr().err.strip() == "Không đọc được đầu vào JSON/CSV; kiểm tra file và định dạng."


def test_no_mood_and_no_scores_distinct(audit):
    result = audit.analyse(fixture(["Music"]))
    assert result["ontology_has_no_mood"] is True
    assert result["windows"] == 0
    result = audit.analyse(fixture(["Sad music"]))
    assert result["ontology_has_no_mood"] is False
    assert result["windows"] == 0
