"""C-GOLDEN5 (cloud-C 21/10, sổ v31-ep-golden-ab-acceptance-2026-10-21): so A/B gói gửi của HAI cây code (main vs M2 tích hợp) trên CÙNG
snapshot CSDL + ref-root chỉ đọc + MỘT file cờ (baseline sản xuất + cờ mới V3.1 = false). Mỗi bên chạy worker cách ly như C-GOLDEN2/4
(request["code_root"] → `core` của cây đó). SAME / DIFF (trường lệch đầu tiên, không in prompt) / ONE_FAIL (= DIFF) / BOTH_FAIL (ghi
riêng). ĐẠT = 0 DIFF + 0 ONE_FAIL. Lịch sử (gói đã gửi) chỉ là cột tham khảo. Worker thật cần native Python 3.14 → test đó ở máy chính."""
import json
import shutil
from pathlib import Path

import pytest

from tests.test_golden_db_replay import database, needs_native_314  # noqa: F401  (fixture CSDL + tệp tổng hợp)
from tools import golden_db_replay as G

ROOT = Path(__file__).resolve().parents[1]
PKG = {"prompt": "A red cube on a white table. Soft daylight.", "refs": [{"label": "cube", "file": "a.png"}], "model": "seedream"}


def _built(pkg):
    return {"status": "BUILT", "raw": json.dumps(pkg, ensure_ascii=False, sort_keys=True)}


def test_first_diff_names_the_field_but_never_prints_the_prompt():
    b = dict(PKG, prompt="A red cube on a white table. Hard noon light.")
    d = G.first_diff(PKG, b)
    assert d["path"] == "prompt" and d["kind"] == "text" and d["at_char"] == len("A red cube on a white table. ")
    assert "light" not in json.dumps(d) and "cube" not in json.dumps(d)
    assert G.first_diff(PKG, dict(PKG, refs=[{"label": "cube", "file": "b.png"}]))["path"] == "refs[0].file"
    assert G.first_diff(PKG, dict(PKG, refs=[]))["kind"] == "length"
    assert G.first_diff(PKG, dict(PKG)) is None


def test_compare_ab_statuses():
    fail = {"status": "INSUFFICIENT_INPUT", "reason": "worker không dựng được gói"}
    assert G.compare_ab(_built(PKG), _built(dict(PKG)))["status"] == "SAME"
    diff = G.compare_ab(_built(PKG), _built(dict(PKG, model="gpt-image")))
    assert diff["status"] == "DIFF" and diff["first_diff"]["path"] == "model"
    one = G.compare_ab(_built(PKG), fail)
    assert one["status"] == "ONE_FAIL" and one["failed"] == "b"
    assert G.compare_ab(fail, fail)["status"] == "BOTH_FAIL"


def _tree(tmp, name, prompt_line):
    """Cây code tổng hợp: chỉ cần core/runner.py + core/sent_package.py để qua kiểm; dòng prompt khác nhau giữa hai cây."""
    root = tmp / name
    (root / "core").mkdir(parents=True)
    (root / "core" / "runner.py").write_text(f"PROMPT = {prompt_line!r}\n", encoding="utf-8")
    (root / "core" / "sent_package.py").write_text("", encoding="utf-8")
    return root


def _fake_builder(broken=()):
    """Builder giả (thay worker 3.14): gói = dòng PROMPT đọc từ core/runner.py của cây code được truyền."""
    def build(*, db, ref_root, job_id, flags, envelope, public_config=None, experimental=None, code_root=None):
        if Path(code_root).name in broken:
            return {"status": "INSUFFICIENT_INPUT", "reason": "worker không dựng được gói"}
        line = (Path(code_root) / "core" / "runner.py").read_text(encoding="utf-8").split("=", 1)[1].strip().strip("'")
        return _built(dict(PKG, prompt=line, job=job_id))
    return build


def test_run_ab_same_diff_and_one_fail(database, tmp_path):  # noqa: F811
    module, db, root, flags = database
    a = _tree(tmp_path, "main", "A red cube on a white table.")
    same = _tree(tmp_path, "m2_same", "A red cube on a white table.")
    other = _tree(tmp_path, "m2_diff", "A red cube on a white table, sharp shadow.")
    kw = dict(db=db, ref_root=root, flags=flags, experimental=[], projects=[24])
    res = G.run_ab(code_a=a, code_b=same, builder=_fake_builder(), **kw)
    assert res["total"]["SAME"] == 2 and res["pass"] is True                       # job ảnh + job video của shot 7
    res = G.run_ab(code_a=a, code_b=other, builder=_fake_builder(), **kw)
    assert res["total"]["DIFF"] == 2 and res["pass"] is False
    assert res["rows"][0]["first_diff"]["path"] == "prompt" and "shadow" not in json.dumps(res)
    res = G.run_ab(code_a=a, code_b=same, builder=_fake_builder(broken={"m2_same"}), **kw)
    assert res["total"]["ONE_FAIL"] == 2 and res["pass"] is False                  # một bên lỗi = lệch
    res = G.run_ab(code_a=a, code_b=same, builder=_fake_builder(broken={"main", "m2_same"}), **kw)
    assert res["total"]["BOTH_FAIL"] == 2 and res["total"]["DIFF"] == 0 and res["pass"] is True
    assert res["rows"][0]["history_a"] == "NOT_BUILT"
    assert "ĐẠT" in G.ab_table(res) and "#24" in G.ab_table(res)


def test_ab_jobs_latest_per_shot_and_type_with_a_fixed_envelope(database):  # noqa: F811
    import sqlite3
    module, db, root, flags = database
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO jobs(id,project_id,scene_id,type,state,created_at,updated_at,sent_package) VALUES(3,24,7,'image_gen',"
                     "'approved','2026-10-21','2026-10-21',?)", (json.dumps({"provider": "deepix", "at": "2026-10-20T10:00:00",
                                                                             "external_id": "t9"}),))
    jobs = G.ab_jobs(db, [24])
    assert sorted((j["type"], j["job_id"]) for j in jobs) == [("image_gen", 3), ("video_gen", 2)]
    env = {j["job_id"]: j["envelope"] for j in jobs}
    assert env[3]["external_id"] == "t9" and env[2] == {"provider": "fake", "at": "2026-01-01T00:00:00", "external_id": "golden-ab"}


def test_code_root_must_be_a_code_tree(database, tmp_path):  # noqa: F811
    module, db, root, flags = database
    with pytest.raises(ValueError, match="cây code"):
        G.build_from_database(db=db, ref_root=root, job_id=1, flags=flags,
                              envelope={"provider": "fake", "at": "2026-01-01T00:00:00", "external_id": "x"},
                              experimental=None, code_root=tmp_path / "khong_phai_code")


def test_main_ab_writes_json_and_exit_code(database, tmp_path, monkeypatch):  # noqa: F811
    module, db, root, flags = database
    spec = tmp_path / "flags.json"
    spec.write_text(json.dumps({"baseline_flags": flags, "experimental_flags": []}), encoding="utf-8")
    a, b = _tree(tmp_path, "main", "x"), _tree(tmp_path, "m2", "y")
    real = G.run_ab
    monkeypatch.setattr(G, "run_ab", lambda **kw: real(builder=_fake_builder(), **kw))
    out = tmp_path / "ab.json"
    code = G.main_ab(["--ab", "--db", str(db), "--ref-root", str(root), "--flags", str(spec), "--code-a", str(a), "--code-b", str(b),
                      "--project", "24", "--output", str(out)])
    assert code == 1 and json.loads(out.read_text(encoding="utf-8"))["total"]["DIFF"] == 2


@needs_native_314
def test_real_worker_two_code_trees_same_and_one_line_changed(database, tmp_path):  # noqa: F811
    """Worker thật (máy chính): cây A = bản sao repo; cây B = bản sao đổi MỘT câu của prompt → DIFF; B y A → SAME."""
    module, db, root, flags = database
    ignore = shutil.ignore_patterns("__pycache__", "data", ".git", "tests", "docs", "mockup")
    a, b = tmp_path / "code_a", tmp_path / "code_b"
    shutil.copytree(ROOT, a, ignore=ignore)
    shutil.copytree(ROOT, b, ignore=ignore)
    kw = dict(db=db, ref_root=root, flags=flags, experimental=[], projects=[24])
    same = G.run_ab(code_a=a, code_b=b, **kw)
    assert same["total"]["DIFF"] == 0 and same["total"]["ONE_FAIL"] == 0
    sp = b / "core" / "sent_package.py"
    sp.write_text(sp.read_text(encoding="utf-8").replace('"version"', '"version_b"', 1), encoding="utf-8")
    changed = G.run_ab(code_a=a, code_b=b, **kw)
    assert changed["total"]["DIFF"] + changed["total"]["ONE_FAIL"] >= 1 and changed["pass"] is False
