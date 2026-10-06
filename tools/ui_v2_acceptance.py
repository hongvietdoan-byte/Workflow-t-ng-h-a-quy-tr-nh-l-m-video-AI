"""S13.10 nghiệm thu giao diện v2 bằng số — chạy lại được, không cần trình duyệt, không gọi API (mock hết).

    py tools/ui_v2_acceptance.py all              # cả ba phép đo, v2 so với bản cũ, in bảng
    py tools/ui_v2_acceptance.py clicks           # số click "Dự án mới → video đầu" (AppTest, kịch bản mẫu)
    py tools/ui_v2_acceptance.py keys             # khóa widget cũ ↔ mới: tĩnh (git, mặc định so với 28d655f) + động (AppTest mọi màn)
    py tools/ui_v2_acceptance.py states --out data/demo   # (sau seed_demo.py) thêm ca "Tự động đang chạy", hộp thư dài... cho ui_contrast_audit.js
    py tools/ui_v2_acceptance.py perf [--reps 25]  # thời gian rerun Storyboard 30 khung và ⌂ 50 dự án (UI_ACCEPT_EVENTS=N: số dòng chi tiêu mỗi dự án, mặc định 40)
Mỗi phép đo chạy hai tiến trình con (FEATURE_UI_V2=0 và =1) để mô-đun không giữ trạng thái giữa hai bản.
Kết quả: mã thoát 0 khi đạt (clicks v2 <= cũ; không khóa mất; perf <= +20 %), 1 nếu không.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP = os.path.join(ROOT, "dashboard", "app.py")
BASE_REV = "28d655f"          # commit ngay trước khi giao diện v2 vào dashboard/
# S14.14 G-a (06/10): màn Kịch bản / Video / Theo dõi không còn bản cũ → phép đo FEATURE_UI_V2=0 không còn là "bản cũ". Mốc số click của
# bản cũ, đo bằng `clicks` ở 7a7154f (ngay trước G-a, cũ 14 · v2 14): v2 phải không vượt mốc này.
OLD_CLICKS_BASELINE = 14
SCRIPT = ("CẢNH 1 - ĐÊM, RỪNG ELDER\nSương mù phủ kín khu rừng.\nLYRA: Có thứ gì đó đang theo chúng ta.\n\n"
          "CẢNH 2 - NGÀY, PHÁO ĐÀI\nKAEL đứng trên tường thành.\nKAEL: Chúng ta phải đi tiếp.")


def _env(v2: str, tmp: str) -> None:
    os.environ.update(PIPELINE_DB=os.path.join(tmp, "m.sqlite"), PIPELINE_DATA=os.path.join(tmp, "projects"),
                      KNOWLEDGE_USER_DIR=os.path.join(tmp, "ku"), AUDIO_PROVIDER="mock", IMAGE_PROVIDER="mock", VIDEO_PROVIDER="mock",
                      LLM_PROVIDER="mock", SUBJECT_PROVIDER="mock", MOCK_REAL_MEDIA="1", FEATURE_UI_V2=v2,
                      DASHBOARD_SYNC_BACKGROUND="0", DASHBOARD_AUTH="off")
    sys.path.insert(0, ROOT)


def _app():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def _type_script(at, pid: int = 1):
    """Dán kịch bản như người dùng: khung chat của step1_box (cờ idea_to_script — bật mặc định từ S14.43, cả v1 lẫn v2) hoặc ô dán cũ
    paste_<pid> (cờ tắt). Một lần nhập, không phải một click — giống ô dán cũ."""
    box = [c for c in at.get("chat_input") if c.key == f"box_in_{pid}"]
    if box:
        box[0].set_value(SCRIPT).run()
    else:
        at.text_area(key=f"paste_{pid}").set_value(SCRIPT).run()
    return at


# ---------------------------------------------------------------- 1. số click
class Scenario:
    """Người dùng đi tay đường ngắn nhất từ dự án trống tới clip video đầu. Mỗi bước có vài khóa nút (bản cũ | bản v2)."""
    STEPS = [
        ("Tạo dự án", [r"new_project_go"]),
        ("Phân tích kịch bản", [r"btn_analyse_\d+"]),
        ("Director (kế hoạch)", [r"script-cta_\d+", r"llm_dir_\d+"]),
        ("Duyệt ngân sách", [r"script-cta-budget_\d+", r"pb_ok_\d+"]),
        ("Xác nhận ngân sách", [r"script-cta-budget_\d+_yes", r"pb_ok_\d+_yes"]),
        ("Khóa Bible → Storyboard", [r"script-cta-lock_\d+", r"lock_go_\d+"]),
        ("Gen ảnh", [r"gen_img_\d+"]),
        ("Duyệt tất cả ảnh", [r"approve_all"]),
        ("Xác nhận duyệt ảnh", [r"approve_all_yes"]),
        ("Viết motion prompt", [r"llm_mot_\d+"]),
        ("Duyệt tất cả prompt", [r"btn_ok_all"]),
        ("Xác nhận duyệt prompt", [r"btn_ok_all_yes"]),
        ("Sang màn Video", ["RADIO:Video"]),
        ("Gen video", [r"gen_vid_\d+"]),
    ]


def measure_clicks(v2: str) -> dict:
    tmp = tempfile.mkdtemp()
    _env(v2, tmp)
    at = _app()
    clicks, inputs, log = 0, 0, []
    for name, pats in Scenario.STEPS:
        t = time.time()
        if name == "Tạo dự án":
            at.text_input(key="new_name").set_value("Thử nghiệm").run()
            inputs += 1
        if name == "Phân tích kịch bản":
            _type_script(at, 1)
            inputs += 1
        if pats == ["RADIO:Video"]:
            at.radio(key="step").set_value("Video").run()
            clicks += 1
            log.append((name, "radio step", round(time.time() - t, 2)))
            continue
        btn = next((b for b in at.button if not b.disabled and any(re.fullmatch(p, b.key or "") for p in pats)), None)
        if btn is None:
            log.append((name, "KHÔNG THẤY NÚT " + "|".join(pats), 0))
            return {"ok": False, "clicks": clicks, "inputs": inputs, "log": log, "exceptions": [e.message for e in at.exception]}
        btn.click().run()
        clicks += 1
        log.append((name, btn.key, round(time.time() - t, 2)))
        if at.exception:
            return {"ok": False, "clicks": clicks, "inputs": inputs, "log": log, "exceptions": [e.message for e in at.exception]}
    from core.db import connect
    conn = connect(os.environ["PIPELINE_DB"])
    auto = measure_auto_path(v2)
    jobs = conn.execute("SELECT state, COUNT(*) n FROM jobs WHERE type='video_gen' GROUP BY state").fetchall()
    n_video = sum(r["n"] for r in jobs)
    return {"ok": n_video > 0, "auto": auto, "clicks": clicks, "inputs": inputs, "video_jobs": {r["state"]: r["n"] for r in jobs}, "log": log,
            "exceptions": [e.message for e in at.exception]}


def measure_auto_path(v2: str) -> dict:
    """Đường tự động: tạo dự án → phân tích → "✔ Duyệt phân cảnh & chạy tự động" (autopilot chạy nền, ngoài AppTest)."""
    from core import autopilot
    from core.db import connect
    from core.pipeline import Pipeline
    tmp = tempfile.mkdtemp()
    _env(v2, tmp)
    at = _app()
    at.text_input(key="new_name").set_value("Tự động").run()
    at.button(key="new_project_go").click().run()
    _type_script(at, 1)
    at.button(key="btn_analyse_1").click().run()
    btn = next((b for b in at.button if b.key == "ap_start_1" and not b.disabled), None)
    if btn is None:
        return {"ok": False, "clicks": 2, "note": "không thấy ap_start_1"}
    btn.click().run()
    st = autopilot.status(Pipeline(connect(os.environ["PIPELINE_DB"])), 1)["state"]
    return {"ok": not at.exception, "clicks": 3, "autopilot_state": st, "exceptions": [e.message[:160] for e in at.exception]}


# ---------------------------------------------------------------- 2. khóa điều khiển
# Khóa cũ được CHỦ Ý đổi tên / bỏ trong v2 (kèm lý do) — mẫu "{}" thay cho số. Bảng này chỉ dài thêm khi có quyết định rõ (S14.8 U6:
# chuyển từ tests/test_ui_v2_acceptance.py vào đây để công cụ, test và devsys/metrics.py dùng chung một bảng).
RENAMED = {
    "retry_{}": "storyboard_cards.py: nút '↻ Vẽ lại' của ảnh lỗi dùng dretry_{} (cùng p.retry) — khóa cũ chỉ còn ở giao diện cũ",
    "inbox_kind": "header.inbox_card: bộ lọc loại việc chỉ hiện khi hộp thư > 3 việc (INBOX_SHOWN)",
    "fold_refs_{}_btn": "v2 thay thẻ gập 'Tham chiếu' bằng khối luôn mở (inputs_and_refs_v2)",
    "fold_script_{}_btn": "v2 thay thẻ gập 'Kịch bản' bằng thẻ ① + expander 'Nhập / thay kịch bản'",
}


def _renamed(key: str) -> bool:
    return re.sub(r"\d+", "{}", key) in RENAMED or re.sub(r"_\d+", "_{}", key) in RENAMED


def explained(keys) -> list:
    """Khóa mất CÓ lý do trong RENAMED."""
    return sorted(k for k in keys if _renamed(k))


def unexplained(keys) -> list:
    """Khóa mất KHÔNG có lý do — chỉ những khóa này làm phép đo `keys` thất bại."""
    return sorted(k for k in keys if not _renamed(k))


KEY_RE = re.compile(r'\bkey\s*=\s*(f?)(["\'])(.*?)\2')


def static_keys(rev: str) -> dict:
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", rev, "dashboard"], text=True, cwd=ROOT).split()
    out = {}
    for f in (n for n in names if n.endswith(".py")):
        src = subprocess.check_output(["git", "show", f"{rev}:{f}"], cwd=ROOT).decode("utf-8")
        for m in KEY_RE.finditer(src):
            out.setdefault(re.sub(r"\{[^}]*\}", "{}", m.group(3)), set()).add(f)
    return out


def _walk(node, acc):
    for c in getattr(node, "children", {}).values():
        k = getattr(c, "key", None)
        if k and not str(k).startswith("$$"):
            acc.add((type(c).__name__, str(k)))
        _walk(c, acc)


def widget_keys_all_screens(v2: str, db_dir: str) -> dict:
    """Mở lần lượt mọi màn (radio `step`) trên CSDL demo, gom (loại, khóa) của mọi widget — AppTest vẽ cả vùng gập và popover."""
    _env(v2, db_dir)
    os.environ["PIPELINE_DB"] = os.path.join(db_dir, "manifest.sqlite")
    os.environ["PIPELINE_DATA"] = os.path.join(db_dir, "projects")
    at = _app()
    seen = {}
    steps = list(at.radio(key="step").options)
    for s in steps:
        at.radio(key="step").set_value(s).run()
        for _ in range(8):                                   # mở hết các thẻ gập (ui.fold): widget trong thẻ gập chỉ vẽ khi mở
            closed = [b for b in at.button if re.fullmatch(r"fold_.*_btn", b.key or "") and b.label.startswith("▸")]
            if not closed:
                break
            closed[0].click().run()
        acc = set()
        _walk(at.main, acc)
        _walk(at.sidebar, acc)
        seen[s] = sorted(acc)
        if at.exception:
            seen[s + " !EXC"] = [e.message[:200] for e in at.exception]
    return seen


def measure_keys(v2: str) -> dict:
    d = os.path.join(tempfile.mkdtemp(), "demo")
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "seed_demo.py"), "--out", d], cwd=ROOT, stdout=subprocess.DEVNULL)
    return widget_keys_all_screens(v2, d)


# ---------------------------------------------------------------- 3. hiệu năng
def build_perf_fixture(tmp: str, n_projects: int = 50, frames: int = 30, events: int = 0) -> int:
    """50 dự án (mỗi dự án vài cảnh + job + sự kiện chi tiêu) + 1 dự án 30 khung có ảnh. Trả về id dự án 30 khung."""
    sys.path.insert(0, ROOT)
    from core.db import connect
    from core.llm_io import lock_character_bible, store_scene_analysis
    from core.pipeline import Pipeline
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import seed_demo
    p = Pipeline(connect(os.environ["PIPELINE_DB"]))
    img_dir = os.path.join(os.environ["PIPELINE_DATA"])
    for i in range(1, n_projects):
        pid = p.create_project(f"Dự án nền {i:02d} với tên khá dài để thử cắt chữ trong thẻ")
        for k in range(1, 5):
            sid = p.create_scene(pid, k, f"CẢNH {k}")
            job = p.create_job(sid)
            p.start(job)
            p.succeed(job)
            p.apply_qc(job, {"character": .9, "hands_face": .8, "composition": .85, "mood_lighting": .9, "consistency": .9})
        for k in range(events or int(os.environ.get("UI_ACCEPT_EVENTS", "40"))):
            p.conn.execute("INSERT INTO usage_events(project_id,kind,provider,model,tier,quantity,unit,at) VALUES(?,?,?,?,?,?,?,datetime('now'))",
                           (pid, "image", "mock", "m", "t", 1.0, "image"))
    big = p.create_project("Dự án 30 khung")
    names = ["Lyra", "Kael"]
    for k in range(1, frames + 1):
        sid = p.create_scene(big, k, f"CẢNH {k}")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"text": f"CẢNH {k}. Lyra đi qua rừng.\nLyra: Đi tiếp."}, ensure_ascii=False), sid))
    p.conn.commit()
    store_scene_analysis(p, big, {
        "characters": [{"name": "Lyra", "description": "Nữ, 25 tuổi, tóc bạc dài"}, {"name": "Kael", "description": "Nam, 35, râu ngắn"}],
        "scenes": [{"idx": k, "location": "Rừng Elder", "time": "Đêm", "characters": names[: 1 + k % 2], "mood": "u ám", "lighting": "tự nhiên",
                    "shot": "wide", "image_prompt": f"Rừng Elder, cảnh {k}"} for k in range(1, frames + 1)]})
    lock_character_bible(p, big)
    images = os.path.join(img_dir, str(big), "images")
    for k in range(1, frames + 1):
        scene = p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=?", (big, k)).fetchone()["id"]
        job = p.create_job(scene)
        p.start(job)
        p.succeed(job)
        seed_demo.draw(os.path.join(images, f"job_{job}.png"), *seed_demo.COLORS[k % 8], f"S{k:02d}")
        p.apply_qc(job, {"character": .9 - (k % 5) * .1, "hands_face": .8, "composition": .85, "mood_lighting": .9, "consistency": .9})
        if k % 3 == 0:
            p.approve(job)
    p.conn.commit()
    return big


def mark_finished(n: int = 20, size: int = 1 << 20) -> list:
    """S14.8 U1: n dự án nền thành "đã xong" (FINAL_VIDEO.mp4 ~1 MB + đã xuất bản giao) → ⌂ có mục 🎬 Sản phẩm đã hoàn tất."""
    from core import delivered
    from core.db import connect
    conn = connect(os.environ["PIPELINE_DB"])
    ids = [r["id"] for r in conn.execute("SELECT id FROM projects ORDER BY id LIMIT ?", (n,)).fetchall()]
    for pid in ids:
        out = os.path.join(os.environ["PIPELINE_DATA"], str(pid), "output")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "FINAL_VIDEO.mp4"), "wb") as fh:
            fh.write(bytes(size))
        delivered.mark(conn, pid, out, source="test")
    return ids


SQL = {"n": 0, "s": 0.0, "by": {}}


def _install_sql_counter() -> None:
    """Đếm số câu SQL và thời gian SQL của mọi kết nối mở qua core.db.connect (kết nối con = lớp con của sqlite3.Connection)."""
    import sqlite3
    real = sqlite3.connect

    class Counting(sqlite3.Connection):
        def execute(self, sql, *a, **k):
            t = time.perf_counter()
            try:
                return super().execute(sql, *a, **k)
            finally:
                d = time.perf_counter() - t
                SQL["n"] += 1
                SQL["s"] += d
                key = " ".join(str(sql).split())[:90]
                n, tot = SQL["by"].get(key, (0, 0.0))
                SQL["by"][key] = (n + 1, tot + d)

    sqlite3.connect = lambda *a, **k: real(*a, **{**k, "factory": Counting})


def measure_perf(v2: str, reps: int) -> dict:
    tmp = tempfile.mkdtemp()
    _env(v2, tmp)
    big = build_perf_fixture(tmp)
    _install_sql_counter()
    at = _app()
    res = {}
    for label, step in (("home_50", "⌂ Tất cả dự án"), ("storyboard_30", "Storyboard"), ("home_50_done20", "⌂ Tất cả dự án")):
        if label == "storyboard_30":
            at.selectbox(key="global_pid").set_value(big)
        if label == "home_50_done20":                         # S14.8 U1: 20 dự án xong không được làm ⌂ chậm hơn 20 %
            mark_finished(20)
        at.radio(key="step").set_value(step).run()
        if at.exception:
            res[label] = {"error": [e.message[:200] for e in at.exception]}
            continue
        at.run()                                              # khởi động nguội đã qua
        times, cpus, sqls = [], [], []
        for _ in range(reps):
            SQL["n"], SQL["s"], SQL["by"] = 0, 0.0, {}
            c, t = time.process_time(), time.perf_counter()
            at.run()
            times.append(time.perf_counter() - t)
            cpus.append(time.process_time() - c)
            sqls.append((SQL["n"], SQL["s"]))
        top = sorted(SQL["by"].items(), key=lambda kv: -kv[1][1])[:3]
        res[label] = {"median_s": round(statistics.median(times), 3), "min_s": round(min(times), 3), "cpu_min_s": round(min(cpus), 3),
                      "sql_n": sqls[-1][0], "sql_ms": round(sqls[-1][1] * 1000, 1),
                      "sql_top": [(k, n, round(t * 1000, 1)) for k, (n, t) in top], "videos": len(at.get("video"))}
    return res


# ---------------------------------------------------------------- 4. ca giao diện cho ui_contrast_audit.js
def seed_states(out: str) -> None:
    """Thêm vào CSDL demo (tools/seed_demo.py) các ca màn hình mà bộ đo tương phản cần: dự án #1 'Tự động đang chạy' (autopilot running + nhật ký),
    4 dự án có ảnh chờ duyệt / clip chờ duyệt (hộp thư 📥 dài hơn 3 việc → hiện bộ lọc loại việc), 1 dự án tạm dừng, 1 dự án tên rất dài."""
    sys.path.insert(0, ROOT)
    from core.db import connect
    from core.pipeline import Pipeline
    p = Pipeline(connect(os.path.join(out, "manifest.sqlite")))
    p.conn.execute("UPDATE projects SET autopilot_state='running', autopilot_note='Đang gen ảnh cảnh 3/8', autopilot_beat=? WHERE id=1", (time.time(),))
    p.conn.execute("UPDATE projects SET autopilot_log=? WHERE id=1", (json.dumps([{"at": "10:0%d" % i, "msg": f"bước {i}: ok"} for i in range(6)], ensure_ascii=False),))
    p.conn.commit()
    for i in range(4):
        pid = p.create_project(f"Dự án chờ duyệt {i + 1}")
        sid = p.create_scene(pid, 1, "CẢNH 1")
        for typ in ("image_gen", "video_gen"):
            job = p.create_job(sid, typ)
            p.start(job)
            p.succeed(job)
            p.conn.execute("UPDATE jobs SET state='pending_review' WHERE id=?", (job,))
    sid2 = p.conn.execute("SELECT id FROM scenes WHERE project_id=1 AND idx=2").fetchone()["id"]      # cảnh 2 có v1…v7: thử dải phiên bản dài
    for _ in range(6):
        job = p.create_job(sid2)
        p.start(job)
        p.succeed(job)
        p.apply_qc(job, {"character": .6, "hands_face": .5, "composition": .6, "mood_lighting": .6, "consistency": .6})
        p.reject(job, "user", "thử dải phiên bản", respawn=False)
    paused = p.create_project("Dự án tạm dừng")
    p.conn.execute("UPDATE projects SET paused=1 WHERE id=?", (paused,))
    p.create_project("Dự án có tên rất dài để thử cắt chữ ở thẻ, hộp thư, thanh chọn dự án và mọi nơi khác nữa của giao diện v2")
    p.conn.commit()
    print("states seeded in", out)


# ---------------------------------------------------------------- điều phối
def child(mode: str, v2: str, extra=()) -> dict:
    # tests/__init__.py đặt FEATURE_PROJECT_BUDGET=0 … → bỏ mọi FEATURE_* thừa hưởng để phép đo giống máy thật (chỉ FEATURE_UI_V2 do _env đặt)
    env = {k: v for k, v in os.environ.items() if not k.startswith("FEATURE_")}
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1", FEATURE_SETTINGS_FILE=os.path.join(tempfile.mkdtemp(), "none.json"))
    out = subprocess.run([sys.executable, os.path.abspath(__file__), "_child", mode, v2, *extra], capture_output=True, text=True,
                         encoding="utf-8", cwd=ROOT, env=env).stdout
    return json.loads(out[out.index("@@JSON@@") + 8:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["all", "clicks", "keys", "perf", "states", "_child"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--out", default=os.path.join("data", "demo"))
    ap.add_argument("--reps", type=int, default=25)
    a = ap.parse_args()
    if a.mode == "_child":
        mode, v2 = a.rest[0], a.rest[1]
        fn = {"clicks": lambda: measure_clicks(v2), "keys": lambda: measure_keys(v2), "perf": lambda: measure_perf(v2, a.reps)}[mode]
        print("@@JSON@@" + json.dumps(fn(), ensure_ascii=False))
        return 0
    if a.mode == "states":
        seed_states(a.out)
        return 0
    bad = False
    if a.mode in ("all", "clicks"):
        old, new = child("clicks", "0"), child("clicks", "1")
        # "cũ N · v2 M" giữ nguyên dạng: devsys/metrics.py (_CLICK) đọc dòng này; "cũ" = mốc bản cũ đã lưu (OLD_CLICKS_BASELINE)
        print(f"CLICK Dự án mới → video đầu: cũ {OLD_CLICKS_BASELINE} · v2 {new['clicks']} (nhập liệu {old['inputs']} / {new['inputs']}) "
              f"· FEATURE_UI_V2=0 hôm nay {old['clicks']} · video job =0 {old.get('video_jobs')} v2 {new.get('video_jobs')}")
        print(f"   đường tự động (ap_start): =0 {old['auto']} · v2 {new['auto']}")
        for (n, ko, _), (_, kn, _) in zip(old["log"], new["log"]):
            print(f"   {n:28} =0:{ko:26} v2:{kn}")
        if not (old["ok"] and new["ok"]) or new["clicks"] > OLD_CLICKS_BASELINE:
            bad = True
            print("   !! kịch bản hỏng hoặc v2 nhiều click hơn", old.get("exceptions"), new.get("exceptions"))
    if a.mode in ("all", "keys"):
        so, sn = static_keys(BASE_REV), static_keys("HEAD")
        print(f"KHÓA TĨNH (mã nguồn, mẫu key=): cũ {len(so)} · mới {len(sn)} · mất {sorted(set(so) - set(sn))}")
        old, new = child("keys", "0"), child("keys", "1")
        for s in old:
            ko, kn = {k for _, k in old[s]}, {k for _, k in new.get(s, [])}
            print(f"   màn {s:22} cũ {len(ko):4} · v2 {len(kn):4} · mất trong v2 {unexplained(ko - kn)}"
                  + (f" · đổi có chủ ý {explained(ko - kn)}" if explained(ko - kn) else ""))
            if unexplained(ko - kn):
                bad = True
    if a.mode in ("all", "perf"):
        rounds = [(child("perf", "0", ["--reps", str(a.reps)]), child("perf", "1", ["--reps", str(a.reps)])) for _ in range(3)]   # xen kẽ 3 vòng: máy ồn
        for k in rounds[0][0]:
            if any("min_s" not in r[k] for pair in rounds for r in pair):
                print("PERF", k, rounds[0])
                bad = True
                continue
            o = min(r[0][k]["min_s"] for r in rounds)
            n = min(r[1][k]["min_s"] for r in rounds)
            oc = min(r[0][k]["cpu_min_s"] for r in rounds)
            nc = min(r[1][k]["cpu_min_s"] for r in rounds)
            d, dc = (n / o - 1) * 100, (nc / oc - 1) * 100
            so, sn = rounds[0][0][k], rounds[0][1][k]
            print(f"PERF {k:14} wall-min cũ {o:.3f}s · v2 {n:.3f}s · {d:+.1f} % | cpu-min cũ {oc:.3f}s · v2 {nc:.3f}s · {dc:+.1f} % "
                  f"| SQL cũ {so['sql_n']} câu/{so['sql_ms']} ms · v2 {sn['sql_n']} câu/{sn['sql_ms']} ms  {'ĐẠT' if d <= 20 else 'VƯỢT'}")
            if d > 20:
                print("     SQL chậm nhất v2:", sn["sql_top"])
            bad = bad or d > 20
        for v in ("0", "1"):                                   # S14.8 U1: ⌂ 20 dự án xong so với 0 dự án xong, cùng một bản giao diện
            if not all("min_s" in r[int(v)].get(k, {}) for r in rounds for k in ("home_50", "home_50_done20")):
                continue
            base = min(r[int(v)]["home_50"]["min_s"] for r in rounds)
            done = min(r[int(v)]["home_50_done20"]["min_s"] for r in rounds)
            nvid = max(r[int(v)]["home_50_done20"]["videos"] for r in rounds)
            d = (done / base - 1) * 100
            ok = d <= 20 and nvid <= 1
            print(f"PERF-DONE ui_v2={v} home_50_done20 {done:.3f}s so home_50 {base:.3f}s · {d:+.1f} % · st.video {nvid}  {'ĐẠT' if ok else 'VƯỢT'}")
            bad = bad or not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
