"""C-GOLDEN4 (cloud-E 21/10): nghiệm thu golden lần 3 vẫn KHÔNG ĐẠT vì công cụ (60/68 ca worker bị chặn đọc data/skills, 4 ca chuỗi
source_job_id, replay_fixture đổi DATA_CHANGED của capture thành INSUFFICIENT_INPUT). Sửa gốc: worker ĐỌC mọi tệp dưới data/ của ref-root
(chỉ đọc, mỗi lần đọc vào manifest có sha) trừ danh sách cấm cứng; replay giữ DATA_CHANGED; chuỗi source_job_id đứt in id + chỗ đứt.
Phần thuần chạy ở mọi máy; phần gọi _worker cần native Python 3.14 (như tests/test_golden_db_replay.py)."""
import importlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_golden_db_replay import database, needs_native_314  # noqa: F401  (fixture CSDL + tệp tổng hợp)
from tests.test_golden_replay import golden  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def _replay_module():
    with patch.object(os, "environ", {}):
        return importlib.import_module("tools.golden_db_replay")


# ---- danh sách cấm cứng ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["data/manifest.sqlite", "data/manifest.sqlite-wal", "data/other.db", "dashboard.env", "data/dashboard.env",
                                  "data/.env", "data/x.env", "data/backup/feature_settings.json", "data/backup", "data/keys/api.pem",
                                  "data/secrets.json", "data/claude_credentials.json", "data/token.txt",
                                  # rà C-GOLDEN4 VỪA-1: biến thể / tên khó
                                  "data/owner_setup_code.txt", "data/dashboard.env.bak", "data/prod.env.local", "data/manifest.sqlite.bak",
                                  "data/x.sqlite3", "data/dashboard.log", "data/dashboard_err.log", "data/p.diag_lost.log",
                                  "data/service_account.json", "data/id_rsa", "data/backup.zip", "data/Backup/x.json", "DATA/BACKUP/x",
                                  "data/dashboard.env::$DATA", "data/x.env.", "data/x.env "])
def test_denied_names(name):
    assert _replay_module().read_denied(name)


@pytest.mark.parametrize("name", ["data/skills/x.json", "data/skills", "data/_plates3d/cache/k/plate.png", "data/assets/9/a.png",
                                  "data/projects/27/world/map.json", "data/pricing.json", "data/feature_settings.json",
                                  "data/assets/9/gold_token.png", "data/assets/9/cookie_jar.png", "data/skills/envelope_dance.json"])
def test_data_files_are_not_denied(name):
    assert not _replay_module().read_denied(name)


# ---- replay giữ DATA_CHANGED của capture ------------------------------------------------------------------------------------------
def test_replay_keeps_data_changed_from_capture():
    module = _replay_module()
    fixture = {"project": 27, "scene_id": 5, "flags": {}, "jobs": [
        {"id": 1, "type": "image_gen", "database_replay": {"status": "DATA_CHANGED", "reason": "builder đòi tệp nền khác",
                                                           "paths": ["data/_plates3d/cache/k/plate.png"]}},
        {"id": 2, "type": "video_gen", "database_replay": {"status": "INSUFFICIENT_INPUT", "reason": "thiếu envelope lịch sử"}},
        # rà THẤP-7: DATA_CHANGED do race lúc chụp (không có paths) không tính là "dữ liệu đổi sau ngày gửi"
        {"id": 3, "type": "video_gen", "database_replay": {"status": "DATA_CHANGED", "reason": "nguồn đổi trong lúc capture/replay"}}]}
    out = module.replay_fixture(fixture, db="unused.sqlite", ref_root=".")
    by_id = {r["job_id"]: r for r in out["jobs"]}
    assert by_id[1]["status"] == "DATA_CHANGED"
    assert by_id[1]["paths"] == ["data/_plates3d/cache/k/plate.png"]
    assert by_id[2]["status"] == "INSUFFICIENT_INPUT"
    assert by_id[3]["status"] == "INSUFFICIENT_INPUT"
    assert out["projects"]["27"]["DATA_CHANGED"] == 1


# ---- chuỗi source_job_id đứt: in chuỗi id + chỗ đứt -------------------------------------------------------------------------------
def test_broken_source_chain_says_ids_and_where(golden):  # noqa: F811
    module, db, flags, root, raw = golden
    final = dict(json.loads(raw), prompt="")                     # bản final không prompt, nguồn trỏ job ẢNH (khác type), không draft
    with sqlite3.connect(db) as conn:
        conn.execute("ALTER TABLE jobs ADD COLUMN source_job_id INTEGER")
        conn.execute("ALTER TABLE jobs ADD COLUMN draft_job_id INTEGER")
        conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,model,quality_tier,sent_package,source_job_id,created_at,updated_at)"
                     " VALUES(9,24,7,'video_gen','succeeded','fake-image','final',?,1,'x','x')", (json.dumps(final),))
    with patch.object(os, "environ", {}), patch.object(module, "head_sha", return_value="a" * 40):
        got = module.capture(db=db, project=24, shot=7, flags_file=flags, ref_root=root, purpose="compat", latest_per_type=True)
    video = next(j for j in got["jobs"] if j["type"] == "video_gen")
    rec = video["database_replay"]
    assert rec["status"] == "INSUFFICIENT_INPUT"
    assert rec["chain"] == [9]
    assert "job 9 → nguồn 1" in rec["broken"] and "image_gen" in rec["broken"]


# ---- worker: đọc được data/skills (vào manifest có sha), cấm dashboard.env / data/backup / CSDL live ------------------------------
_PROBE = """import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker,SandboxDenied
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 original=runner.ImageRunner._submit_args
 def probe(self,job):
  root=Path(request['root'])
  out={}
  for name in sys.argv[3].split(','):
   try:
    (root/name).read_bytes(); out[name]='read'
   except ValueError as exc:      # SandboxDenied (ValueError) hoặc _plain: symlink / ngoài nguồn
    out[name]='denied:'+(exc.diagnostic['kind'] if isinstance(exc,SandboxDenied) else 'path')
   except OSError as exc:
    out[name]='oserror'
  Path('probe.json').write_text(json.dumps(out))
  return original(self,job)
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  answer=_worker(request)
 Path('answer.json').write_text(json.dumps({k:v for k,v in answer.items() if k!='raw'}))
"""


def _probe(database, names):  # noqa: F811
    module, db, root, flags = database
    with tempfile.TemporaryDirectory(prefix="golden4-") as temp, patch.object(os, "environ", {}):
        box = Path(temp)
        (box / "data").mkdir()
        module._db_snapshot(db, box / "data/manifest.sqlite")
        request = {"root": str(root), "job_id": 1, "flags": flags, "envelope": {"provider": "fake", "at": "2026-10-21", "external_id": "x"},
                   "public_config": {}, "expected_files": None}
        path = box / "req.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", _PROBE, str(ROOT), str(path), ",".join(names)], cwd=box,
                                env={"SYSTEMROOT": "C:/Windows", "HOME": temp, "USERPROFILE": temp, "TEMP": temp, "TMP": temp},
                                capture_output=True, timeout=120)
        assert result.returncode == 0, result.stderr.decode(errors="replace")[-2000:]
        return json.loads((box / "probe.json").read_text()), json.loads((box / "answer.json").read_text())


@needs_native_314
def test_worker_reads_any_data_file_into_the_manifest(database):  # noqa: F811
    _, _, root, _ = database
    skill = root / "data/skills/kelly_dance.json"
    skill.parent.mkdir(parents=True)
    skill.write_text('{"x": 1}', encoding="utf-8")
    seen, answer = _probe(database, ["data/skills/kelly_dance.json"])
    assert seen == {"data/skills/kelly_dance.json": "read"}
    import hashlib
    assert answer["status"] == "BUILT", answer
    assert answer["files"]["data/skills/kelly_dance.json"] == hashlib.sha256(b'{"x": 1}').hexdigest()


@needs_native_314
def test_worker_still_denies_env_backup_and_live_database(database):  # noqa: F811
    _, db, root, _ = database
    (root / "dashboard.env").write_text("SECRET=1", encoding="utf-8")
    (root / "data/backup").mkdir(parents=True)
    (root / "data/backup/feature_settings.json").write_text("{}", encoding="utf-8")
    (root / "data/x.env").write_text("K=1", encoding="utf-8")
    live = root / "data/manifest.sqlite"
    live.write_bytes(Path(db).read_bytes())
    seen, answer = _probe(database, ["dashboard.env", "data/backup/feature_settings.json", "data/x.env", "data/manifest.sqlite"])
    assert all(v.startswith("denied") for v in seen.values()), seen
    assert answer["status"] == "INSUFFICIENT_INPUT"          # một lần bị chặn → không coi là dựng đủ
    assert not any(k in json.dumps(answer.get("files", {})) for k in ("dashboard.env", "backup", "x.env"))


def test_secret_block_is_not_relabelled_data_changed():
    """Rà VỪA-2: lần chặn vì bí mật (kind secret) dưới data/assets không bị classify_answer gán 'Kho đổi sau ngày gửi'."""
    module = _replay_module()
    answer = {"status": "INSUFFICIENT_INPUT", "diagnostic": [{"kind": "secret", "path": "data/assets/9/service_account.json"}]}
    assert module.classify_answer(answer)["status"] == "INSUFFICIENT_INPUT"


def test_stat_only_signature(tmp_path):
    module = _replay_module()
    f = tmp_path / "a.json"
    f.write_text("12345", encoding="utf-8")
    assert module._signature(f, {"stat": 5}) == {"stat": 5}
    f.write_text("54321", encoding="utf-8")                       # cùng kích thước: hỏi tồn tại không đổi
    assert module._signature(f, {"stat": 5}) == {"stat": 5}
    assert module._signature(tmp_path / "missing", {"stat": None}) == {"stat": None}
    assert module._signature(tmp_path, {"stat": "dir"}) == {"stat": "dir"}


@needs_native_314
def test_exists_check_is_not_hashed_but_open_is(database):  # noqa: F811
    """Rà VỪA-3: skill_dossier.names() kiểu os.path.exists(<d>/skill.json) → chỉ ghi kích thước; mở tệp → sha."""
    _, _, root, _ = database
    (root / "data/skills/a").mkdir(parents=True)
    (root / "data/skills/a/skill.json").write_text("{}", encoding="utf-8")
    (root / "data/skills/b.json").write_text('{"b": 1}', encoding="utf-8")
    _probe_exists(database)


_PROBE_EXISTS = """import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import _worker
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 original=runner.ImageRunner._submit_args
 def probe(self,job):
  root=Path(request['root'])
  assert os.path.exists(root/'data/skills/a/skill.json')
  (root/'data/skills/b.json').read_bytes()
  return original(self,job)
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  answer=_worker(request)
 Path('answer.json').write_text(json.dumps({k:v for k,v in answer.items() if k!='raw'}))
"""


def _probe_exists(database):  # noqa: F811
    import hashlib
    module, db, root, flags = database
    with tempfile.TemporaryDirectory(prefix="golden4-") as temp, patch.object(os, "environ", {}):
        box = Path(temp)
        (box / "data").mkdir()
        module._db_snapshot(db, box / "data/manifest.sqlite")
        request = {"root": str(root), "job_id": 1, "flags": flags, "envelope": {"provider": "fake", "at": "2026-10-21", "external_id": "x"},
                   "public_config": {}, "expected_files": None}
        (box / "req.json").write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", _PROBE_EXISTS, str(ROOT), str(box / "req.json")], cwd=box,
                                env={"SYSTEMROOT": "C:/Windows", "HOME": temp, "USERPROFILE": temp, "TEMP": temp, "TMP": temp},
                                capture_output=True, timeout=120)
        assert result.returncode == 0, result.stderr.decode(errors="replace")[-2000:]
        answer = json.loads((box / "answer.json").read_text())
    assert answer["status"] == "BUILT", answer
    assert answer["files"]["data/skills/a/skill.json"] == {"stat": 2}
    assert answer["files"]["data/skills/b.json"] == hashlib.sha256(b'{"b": 1}').hexdigest()


@needs_native_314
def test_symlink_in_data_pointing_outside_is_denied(database):  # noqa: F811
    """Rà THẤP-5: symlink dưới data/ trỏ ra ngoài nguồn không đọc được (kể cả qua locate)."""
    _, _, root, _ = database
    outside = Path(tempfile.mkdtemp(prefix="golden4-outside-")) / "secret.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "data/skills").mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(outside, root / "data/skills/link.json")
    except OSError as exc:                       # gộp M2 22/10: Windows không Developer Mode / admin → WinError 1314
        pytest.skip(f"không tạo được symlink trên máy này: {exc}")
    seen, answer = _probe(database, ["data/skills/link.json"])
    assert seen["data/skills/link.json"] != "read"
