"""Chấm điểm AI khách quan cho từng khu vực của hệ thống (AI Development System). Thang: devsys/rubric.md.

    py tools/devsys_score.py                      ước tính cho các khu vực đã đổi từ lần chấm trước (KHÔNG gọi gì)
    py tools/devsys_score.py --yes                chấm các khu vực đó (Claude API, ghi sổ chi stage "devsys", trần Claude)
    py tools/devsys_score.py --all --yes          chấm lại mọi khu vực
    py tools/devsys_score.py --areas step1,step5  chỉ các khu vực này
    py tools/devsys_score.py --provider mock --yes   người chấm giả lập (không mạng, không tiền) — thử luồng
    py tools/devsys_score.py --export step1       ghi dữ liệu đầu vào ra devsys/data/exports/step1.md cho người chấm ngoài (miễn phí)
    py tools/devsys_score.py --import f.json --scorer claude-code-session   nhập điểm của người chấm ngoài

Luôn in ước tính trước; không có --yes thì dừng ở đó.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from devsys import collect, scorer, scores  # noqa: E402


def _utf8_console() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")   # redirected to a log file (web) the code page cannot print Vietnamese
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chấm điểm AI khách quan các khu vực (devsys/rubric.md)")
    ap.add_argument("--all", action="store_true", help="chấm lại mọi khu vực (mặc định: chỉ khu vực đã đổi)")
    ap.add_argument("--areas", default="", help="danh sách id khu vực, cách nhau bằng dấu phẩy")
    ap.add_argument("--provider", default="anthropic", choices=("anthropic", "mock"))
    ap.add_argument("--yes", action="store_true", help="đồng ý chi phí đã ước tính và gọi thật")
    ap.add_argument("--export", metavar="AREA", help="ghi dữ liệu đầu vào của một khu vực cho người chấm ngoài")
    ap.add_argument("--import", dest="import_file", metavar="FILE", help="nhập file điểm của người chấm ngoài")
    ap.add_argument("--scorer", help="tên người chấm khi --import (vd. claude-code-session)")
    ap.add_argument("--db", default=None, help="sổ chi (mặc định data/manifest.sqlite hoặc PIPELINE_DB)")
    args = ap.parse_args(argv)

    cfg = collect.load_areas()
    snap = collect.collect(ROOT, cfg)
    health = collect.area_health(snap, cfg)

    if args.import_file:
        with open(args.import_file, encoding="utf-8") as f:
            raw = json.load(f)
        try:
            path = scorer.import_score(ROOT, cfg, snap, health, raw, args.scorer)
        except scores.ScoreError as e:
            print(f"Không nhập được: {e}")
            return 2
        print(f"Đã nhập điểm → {os.path.relpath(path, ROOT)}")
        return 0

    if args.export:
        area = collect.area_by_id(cfg).get(args.export)
        if area is None:
            print(f"Không có khu vực '{args.export}'")
            return 2
        all_scores, _ = scores.load_all(ROOT)
        last = scores.latest_by_area([s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]).get(area["id"])
        b = scorer.build_bundle(ROOT, cfg, area, snap, health[area["id"]], last)
        path = scorer.export_bundle(ROOT, b)
        print(f"Đã ghi dữ liệu đầu vào → {os.path.relpath(path, ROOT)} (~{b['chars'] // 3} token). Chấm theo devsys/rubric.md rồi --import.")
        return 0

    ids = [a.strip() for a in args.areas.split(",") if a.strip()] or None
    try:
        p = scorer.plan(ROOT, cfg, snap, health, ids, args.all, args.provider)
    except scorer.ScorerError as e:
        print(f"Lỗi: {e}")
        return 2
    for s in p["skipped"]:
        print(f"- bỏ qua {s['area']}: {s['why']}")
    for b in p["todo"]:
        print(f"- chấm {b['area']}: {b['why']} (~{b['chars'] // 3} token vào)" + (f" · cắt: {len(b['notes'])} mục" if b["notes"] else ""))
    if args.provider == "mock":
        print(f"Người chấm giả lập: {len(p['todo'])} khu vực, $0 (không gọi mạng, không ghi sổ chi).")
    else:
        est = scorer.estimate(p["todo"])
        print(scorer.estimate_text(est))
        if p["todo"] and not est["priced"]:
            return 2
    if not p["todo"]:
        return 0
    if not args.yes:
        print("Chưa gọi gì. Thêm --yes để đồng ý chi phí trên và chấm.")
        return 1
    try:
        res = scorer.run(ROOT, cfg, snap, p["todo"], args.provider, yes=True, db_path=args.db)
    except scorer.ScorerError as e:
        print(f"Không chấm: {e}")
        return 2
    print(f"Xong: {len(res['saved'])} khu vực đã lưu, {len(res['failed'])} lỗi, chi ≈ ${res['usd']:.4f}.")
    collect.append_event("score", ROOT, provider=args.provider, areas=[b["area"] for b in p["todo"]], saved=len(res["saved"]),
                         failed=res["failed"], usd=res["usd"])
    return 0 if not res["failed"] else 3


if __name__ == "__main__":
    os.chdir(ROOT)
    _utf8_console()
    sys.exit(main())
