"""Rà 22/10 (sau GOLDEN7 máy chính): worker golden_db_replay trên Windows + 10 BOTH_FAIL 'operation'.

1. Hỏi tồn tại (os.path.exists / isfile / isdir, Path.exists / is_file / is_dir) với đường dẫn 'data/…' TƯƠNG ĐỐI (cwd = scratch, như
   runner dùng "data/projects") phải nhìn thấy ref-root và vào manifest {stat}. Windows 3.12+: ba hàm là hàm C của nt, không qua os.stat
   đã bọc → trước 79cfb019 nhìn vào scratch (False); GOLDEN7 máy chính chạy TRƯỚC bản vá đó.
2. Ghi vào thư mục chỉ có ở ref-root (refs_clean): makedirs thấy 'đã có' qua locate → lần ghi trong scratch FileNotFoundError.
3. Kho chủ thể: ảnh chưa có dòng → code thật tải lên ClipAI. --ab giả asset tất định theo sha; capture/replay thường vẫn cấm, nói rõ loại.
4. Ngoại lệ trong worker giữ loại thao tác + vị trí + `loaded`.
Không dùng data/ thật: CSDL + tệp tổng hợp trong tmp_path. Cần worker native 3.14 như tests/test_golden_db_replay.py."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.test_golden_db_replay import database, needs_native_314  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]

_PROBE = """import os,sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
with patch.object(os,'environ',{}):
 from tools.golden_db_replay import worker_answer
 from core import runner
 request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
 mode=sys.argv[3]
 seen={}
 original=runner.ImageRunner._submit_args
 def probe(self,job):
  if mode=='exists':
   rel='data/probe_only/qq/skill.json'
   seen.update(exists=os.path.exists(rel),isfile=os.path.isfile(rel),isdir=os.path.isdir('data/probe_only/qq'),
               p_exists=Path(rel).exists(),p_is_file=Path(rel).is_file(),p_is_dir=Path('data/probe_only/qq').is_dir(),
               missing=os.path.exists('data/probe_only/zz.json'))
  elif mode=='write':
   folder='data/projects/24/refs_clean'
   seen['isdir']=os.path.isdir(folder)
   with open(folder+'/x.png','wb') as f: f.write(b'xyz')
   with open(folder+'/x.png','rb') as f: seen['back']=f.read().decode()
  elif mode=='upload':
   seen['asset']=self.subject_library.upload('data/projects/24/images/job_1.png','synthetic_name')
  elif mode=='list':
   self.subject_library.list_assets()
  elif mode=='mkdir_new':
   os.makedirs('data/projects/24/refs_new',exist_ok=True)
   seen['isdir']=os.path.isdir('data/projects/24/refs_new')
  elif mode=='mark':
   import hashlib
   from core import seedance_refs
   out=seedance_refs.mark('data/projects/24/images/job_1.png','data/projects/24/refs_clean',style='none')
   with open(out,'rb') as f: seen['sha']=hashlib.sha256(f.read()).hexdigest()
   seen['name']=os.path.basename(out)
  return original(self,job)
 with patch.object(runner.ImageRunner,'_submit_args',probe):
  answer=worker_answer(request)
 answer.pop('raw',None)
 Path('probe.json').write_text(json.dumps({'seen':seen,'answer':answer}),encoding='utf-8')
"""


def _run(database, mode, code_root=None):  # noqa: F811
    module, db, root, flags = database
    with tempfile.TemporaryDirectory(prefix="golden-win-") as temp, patch.object(os, "environ", {}):
        box = Path(temp)
        (box / "data").mkdir()
        module._db_snapshot(db, box / "data/manifest.sqlite")
        request = {"root": str(root), "job_id": 1, "flags": flags, "envelope": {"provider": "fake", "at": "2026-10-21", "external_id": "x"},
                   "public_config": {}, "expected_files": None}
        if code_root:
            request["code_root"] = str(code_root)
        (box / "req.json").write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, "-I", "-B", "-c", _PROBE, str(ROOT), str(box / "req.json"), mode], cwd=box,
                                env={"SYSTEMROOT": "C:/Windows", "HOME": temp, "USERPROFILE": temp, "TEMP": temp, "TMP": temp},
                                capture_output=True, timeout=120)
        assert result.returncode == 0, result.stderr.decode(errors="replace")[-2000:]
        out = json.loads((box / "probe.json").read_text(encoding="utf-8"))
        return out["seen"], out["answer"]


@needs_native_314
def test_relative_existence_probes_see_ref_root_and_enter_manifest(database):  # noqa: F811
    _, _, root, _ = database
    (root / "data/probe_only/qq").mkdir(parents=True)
    (root / "data/probe_only/qq/skill.json").write_text("{}", encoding="utf-8")
    seen, answer = _run(database, "exists")
    assert seen == {"exists": True, "isfile": True, "isdir": True, "p_exists": True, "p_is_file": True, "p_is_dir": True,
                    "missing": False}, seen
    assert answer["status"] == "BUILT", answer
    assert answer["files"]["data/probe_only/qq/skill.json"] == {"stat": 2}
    assert answer["files"]["data/probe_only/qq"] == {"stat": "dir"}
    assert answer["files"]["data/probe_only/zz.json"] == {"stat": None}     # hỏi tồn tại tệp KHÔNG có cũng vào manifest (thêm sau = DATA_CHANGED)


@needs_native_314
def test_write_into_a_folder_that_exists_only_in_ref_root(database):  # noqa: F811
    _, _, root, _ = database
    (root / "data/projects/24/refs_clean").mkdir(parents=True)
    seen, answer = _run(database, "write")
    assert seen == {"isdir": True, "back": "xyz"}, (seen, answer)   # ghi thẳng (không makedirs) vào thư mục chỉ có ở ref-root
    assert answer["status"] == "BUILT", answer
    assert not (root / "data/projects/24/refs_clean/x.png").exists()      # ghi chỉ trong scratch, ref-root không đổi


@needs_native_314
def test_subject_upload_is_simulated_only_in_ab_and_deterministic(database):  # noqa: F811
    _, _, root, _ = database
    sha = hashlib.sha256((root / "data/projects/24/images/job_1.png").read_bytes()).hexdigest()
    seen, answer = _run(database, "upload", code_root=ROOT)
    assert seen["asset"]["asset_uri"] == "asset://golden-ab-" + sha[:16] and seen["asset"]["provider_status"] == "active"
    assert answer["status"] == "BUILT" and answer["simulated_uploads"] == [{"sha": sha[:16], "name": "synthetic_name"}], answer
    assert answer["loaded"]["core.runner"].endswith("runner.py")
    seen, answer = _run(database, "upload")                                # capture / replay thường: không giả lịch sử
    assert answer["status"] == "INSUFFICIENT_INPUT" and answer["diagnostic"]["kind"] == "subject_library_upload", answer
    assert "asset" not in seen


@needs_native_314
def test_forbidden_operation_names_its_kind_position_and_loaded_tree(database):  # noqa: F811
    _, answer = _run(database, "list", code_root=ROOT)
    assert answer["status"] == "INSUFFICIENT_INPUT"
    assert answer["diagnostic"]["kind"] == "subject_library_list"           # trước: {"kind": "operation", "path": "<outside-root>"}
    assert any(p.startswith("golden_db_replay.py:") for p in answer["diagnostic"]["positions"])
    assert set(answer["loaded"]) == {"core.runner", "core.sent_package"}      # bằng chứng nạp cây vẫn có khi ca hỏng



@needs_native_314
def test_makedirs_new_folder_whose_parent_is_only_in_ref_root(database):  # noqa: F811
    _, _, root, _ = database
    seen, answer = _run(database, "mkdir_new")
    assert seen == {"isdir": True} and answer["status"] == "BUILT", (seen, answer)
    assert not (root / "data/projects/24/refs_new").exists()


@needs_native_314
def test_ab_rebuilds_marked_pictures_instead_of_reusing_the_ref_root_cache(database):  # noqa: F811
    """mark() dùng lại tệp ra cũ (mtime mới hơn ảnh) — ở ref-root đó là ảnh do code lịch sử dựng → --ab phải dựng lại bằng code cây đang so
    (nếu không, B sửa mark/clean vẫn SAME); capture / replay thường giữ hành vi sản xuất (dùng cache)."""
    from PIL import Image
    _, _, root, _ = database
    source = root / "data/projects/24/images/job_1.png"
    key = hashlib.sha1(os.path.abspath(str(source)).lower().encode("utf-8")).hexdigest()[:10]
    cache = root / f"data/projects/24/refs_clean/job_1_{key}_marked_none.png"
    cache.parent.mkdir(parents=True)
    Image.new("RGB", (16, 16), "blue").save(cache)                     # bản cache "lịch sử" khác nội dung, mtime mới hơn ảnh gốc
    cached_sha = hashlib.sha256(cache.read_bytes()).hexdigest()
    seen, answer = _run(database, "mark")
    assert answer["status"] == "BUILT" and seen == {"sha": cached_sha, "name": cache.name}, (seen, answer)
    seen, answer = _run(database, "mark", code_root=ROOT)
    assert answer["status"] == "BUILT", answer
    assert seen["name"] == cache.name and seen["sha"] != cached_sha     # cùng tên tệp như sản xuất, nội dung do code cây này dựng
    assert hashlib.sha256(cache.read_bytes()).hexdigest() == cached_sha  # ref-root không bị ghi


def test_simulated_uploads_that_differ_are_a_diff():
    with patch.object(os, "environ", {}):
        import importlib
        G = importlib.import_module("tools.golden_db_replay")
    a = {"status": "BUILT", "raw": "{}", "simulated_uploads": [{"sha": "1", "name": "x"}]}
    b = {"status": "BUILT", "raw": "{}", "simulated_uploads": [{"sha": "2", "name": "x"}]}
    assert G.compare_ab(a, b)["status"] == "DIFF" and G.compare_ab(a, b)["first_diff"]["path"] == "simulated_uploads"
    assert G.compare_ab(a, dict(a))["status"] == "SAME"
