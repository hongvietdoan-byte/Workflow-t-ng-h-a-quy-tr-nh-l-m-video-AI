"""Khu vực liên quan tới một thay đổi code (người dùng 10/10: "mỗi lần đổi bất kì điều gì trong khâu làm việc, đều cần 1 agent rà soát
lại những khâu liên quan đến nó"). Đọc devsys/areas.json: khu vực chứa file đổi + khu vực dùng chung cờ / gọi tới module đổi.
In đề bài cho agent rà (Claude Code chạy Agent với đề bài này TRƯỚC khi commit — CLAUDE.md quy ước 7).

  py tools/related_areas.py                    # file đổi so với HEAD (chưa commit)
  py tools/related_areas.py core/runner.py …   # file chỉ định
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def changed_files():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    return [line[3:].strip().strip('"') for line in out.splitlines() if line[3:].strip().endswith((".py", ".md", ".json", ".ps1"))]


def areas():
    a = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))
    return a["areas"] if isinstance(a, dict) else a


def _match(path, pats):
    return any(fnmatch.fnmatch(path, p) for p in pats or [])


def importers(module_file):
    """File .py trong core/ dashboard/ tools/ có import module này (gọi tới nó = khâu phụ thuộc)."""
    mod = os.path.splitext(os.path.basename(module_file))[0]
    pat = re.compile(rf"\b(from \. import [^\n]*\b{mod}\b|from core import [^\n]*\b{mod}\b|import core\.{mod}\b|from core\.{mod} import|"
                     rf"from \.{mod} import)")
    hits = []
    for d in ("core", "dashboard", "tools"):
        for base, _, files in os.walk(os.path.join(ROOT, d)):
            for f in files:
                if f.endswith(".py"):
                    p = os.path.join(base, f)
                    try:
                        if pat.search(open(p, encoding="utf-8").read()):
                            hits.append(os.path.relpath(p, ROOT).replace("\\", "/"))
                    except OSError:
                        pass
    return hits


def related(files):
    A = areas()
    own, users = {}, {}
    for f in files:
        for a in A:
            if any(_match(f, a.get(k)) for k in ("code", "assets", "tests", "docs")):
                own.setdefault(a["id"], set()).add(f)
        if f.endswith(".py") and f.startswith("core/"):
            for imp in importers(f):
                for a in A:
                    if _match(imp, a.get("code")):
                        users.setdefault(a["id"], set()).add(f"{imp} (gọi {os.path.basename(f)})")
    flags = {fl for a in A if a["id"] in own for fl in a.get("flags") or []}
    via_flag = {a["id"] for a in A if a["id"] not in own and set(a.get("flags") or []) & flags}
    return own, users, via_flag, A


def main(argv):
    files = [f.replace("\\", "/") for f in argv] or changed_files()
    if not files:
        print("không có file đổi")
        return
    own, users, via_flag, A = related(files)
    by = {a["id"]: a for a in A}
    print("# Đề bài agent rà khâu liên quan (CLAUDE.md quy ước 7)\n")
    print("File đổi:\n" + "\n".join(f"- {f}" for f in files))
    print("\nKhu vực chứa file đổi:")
    for k, fs in own.items():
        print(f"- {k} ({by[k].get('name', '')}): {', '.join(sorted(fs))} — test: {', '.join(by[k].get('tests') or []) or '—'}")
    print("\nKhu vực GỌI TỚI module đổi (phải rà hành vi của chúng):")
    for k, fs in users.items():
        if k not in own:
            print(f"- {k} ({by[k].get('name', '')}): {'; '.join(sorted(fs)[:6])}")
    if via_flag:
        print("\nKhu vực dùng chung cờ: " + ", ".join(sorted(via_flag)))
    print("\nViệc của agent: với từng khu vực trên, đọc chỗ dùng module/cờ đổi, tìm hành vi bị đổi theo mà chưa sửa / chưa có test "
          "(đầu vào cũ còn được dùng, giả định cũ, đường ghi khác, khóa cache, chặn gen, giao diện); trả danh sách lỗi có file:dòng + "
          "đề xuất sửa; không sửa code.")


if __name__ == "__main__":
    main(sys.argv[1:])
