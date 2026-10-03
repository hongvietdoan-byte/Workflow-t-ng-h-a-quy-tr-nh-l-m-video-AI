"""Lưu kết quả ĐO GIAO DIỆN THẬT cho AI Development System (thang bản 2: khu vực giao diện chưa có file này bị giới hạn trai_nghiem ≤ 6/10).

    py tools/devsys_ui_metrics.py --run-acceptance                 chạy py tools/ui_v2_acceptance.py all (0 USD, nhà cung cấp giả; vài phút) rồi lưu
    py tools/devsys_ui_metrics.py --acceptance out.txt             đọc đầu ra đã lưu của ui_v2_acceptance.py all
    py tools/devsys_ui_metrics.py --contrast contrast.txt          đọc kết quả tools/ui_contrast_audit.js (mỗi dòng "<vùng> | chữ<4.5: N | chữ<12.5px: M")
    py tools/devsys_ui_metrics.py --show                           in số đo đang lưu
Có thể truyền cả --acceptance và --contrast một lần. Ghi devsys/data/ui_metrics.json (không commit). Không gọi API, không tốn tiền.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from devsys import collect, metrics  # noqa: E402


def read_text(path: str) -> str:
    """A text file saved by a Windows shell can be UTF-16 (PowerShell `>`): try the BOMs first."""
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeError:
            continue
    return data.decode("utf-8", errors="replace")


def save(root: str, acceptance: str = "", contrast: str = "", source: str = "") -> dict:
    prev = metrics.ui_metrics(root) or {}
    new = metrics.ui_from_text(acceptance, contrast, source)
    for k, v in new.items():                       # one run may bring only one of the two measures: keep the other from before
        if v is None and prev.get(k) is not None:
            new[k] = prev[k]
    hd = collect.head(root) or {}
    new.update(date=collect.now_iso(), commit=hd.get("hash"))
    path = os.path.join(root, metrics.UI_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    return new


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lưu số đo giao diện thật cho thang chấm bản 2")
    ap.add_argument("--run-acceptance", action="store_true", help="chạy tools/ui_v2_acceptance.py all rồi lưu")
    ap.add_argument("--acceptance", metavar="FILE", help="đầu ra đã lưu của tools/ui_v2_acceptance.py all")
    ap.add_argument("--contrast", metavar="FILE", help="kết quả tools/ui_contrast_audit.js")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args(argv)
    if args.show or not (args.run_acceptance or args.acceptance or args.contrast):
        cur = metrics.ui_metrics(ROOT)
        print(json.dumps(cur, ensure_ascii=False, indent=1) if cur else "Chưa có số đo giao diện thật (devsys/data/ui_metrics.json).")
        return 0
    acc, con, src = "", "", []
    if args.run_acceptance:
        proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_v2_acceptance.py"), "all"], cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        acc = proc.stdout
        print(acc)
        src.append("tools/ui_v2_acceptance.py all" + ("" if proc.returncode == 0 else f" (mã thoát {proc.returncode}: có phép đo không đạt)"))
    if args.acceptance:
        acc = read_text(args.acceptance)
        src.append(os.path.basename(args.acceptance))
    if args.contrast:
        con = read_text(args.contrast)
        src.append(os.path.basename(args.contrast))
    out = save(ROOT, acc, con, "; ".join(src))
    print("Đã lưu devsys/data/ui_metrics.json:", json.dumps({k: out[k] for k in ("clicks_old", "clicks_v2", "perf_worst_pct", "keys_lost",
                                                                              "contrast_fail", "small_text", "zones")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    os.chdir(ROOT)
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
