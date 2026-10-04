r"""S11.2 — bộ đo 5 ý tưởng thô cho 💡 Ý tưởng → kịch bản (docs/KE_HOACH_TINH_NANG_DIRECTOR_2026-10-01.md mục 2).

    py tools/experiments/idea_script_eval.py                                          kế hoạch (0 USD): số ý tưởng, ước tính
    py tools/experiments/idea_script_eval.py --yes --max-usd 1.0                      chạy thật (Claude), ghi calls.jsonl + phiếu chấm
    py tools/experiments/idea_script_eval.py --replay <calls.jsonl>                   chạy lại offline từ bản ghi (0 USD)
    py tools/experiments/idea_script_eval.py --score <phiếu đã chấm .md> --run <run>  đọc điểm → cổng bật cờ

Mỗi ý tưởng đi đủ 4 lượt tự động: câu trả lời mặc định (ghi `defaulted`) → hướng 1 → dàn ý giữ nguyên → kịch bản; người dùng chấm 1–5
theo 5 tiêu chí. Cổng bật cờ `idea_to_script`: TB ≥ 4 và 0 lỗi chặn của kiểm code. Tiền tính vào dự án riêng 'Nghiệm thu Biên kịch'.
Kết quả: data/idea_golden/runs/<giờ>/result.json + calls.jsonl; phiếu docs/DO_S11_2_Y_TUONG_<ngày>.md.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "experiments"))
from core import script_cap  # noqa: E402  (S14.2: trần cứng --max-usd)
EVAL_PROJECT = "Nghiệm thu Biên kịch"
IDEAS = os.path.join(ROOT, "data", "idea_golden", "ideas.json")
CRITERIA = ("giữ ý", "hook", "logic", "độ dài", "quay được")
GATE_MEAN = 4.0
TURNS = 4


def _key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class RecordingClient:
    """Wraps a real client's `complete` (what core/idea_to_script asks through): every call written to `path` as one JSON line."""

    def __init__(self, inner, path: str):
        self.inner, self.path = inner, path
        self.model = getattr(inner, "model", "")

    def complete(self, prompt, images=()):
        reply = self.inner.complete(prompt, images)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": _key(prompt), "model": self.model, "text": reply.text, "input_tokens": reply.input_tokens,
                                 "output_tokens": reply.output_tokens, "cache_read_tokens": reply.cache_read_tokens,
                                 "cache_write_tokens": reply.cache_write_tokens, "stop_reason": reply.stop_reason},
                                ensure_ascii=False) + "\n")
        return reply


class ReplayClient:
    """Answers recorded prompts again (0 USD); a prompt not in the record raises — the code changed what is sent."""
    name = "replay"

    def __init__(self, path: str):
        from core.llm_runner import LlmReply
        self.model, self.calls, self.misses = "replay", {}, 0
        for line in open(path, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                self.calls[d["key"]] = LlmReply(d["text"], d.get("input_tokens", 0), d.get("output_tokens", 0), d.get("stop_reason", ""),
                                                d.get("cache_write_tokens", 0), d.get("cache_read_tokens", 0))

    def complete(self, prompt, images=()):
        from core.llm_runner import LlmError
        k = _key(prompt)
        if k not in self.calls:
            self.misses += 1
            raise LlmError("replay: prompt này chưa có trong bản ghi (code đã đổi điều gửi đi)", code="replay_miss")
        return self.calls[k]


def run_idea(p, pid: int, item: dict, client) -> dict:
    """The 4 turns with the eval's fixed choices; returns the final state (+ error when a turn failed — the turns done are kept)."""
    from core import idea_to_script as I
    I.start(p.conn, pid, item["idea"], duration_s=int(item.get("duration_s") or 30), characters=item.get("characters") or [],
            cta=item.get("cta") or "", trend="off")
    steps = (lambda: I.questions(p.conn, pid, client), lambda: I.answer(p.conn, pid, []),
             lambda: I.directions(p.conn, pid, client), lambda: I.outline(p.conn, pid, client, 0),
             lambda: I.write(p.conn, pid, client))
    for step in steps:
        step()
    return I.get_state(p.conn, pid)


def run_all(p, pid: int, items, client, max_usd, log=print) -> dict:
    """max_usd: the run's hard lock is core.script_cap (main); here it only labels llm_runner.spend_cap (None = replay, 0 USD)."""
    from core import idea_to_script as I, llm_runner, script_cap
    results, errors = {}, []
    hard = script_cap.active() or script_cap.NO_CAP
    with llm_runner.tagged(I.STAGE, pid), llm_runner.spend_cap(max_usd or float("inf"), "đo Biên kịch") as cap:
        for it in items:
            if not hard.allow(TURNS * I.TURN_USD, f"ý tưởng {it['id']} ({TURNS} lượt)"):
                errors.append({"id": it["id"], "error": hard.stopped, "code": "script_cap"})
                break
            try:
                st = run_idea(p, pid, it, client)
            except script_cap.CapReached as e:          # S14.2: chạm --max-usd giữa ý tưởng — giữ các ý tưởng đã xong
                errors.append({"id": it["id"], "error": str(e), "code": "script_cap"})
                break
            except (llm_runner.LlmError, I.IdeaError) as e:
                st = I.get_state(p.conn, pid)
                st["error"] = str(e)
                code = getattr(e, "code", "idea")
                errors.append({"id": it["id"], "error": str(e), "code": code})
                log(f"ý tưởng {it['id']}: lỗi {code}: {e}")
                results[str(it["id"])] = st
                if code in ("budget", "auth", "config"):
                    break
                continue
            results[str(it["id"])] = st
            sc = st.get("script_checks") or {}
            log(f"ý tưởng {it['id']}: {sc.get('scenes', 0)} cảnh · ${float(st.get('spent') or 0):.3f}"
                + (f" · chặn: {sc['problems']}" if sc.get("problems") else "") + (f" · ghi chú: {len(sc.get('flags') or [])}"), flush=True)
        spent = cap["spent"]
    return {"results": results, "errors": errors, "usd": round(spent, 4)}


def blocking(st: dict) -> list:
    """Code-check blocks of one idea: script problems + outline blocks + a failed run."""
    out = list((st.get("script_checks") or {}).get("problems") or [])
    out += [c["text"] for c in st.get("outline_checks") or [] if c.get("level") == "block"]
    if st.get("error"):
        out.append(f"không chạy xong: {st['error']}")
    elif not st.get("script"):
        out.append("không có kịch bản")
    return out


def sheet(items, out: dict, run_dir: str) -> str:
    """The scoring sheet (Markdown): everything the person needs to judge each idea, then an empty 5 × 5 table."""
    from core import idea_to_script as I
    L = [f"# Bộ đo S11.2 — 💡 Ý tưởng thô → kịch bản ({time.strftime('%d/%m/%Y')})", "",
         f"Bản chạy: `{run_dir}` · tiền thật: **{out['usd']:.3f} USD** · chạy tự động: câu trả lời mặc định → hướng 1 "
         "→ dàn ý giữ nguyên → kịch bản.", "",
         f"**Cách chấm:** điền 1–5 vào bảng cuối phiếu cho 5 tiêu chí ({', '.join(CRITERIA)}). Cổng bật cờ `idea_to_script`: "
         f"TB ≥ {GATE_MEAN:g} và 0 lỗi chặn của kiểm code.", "",
         "- **giữ ý**: kịch bản còn đúng ý tưởng gốc, không lạc đề", "- **hook**: 3 s đầu đủ giữ người xem",
         "- **logic**: chuyện có nhân quả, kết có lý", "- **độ dài**: vừa thời lượng mục tiêu, thoại nói kịp",
         "- **quay được**: dựng được bằng nhân vật / nơi trong Kho FF, không cần cảnh bất khả thi", ""]
    for it in items:
        st = out["results"].get(str(it["id"])) or {}
        inp = st.get("inputs") or {}
        L += [f"## Ý tưởng {it['id']} — {inp.get('duration_s', it.get('duration_s'))} s", "", f"> {it['idea']}", "",
              f"Kiểm thêm: {it.get('tests', '')} · tiền: ${float(st.get('spent') or 0):.3f}", ""]
        if st.get("error"):
            L += [f"**⚠ Không chạy xong:** {st['error']}", ""]
        if st.get("answers"):
            L += ["**Câu hỏi của Biên kịch (dùng mặc định):**", ""]
            L += [f"- {a['q']} → _{a['a']}_" for a in st["answers"]]
            L.append("")
        if st.get("directions"):
            L += ["**3 hướng** (★ = hướng được chọn):", ""]
            for i, d in enumerate(st["directions"]):
                L.append(f"{i + 1}. {'★ ' if i == st.get('chosen') else ''}**{d.get('title')}** — {d.get('logline')}  ")
                L.append(f"   hook 3 s: {d.get('hook_3s')} · cú chốt: {d.get('payoff')}")
            L.append("")
        if st.get("beats"):
            L += ["**Dàn ý theo giây:**", "", "| Nhịp | Giây | Nơi · ai | Nội dung | Thoại |", "|---|---|---|---|---|"]
            for b in st["beats"]:
                talk = " / ".join(f"{d.get('speaker')}: {d.get('line')}" for d in b.get("dialogue") or [] if isinstance(d, dict))
                cells = [str(b.get("name")), f"{b.get('start')}–{b.get('end')}", f"{b.get('place') or ''} · {', '.join(b.get('who') or [])}",
                         str(b.get("what") or ""), talk]
                L.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
            L.append("")
            for c in st.get("outline_checks") or []:
                L.append(f"- {'⛔' if c['level'] == 'block' else '⚠'} {c['text']}")
            L.append("")
        if st.get("script"):
            L += ["**Kịch bản** (dòng bắt đầu `+` = Biên kịch thêm, không có trong ý tưởng):", "", "```"]
            L += [("+ " if m["new"] else "  ") + m["text"] for m in I.marked_lines(it["idea"], st["script"])]
            L += ["```", ""]
            sc = st.get("script_checks") or {}
            L += [f"Kiểm code: {sc.get('scenes', 0)} cảnh · {'✅ đạt' if sc.get('ok') else '⛔ chặn'}"]
            L += [f"- ⛔ {x}" for x in sc.get("problems") or []] + [f"- ⚠ {x}" for x in sc.get("flags") or []]
            L.append("")
    L += ["## Bảng điểm (điền 1–5)", "", "| Ý tưởng | " + " | ".join(CRITERIA) + " | Ghi chú |",
          "|---|" + "---|" * (len(CRITERIA) + 1)]
    L += [f"| {it['id']} |" + "  |" * len(CRITERIA) + "  |" for it in items]
    return "\n".join(L) + "\n"


def read_scores(path: str) -> dict:
    """{idea id: [5 scores]} from the filled table; a row with an empty or out-of-range cell is refused (no silent zero)."""
    text = open(path, encoding="utf-8").read()
    part = text.split("## Bảng điểm", 1)
    if len(part) < 2:
        raise SystemExit("phiếu không có mục '## Bảng điểm'")
    scores = {}
    for line in part[1].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"\d+", cells[0]):
            continue
        vals = cells[1:1 + len(CRITERIA)]
        if len(vals) < len(CRITERIA) or not all(re.fullmatch(r"[1-5]", v) for v in vals):
            raise SystemExit(f"ý tưởng {cells[0]}: cần đủ {len(CRITERIA)} điểm 1–5, đang có {vals}")
        scores[cells[0]] = [int(v) for v in vals]
    if not scores:
        raise SystemExit("bảng điểm trống")
    return scores


def gate(scores: dict, results: dict) -> dict:
    allv = [v for row in scores.values() for v in row]
    per = {c: round(sum(row[i] for row in scores.values()) / len(scores), 2) for i, c in enumerate(CRITERIA)}
    blocks = {k: blocking(st) for k, st in results.items() if blocking(st)}
    missing = sorted(set(results) - set(scores))
    mean = round(sum(allv) / len(allv), 2)
    ok = mean >= GATE_MEAN and not blocks and not missing
    return {"mean": mean, "per_criterion": per, "per_idea": {k: round(sum(v) / len(v), 2) for k, v in scores.items()},
            "blocks": blocks, "unscored": missing, "pass": ok}


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join("data", "manifest.sqlite"))
    ap.add_argument("--ideas", default=IDEAS)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--yes", action="store_true")
    script_cap.add_argument(ap)          # S14.2: trần CỨNG, bắt buộc khi --yes
    ap.add_argument("--replay", default=None)
    ap.add_argument("--score", default=None, help="phiếu đã chấm (.md)")
    ap.add_argument("--run", default=None, help="thư mục bản chạy (với --score)")
    ap.add_argument("--sheet-dir", default=os.path.join(ROOT, "docs"))
    a = ap.parse_args(argv)
    if a.score:
        run_dir = a.run or os.path.dirname(os.path.abspath(a.score))
        res_path = os.path.join(run_dir, "result.json")
        out = json.load(open(res_path, encoding="utf-8"))
        g = gate(read_scores(a.score), out["results"])
        out["gate"] = g
        json.dump(out, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(g, ensure_ascii=False, indent=1))
        print("QUA — được bật cờ idea_to_script" if g["pass"] else "CHƯA QUA — giữ cờ TẮT")
        return g
    from core import idea_to_script as I
    from core.db import connect
    from core.pipeline import Pipeline
    items = json.load(open(a.ideas, encoding="utf-8"))
    if a.limit:
        items = items[:a.limit]
    usd = len(items) * TURNS * I.TURN_USD
    print(f"{len(items)} ý tưởng × {TURNS} lượt · ước tính ≈ ${usd:.2f} (trần mỗi ý tưởng ${I.RUN_CAP_USD:.2f}, trần cả bộ "
          + (f"${a.max_usd:.2f})" if a.max_usd is not None else "chưa khai --max-usd)"))
    hard = script_cap.from_args(argparse.Namespace(yes=a.yes and not a.replay, max_usd=a.max_usd), "đo Biên kịch")
    if not a.yes and not a.replay:
        print("(chưa chạy — thêm --yes để chạy thật, hoặc --replay <calls.jsonl> để chạy lại 0 USD)")
        return None
    p = Pipeline(connect(a.db))
    run_dir = os.path.join(os.path.dirname(os.path.abspath(a.db)), "idea_golden", "runs", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    row = p.conn.execute("SELECT id FROM projects WHERE name=?", (EVAL_PROJECT,)).fetchone()
    pid = row["id"] if row else p.create_project(EVAL_PROJECT, created_by="idea_script_eval", game="FF", aspect="9:16")
    if a.replay:
        client = ReplayClient(a.replay)
    else:
        from core import llm_runner, project_budget
        from group_test import load_env
        load_env(os.path.dirname(os.path.dirname(os.path.abspath(a.db))))   # dashboard.env next to the data folder
        real = llm_runner.client_from_env(ledger=a.db)
        if real is None or getattr(real, "name", "") == "mock-llm":
            raise SystemExit("cần Claude API (LLM_PROVIDER=anthropic)")
        over = project_budget.check(p.conn, pid, project_budget.claude_stage(I.STAGE), usd)
        if over:
            raise SystemExit(f"dừng trước khi chạy: {over}")
        client = RecordingClient(real, os.path.join(run_dir, "calls.jsonl"))
        hard.start()
        print(f"tiền tính vào dự án #{pid} '{EVAL_PROJECT}'")
    out = run_all(p, pid, items, client, a.max_usd)
    out.update(ideas=items, replay_misses=getattr(client, "misses", 0), model=getattr(client, "model", ""))
    json.dump(out, open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    path = os.path.join(a.sheet_dir, f"DO_S11_2_Y_TUONG_{time.strftime('%Y-%m-%d')}{'_replay' if a.replay else ''}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sheet(items, out, run_dir))
    print(f"tiền thật ${out['usd']:.3f} · lỗi {len(out['errors'])} · ghi: {run_dir}\nphiếu chấm: {path}")
    return out


if __name__ == "__main__":
    main()
