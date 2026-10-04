"""C — hoàn thiện hồ sơ nháp so với thông tin CHÍNH THỨC của trang Free Fire (người dùng 02/10/2026): chỉ cần đủ ý chính, không cần hoàn hảo.

    py tools/profile_finalize.py                      chỉ ước tính
    py tools/profile_finalize.py --yes --max-usd 0.5  gọi Claude (chỉ chữ, không ảnh): 1 lượt / nhân vật
    py tools/profile_finalize.py --yes --approve      duyệt luôn hồ sơ nào đủ ý chính (giới tính, tuổi/độ tuổi, vai trò)

Ý chính lấy từ khối `[ff.garena.com]` của mô tả (danh hiệu, giới tính, tuổi, tiểu sử) và `[Độ khó & vai trò gameplay]`: câu `identity` phải nêu
giới tính + tuổi (hoặc 'adult' / 'young, not yet 20' — luật tuổi: không ghi số dưới 18) + danh hiệu/vai trò + một nét tính cách hoặc tiểu sử.
Ngoại hình (must_keep…) giữ nguyên trừ khi lượt xem ảnh (library_vision_check) báo mâu thuẫn: khi đó sửa theo đúng mâu thuẫn đó.
Hồ sơ đã duyệt không bị đụng tới."""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import assets, script_cap  # noqa: E402

EST_USD = 0.006
GENDER = re.compile(r"\b(male|female|man|woman|boy|girl|he|she)\b", re.I)
AGE = re.compile(r"\b(\d{2}|adult|young|teen\w*|elderly|middle-aged)\b", re.I)
AGE_RULE = ("Never write an age number under 18 (the picture models refuse it): for such a character write 'young, not yet 20'. Adults may keep "
            "their age.")


def official_text(a: dict) -> str:
    d = a.get("description") or ""
    i = d.find("[ff.garena.com]")
    return d[i:] if i >= 0 else ""


def prompt_for(a: dict, prof: dict, issues: list) -> str:
    keys = ", ".join(assets.PROFILE_KEYS)
    return ("Finish the STANDARD PROFILE of a Free Fire character so it carries the MAIN facts of the official site text. Keep it a profile for "
            "picture/video models. Return the full profile as JSON with keys " + keys + ".\n"
            "1. `identity` = ONE English sentence that states: gender, age (or 'adult' / 'young, not yet 20'), the character's title or role "
            "(translate the Vietnamese title), one trait of personality or backstory from the official text, and the 3-5 things that identify "
            "the look. " + AGE_RULE + "\n"
            "2. Keep must_keep / may_change / forbidden / build as they are, EXCEPT fix what the picture check found wrong (listed below): correct "
            "only those items (remove a detail that is not visible, or add the one that is).\n"
            "3. height_m: only if the official text gives it, else null.\n"
            f"Character: {a['name']}\nOfficial site text (Vietnamese):\n{official_text(a)[:1500] or '—'}\n\n"
            f"Current profile (draft): {json.dumps({k: prof.get(k) for k in assets.PROFILE_KEYS}, ensure_ascii=False)}\n"
            f"Contradictions found by looking at the pictures: {json.dumps(issues, ensure_ascii=False) if issues else 'none'}\n"
            "Answer with the JSON only.")


def complete(identity: str) -> bool:
    return bool(GENDER.search(identity or "")) and bool(AGE.search(identity or ""))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("PIPELINE_DB", os.path.join("data", "manifest.sqlite")))
    ap.add_argument("--repo", default=None)
    ap.add_argument("--game", default="FF")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--approve", action="store_true")
    script_cap.add_argument(ap)          # S14.2: trần CỨNG, bắt buộc khi --yes
    ap.add_argument("--only", default="")
    ap.add_argument("--checks", default=os.path.join("data", "library_check.json"))
    a = ap.parse_args()
    cap = script_cap.from_args(a, "soạn hồ sơ nhân vật")
    if a.repo:
        assets.REPO = a.repo
    from core.db import connect
    conn = connect(a.db)
    checks = json.load(open(a.checks, encoding="utf-8")) if os.path.exists(a.checks) else {}
    only = {s.strip().lower() for s in a.only.split(",") if s.strip()}
    todo = []
    for c in assets.list_assets(conn, a.game, "character"):
        prof = assets.get_profile(conn, c["id"])
        if prof and not prof.get("approved") and (not only or c["name"].lower() in only) and official_text(c):
            todo.append((c, prof))
    print(f"{len(todo)} hồ sơ nháp có thông tin chính thức · ước tính ≈ ${EST_USD * len(todo):.2f} Claude (chỉ chữ)")
    if not a.yes:
        print("(chưa gọi Claude — thêm --yes)")
        return
    from core import budget, llm_io, llm_runner
    from core.adapters.check import load_dashboard_env
    load_dashboard_env()
    if budget.check_llm(conn):
        sys.exit(budget.check_llm(conn))
    client = llm_runner.client_from_env(ledger=a.db)
    if client is None:
        sys.exit("Chưa cấu hình Claude API.")
    start, ok, left = budget.llm_spent(conn), 0, []

    def check(obj) -> None:
        if not isinstance(obj, dict) or not all(k in obj for k in ("identity", "must_keep", "forbidden")):
            raise llm_io.SchemaError("root: {identity, must_keep, may_change, forbidden, height_m, build}")
        if re.search(r"\b(1[0-7]|[1-9])[- ]?(year[- ]old|yo)\b", json.dumps(obj), re.I):
            raise llm_io.SchemaError("an age under 18 is written — use 'young, not yet 20'")

    cap.start()
    for c, prof in todo:
        if not cap.allow(max(EST_USD, cap.estimate_llm("profile_draft"))):
            break                                    # script_cap đã in: đã chi bao nhiêu, vì sao dừng
        issues = (checks.get(c["name"]) or {}).get("profile_issues") or []
        try:
            with llm_runner.tagged("profile_draft"):
                obj = llm_runner.ask_json(client, prompt_for(c, prof, issues), check)[0]
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {c['name']}: {e}")
            left.append(c["name"])
            continue
        good = complete(obj.get("identity", ""))
        assets.set_profile(conn, c["id"], obj, approved=bool(a.approve and good), reason="soạn lại theo thông tin chính thức + đối chiếu ảnh (02/10)")
        ok += good
        if not good:
            left.append(c["name"])
        print(f"  {'✔' if good else '…'} {c['name']}: {obj.get('identity', '')[:110]}")
    print(f"đủ ý chính: {ok}/{len(todo)} · chưa đủ: {', '.join(left) or '—'} · đã dùng ≈ ${budget.llm_spent(conn) - start:.3f}")


if __name__ == "__main__":
    main()
