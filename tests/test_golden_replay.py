"""Đ20: fixture tổng hợp, không nạp provider hay dữ liệu máy chính."""
import hashlib
import ast
import importlib
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def golden(tmp_path):
    with patch.object(os, "environ", {}):
        module = importlib.import_module("tools.golden_capture")
        db = tmp_path / "synthetic.sqlite"
        conn = sqlite3.connect(db)
        tree = ast.parse((Path(__file__).resolve().parents[1] / "core/db.py").read_text(encoding="utf-8"))
        schema = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "SCHEMA" for target in node.targets))
        conn.executescript(schema)
        for column in ("model", "quality_tier", "sent_package"):
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} TEXT")
        ref = tmp_path / "ref.bin"
        ref.write_bytes(b"synthetic")
        package = {"v": 1, "prompt": "chữ gốc", "negative": None, "refs": [
            {"param": "references", "role": "cast", "path": "ref.bin", "sha256": hashlib.sha256(b"synthetic").hexdigest()}],
            "provider": "fake", "model": "fake-image", "params": {}, "external_id": "fixture", "at": "2026-10-20"}
        raw = json.dumps(package, ensure_ascii=False)
        for i, kind in enumerate(("image_gen", "video_gen"), 1):
            conn.execute("INSERT INTO jobs (id,project_id,scene_id,type,state,model,quality_tier,sent_package,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (i, 24, 7, kind, "succeeded", "fake-image", "draft", raw, "2026-10-20", "2026-10-20"))
        conn.commit()
        conn.close()
        flags = tmp_path / "flags.json"
        flags.write_text('{"new_feature": false}', encoding="utf-8")
        yield module, db, flags, tmp_path, raw


def capture(golden):
    module, db, flags, root, _ = golden
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        return module.capture(db=db, project=24, shot=7, flags_file=flags, ref_root=root, purpose="compat")


def test_capture_preserves_bytes_order_hash_and_readonly(golden):
    module, db, _, _, raw = golden
    before = db.read_bytes()
    result = capture(golden)
    assert db.read_bytes() == before
    assert len(result["jobs"]) == 2
    assert result["jobs"][0]["sent_package_raw"] == raw
    assert result["jobs"][0]["refs"][0]["hash_status"] == "match"
    assert result["head_sha"] == "a" * 40
    assert result["flags"] == {"new_feature": False}
    assert result["schema"]["user_version"] == 0
    assert result["replay_status"] == "OPEN"


def test_one_byte_divergence_and_correctness_separate(golden):
    module = golden[0]
    with patch.object(os, "environ", {}):
        module.compare_compat(b"abc", b"abc")
        with pytest.raises(module.GoldenError, match="COMPAT"):
            module.compare_compat(b"abc", b"abd")


@pytest.mark.parametrize("field", ["prompt", "provider", "model", "refs", "v"])
def test_missing_field_is_explicit(golden, field):
    module, db, _, _, raw = golden
    package = json.loads(raw)
    del package[field]
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE jobs SET sent_package=?", (json.dumps(package),))
    with pytest.raises(module.GoldenError, match=field):
        capture(golden)


def test_missing_file_and_escape_are_reported(golden):
    _, _, _, root, _ = golden
    (root / "ref.bin").unlink()
    assert capture(golden)["jobs"][0]["refs"][0]["hash_status"] == "missing"


def test_running_jobs_warn_snapshot(golden):
    with sqlite3.connect(golden[1]) as conn:
        conn.execute("UPDATE jobs SET state='running'")
    assert any("snapshot" in item for item in capture(golden)["warnings"])


def test_flags_required_and_compat_off(golden):
    module, _, flags, _, _ = golden
    flags.write_text('{"new_feature": true}', encoding="utf-8")
    with pytest.raises(module.GoldenError, match="COMPAT"):
        capture(golden)


def test_ref_outside_scope_and_url_never_read(golden):
    _, db, _, _, raw = golden
    package = json.loads(raw)
    package["refs"][0]["path"] = "../outside.bin"
    package["refs"].append({"path": "https://example.invalid/ref", "sha256": None})
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE jobs SET sent_package=?", (json.dumps(package),))
    refs = capture(golden)["jobs"][0]["refs"]
    assert [r["hash_status"] for r in refs] == ["outside_scope", "remote_not_fetched"]


def test_missing_table_clear_error(golden):
    module = golden[0]
    with sqlite3.connect(golden[1]) as conn:
        conn.execute("DROP TABLE jobs")
    with pytest.raises(module.GoldenError, match="jobs"):
        capture(golden)

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_package_rejected_before_output(golden, value):
    module, db, flags, root, raw = golden
    package = json.loads(raw)
    package["params"]["duration"] = value
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE jobs SET sent_package=?", (json.dumps(package),))
    output = root / "invalid.json"
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        with pytest.raises(SystemExit):
            module.main(["--db", str(db), "--project", "24", "--shot", "7", "--flags-file", str(flags),
                         "--ref-root", str(root), "--purpose", "compat", "--output", str(output)])
    assert not output.exists()


def test_url_credentials_rejected(golden):
    module, db, _, _, raw = golden
    package = json.loads(raw)
    package["refs"][0]["path"] = "https://fake-user:fake-pass@example.invalid/ref"
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE jobs SET sent_package=?", (json.dumps(package),))
    with pytest.raises(module.GoldenError):
        capture(golden)


def test_output_cannot_overwrite_database(golden):
    module, db, flags, root, _ = golden
    before = db.read_bytes()
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        with pytest.raises(SystemExit):
            module.main(["--db", str(db), "--project", "24", "--shot", "7", "--flags-file", str(flags),
                         "--ref-root", str(root), "--purpose", "compat", "--output", str(db)])
    assert db.read_bytes() == before

@pytest.mark.parametrize("kind", ["image", "video"])
@pytest.mark.parametrize("provider", ["fake", "clipai", "deepix"])
def test_current_builder_frozen_input_replay(kind, provider, tmp_path):
    with patch.object(os, "environ", {}):
        module = importlib.import_module("tools.golden_capture")
        snapshot = json.loads((Path(__file__).parent / "golden" / "package_inputs.json").read_text(encoding="utf-8"))[kind]
        snapshot["provider"] = provider
        snapshot["baseline"] = snapshot["baseline"].replace('"provider": "fake"', '"provider": "' + provider + '"')
        (tmp_path / "ref.bin").write_bytes(b"synthetic")
        actual = module.replay_builder(snapshot, ref_root=tmp_path)
        module.compare_compat(snapshot["baseline"].encode("utf-8"), actual)
        changed = json.loads(json.dumps(snapshot))
        changed["args"][0 if kind == "image" else 1] += "!"
        with pytest.raises(module.GoldenError, match="COMPAT"):
            module.compare_compat(snapshot["baseline"].encode("utf-8"), module.replay_builder(changed, ref_root=tmp_path))
        assert module.check_correctness(actual, {"prompt_contains": ["chữ gốc"], "ref_roles": snapshot.get("correctness_roles", ["cast"])}) == []
        assert module.check_correctness(actual, {"prompt_contains": ["không tồn tại"], "ref_roles": snapshot.get("correctness_roles", ["cast"])}) == ["prompt_contains"]


def test_replay_missing_snapshot_field_and_ref(tmp_path):
    with patch.object(os, "environ", {}):
        module = importlib.import_module("tools.golden_capture")
        with pytest.raises(module.GoldenError, match="snapshot thiếu"):
            module.replay_builder({}, ref_root=tmp_path)
        snapshot = json.loads((Path(__file__).parent / "golden" / "package_inputs.json").read_text(encoding="utf-8"))["image"]
        with pytest.raises(module.GoldenError, match="ref"):
            module.replay_builder(snapshot, ref_root=tmp_path)


def test_capture_attaches_explicit_input_sidecar(golden):
    module, db, flags, root, _ = golden
    sidecar = root / "inputs.json"
    sidecar.write_text('{"1": {"provenance": "pre_send_snapshot"}}', encoding="utf-8")
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        result = module.capture(db=db, project=24, shot=7, flags_file=flags, ref_root=root, purpose="compat", input_snapshots_file=sidecar)
    assert result["jobs"][0]["input_snapshot"] == {"provenance": "pre_send_snapshot"}
    assert result["jobs"][1]["input_snapshot"] is None

@pytest.mark.parametrize("field", ["passwd", "access_key", "auth_session"])
def test_sidecar_rejects_credential_fields_before_output(golden, field):
    module, db, flags, root, _ = golden
    sidecar = root / "inputs.json"
    sidecar.write_text(json.dumps({"1": {"kwargs": {field: "synthetic-value"}}}), encoding="utf-8")
    output = root / "credential-fixture.json"
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        with pytest.raises(SystemExit):
            module.main(["--db", str(db), "--project", "24", "--shot", "7", "--flags-file", str(flags),
                         "--ref-root", str(root), "--purpose", "compat", "--input-snapshots-file", str(sidecar),
                         "--output", str(output)])
    assert not output.exists()
