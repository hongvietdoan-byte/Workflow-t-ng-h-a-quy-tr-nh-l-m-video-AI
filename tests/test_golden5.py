"""C-GOLDEN5 (cloud-C 21/10, sổ v31-ep-golden-ab-acceptance-2026-10-21): so A/B gói gửi của HAI cây code (main vs M2 tích hợp) trên CÙNG
snapshot CSDL + ref-root chỉ đọc + MỘT file cờ (baseline sản xuất + cờ mới V3.1 = false). Mỗi bên chạy worker cách ly như C-GOLDEN2/4
(request["code_root"] → `core` của cây đó). SAME / DIFF (trường lệch đầu tiên, không in prompt) / ONE_FAIL (= DIFF) / BOTH_FAIL (ghi
riêng). ĐẠT = 0 DIFF + 0 ONE_FAIL. Lịch sử (gói đã gửi) chỉ là cột tham khảo. Worker thật cần native Python 3.14 → test đó ở máy chính."""
import json
import shutil
from unittest import mock
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


def _tree(tmp, name, prompt_line, catalog=None):
    """Cây code tổng hợp: core/runner.py + sent_package.py + features.py (catalog = cờ của cây, mặc định catalog thật) để qua kiểm;
    dòng prompt khác nhau giữa hai cây."""
    from core.features import FEATURES
    root = tmp / name
    (root / "core").mkdir(parents=True)
    (root / "core" / "runner.py").write_text(f"PROMPT = {prompt_line!r}\n", encoding="utf-8")
    (root / "core" / "sent_package.py").write_text("", encoding="utf-8")
    cat = {n: {} for n in (FEATURES if catalog is None else catalog)}
    (root / "core" / "features.py").write_text(f"FEATURES: dict = {cat!r}\n", encoding="utf-8")
    return root


def _fake_builder(broken=()):
    """Builder giả (thay worker 3.14): gói = dòng PROMPT đọc từ core/runner.py của cây code được truyền."""
    def build(*, db, ref_root, job_id, flags, envelope, public_config=None, experimental=None, code_root=None, catalog_union=None):
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
    # toàn BOTH_FAIL = không so được gì → CHƯA ĐẠT (rà C-GOLDEN5: trước đây thành ĐẠT giả)
    assert res["total"]["BOTH_FAIL"] == 2 and res["total"]["DIFF"] == 0 and res["pass"] is False
    assert res["no_same_projects"] == ["24"] and res["rows"][0]["history_a"] == "NOT_BUILT"
    assert "CHƯA ĐẠT" in G.ab_table(res) and "#24" in G.ab_table(res)
    assert {r["state"] for r in res["rows"]} <= {"approved", "succeeded", "queued", "pending_review", "sent", "failed", "running"}


def test_preflight_stops_the_run_instead_of_folding_into_both_fail(database, tmp_path):  # noqa: F811
    """Rà C-GOLDEN5: lỗi đầu vào / môi trường (cờ thiếu so với catalog CỦA TỪNG CÂY, cây code sai, Python không phải 3.14) dừng cả
    lượt bằng ABError — không thành BOTH_FAIL rồi 'ĐẠT'."""
    module, db, root, flags = database
    kw = dict(db=db, ref_root=root, flags=flags, experimental=[], projects=[24])
    a = _tree(tmp_path, "main", "x")
    b = _tree(tmp_path, "m2", "x", catalog=list(flags) + ["co_moi_v31"])          # cây B có cờ mà file cờ không có
    with pytest.raises(G.ABError, match="co_moi_v31"):
        G.run_ab(code_a=a, code_b=b, builder=_fake_builder(), **kw)
    with pytest.raises(G.ABError, match="cây code"):
        G.run_ab(code_a=a, code_b=tmp_path / "khong_co", builder=_fake_builder(), **kw)
    import sys
    if sys.version_info[:2] != (3, 14):
        with pytest.raises(ValueError, match="3.14"):                              # builder mặc định = worker thật
            G.run_ab(code_a=a, code_b=a, **kw)


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
    args = ["--ab", "--db", str(db), "--ref-root", str(root), "--code-a", str(a), "--code-b", str(b), "--project", "24"]
    with pytest.raises(SystemExit) as e:                                              # tệp kết quả đã có → dừng TRƯỚC khi chạy
        G.main_ab(args + ["--flags", str(spec), "--output", str(out)])
    assert e.value.code == 2
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"experimental_flags": []}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:                                              # thiếu baseline_flags → mã 2, không KeyError
        G.main_ab(args + ["--flags", str(bad), "--output", str(tmp_path / "ab2.json")])
    assert e.value.code == 2 and not (tmp_path / "ab2.json").exists()


@needs_native_314
def test_real_worker_two_code_trees_same_and_one_line_changed(database, tmp_path):  # noqa: F811
    """Worker thật (native 3.14): cây A = bản sao repo; cây B = bản sao đổi MỘT dòng builder → DIFF; B y A → SAME.
    C-GOLDEN6: bản trước đổi `meta_entry` (nhãn ảnh tham chiếu) — gói của fixture KHÔNG có ảnh tham chiếu nên dòng đó không chạy → 0 DIFF
    (negative control đỏ ở máy chính, KHÔNG phải worker nạp sai cây). Nay đổi dòng `"call": call,` mà MỌI gói đều đi qua, và kiểm module
    thật đã nạp (loaded_a / loaded_b) nằm trong đúng cây."""
    module, db, root, flags = database
    ignore = shutil.ignore_patterns("__pycache__", "data", ".git", "tests", "docs", "mockup")
    a, b = tmp_path / "code_a", tmp_path / "code_b"
    shutil.copytree(ROOT, a, ignore=ignore)
    shutil.copytree(ROOT, b, ignore=ignore)
    kw = dict(db=db, ref_root=root, flags=flags, experimental=[], projects=[24])
    same = G.run_ab(code_a=a, code_b=b, **kw)
    assert same["total"]["SAME"] >= 1 and same["total"]["DIFF"] == 0 and same["total"]["ONE_FAIL"] == 0   # có ca BUILT thật để so
    for row in same["rows"]:
        if row["status"] == "SAME":
            assert all(Path(p).is_relative_to(a) for p in row["loaded_a"].values()), row["loaded_a"]
            assert all(Path(p).is_relative_to(b) for p in row["loaded_b"].values()), row["loaded_b"]
    sp = b / "core" / "sent_package.py"
    text = sp.read_text(encoding="utf-8")
    assert text.count('"call": call,') == 1                                          # chỗ đổi phải CÓ THẬT và nằm trên đường mọi gói
    sp.write_text(text.replace('"call": call,', '"call": str(call) + "_b",', 1), encoding="utf-8")
    changed = G.run_ab(code_a=a, code_b=b, **kw)
    assert changed["total"]["DIFF"] == same["total"]["SAME"] and changed["pass"] is False
    assert {r["first_diff"]["path"] for r in changed["rows"] if r["status"] == "DIFF"} == {"call"}


@needs_native_314
def test_stale_bytecode_in_a_code_tree_is_never_used(database, tmp_path):  # noqa: F811
    """C-GOLDEN6: .pyc cũ trong __pycache__ của cây code (cùng mtime + kích thước nguồn) không được dùng — worker dịch từ nguồn
    (sys.pycache_prefix trong thư mục tạm)."""
    import os
    import py_compile
    module, db, root, flags = database
    ignore = shutil.ignore_patterns("__pycache__", "data", ".git", "tests", "docs", "mockup")
    b = tmp_path / "code_b"
    shutil.copytree(ROOT, b, ignore=ignore)
    sp = b / "core" / "sent_package.py"
    text = sp.read_text(encoding="utf-8")
    st = sp.stat()
    assert len('"call": call,') == len('"call": "zz",')
    sp.write_text(text.replace('"call": call,', '"call": "zz",', 1), encoding="utf-8")       # CÙNG độ dài → .pyc cũ hợp lệ theo mtime+size
    os.utime(sp, (st.st_atime, st.st_mtime))
    py_compile.compile(str(sp), cfile=str(b / "core" / "__pycache__" / f"sent_package.{__import__('sys').implementation.cache_tag}.pyc"))
    sp.write_text(text, encoding="utf-8")                                              # nguồn về như cũ, .pyc vẫn là bản đổi
    os.utime(sp, (st.st_atime, st.st_mtime))
    res = G.run_ab(code_a=b, code_b=b, **dict(db=db, ref_root=root, flags=flags, experimental=[], projects=[24]))
    built = [r for r in res["rows"] if r["status"] == "SAME"]
    assert built
    raw = G.build_from_database(db=db, ref_root=root, job_id=built[0]["job_id"], flags=flags,
                                envelope={"provider": "fake", "at": "2026-01-01T00:00:00", "external_id": "x"}, experimental=[],
                                code_root=b)
    assert raw["status"] == "BUILT" and json.loads(raw["raw"])["call"] != "zz"


def test_loaded_outside_names_the_wrong_tree(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    (a / "core").mkdir(parents=True)
    (b / "core").mkdir(parents=True)
    good = {"core.runner": str(a / "core" / "runner.py"), "core.sent_package": str(a / "core" / "sent_package.py")}
    assert G.loaded_outside(good, a) == []
    assert G.loaded_outside(dict(good, **{"core.sent_package": str(b / "core" / "sent_package.py")}), a) == ["core.sent_package"]
    assert G.loaded_outside(None, a) == ["core.runner", "core.sent_package"]


# ---- C-GOLDEN7: validator cờ theo catalog CÂY ĐANG DỰNG (CX21-GOLDEN6: 158/158 BOTH_FAIL trước worker) -------------------------------
def _with_extra_flag(root, name):
    """Cây code có thêm MỘT cờ (như gen_auth_shadow ở main) mà cây công cụ chưa có."""
    fp = root / "core" / "features.py"
    text = fp.read_text(encoding="utf-8")
    marker = "FEATURES: Dict[str, Dict] = {" if "FEATURES: Dict[str, Dict] = {" in text else "FEATURES: dict = {"
    assert marker in text
    fp.write_text(text.replace(marker, marker + f"\n    {name!r}: {{'label': 'x', 'verified': False}},", 1), encoding="utf-8")
    return root


def test_ab_validates_flags_by_the_tree_being_built(database, tmp_path):  # noqa: F811
    """Cây A có cờ mới mà cây công cụ không có; file cờ phủ A∪B, cờ mới là experimental TẮT → validator KHÔNG chặn (trước: ValueError
    'experimental_flags cần list tên cờ duy nhất có trong catalog' ở mọi ca → BOTH_FAIL)."""
    module, db, root, flags = database
    a = _with_extra_flag(_tree(tmp_path, "main", "x"), "zz_new_flag")
    G.validate_ab_flags(dict(flags, zz_new_flag=False), ["zz_new_flag"], a, {"zz_new_flag"} | set(flags))
    try:
        G.build_from_database(db=db, ref_root=root, job_id=1, flags=dict(flags, zz_new_flag=False),
                              envelope={"provider": "fake", "at": "2026-01-01T00:00:00", "external_id": "x"},
                              experimental=["zz_new_flag"], code_root=a, catalog_union=G._catalog(a))
    except ValueError as e:
        assert "catalog" not in str(e) and "experimental" not in str(e), e          # chỉ còn lỗi môi trường (3.13) / cây giả
    b = _tree(tmp_path, "m2", "x")                                                     # cây B không có cờ đó: vẫn hợp lệ (cờ của cây kia)
    G.validate_ab_flags(dict(flags, zz_new_flag=False), ["zz_new_flag"], b, G._catalog(a) | G._catalog(b))


def test_config_error_stops_the_whole_run_with_exit_2(database, tmp_path):  # noqa: F811
    module, db, root, flags = database
    a, b = _tree(tmp_path, "main", "x"), _tree(tmp_path, "m2", "x")
    calls = []

    def builder(**kw):
        calls.append(kw)
        return _built(PKG)
    kw = dict(db=db, ref_root=root, flags=flags, projects=[24], code_a=a, code_b=b, builder=builder)
    with pytest.raises(G.ABError, match="khong_co_dau"):
        G.run_ab(experimental=["khong_co_dau"], **kw)                                  # cờ lạ không thuộc A∪B
    with pytest.raises(G.ABError, match="TẮT"):
        G.run_ab(experimental=[next(iter(flags))], **dict(kw, flags=dict(flags, **{next(iter(flags)): True})))
    assert calls == []                                                                 # không chạy ca nào
    spec = tmp_path / "flags.json"
    spec.write_text(json.dumps({"baseline_flags": flags, "experimental_flags": ["khong_co_dau"]}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        G.main_ab(["--ab", "--db", str(db), "--ref-root", str(root), "--flags", str(spec), "--code-a", str(a), "--code-b", str(b),
                   "--project", "24", "--output", str(tmp_path / "ab.json")])
    assert e.value.code == 2 and not (tmp_path / "ab.json").exists()


def test_config_error_raised_mid_run_is_not_folded_into_both_fail(database, tmp_path):  # noqa: F811
    module, db, root, flags = database
    a, b = _tree(tmp_path, "main", "x"), _tree(tmp_path, "m2", "x")

    def builder(**kw):
        raise G.ABError("catalog cây đổi giữa chừng")
    with pytest.raises(G.ABError):
        G.run_ab(db=db, ref_root=root, flags=flags, experimental=[], projects=[24], code_a=a, code_b=b, builder=builder)


@needs_native_314
def test_real_worker_tree_with_a_new_flag_builds_both_sides(database, tmp_path):  # noqa: F811
    """Native: cây A = repo + MỘT cờ mới (experimental, TẮT), cây B = repo → cả hai bên dựng được, SAME (trước: mọi ca BOTH_FAIL)."""
    module, db, root, flags = database
    ignore = shutil.ignore_patterns("__pycache__", "data", ".git", "tests", "docs", "mockup")
    a, b = tmp_path / "code_a", tmp_path / "code_b"
    shutil.copytree(ROOT, a, ignore=ignore)
    shutil.copytree(ROOT, b, ignore=ignore)
    _with_extra_flag(a, "zz_new_flag")
    res = G.run_ab(db=db, ref_root=root, flags=dict(flags, zz_new_flag=False), experimental=["zz_new_flag"], projects=[24],
                   code_a=a, code_b=b)
    assert res["total"]["SAME"] >= 1 and res["total"]["BOTH_FAIL"] == 0 and res["pass"] is True


def test_every_whole_run_config_error_is_exit_2_not_both_fail(database, tmp_path):  # noqa: F811
    """Rà C-GOLDEN7: public_config sai khóa, experimental None, ref-root hỏng → ABError TRƯỚC ca đầu (trước: N/N BOTH_FAIL, mã 1)."""
    module, db, root, flags = database
    a, b = _tree(tmp_path, "main", "x"), _tree(tmp_path, "m2", "x")
    calls = []

    def builder(**kw):
        calls.append(kw)
        return _built(PKG)
    kw = dict(db=db, ref_root=root, flags=flags, projects=[24], code_a=a, code_b=b, builder=builder)
    with pytest.raises(G.ABError, match="public_config"):
        G.run_ab(experimental=[], public_config={"API_KEY_X": "1"}, **kw)
    with pytest.raises(G.ABError, match="list"):
        G.run_ab(experimental=None, **kw)
    with pytest.raises(G.ABError, match="ref-root"):
        G.run_ab(experimental=[], **dict(kw, ref_root=tmp_path / "khong_co"))
    assert calls == []


def test_cli_refuses_an_experimental_flag_that_is_on_and_a_bad_db(database, tmp_path):  # noqa: F811
    module, db, root, flags = database
    a, b = _tree(tmp_path, "main", "x"), _tree(tmp_path, "m2", "x")
    name = next(iter(flags))
    spec = tmp_path / "flags.json"
    spec.write_text(json.dumps({"baseline_flags": dict(flags, **{name: True}), "experimental_flags": [name]}), encoding="utf-8")
    args = ["--ab", "--ref-root", str(root), "--code-a", str(a), "--code-b", str(b), "--project", "24"]
    with pytest.raises(SystemExit) as e:                                              # trước: ép False lặng lẽ
        G.main_ab(args + ["--db", str(db), "--flags", str(spec), "--output", str(tmp_path / "o1.json")])
    assert e.value.code == 2
    bad = tmp_path / "hong.sqlite"
    bad.write_bytes(b"khong phai sqlite" * 10)
    spec.write_text(json.dumps({"baseline_flags": flags, "experimental_flags": []}), encoding="utf-8")
    with mock.patch.object(G, "run_ab", lambda **kw: G.ab_jobs(kw["db"], kw["projects"])):
        with pytest.raises(SystemExit) as e:                                          # sqlite3.Error → mã 2, không traceback
            G.main_ab(args + ["--db", str(bad), "--flags", str(spec), "--output", str(tmp_path / "o2.json")])
    assert e.value.code == 2
