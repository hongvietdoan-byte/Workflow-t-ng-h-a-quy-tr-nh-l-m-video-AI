"""Dựng lại GÓI ẢNH mà job gen ảnh sẽ gửi model — 0 USD, CHỈ ĐỌC dữ liệu thật (người dùng 14/10, việc 4: "không gọi 'đã sửa' khi
chỉ có test theo giả thuyết; dựng lại gói gửi model của dự án thật rồi kiểm").

    PYTHONUTF8=1 py tools/replay_payload.py --project 30 [--shot 1] [--main D:/AI-Video-Pipeline] [--flag tên=on|off] [--json out.json]

Đi ĐÚNG đường của pipeline: core.runner.ImageRunner._submit_args (prompt cuối + ảnh tham chiếu + nhãn `sent_refs`), không viết lại
logic song song. Cách chạy an toàn trên dữ liệu thật (CSDL lưu đường dẫn TƯƠNG ĐỐI `data\\assets\\...`):
  - thư mục thử tạm (scratch): data/manifest.sqlite = BẢN SAO (sqlite backup từ kết nối chỉ đọc), data/feature_settings.json = bản sao
    (D6 `chat_prompts` luôn TẮT → chỉ bản code ghép, không gọi Claude), data/projects/<pid> = bản sao thư mục dự án;
  - junction data/assets, data/_plates3d → bản chính (chỉ đọc); cwd = thư mục thử; PIPELINE_DB / FEATURE_SETTINGS_FILE trỏ bản sao;
  - cờ FEATURE_ của <main>/dashboard.env chép vào env (chỉ dòng FEATURE_, như Dashboard chạy; --no-env bỏ) — --flag thắng;
  - so với jobs.sent_package thật: ảnh (nhãn, file), câu khóa đạo cụ, câu HÌNH vật kỹ năng, câu hướng chạy;
  - provider giả (không có hàm gửi); mọi lệnh MỞ GHI / tạo / xóa / đổi tên dưới `<main>/data` bị CHẶN (PermissionError);
  - xong: gỡ junction bằng os.rmdir (không theo link) rồi mới xóa thư mục thử.
In ra từng shot: ảnh gửi (Image N, nhãn, vai, file, mã mục Kho), so với `jobs.sent_refs` thật của job gần nhất, các diag, prompt.
"""
import argparse
import builtins
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # gốc repo (worktree), không theo cwd
sys.path.insert(0, ROOT)

_WRITE = ("w", "a", "x", "+")


def _norm(path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


class WriteGuard:
    """Chặn mọi ghi dưới `forbidden` (realpath — đi qua junction cũng bị chặn). Dùng như context manager."""

    def __init__(self, forbidden: str):
        self.root = _norm(forbidden)
        self.saved = {}

    def _bad(self, path) -> bool:
        try:
            p = _norm(path)
        except (TypeError, ValueError):
            return False
        return p == self.root or p.startswith(self.root + os.sep)

    def _check(self, path, what: str):
        if self._bad(path):
            raise PermissionError(f"replay_payload: chặn {what} dưới dữ liệu thật: {path}")

    def __enter__(self):
        guard = self
        orig_open, orig_io_open = builtins.open, io.open

        def g_open(file, mode="r", *a, **kw):
            if isinstance(file, (str, bytes, os.PathLike)) and any(c in str(mode) for c in _WRITE):
                guard._check(file, f"mở ghi ({mode})")
            return orig_open(file, mode, *a, **kw)

        def g_io_open(file, mode="r", *a, **kw):
            if isinstance(file, (str, bytes, os.PathLike)) and any(c in str(mode) for c in _WRITE):
                guard._check(file, f"mở ghi ({mode})")
            return orig_io_open(file, mode, *a, **kw)

        self.saved = {(builtins, "open"): orig_open, (io, "open"): orig_io_open}
        builtins.open, io.open = g_open, g_io_open
        for mod, name in ((os, "makedirs"), (os, "mkdir"), (os, "remove"), (os, "unlink"), (os, "rmdir"), (os, "replace"),
                          (os, "rename"), (shutil, "move"), (shutil, "rmtree"), (shutil, "copy"), (shutil, "copy2"),
                          (shutil, "copyfile")):
            orig = getattr(mod, name)
            self.saved[(mod, name)] = orig

            def wrap(*a, _orig=orig, _name=name, **kw):
                targets = a[1:2] if _name in ("move", "copy", "copy2", "copyfile", "replace", "rename") else a[:1]
                if _name in ("replace", "rename", "move"):
                    targets = a[:2]
                for t in targets:
                    if isinstance(t, (str, bytes, os.PathLike)):
                        guard._check(t, _name)
                return _orig(*a, **kw)
            setattr(mod, name, wrap)
        return self

    def __exit__(self, *exc):
        for (mod, name), orig in self.saved.items():
            setattr(mod, name, orig)
        return False


class ReplayProvider:
    """Provider giả: cùng khả năng như provider ảnh thật (chọn model, storyboard) nhưng KHÔNG có hàm gửi — không thể tốn tiền."""
    name = "replay"
    supports_model = True
    supports_storyboard = True


def _junction(link: str, target: str) -> None:
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", link, target], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)


def _unlink_dir(link: str) -> None:
    """Gỡ junction/symlink KHÔNG theo link (os.rmdir trên junction chỉ gỡ link)."""
    if os.path.islink(link) or (hasattr(os.path, "isjunction") and os.path.isjunction(link)):
        if os.name == "nt":
            os.rmdir(link)
        else:
            os.unlink(link)


def env_flags(path: str) -> dict:
    """{FEATURE_X: giá trị} — CHỈ các dòng FEATURE_ của dashboard.env máy chính (cờ bật bằng env, vd skill_object_guard trên máy
    khác); không đọc dòng nào khác (khóa API ở cùng file không bao giờ được lấy)."""
    out = {}
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("FEATURE_") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                if k.replace("_", "").isalnum():
                    out[k] = v.split("#", 1)[0].strip().strip('"').strip("'")
    except OSError:
        return {}
    return out


_PROP_LOCK_RX = None


def _key_sentences(prompt: str) -> dict:
    """Các câu chính để so gói dựng lại với gói gửi thật: câu khóa đạo cụ (Prop lock), câu HÌNH vật kỹ năng (skill_objects.SHAPE),
    câu hướng chạy (travel_truth)."""
    import re
    global _PROP_LOCK_RX
    if _PROP_LOCK_RX is None:
        _PROP_LOCK_RX = re.compile(r"Prop lock: [^;]*")
    from core import skill_objects
    shapes = [k for k, v in getattr(skill_objects, "SHAPE", {}).items() if v[:60] in (prompt or "")]
    return {"prop_lock": _PROP_LOCK_RX.findall(prompt or ""), "shape": shapes,
            "travel": "Direction of travel (measured on the 3D map):" in (prompt or "")}


def compare(real_pkg, prompt: str, refs: list) -> dict:
    """So gói dựng lại với jobs.sent_package thật (một job): câu chính + danh sách ảnh (nhãn, tên file). None khi job không có gói."""
    if not real_pkg:
        return None
    pkg = json.loads(real_pkg) if isinstance(real_pkg, str) else real_pkg
    real_k, now_k = _key_sentences(pkg.get("prompt") or ""), _key_sentences(prompt)
    # theo tên file theo thứ tự (nhãn trong gói ghi khác: ảnh rộng mang tên nơi chốn); storyboard Deepix đi tham số riêng, không ở refs
    real_refs = [r.get("file") for r in pkg.get("refs") or []]
    now_refs = [r.get("file") for r in refs or [] if r.get("role") != "storyboard"]
    return {"shape_same": real_k["shape"] == now_k["shape"], "shape_real": real_k["shape"], "shape_now": now_k["shape"],
            "prop_lock_same": real_k["prop_lock"] == now_k["prop_lock"], "prop_lock_real": real_k["prop_lock"],
            "prop_lock_now": now_k["prop_lock"], "travel_real": real_k["travel"], "travel_now": now_k["travel"],
            "refs_same": real_refs == now_refs, "refs_real": real_refs, "refs_now": now_refs}


def build_sandbox(main: str, pid: int, work: str, flags: dict) -> dict:
    """Thư mục thử: bản sao CSDL + cài đặt cờ + thư mục dự án; junction assets/_plates3d. Trả {db, settings, data_dir, links}."""
    real = os.path.join(main, "data")
    data = os.path.join(work, "data")
    os.makedirs(os.path.join(data, "projects"), exist_ok=True)
    db = os.path.join(data, "manifest.sqlite")
    src = sqlite3.connect(f"file:{os.path.join(real, 'manifest.sqlite')}?mode=ro", uri=True)
    dst = sqlite3.connect(db)
    src.backup(dst)                      # kể cả phần còn trong WAL
    src.close()
    dst.close()
    settings = {}
    sp = os.path.join(real, "feature_settings.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            settings = json.load(f)
    box = settings.get("flags") if isinstance(settings.get("flags"), dict) else settings
    box["chat_prompts"] = False         # D6 không gọi Claude: chỉ bản code ghép (assembled)
    for k, v in flags.items():
        box[k] = v
    sfile = os.path.join(data, "feature_settings.json")
    with open(sfile, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=1)
    proj_src = os.path.join(real, "projects", str(pid))
    proj_dst = os.path.join(data, "projects", str(pid))
    if os.path.isdir(proj_src):
        shutil.copytree(proj_src, proj_dst, ignore=shutil.ignore_patterns("output", "trash", "music*", "*.mp4", "*.wav"))
    links = []
    for name in ("assets", "_plates3d"):
        target = os.path.join(real, name)
        if os.path.isdir(target):
            link = os.path.join(data, name)
            _junction(link, target)
            links.append(link)
    return {"db": db, "settings": sfile, "data_dir": os.path.join(data, "projects"), "links": links, "work": work}


def _kho_index(conn) -> dict:
    """{đường dẫn chuẩn hóa: (asset_id, tên mục, variant)} của ảnh Kho — để gắn nhãn mục Kho cho ảnh gửi."""
    from core import assets
    out = {}
    for r in conn.execute("SELECT i.asset_id, i.path, i.variant, a.name FROM asset_images i JOIN assets a ON a.id=i.asset_id "
                          "WHERE i.removed_at IS NULL"):
        try:
            out[_norm(assets.resolve(r["path"]))] = (r["asset_id"], r["name"], r["variant"])
        except Exception:  # noqa: BLE001 - một dòng hỏng không làm hỏng bảng nhãn
            continue
    return out


def replay(conn, pid: int, data_dir: str, shot=None) -> list:
    """[{idx, scene_id, job_id, refs:[{n,label,role,file,kho}], real_sent, prompt, diags}] — gọi đúng ImageRunner._submit_args."""
    from core.pipeline import Pipeline
    from core.runner import ImageRunner
    pipe = Pipeline(conn)
    runner = ImageRunner(pipe, ReplayProvider(), data_dir)
    notes = []
    runner._diag = lambda job, sev, code, msg: notes.append((job["scene_id"], sev, code, msg))
    kho = _kho_index(conn)
    rows = conn.execute("SELECT id, idx FROM scenes WHERE project_id=? ORDER BY idx", (pid,)).fetchall()
    out = []
    for r in rows:
        if shot is not None and int(r["idx"]) != int(shot):
            continue
        real = conn.execute("SELECT * FROM jobs WHERE scene_id=? AND type='image_gen' ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
        job = dict(real) if real else {"id": -int(r["id"]), "project_id": pid, "scene_id": r["id"], "retry_reason": None}
        before = len(notes)
        try:
            args = runner._submit_args(job)
        except Exception as e:  # noqa: BLE001 - shot hỏng được báo, các shot khác vẫn chạy
            out.append({"idx": r["idx"], "scene_id": r["id"], "job_id": job["id"], "error": f"{type(e).__name__}: {e}"})
            continue
        if not args:
            out.append({"idx": r["idx"], "scene_id": r["id"], "job_id": job["id"], "error": "shot chưa có image_prompt"})
            continue
        prompt, paths = args[0], (args[1] if len(args) > 1 else [])
        sent = (getattr(runner, "_sent", {}) or {}).pop(job["id"], None) or []
        refs = []
        for n, s in enumerate(sent, 1):
            path = paths[n - 1] if n - 1 < len(paths) else None
            hit = kho.get(_norm(path)) if path else None
            refs.append({"n": n, "label": s.get("label"), "role": s.get("role"), "file": s.get("file"),
                         "kho": ({"id": hit[0], "name": hit[1], "variant": hit[2]} if hit else None)})
        getattr(runner, "_storyboard", {}).pop(job["id"], None)
        out.append({"idx": r["idx"], "scene_id": r["id"], "job_id": job["id"], "refs": refs,
                    "real_sent": json.loads(real["sent_refs"] or "[]") if real and real["sent_refs"] else None,
                    "vs_package": compare(real["sent_package"] if real and "sent_package" in real.keys() else None, prompt, refs),
                    "prompt": prompt, "diags": [n[1:] for n in notes[before:]]})
    return out


def _print(results: list, width: int) -> None:
    for s in results:
        print(f"=== shot {s['idx']} (scene {s['scene_id']}, job {s['job_id']}) ===")
        if s.get("error"):
            print("  LỖI:", s["error"])
            continue
        for r in s["refs"]:
            k = r["kho"]
            tag = f" [Kho #{k['id']} {k['name']}" + (f" · dạng '{k['variant']}'" if k.get("variant") else "") + "]" if k else ""
            print(f"  Image {r['n']}: {r['label']} ({r['role']}) {r['file']}{tag}")
        if s["real_sent"] is not None:
            now = [r["label"] for r in s["refs"]]
            was = [r.get("label") for r in s["real_sent"]]
            print("  so job thật:", "GIỐNG nhãn" if now == was else f"KHÁC — thật {was}")
        v = s.get("vs_package")
        if v is not None:
            print("  so sent_package thật:", "ảnh " + ("GIỐNG" if v["refs_same"] else "KHÁC"),
                  "· câu HÌNH " + ("GIỐNG" if v["shape_same"] else f"KHÁC (thật {v['shape_real']}, giờ {v['shape_now']})"),
                  "· câu khóa " + ("GIỐNG" if v["prop_lock_same"] else "KHÁC"),
                  "· câu hướng chạy " + f"thật={v['travel_real']} giờ={v['travel_now']}")
            if not v["prop_lock_same"]:
                print("    khóa thật:", v["prop_lock_real"], "\n    khóa giờ:", v["prop_lock_now"])
        for sev, code, msg in s["diags"]:
            if sev != "info":
                print(f"  diag {sev} {code}: {msg[:200]}")
        print("  prompt:", (s["prompt"][:width] + " …") if width and len(s["prompt"]) > width else s["prompt"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dựng lại gói ảnh gửi model của một dự án thật (0 USD, chỉ đọc)")
    ap.add_argument("--project", type=int, required=True)
    ap.add_argument("--shot", type=int, help="số thứ tự shot (scenes.idx); bỏ trống = mọi shot")
    ap.add_argument("--main", default=r"D:\AI-Video-Pipeline", help="thư mục cài đặt chứa data/ thật")
    ap.add_argument("--flag", action="append", default=[], help="ghi đè cờ trong BẢN SAO cài đặt: tên=on|off (lặp được)")
    ap.add_argument("--json", help="ghi kết quả đầy đủ ra file JSON (ngoài data/ thật)")
    ap.add_argument("--width", type=int, default=0, help="cắt prompt in ra màn hình (0 = in đủ)")
    ap.add_argument("--keep", action="store_true", help="giữ thư mục thử (junction vẫn được gỡ)")
    ap.add_argument("--no-env", dest="no_env", action="store_true", help="không chép cờ FEATURE_ từ <main>/dashboard.env")
    a = ap.parse_args(argv)
    flags = {}
    for f in a.flag:
        k, _, v = f.partition("=")
        flags[k.strip()] = v.strip().lower() in ("1", "on", "true", "yes")
    from core import features as _features
    stuck = [k for k, v in flags.items() if not v and _features.locked(k)]
    if stuck:                                        # 15/10: verified = 🔒 khóa bật — '--flag x=off' would be silently ignored
        print("Lưu ý: cờ đã kiểm chứng bị khóa BẬT, '--flag …=off' không có tác dụng (muốn tắt phải sửa code): " + ", ".join(stuck))
    main_dir = os.path.abspath(a.main)
    work = tempfile.mkdtemp(prefix=f"replay_p{a.project}_")
    envf = {} if a.no_env else env_flags(os.path.join(main_dir, "dashboard.env"))   # cờ FEATURE_ máy chính, như Dashboard chạy
    for k, v in flags.items():                       # --flag thắng dashboard.env (ghi cả hai nơi)
        envf["FEATURE_" + k.upper()] = "1" if v else "0"
    old_cwd = os.getcwd()
    old_env = {k: os.environ.get(k) for k in ("PIPELINE_DB", "FEATURE_SETTINGS_FILE", *envf)}
    box = None
    try:
        box = build_sandbox(main_dir, a.project, work, flags)
        os.environ["PIPELINE_DB"] = box["db"]
        os.environ["FEATURE_SETTINGS_FILE"] = box["settings"]
        os.environ.update(envf)
        os.chdir(work)
        conn = sqlite3.connect(box["db"])
        conn.row_factory = sqlite3.Row
        with WriteGuard(os.path.join(main_dir, "data")):
            results = replay(conn, a.project, box["data_dir"], a.shot)
        conn.close()
        _print(results, a.width)
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=1)
            print("đã ghi", a.json)
    finally:
        os.chdir(old_cwd)
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for link in (box or {}).get("links", []) if box else []:
            _unlink_dir(link)
        for name in ("assets", "_plates3d"):          # build_sandbox lỗi giữa chừng: gỡ link nào đã tạo
            _unlink_dir(os.path.join(work, "data", name))
        if not a.keep:
            if any(os.path.exists(os.path.join(work, "data", n)) for n in ("assets", "_plates3d")):
                print("CẢNH BÁO: junction chưa gỡ được — KHÔNG xóa thư mục thử", work, file=sys.stderr)
            else:
                shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
