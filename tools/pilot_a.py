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
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
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
    {"nhom": "lineage", "can": "SHA HEAD + dòng FEATURE_ của dashboard.env + schema version (D08)", "ma": []},
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
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "data"], cwd=ROOT, capture_output=True, text=True,
                             timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line[3:] for line in out.splitlines() if line.strip()}


def run(out_dir: str, xdist: bool = True) -> Dict:
    registry = json.load(open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8"))
    cs = cases(registry)
    nodes = sorted({t for c in cs for t in c["tests"]} | (set(GOLDEN_TESTS) if sys.version_info[:2] == GOLDEN_PY else set()))
    os.makedirs(out_dir, exist_ok=True)
    xml, guard_out = os.path.join(out_dir, "pilot_a_junit.xml"), os.path.join(out_dir, "pilot_a_guard")
    for old in glob.glob(guard_out + ".*.json"):
        os.remove(old)
    env = dict(os.environ, PILOT_A_GUARD_OUT=guard_out, PYTHONUTF8="1",
               PYTHONPATH=os.pathsep.join([os.path.join(ROOT, "tools"), ROOT, os.environ.get("PYTHONPATH", "")]))
    before = _data_status()
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "pilot_a_guard", f"--junitxml={xml}"]
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
    L += ["", v["ghi_chu"]]
    return "\n".join(L) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=os.path.join(tempfile.gettempdir(), "pilot_a"))
    ap.add_argument("--md")
    ap.add_argument("--json")
    ap.add_argument("--no-xdist", action="store_true")
    a = ap.parse_args(argv)
    rep = run(a.out_dir, xdist=not a.no_xdist)
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
