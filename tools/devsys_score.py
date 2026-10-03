"""Chấm điểm AI khách quan cho từng khu vực của hệ thống (AI Development System). Thang: devsys/rubric.md.

    py tools/devsys_score.py                      ước tính cho các khu vực đã đổi từ lần chấm trước (KHÔNG gọi gì)
    py tools/devsys_score.py --yes                chấm các khu vực đó (Claude API, ghi sổ chi stage "devsys", trần Claude)
    py tools/devsys_score.py --all --yes          chấm lại mọi khu vực
    py tools/devsys_score.py --areas step1,step5  chỉ các khu vực này
    py tools/devsys_score.py --provider mock --yes   người chấm giả lập (không mạng, không tiền) — thử luồng
    py tools/devsys_score.py --export step1       ghi dữ liệu đầu vào ra devsys/data/exports/step1.md cho người chấm ngoài (miễn phí)
    py tools/devsys_score.py --export all         như trên cho cả 16 khu vực
    py tools/devsys_score.py --import f.json --scorer claude-code-session   nhập điểm của người chấm ngoài
    py tools/devsys_score.py --report [out.md]    báo cáo hành động theo khu vực (vì sao trừ, sửa gì, ai làm, ưu tiên) → devsys/data/report.md
    py tools/devsys_score.py --compare            so điểm thang cũ (bản 1) ↔ mới (bản 2) theo khu vực
    py tools/devsys_score.py --stability          độ ổn định: điểm lệch giữa các lần chấm cùng thang

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


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:                           # another drive (Windows)
        return path


def _read_only(args, cfg) -> int:
    """--report / --compare / --stability: read the saved score files only (no measuring, no calls)."""
    all_scores, problems = scores.load_all(ROOT)
    real = [s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]
    for p in problems:
        print(f"⚠ file điểm không đọc được: {p}")
    if args.stability:
        st = scores.stability(real)
        if not st["n"]:
            print("Chưa có hai lần chấm cùng thang cho cùng một khu vực — chưa đo được độ ổn định.")
        else:
            print(f"{st['n']} cặp lần chấm liền nhau cùng thang: lệch trung bình {st['mean_abs']} điểm, lớn nhất {st['max_abs']}, "
                  f"{st['over_limit']} cặp lệch > {scores.DRIFT_LIMIT:g}; {len(st['noise'])} cặp lệch dù dấu vân tay không đổi (nhiễu của người chấm).")
            for p in st["pairs"]:
                print(f"  {p['area']:14} {p['from']:g} → {p['to']:g} (lệch {p['delta']:+g}) " + ("· vân tay không đổi" if p["same_fingerprint"] else "")
                      + ("· đã giải thích" if p["explained"] else ""))
    if args.compare:
        old = scores.latest_by_area([s for s in real if s.get("format") == scores.FORMAT])
        new = scores.latest_by_area([s for s in real if s.get("format") == scores.FORMAT_V2])
        if not new:
            print("Chưa có điểm bản 2 — chấm theo devsys/rubric.md (bản 2) rồi chạy lại.")
        for r in scores.compare_rounds(old, new, cfg):
            if r["old"] is None and r["new"] is None:
                continue
            crit = " ".join(f"{k}:{v['old_pct']}→{v['new_pct']}%" for k, v in r["criteria"].items())
            extra = " ".join(f"{k}:{v}%" for k, v in r["only_new"].items())
            print(f"  {r['area']:14} bản 1 {r['old'] if r['old'] is not None else '—':>5} · bản 2 {r['new'] if r['new'] is not None else '—':>5} "
                  f"· Δ {r['delta'] if r['delta'] is not None else '—':>6} | {crit} | chỉ bản 2: {extra or '—'}")
        o, n = scores.overall(old, cfg), scores.overall(new, cfg)
        print(f"Tổng có trọng số: bản 1 = {o['score']} ({len(o['covered'])} khu vực) · bản 2 = {n['score']} ({len(n['covered'])} khu vực)")
    if args.report is not None:
        latest = scores.latest_by_area(real)
        path = args.report or os.path.join(collect.data_dir(ROOT), "report.md")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(scores.action_report(latest, cfg))
        print(f"Đã ghi báo cáo hành động → {_rel(path)} ({len(latest)} khu vực)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chấm điểm AI khách quan các khu vực (devsys/rubric.md)")
    ap.add_argument("--all", action="store_true", help="chấm lại mọi khu vực (mặc định: chỉ khu vực đã đổi)")
    ap.add_argument("--areas", default="", help="danh sách id khu vực, cách nhau bằng dấu phẩy")
    ap.add_argument("--provider", default="anthropic", choices=("anthropic", "mock"))
    ap.add_argument("--yes", action="store_true", help="đồng ý chi phí đã ước tính và gọi thật")
    ap.add_argument("--export", metavar="AREA", help="ghi dữ liệu đầu vào của một khu vực (hoặc 'all') cho người chấm ngoài")
    ap.add_argument("--report", nargs="?", const="", metavar="FILE", help="ghi báo cáo hành động theo khu vực (mặc định devsys/data/report.md)")
    ap.add_argument("--compare", action="store_true", help="so điểm bản 1 ↔ bản 2 theo khu vực")
    ap.add_argument("--stability", action="store_true", help="độ ổn định giữa các lần chấm cùng thang")
    ap.add_argument("--import", dest="import_file", metavar="FILE", help="nhập file điểm của người chấm ngoài")
    ap.add_argument("--scorer", help="tên người chấm khi --import (vd. claude-code-session)")
    ap.add_argument("--db", default=None, help="sổ chi (mặc định data/manifest.sqlite hoặc PIPELINE_DB)")
    args = ap.parse_args(argv)

    cfg = collect.load_areas()
    if args.report is not None or args.compare or args.stability:
        return _read_only(args, cfg)
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
        by_id = collect.area_by_id(cfg)
        wanted = list(by_id) if args.export == "all" else [args.export]
        if any(w not in by_id for w in wanted):
            print(f"Không có khu vực '{args.export}'")
            return 2
        all_scores, _ = scores.load_all(ROOT)
        real = [s for s in all_scores if not str(s.get("scorer", "")).startswith("mock")]
        for aid in wanted:
            last = scores.latest_by_area(real).get(aid)
            b = scorer.build_bundle(ROOT, cfg, by_id[aid], snap, health[aid], last)
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
