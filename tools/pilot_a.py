"""DP12 — V3.1 M5.3 pilot vòng A OFFLINE (0 USD) theo docs/V3_1_M0_11_PILOT_3_VONG_2026-10-20.md mục 1.

    PYTHONUTF8=1 python3 tools/pilot_a.py [--out-dir DIR] [--md BÁO_CÁO.md] [--no-xdist]

Ca = mục sổ lỗi devsys/errors.json (một nguồn, không chép tay) có `tests`:
  FIXED_UNVERIFIED → "phai_xanh" (tiêu chí 1)   OPEN → "phai_do" (tiêu chí 5: còn đỏ / xfail, không "xanh vì bỏ qua")
  IN_PROGRESS → "dang_lam" (báo, không chấm).  Mục không có test → liệt kê "khong_co_test".
Nhóm theo `category` → payload / continuity / qc / lineage / phuc_hoi (mục 1.2).
Chạy pytest đúng các test đó dưới lớp chặn tools/pilot_a_guard.py (chặn mạng ra ngoài + ghi lại mọi lần mở ghi dưới data/), cộng so `git status data/`
trước/sau. Tiêu chí mục 1.3: c1 ca đã sửa xanh · c2 compatibility golden (cờ TẮT = byte giống — cần Python 3.14 như tools/golden_capture; khác →
"không đo được", KHÔNG coi là đạt) · c3 0 kết nối ra ngoài · c4 0 ghi vào data/ · c5 ca chưa sửa còn đỏ.
Kết quả cao nhất "DAT_OFFLINE" — KHÔNG BAO GIỜ VERIFIED (sổ lỗi V3.1: cần vòng B chạy thật). Ca cần dữ liệu thật: MAY_CHINH (mục 7.4)."""
import argparse
import glob
import hashlib
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import uuid
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_PY = (3, 14)                     # tools/golden_capture.replay_builder chỉ chạy native Python 3.14
GOLDEN_TESTS = ["tests/test_golden_replay.py", "tests/test_golden_db_replay.py"]

GROUPS = {
    "payload": ("goi_anh", "goi_video", "do_dai_prompt", "router", "kho_chu_the", "so_goi", "video_ref", "anh_mau", "khung_dau", "khop_moi",
                "thong_diep"),
    "continuity": ("continuity", "vi_tri", "byd", "chen_shot", "vat", "dang_nhan_vat", "may", "kho_3d", "nen_3d", "bo_cuc", "ti_le",
                   "chuyen_dong", "motion", "loi_dan", "thoi_luong", "dung", "ref_bau_troi", "kho_forms"),
    "qc": ("bao_nham", "qc_crash", "cong", "chu_viet"),
    "lineage": ("khoa_tay", "diag", "van_hanh", "cong_cu"),
    "phuc_hoi": ("vong_doi_job", "provider", "giu_job", "tam_dung", "chi_phi"),
}
KINDS = {"FIXED_UNVERIFIED": "phai_xanh", "OPEN": "phai_do", "IN_PROGRESS": "dang_lam"}

# mục 7.4 (ĐÃ CHỐT 20/10): dữ liệu vòng A máy chính chụp (chỉ đọc, D08) — ca chưa chạy được ở cloud
MAY_CHINH = [
    {"nhom": "payload", "can": "jobs.sent_package + sent_refs #31 shot 27, 28, 29, 30, 33, 35, 36 và #33 (6 clip 1080p + nháp; job 1162, 1163)",
     "ma": ["P31-G27", "P31-G37", "P31-G38", "P31-G7", "P31-G10", "P31-G24"]},
    {"nhom": "qc", "can": "ảnh/clip jobs.result_path #33 S2, #33 shot 6 (+ motion_prompts.ref_video_path), #31 shot 33",
     "ma": ["P33-A5", "P33-A6", "V21-R3"]},
    {"nhom": "payload", "can": "ảnh Kho #427 (dạng bóng mờ, vai character_form), #367 (tường keo)", "ma": ["P31-G37", "P31-G38"]},
    {"nhom": "continuity", "can": "scenes.data + story_scenes #31 cảnh 4/6/8 (shot 14, 26–29, 35) và #33", "ma": ["P31-G41", "P31-G43", "P31-G45"]},
    {"nhom": "lineage", "can": "change_events 17/10 #31 (13 mục đỏ noi_chon)", "ma": ["P31-G22"]},
    {"nhom": "phuc_hoi", "can": "job_events / diag_events #33 job 1162→1163, #31 job 1058–1072", "ma": ["P33-A1", "P31-G36"]},
    {"nhom": "lineage", "can": "SHA HEAD + schema version; không đọc dashboard.env theo luật bảo mật", "ma": []},
]


def group_of(item: Dict) -> str:
    cat = item.get("category")
    return next((g for g, cats in GROUPS.items() if cat in cats), "khac")


def cases(registry: Dict) -> List[Dict]:
    out = []
    for it in registry.get("items") or []:
        kind = KINDS.get(it.get("status"))
        if kind is None or not it.get("tests"):
            continue
        out.append({"id": it["id"], "kind": kind, "group": group_of(it), "status_so": it.get("status"), "title": it.get("title"),
                    "tests": list(it["tests"])})
    return out


def untested(registry: Dict) -> List[str]:
    return [it["id"] for it in registry.get("items") or [] if it.get("status") in KINDS and not it.get("tests")]


def missing_tests(cs: List[Dict], root: str = ROOT) -> List[str]:
    return sorted({t for c in cs for t in c["tests"] if not os.path.exists(os.path.join(root, t.split("::", 1)[0]))})


# ---- kết quả pytest (junit) ----------------------------------------------------------------------------------------------------
def _split_class(classname: str):
    parts = classname.split(".")
    mod_end = max((i for i, p in enumerate(parts) if p.startswith("test")), default=len(parts) - 1)
    return "/".join(parts[:mod_end + 1]) + ".py", "::".join(parts[mod_end + 1:])


def junit(path: str) -> List[Dict]:
    out = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        f, cls = _split_class(tc.get("classname") or "")
        qual = f"{cls}::{tc.get('name')}" if cls else tc.get("name")
        status = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                status = "failed"
            elif child.tag == "skipped":
                status = "xfailed" if "xfail" in (child.get("type") or "") else "skipped"
        out.append({"file": f, "qual": qual, "status": status})
    return out


def node_status(node: str, res: List[Dict]) -> str:
    f, _, rest = node.partition("::")
    hits = [r for r in res if r["file"] == f and (not rest or r["qual"] == rest or r["qual"].startswith(rest + "["))]
    if not hits:
        return "missing"
    states = {r["status"] for r in hits}
    if "failed" in states:
        return "failed"
    if "passed" in states:
        return "passed"
    return "xfailed" if "xfailed" in states else "skipped"


def case_status(case: Dict, res: List[Dict]) -> str:
    states = [node_status(t, res) for t in case["tests"]]
    for s in ("failed", "missing", "passed", "xfailed"):
        if s in states:
            return s
    return "skipped"


# ---- MAY_CHINH: snapshot tóm tắt, chỉ đọc, không xuất nội dung dự án ------------------------------------------------------------
def open_db_readonly(path: str) -> sqlite3.Connection:
    """Mở CSDL hiện có bằng URI mode=ro và khóa mọi câu ghi ở cấp kết nối."""
    db_path = pathlib.Path(path).resolve(strict=True)
    if not db_path.is_file():
        raise FileNotFoundError("CSDL pilot không phải tệp thường")
    conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_fingerprints(db_path: pathlib.Path) -> Optional[Dict[str, Optional[str]]]:
    """Fingerprint database and WAL sidecar; unknown on any read/race error."""
    wal_path = db_path.with_name(db_path.name + "-wal")
    try:
        return {"database": _sha256_file(db_path), "wal": _sha256_file(wal_path) if wal_path.exists() else None}
    except OSError:
        return None


def _fingerprint_rows(rows: List[Dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, default=lambda value: value.hex() if isinstance(value, bytes) else str(value))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _table_columns(conn: sqlite3.Connection, table: str) -> set:
    # table names below are constants in this file, never user input.
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _query_summary(conn: sqlite3.Connection, tables: set, table: str, required: set, sql: str,
                   params: tuple = ()) -> Dict:
    if table not in tables:
        return {"status": "missing", "records": 0, "sha256": None}
    if not required <= _table_columns(conn, table):
        return {"status": "partial", "records": 0, "sha256": None}
    rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    return {"status": "available" if rows else "partial", "records": len(rows), "sha256": _fingerprint_rows(rows)}


def _within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _file_metadata(root: pathlib.Path, value: Optional[str], record_id: Optional[int] = None) -> Dict:
    result = {"record_id": record_id, "exists": False, "bytes": None, "outside_root": False}
    if not value:
        return result
    candidate = pathlib.Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve()
    except (OSError, RuntimeError):
        result["outside_root"] = True
        return result
    if not _within(candidate, root):
        result["outside_root"] = True
        return result
    try:
        stat = candidate.stat()
    except OSError:
        return result
    if candidate.is_file():
        result.update({"exists": True, "bytes": stat.st_size})
    return result


def _safe_command_env() -> Dict[str, str]:
    """Allow only OS execution paths for local git inspection; never forward API credentials."""
    return {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if os.environ.get(key)}


def _pytest_child_env(guard_out: str) -> Dict[str, str]:
    env = _safe_command_env()
    env.update({"PILOT_A_GUARD_OUT": str(guard_out), "PYTHONUTF8": "1",
                "PYTHONPATH": os.pathsep.join([os.path.join(ROOT, "tools"), ROOT])})
    return env


def capture_may_chinh(main_root: str) -> Dict:
    """Tóm tắt 7 nhóm dữ liệu MAY_CHINH; không trả nội dung prompt, sự kiện, đường dẫn hay ảnh."""
    root = pathlib.Path(main_root).resolve(strict=True)
    data_root = (root / "data").resolve(strict=True)
    if not data_root.is_dir() or not _within(data_root, root):
        raise ValueError("Thư mục data của pilot phải nằm trong gốc đã chọn")
    db_path = (data_root / "manifest.sqlite").resolve(strict=True)
    if not _within(db_path, data_root):
        raise ValueError("CSDL pilot phải nằm trong data/ của gốc đã chọn")
    before = _database_fingerprints(db_path)
    cases_out = []
    file_count = outside_count = 0
    conn = open_db_readonly(db_path)
    try:
        journal_mode_before = conn.execute("PRAGMA journal_mode").fetchone()[0]
        data_version_before = conn.execute("PRAGMA data_version").fetchone()[0]
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        versions = {name: conn.execute(f"PRAGMA {name}").fetchone()[0] for name in ("user_version", "schema_version")}

        jobs_required = {"id", "project_id", "scene_id", "type", "state", "sent_package", "sent_refs"}
        scenes_required = {"id", "project_id", "idx"}
        if "jobs" in tables and "scenes" in tables and jobs_required <= _table_columns(conn, "jobs") and scenes_required <= _table_columns(conn, "scenes"):
            payload_rows = [dict(row) for row in conn.execute(
                "SELECT j.id,j.project_id,s.idx,j.type,j.state,j.sent_package,j.sent_refs FROM jobs j "
                "JOIN scenes s ON s.id=j.scene_id WHERE (j.project_id=31 AND s.idx IN (27,28,29,30,33,35,36)) "
                "OR j.project_id=33 ORDER BY j.id").fetchall()]
            payload_summary = {"status": "available" if payload_rows else "partial", "records": len(payload_rows),
                               "sha256": _fingerprint_rows(payload_rows)}
        else:
            payload_summary = {"status": "partial", "records": 0, "sha256": None}
        cases_out.append({"id": "payload_sent_package", **payload_summary})

        if "jobs" in tables and "scenes" in tables and {"id", "project_id", "scene_id", "result_path"} <= _table_columns(conn, "jobs") and scenes_required <= _table_columns(conn, "scenes"):
            result_rows = conn.execute(
                "SELECT j.id,j.result_path FROM jobs j JOIN scenes s ON s.id=j.scene_id "
                "WHERE (j.project_id=33 AND s.idx IN (2,6)) OR (j.project_id=31 AND s.idx=33) ORDER BY j.id").fetchall()
            files = [_file_metadata(root, row["result_path"], row["id"]) for row in result_rows]
            file_count += len(files)
            outside_count += sum(1 for item in files if item["outside_root"])
            cases_out.append({"id": "qc_result_files", "status": "available" if result_rows else "partial", "records": len(result_rows),
                              "files": files, "outside_root_rejected": sum(1 for item in files if item["outside_root"]),
                              "sha256": _fingerprint_rows([dict(row) for row in result_rows])})
        else:
            cases_out.append({"id": "qc_result_files", "status": "partial", "records": 0, "files": [],
                              "outside_root_rejected": 0, "sha256": None})

        if "asset_images" in tables and {"id", "asset_id", "path"} <= _table_columns(conn, "asset_images"):
            image_rows = conn.execute("SELECT id,path FROM asset_images WHERE asset_id IN (427,367) ORDER BY asset_id,id").fetchall()
            images = [_file_metadata(root, row["path"], row["id"]) for row in image_rows]
            file_count += len(images)
            outside_count += sum(1 for item in images if item["outside_root"])
            cases_out.append({"id": "kho_reference_images", "status": "available" if image_rows else "partial", "records": len(image_rows),
                              "files": images, "sha256": _fingerprint_rows([dict(row) for row in image_rows])})
        else:
            cases_out.append({"id": "kho_reference_images", "status": "partial", "records": 0, "files": [], "sha256": None})

        continuity_rows = []
        for table in ("scenes", "story_scenes"):
            if table in tables and {"id", "project_id", "idx", "data"} <= _table_columns(conn, table):
                continuity_rows.extend({"table": table, **dict(row)} for row in conn.execute(
                    f"SELECT id,project_id,idx,data FROM {table} WHERE (project_id=31 AND idx IN (4,6,8)) OR project_id=33 ORDER BY id").fetchall())
        cases_out.append({"id": "scene_continuity", "status": "available" if continuity_rows else "partial", "records": len(continuity_rows),
                          "sha256": _fingerprint_rows(continuity_rows)})

        change_summary = _query_summary(conn, tables, "change_events", {"id", "at", "project_id", "state"},
            "SELECT id,at,state,keys,before,after FROM change_events WHERE project_id=31 AND at LIKE '2026-10-17%' ORDER BY id",
            ()) if "change_events" in tables and {"keys", "before", "after"} <= _table_columns(conn, "change_events") else {
                "status": "partial", "records": 0, "sha256": None}
        cases_out.append({"id": "change_lineage", **change_summary})

        target_jobs = tuple([1162, 1163] + list(range(1058, 1073)))
        placeholders = ",".join("?" for _ in target_jobs)
        recovery_rows = []
        for table, fields in (("job_events", {"id", "job_id", "to_state", "actor", "at"}),
                              ("diag_events", {"id", "job_id", "code", "count"})):
            if table in tables and fields <= _table_columns(conn, table):
                selected = sorted(fields)
                sql = f"SELECT {','.join(selected)} FROM {table} WHERE job_id IN ({placeholders}) ORDER BY id"
                recovery_rows.extend({"table": table, **dict(row)} for row in conn.execute(sql, target_jobs).fetchall())
        cases_out.append({"id": "job_recovery", "status": "available" if recovery_rows else "partial", "records": len(recovery_rows),
                          "sha256": _fingerprint_rows(recovery_rows)})

        head = None
        try:
            proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"], capture_output=True, text=True,
                                  timeout=5, check=True, env=_safe_command_env())
            head = proc.stdout.strip()[:40]
        except (OSError, subprocess.SubprocessError):
            pass
        cases_out.append({"id": "machine_provenance", "status": "partial", "git_head": head,
                          "schema_versions": versions})
        data_version_after = conn.execute("PRAGMA data_version").fetchone()[0]
        journal_mode_after = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    after = _database_fingerprints(db_path)
    fingerprints_known = before is not None and after is not None
    versions_known = data_version_before is not None and data_version_after is not None
    journal_known = journal_mode_before is not None and journal_mode_after is not None
    unchanged = None
    if fingerprints_known and versions_known and journal_known:
        unchanged = before == after and data_version_before == data_version_after and journal_mode_before == journal_mode_after
    return {"database": {"sha256_before": before.get("database") if before else None,
                         "sha256_after": after.get("database") if after else None,
                         "wal_sha256_before": before.get("wal") if before else None,
                         "wal_sha256_after": after.get("wal") if after else None,
                         "journal_mode_before": journal_mode_before, "journal_mode_after": journal_mode_after,
                         "data_version_before": data_version_before, "data_version_after": data_version_after,
                         "unchanged": unchanged,
                         "query_only": True, "schema_versions": versions},
            "cases": cases_out, "referenced_files": file_count, "outside_root_rejected": outside_count,
            "note": "Chỉ metadata/dấu vân tay; không xuất nội dung dự án hoặc đường dẫn. Không đọc dashboard.env hay thông tin bí mật.",
            "not_run_here": False}


def validate_output_paths(paths: List[str], data_roots: List[pathlib.Path]) -> None:
    """Không cho kết quả của pilot ghi vào bất kỳ thư mục data/ nào."""
    for raw in paths:
        if not raw:
            continue
        candidate = pathlib.Path(raw).resolve()
        if any(_within(candidate, root) for root in data_roots):
            raise ValueError("Đường dẫn kết quả nằm trong data/; hãy chọn thư mục ngoài dữ liệu dự án")


# ---- chấm tiêu chí (mục 1.3) ----------------------------------------------------------------------------------------------------
def evaluate(d: Dict) -> Dict:
    """d: {"cases": [{id, kind, status}], "golden": passed|failed|khong_do_duoc, "network": n, "data_writes": [...]}."""
    must_green = [c for c in d["cases"] if c["kind"] == "phai_xanh"]
    must_red = [c for c in d["cases"] if c["kind"] == "phai_do"]
    bad_green = [c["id"] for c in must_green if c["status"] != "passed"]
    bad_red = [c["id"] for c in must_red if c["status"] not in ("failed", "xfailed")]
    golden = {"passed": True, "failed": False}.get(d.get("golden"))
    crit = {
        "c1": {"ten": "ca sổ ghi đã sửa (chưa xác nhận) xanh", "dat": not bad_green, "chi_tiet": bad_green},
        "c2": {"ten": "compatibility golden (cờ TẮT = byte giống)", "dat": golden, "chi_tiet": d.get("golden")},
        "c3": {"ten": "0 kết nối ra ngoài (0 lời gọi trả tiền)", "dat": d.get("network", 0) == 0, "chi_tiet": d.get("network", 0)},
        "c4": {"ten": "0 ghi vào data/", "dat": not d.get("data_writes"), "chi_tiet": list(d.get("data_writes") or [])[:20]},
        "c5": {"ten": "ca chưa sửa (OPEN) còn đỏ, không xanh vì bỏ qua", "dat": not bad_red, "chi_tiet": bad_red},
    }
    vals = [c["dat"] for c in crit.values()]
    result = "ROT" if False in vals else "CHUA_DO_DU" if None in vals else "DAT_OFFLINE"
    return {"ket_qua": result, "tieu_chi": crit,
            "ghi_chu": "Vòng A offline không đổi trạng thái sổ lỗi — xác nhận thật = vòng B (chạy thật, Cấp 3)."}


# ---- chạy ----------------------------------------------------------------------------------------------------------------------
def _data_status() -> set:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "data"], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, env=_safe_command_env()).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line[3:] for line in out.splitlines() if line.strip()}


def run(out_dir: str, xdist: bool = True) -> Dict:
    registry = json.load(open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8"))
    cs = cases(registry)
    nodes = sorted({t for c in cs for t in c["tests"]} | (set(GOLDEN_TESTS) if sys.version_info[:2] == GOLDEN_PY else set()))
    os.makedirs(out_dir, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    xml, guard_out = os.path.join(out_dir, f"pilot_a_{run_id}_junit.xml"), os.path.join(out_dir, f"pilot_a_guard_{run_id}")
    env = _pytest_child_env(guard_out)
    before = _data_status()
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "pilot_a_guard", "--tb=no", f"--junitxml={xml}"]
    if xdist:
        cmd += ["-n", "auto"]
    proc = subprocess.run(cmd + nodes, cwd=ROOT, env=env, capture_output=True, text=True)
    new_files = sorted(_data_status() - before)
    res = junit(xml) if os.path.exists(xml) else []
    net, hosts, writes = 0, set(), set(new_files)
    for f in glob.glob(guard_out + ".*.json"):
        g = json.load(open(f, encoding="utf-8"))
        net += g["network"]
        hosts |= set(g["network_hosts"])
        writes |= set(os.path.relpath(w, ROOT) if os.path.isabs(w) else w for w in g["data_writes"])
    for c in cs:
        c["status"] = case_status(c, res)
    if sys.version_info[:2] != GOLDEN_PY:
        golden = "khong_do_duoc"
    else:
        golden = "passed" if all(node_status(t, res) == "passed" for t in GOLDEN_TESTS) else "failed"
    verdict = evaluate({"cases": cs, "golden": golden, "network": net, "data_writes": sorted(writes)})
    return {"python": ".".join(map(str, sys.version_info[:3])), "pytest_rc": proc.returncode, "tail": proc.stdout.strip().splitlines()[-1:],
            "cases": cs, "khong_co_test": untested(registry), "missing_tests": missing_tests(cs), "network_hosts": sorted(hosts),
            "verdict": verdict, "may_chinh": MAY_CHINH}


def markdown(rep: Dict) -> str:
    v = rep["verdict"]
    L = [f"## Kết quả pilot vòng A (offline): **{v['ket_qua']}**", "",
         f"Python {rep['python']} · pytest rc={rep['pytest_rc']} · {' '.join(rep['tail'])}", "", "| Tiêu chí | Đạt | Chi tiết |", "|---|---|---|"]
    for k, c in v["tieu_chi"].items():
        mark = {True: "✅", False: "❌", None: "— không đo được"}[c["dat"]]
        L.append(f"| {k} {c['ten']} | {mark} | {json.dumps(c['chi_tiet'], ensure_ascii=False)[:300]} |")
    L += ["", "| Nhóm | Mã | Loại | Trạng thái sổ | Kết quả |", "|---|---|---|---|---|"]
    for c in sorted(rep["cases"], key=lambda x: (x["group"], x["kind"], x["id"])):
        L.append(f"| {c['group']} | {c['id']} | {c['kind']} | {c['status_so']} | {c['status']} |")
    L += ["", "Mục sổ lỗi đang mở / đã sửa mà CHƯA có test (không chấm được): " + (", ".join(rep["khong_co_test"]) or "—"),
          "", "### Dữ liệu cần máy chính chụp (chỉ đọc, D08)", ""]
    L += [f"- [{m['nhom']}] {m['can']}" + (f" — mã {', '.join(m['ma'])}" if m["ma"] else "") for m in rep["may_chinh"]]
    snapshot = rep.get("may_chinh_snapshot")
    if snapshot:
        db = snapshot["database"]
        L += ["", "### Snapshot MAY_CHINH (chỉ đọc)", "",
              f"- SHA CSDL trước/sau: `{db['sha256_before']}` / `{db['sha256_after']}` · không đổi: **{db['unchanged']}** · query_only: **{db['query_only']}**",
              f"- SHA WAL trước/sau: `{db['wal_sha256_before']}` / `{db['wal_sha256_after']}` · journal: `{db['journal_mode_before']}` / `{db['journal_mode_after']}` · data_version: `{db['data_version_before']}` / `{db['data_version_after']}`",
              f"- Tệp được kiểm tra: {snapshot['referenced_files']} · đường dẫn ngoài vùng gốc bị từ chối: {snapshot['outside_root_rejected']}",
              "", "| Ca | Trạng thái | Số bản ghi | Dấu vân tay |", "|---|---|---:|---|"]
        for case in snapshot["cases"]:
            fingerprint = case.get("sha256") or "—"
            L.append(f"| {case['id']} | {case['status']} | {case.get('records', '—')} | `{fingerprint}` |")
        L += ["", snapshot["note"]]
        if not db["unchanged"]:
            L += ["", "⚠ CSDL thay đổi trong lúc đo; cần phiên chính xem lại trước khi kết luận."]
    L += ["", v["ghi_chu"]]
    return "\n".join(L) + "\n"


def add_may_chinh_integrity(rep: Dict, snapshot: Dict) -> None:
    """Gắn cổng hash cho phép đo máy chính; hash lệch thì kết quả phải ROT."""
    unchanged = snapshot.get("database", {}).get("unchanged")
    rep["verdict"]["tieu_chi"]["c6"] = {
        "ten": "SHA CSDL máy chính trước/sau không đổi",
        "dat": unchanged if isinstance(unchanged, bool) else None,
        "chi_tiet": unchanged,
    }
    if unchanged is False:
        rep["verdict"]["ket_qua"] = "ROT"
    elif unchanged is None and rep["verdict"]["ket_qua"] == "DAT_OFFLINE":
        rep["verdict"]["ket_qua"] = "CHUA_DO_DU"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=os.path.join(tempfile.gettempdir(), "pilot_a"))
    ap.add_argument("--md")
    ap.add_argument("--json")
    ap.add_argument("--no-xdist", action="store_true")
    ap.add_argument("--may-chinh", action="store_true", help="đọc snapshot 7 ca trên máy chính; SQLite mode=ro, không xuất nội dung dự án")
    ap.add_argument("--main-root", default="D:/AI-Video-Pipeline", help="thư mục máy chính (chỉ dùng khi có --may-chinh)")
    a = ap.parse_args(argv)
    data_roots = [pathlib.Path(ROOT) / "data"]
    if a.may_chinh:
        data_roots.append(pathlib.Path(a.main_root) / "data")
    validate_output_paths([a.out_dir, a.md, a.json], data_roots)
    rep = run(a.out_dir, xdist=not a.no_xdist)
    if a.may_chinh:
        rep["may_chinh_snapshot"] = capture_may_chinh(a.main_root)
        add_may_chinh_integrity(rep, rep["may_chinh_snapshot"])
    text = markdown(rep)
    print(text)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(text)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    return {"DAT_OFFLINE": 0, "CHUA_DO_DU": 2}.get(rep["verdict"]["ket_qua"], 1)


if __name__ == "__main__":
    sys.exit(main())
