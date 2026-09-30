"""Polish the pictures sent to the video model (người dùng 30/09: "tối ưu những ảnh video để gửi cho model, có thể dùng Deepix").

A character's reference pictures often come small (a 445 px in-game crop), on a coloured background, or as a sheet of 20 tiny panels;
the skill frames carry game interface. This redraws ONE picture with Deepix from the given references — same person, cleaner, larger —
under a hard cap of its own, with the ledger and the global cap checked before every send:

    py tools/asset_polish.py draw --name orion_front --size 1024x1536 --model gpt-image-2.5-sunburst \\
        --ref a.png --ref b.png --prompt "..."          → D:/AI-Video-Output/2026-09-30_tai_san_toi_uu/<name>_<n>.png

Every picture is logged in polish_log.json next to it (prompt, references, model, size, USD). The person (or Claude reading it) looks at
each one before it goes into the library — nothing is added to the library here."""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

OUT = r"D:\AI-Video-Output\2026-09-30_tai_san_toi_uu"
CAP_USD = 1.0           # người dùng 30/09: part of the approved 15 USD test money — this job's own hard cap
IMAGE_USD = 0.052


def _log_path():
    return os.path.join(OUT, "polish_log.json")


def load_log():
    try:
        with open(_log_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def spent(log=None) -> float:
    return round(sum(float(x.get("usd") or 0) for x in (log if log is not None else load_log())), 3)


def draw(name, prompt, refs, size, model, db=r"D:\AI-Video-Pipeline\data\manifest.sqlite"):
    from core import budget
    from core.adapters import factory
    from core.cost import record_usage
    from core.db import connect
    from core.providers import ProviderError
    os.makedirs(OUT, exist_ok=True)
    log = load_log()
    if spent(log) + IMAGE_USD > CAP_USD + 1e-9:
        raise SystemExit(f"TRẦN CHẶN: đã chi ${spent(log):.2f} cho việc tối ưu tài sản, trần ${CAP_USD:.2f}")
    for r in refs:
        if not os.path.exists(r):
            raise SystemExit("thiếu ảnh tham chiếu: " + r)
    conn = connect(db)
    provider = factory.image_provider()
    with budget.SPEND_LOCK:
        over = budget.check_image(conn, provider.name, model)
        if over:
            raise SystemExit("TRẦN CHUNG CHẶN: " + over)
        try:
            ext = provider.submit(prompt, refs, size=size, model=model)
        except ProviderError as e:
            raise SystemExit(f"Deepix từ chối: [{e.code}] {e}")
        info = getattr(provider, "usage_info", None)
        used, tier = info(model) if info else (model, None)
        record_usage(conn, None, "image", provider.name, used, tier, 1, "image", project_id=None, stage="asset_polish")
    n = sum(1 for x in log if x["name"] == name) + 1
    dest = os.path.join(OUT, f"{name}_{n}.png")
    entry = {"name": name, "file": os.path.basename(dest), "prompt": prompt, "refs": refs, "model": model, "size": size, "usd": IMAGE_USD,
             "external_id": ext, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "state": "running"}
    log.append(entry)
    json.dump(log, open(_log_path(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t0 = time.time()
    while time.time() - t0 < 900:
        st = provider.status(ext)
        if st.state == "succeeded":
            provider.download(ext, dest)
            entry["state"] = "ready"
            break
        if st.state == "failed":
            entry["state"] = "failed"
            entry["message"] = getattr(st, "message", "")
            break
        time.sleep(8)
    json.dump(log, open(_log_path(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(entry["state"], dest if entry["state"] == "ready" else entry.get("message", ""), f"· đã chi ${spent(log):.2f} / ${CAP_USD:.2f}")
    return dest if entry["state"] == "ready" else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("draw", "spent"))
    ap.add_argument("--name")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--size", default="1024x1536")
    ap.add_argument("--model", default="gpt-image-2.5-sunburst")
    a = ap.parse_args(argv)
    if a.step == "spent":
        print(spent())
        return
    from tools.experiments.group_test import load_env
    load_env(r"D:\AI-Video-Pipeline")
    prompt = open(a.prompt_file, encoding="utf-8").read() if a.prompt_file else a.prompt
    draw(a.name, prompt, a.ref, a.size, a.model)


if __name__ == "__main__":
    main()
