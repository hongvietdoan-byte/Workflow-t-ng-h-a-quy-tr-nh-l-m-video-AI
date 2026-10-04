"""Reference-video research from the command line (kế hoạch v3, GĐ1). Only text data is written to the repo.

  py tools/reference_video.py sheets <video.mp4> <work_dir>            cut shots, one frame per shot, contact sheets
  py tools/reference_video.py label <work_dir> <STYLE> [--title T]      label with the Dashboard's Claude (LLM_PROVIDER) and save
  py tools/reference_video.py save <work_dir> <STYLE> <labels.json> [--title T] [--source S]
                                                                        save labels written in the chat session
  py tools/reference_video.py cuts <STYLE> <source url> <duration> <cuts.json|diffs.json> <labels.json> [--title T] [--width W --height H]
                                                                        a video cut in the browser (YouTube): cut times or frame diffs
  py tools/reference_video.py stats [STYLE]                             numbers per style (for knowledge/ff_styles/*.md)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import reference_analysis as ra  # noqa: E402


def _sheets(args):
    from core.video_analysis import probe
    meta = probe(args.video)
    shots = ra.shots_from_cuts(ra.detect_cuts(args.video, args.threshold), meta["duration_sec"] or 0)
    frames = ra.mid_frames(args.video, shots, args.work)
    sheets = ra.contact_sheets(frames, shots, args.work, portrait=bool(meta.get("height") and meta["height"] > (meta.get("width") or 0)))
    with open(os.path.join(args.work, "shots.json"), "w", encoding="utf-8") as f:
        json.dump({"source": args.video, "meta": meta, "shots": shots, "sheets": [p for _, p in sheets]}, f, ensure_ascii=False, indent=1)
    print(json.dumps({"shots": len(shots), "duration": meta["duration_sec"], "sheets": [p for _, p in sheets]}, ensure_ascii=False))


def _load_work(work):
    with open(os.path.join(work, "shots.json"), encoding="utf-8") as f:
        return json.load(f)


def _label(args):
    from core import llm_runner
    work = _load_work(args.work)
    db = os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite"))
    client = llm_runner.client_from_env(ledger=db if os.path.exists(db) else None)
    if client is None:
        raise SystemExit("Chưa cấu hình Claude (LLM_PROVIDER / ANTHROPIC_API_KEY)")
    sheets = [(f"Bảng khung hình {i}:", p) for i, p in enumerate(work["sheets"], 1)]
    labels = ra.label(client, args.style, work["meta"], work["shots"], sheets, args.title or os.path.basename(work["source"]))
    path = ra.save_record(args.style, work["source"], args.title or os.path.splitext(os.path.basename(work["source"]))[0],
                          work["meta"], ra.merge_labels(work["shots"], labels), labels.get("overall"))
    print(path)


def _save(args):
    work = _load_work(args.work)
    with open(args.labels, encoding="utf-8") as f:
        labels = ra.validate_labels(json.load(f), len(work["shots"]))
    source = args.source or work["source"]
    path = ra.save_record(args.style, source, args.title or os.path.splitext(os.path.basename(work["source"]))[0], work["meta"],
                          ra.merge_labels(work["shots"], labels), labels.get("overall"), method="ffmpeg")
    print(path)


def _cuts(args):
    with open(args.cuts, encoding="utf-8") as f:
        raw = json.load(f)
    cuts = ra.cuts_from_diffs([tuple(x) for x in raw]) if raw and isinstance(raw[0], list) else [float(x) for x in raw]
    shots = ra.shots_from_cuts(cuts, float(args.duration))
    with open(args.labels, encoding="utf-8") as f:
        labels = ra.validate_labels(json.load(f), len(shots))
    meta = {"duration_sec": float(args.duration), "width": args.width, "height": args.height}
    path = ra.save_record(args.style, args.source, args.title or args.source, meta, ra.merge_labels(shots, labels),
                          labels.get("overall"), method="browser")
    print(path)


def _stats(args):
    styles = [args.style] if args.style else sorted(ra.STYLES)
    for st in styles:
        recs = ra.load_records(st)
        if recs:
            print(ra.stats_markdown(st, ra.style_stats(recs)) + "\n")
    allrec = ra.load_records()
    if not args.style and allrec:
        print(ra.stats_markdown("ALL", ra.style_stats(allrec)))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets"); s.add_argument("video"); s.add_argument("work"); s.add_argument("--threshold", type=float, default=ra.DEFAULT_THRESHOLD)
    s.set_defaults(fn=_sheets)
    s = sub.add_parser("label"); s.add_argument("work"); s.add_argument("style", choices=sorted(ra.STYLES)); s.add_argument("--title")
    s.set_defaults(fn=_label)
    s = sub.add_parser("save"); s.add_argument("work"); s.add_argument("style", choices=sorted(ra.STYLES)); s.add_argument("labels")
    s.add_argument("--title"); s.add_argument("--source"); s.set_defaults(fn=_save)
    s = sub.add_parser("cuts"); s.add_argument("style", choices=sorted(ra.STYLES)); s.add_argument("source"); s.add_argument("duration")
    s.add_argument("cuts"); s.add_argument("labels"); s.add_argument("--title"); s.add_argument("--width", type=int); s.add_argument("--height", type=int)
    s.set_defaults(fn=_cuts)
    s = sub.add_parser("stats"); s.add_argument("style", nargs="?"); s.set_defaults(fn=_stats)
    from core import script_cap  # noqa: E402  (S14.2: trần CỨNG --max-usd, bắt buộc khi gọi API trả tiền)
    script_cap.add_argument(ap)
    args = ap.parse_args()
    script_cap.from_args(argparse.Namespace(paid=args.cmd == "label", max_usd=args.max_usd), "reference_video").start()
    if getattr(args, "work", None) and args.cmd == "sheets":
        os.makedirs(args.work, exist_ok=True)
    args.fn(args)


if __name__ == "__main__":
    main()
