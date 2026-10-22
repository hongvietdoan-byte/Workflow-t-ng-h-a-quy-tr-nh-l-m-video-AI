"""V3.1 M2.10 (C-M210-DESIGN): gói gửi TỐI GIẢN — SHADOW (cờ `lean_package` TẮT, verified False). docs/KE_HOACH_GOI_GUI_TOI_GIAN_2026-10-21.md.

Kiểm theo loại shot: ảnh 1 người / nhiều người / có vật / đổi dạng / đổi nền; video khung đầu / đầu+cuối / ref hành động; + họ câu GIỮ/BỎ/ĐỔI,
phủ BYĐ, cờ TẮT = runner không gọi gì, cờ BẬT = chỉ ghi tệp + ⚙ (gói thật byte giữ), công cụ đọc CSDL chỉ đọc."""
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import lean_package as L  # noqa: E402

ON = {"FEATURE_LEAN_PACKAGE": "1"}
OFF = {"FEATURE_LEAN_PACKAGE": ""}


def ref(role, label=None, sha=None, param="references", path=None):
    return {"param": param, "role": role, "label": label, "path": path or f"x/{role}_{label}_{sha}.png",
            "file": "f.png", "sha256": sha or hashlib.sha256(f"{role}{label}{param}".encode()).hexdigest()}


def pkg(refs, prompt="P " * 50, model="gpt-image-2.5-sunburst"):
    return {"v": 1, "call": "submit", "prompt": prompt, "negative": None, "refs": refs, "provider": "deepix", "model": model,
            "params": {}, "external_id": "t1", "at": "2026-10-21T00:00:00+00:00"}


def byd(cast=("KELLY",), vat=None, co="WS", trong_nha=None, kho=41, absent=(), thay=None, dang=None, hanh=None, thoai=None, **more):
    tp = [{"vat": c, "vai": "chinh" if i == 0 else "phu", "vung": "giua"} for i, c in enumerate(cast)]
    for t in tp:
        if thay and t["vat"] in thay:
            t["thay"] = thay[t["vat"]]
        if dang and t["vat"] in dang:
            t["dang"] = dang[t["vat"]]
    tp += [{"vat": a, "vai": "khong_duoc_co", "vung": "giua"} for a in absent]
    b = {"byd_v": 2, "shot": 3, "truyen": {"muc_dich": "Kelly thắng", "cam_xuc": "hả hê"}, "thanh_phan": tp,
         "may": {"co": co, "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"},
         "noi_chon": {"kho_id": kho, "trong_nha": trong_nha, "thoi_gian": "night"},
         "vat": vat if vat is not None else [], "hanh_dong": hanh or [],
         "am_chu": {"thoai": thoai or []}}
    b.update(more)
    return b


REAL_IMAGE = ("Image 1 is this shot's 3D render: keep exactly the background, architecture and layout of Image 1. Reference images are "
              "attached, grouped per named subject. Image 2 is KELLY: the person called KELLY in the scene must be exactly this person "
              "(same face, hairstyle and hair color, outfit and its colors, body build). Each person keeps ONLY the look of their own "
              "reference image(s): never swap or blend faces. Before drawing, pick ONE unmistakable visual anchor per named person. "
              "The place is decided by the 3D render image of this shot, not by words. Render style: Garena Free Fire in-game 3D "
              "character art — match the reference images exactly. Stylized mobile-game proportions. Framing: wide shot. Kelly sprints "
              "across the hedge junction, the SKORP raised. Weapon scale: SKORP — compact SMG ≈ 3 head-heights long. Fix: Every enemy "
              "holds a plain dark-metal assault rifle. Setting: cong troi. Real sizes: cua chinh about 2.2 m tall. Camera and scale, "
              "measured on the 3D map of this place: 24 mm lens, camera 0.8 m above the ground. Identity lock — Kelly: young female "
              "sprinter, dark brown bob. Background in focus; not a cinematic movie still.")


def run(p, data, kind="image", prev=None):
    return L.shadow(json.dumps(p, ensure_ascii=False), data, kind=kind, job_id=7, prev_data=prev)


def codes(rep):
    return {(r["role"], r["label"]): r["ly_do"] for r in rep["ref_bo"]}


class FlagRegistration(unittest.TestCase):
    def test_flag_off_unverified_golden_areas(self):
        from core import features
        self.assertIs(features.FEATURES["lean_package"]["verified"], False)
        with mock.patch.dict(os.environ, OFF):
            self.assertFalse(L.enabled())
        golden = json.load(open(os.path.join(ROOT, "tests", "golden", "package_inputs.json"), encoding="utf-8"))
        self.assertTrue(all(golden[k]["flags"]["lean_package"] is False for k in ("image", "video")))
        areas = json.load(open(os.path.join(ROOT, "devsys", "areas.json"), encoding="utf-8"))["areas"]
        hit = [a for a in areas if "core/lean_package.py" in a["code"]]
        self.assertTrue(hit)
        self.assertIn("lean_package", hit[0]["flags"])
        self.assertIn("tests/test_v31_m210_lean_package.py", hit[0]["tests"])
        self.assertIn("tools/lean_package_shadow.py", hit[0]["code"])


class ImageShots(unittest.TestCase):
    def test_one_person_drops_second_angle_and_wide_plate(self):
        p = pkg([ref("place_render", "Cổng Trời"), ref("character", "KELLY"), ref("character", "KELLY", param="references2"),
                 ref("place_render", "Cổng Trời", param="wide")], prompt=REAL_IMAGE)
        rep = run(p, {"byd": byd(), "image_prompt": "Kelly sprints across the hedge junction. She raises the SKORP."})
        self.assertEqual(rep["loai"], "anh_1_nguoi")
        self.assertEqual([r["role"] for r in rep["ref_giu"]], ["place_render", "character"])
        self.assertEqual(sorted(codes(rep).values()), ["goc_thu_2", "nen_rong_trung"])
        g = rep["goi_gon"]
        self.assertEqual(len(g["role_lines"]), len(g["refs"]))                 # mỗi ref giữ đúng một dòng vai, đánh số
        self.assertTrue(g["role_lines"][0].startswith("Image 1 ") and g["role_lines"][1].startswith("Image 2 "))
        self.assertLessEqual(len(g["body"]), 4)
        self.assertLess(rep["gon"]["chars"], rep["that"]["chars"])
        self.assertIn("KHÔNG gửi", g["note"])

    def test_many_people_absent_cast_and_swap_rule(self):
        p = pkg([ref("place_render", "Cổng Trời"), ref("character", "KELLY"), ref("character", "MAXIM"), ref("character", "KENTA")])
        rep = run(p, {"byd": byd(cast=("KELLY", "MAXIM"), absent=("SU_GIA",))})
        self.assertEqual(rep["loai"], "anh_nhieu_nguoi")
        self.assertEqual(codes(rep), {("character", "KENTA"): "khong_trong_khung"})
        text = rep["goi_gon"]["prompt"]
        self.assertIn("never swap", text)
        self.assertIn("SU GIA is NOT in this frame", text)

    def test_object_only_from_byd_and_weapon_scale_kept(self):
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("object", "SKORP"), ref("object", "AWM")], prompt=REAL_IMAGE)
        rep = run(p, {"byd": byd(vat=[{"vat": "SKORP", "kho_id": 9, "nguoi": "KELLY", "cach": "cam"}])})
        self.assertEqual(rep["loai"], "anh_co_vat")
        self.assertEqual(codes(rep), {("object", "AWM"): "vat_khong_trong_byd"})
        text = rep["goi_gon"]["prompt"]
        self.assertIn("Weapon scale: SKORP", text)                              # GIỮ: ảnh vật không cho cỡ so với người
        self.assertIn("Camera and scale, measured", text)                       # GIỮ: câu đo M3.3
        self.assertIn("Fix: Every enemy", text)                                 # GIỮ: sửa của người
        self.assertNotIn("Real sizes", text)                                    # BỎ
        self.assertNotIn("pick ONE unmistakable", text)                         # BỎ
        self.assertNotIn("Identity lock", text)                                 # BỎ (có ảnh người)

    def test_form_change_keeps_form_ref_and_says_not_the_clothes(self):
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("character_form", "KELLY")])
        rep = run(p, {"byd": byd(dang={"KELLY": "bong_mo"})})
        self.assertEqual(rep["loai"], "anh_doi_dang")
        self.assertEqual(rep["ref_bo"], [])
        lines = rep["goi_gon"]["role_lines"]
        self.assertIn("NOT the clothes", lines[1])
        self.assertIn("bong mo", lines[2])

    def test_background_change_tag_and_sky_indoor(self):
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("atmosphere_sky", "SKY")])
        rep = run(p, {"byd": byd(kho=42, trong_nha=True)}, prev={"byd": byd(kho=41)})
        self.assertIn("doi_nen", rep["the"])
        self.assertEqual(codes(rep), {("atmosphere_sky", "SKY"): "trong_nha"})

    def test_missing_byd_keeps_everyone_and_says_so(self):
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("character", "KENTA"), ref("object", "AWM")])
        rep = run(p, {})
        self.assertEqual(len(rep["ref_giu"]), 4)
        self.assertIn("thieu_byd", [w["ma"] for w in rep["canh_bao"]])

    def test_duplicate_sha_and_unknown_role(self):
        same = "a" * 64
        p = pkg([ref("place_render", "P", sha=same), ref("location", "P", sha=same), ref("reference_only", None)])
        rep = run(p, {"byd": byd(cast=())})
        self.assertEqual(codes(rep)[("location", "P")], "trung_sha")
        self.assertIn("vai_khong_ro", [w["ma"] for w in rep["canh_bao"]])
        self.assertIn("reference_only", [r["role"] for r in rep["ref_giu"]])


class VideoShots(unittest.TestCase):
    def _v(self, refs, model="seedance-2.5", **kw):
        return pkg(refs, model=model, prompt="Style lock: Garena Free Fire in-game 3D character render. " + "Shot words. " * 80, **kw)

    def test_first_frame_drops_place_form_and_duplicates(self):
        same = "b" * 64
        refs = [ref("start_frame", None, param="image_path"), ref("character", "KELLY", sha=same, param="image_references"),
                ref("character", "KELLY", sha=same, param="image_references"), ref("location", "Cổng Trời", param="image_references"),
                ref("character_form", "KELLY", param="image_references")]
        rep = run(self._v(refs), {"byd": byd(co="MCU", dang={"KELLY": "bong_mo"}), "action": "Kelly catches her breath."},
                  kind="video")
        self.assertEqual(rep["loai"], "video_khung_dau")
        self.assertEqual([r["role"] for r in rep["ref_giu"]], ["start_frame", "character"])
        self.assertEqual(sorted(codes(rep).values()), ["khung_dau_da_o_dang", "khung_dau_mang_noi_chon", "trung_sha"])
        lines = rep["goi_gon"]["role_lines"]
        self.assertTrue(lines[0].startswith("@Image 1 ") and "first frame" in lines[0])
        self.assertTrue(lines[1].startswith("@Image 2 "))

    def test_form_changing_by_beat_is_kept(self):
        refs = [ref("start_frame", None, param="image_path"), ref("character", "KELLY"), ref("character_form", "KELLY")]
        rep = run(self._v(refs), {"byd": byd(dang={"KELLY": {"bat_dau": "thuong", "ket_thuc": "bong_mo"}})}, kind="video")
        self.assertEqual(rep["ref_bo"], [])

    def test_first_and_last_frame(self):
        refs = [ref("start_frame", None, param="image_path"), ref("last_frame", None, param="last_frame"), ref("character", "KELLY")]
        rep = run(self._v(refs), {"byd": byd()}, kind="video")
        self.assertEqual(rep["loai"], "video_dau_cuoi")
        self.assertIn("last frame", rep["goi_gon"]["role_lines"][1])

    def test_reference_video_not_redescribed_and_dialogue_vietnamese(self):
        refs = [ref("start_frame", None, param="image_path"), ref("character", "KENTA"),
                ref("reference_video", "skill", param="reference_video")]
        b = byd(cast=("KENTA",), hanh=[{"ai": "KENTA", "bat_dau": {"tu_the": "dung"}, "ket_thuc": {"tu_the": "quy"}}],
                thoai=[{"ai": "KENTA", "cau": "Đi thôi!"}])
        rep = run(self._v(refs), {"byd": b, "action": "Kenta swings the blade in a wide arc, then the wind ring spreads."}, kind="video")
        self.assertEqual(rep["loai"], "video_ref_hanh_dong")
        text = rep["goi_gon"]["prompt"]
        self.assertIn("@Video 1", text)
        self.assertNotIn("wide arc", text)                     # có video mang động tác → không tả lại
        self.assertIn('"Đi thôi!"', text)                       # thoại tiếng Việt gửi thẳng
        self.assertIn("kneeling", text)                         # chỉ trạng thái cuối

    def test_kling_naming_and_cap_with_video(self):
        refs = [ref("start_frame", None, param="image_path"), ref("character", "A"), ref("character", "B"), ref("character", "C"),
                ref("object", "X"), ref("reference_video", "v", param="reference_video")]
        rep = run(self._v(refs, model="kling"), {"byd": byd(cast=("A", "B", "C"), vat=[{"vat": "X", "kho_id": 1, "cach": "nem"}])},
                  kind="video")
        g = rep["goi_gon"]
        self.assertTrue(g["role_lines"][0].startswith("<<<image_1>>>"))
        self.assertIn("<<<video_1>>>", g["prompt"])
        images = [r for r in g["refs"] if r["role"] != "reference_video"]
        self.assertLessEqual(len(images), 4)
        self.assertIn("vuot_tran_model", codes(rep).values())

    def test_back_view_person_dropped_with_first_frame(self):
        refs = [ref("start_frame", None, param="image_path"), ref("character", "KELLY"), ref("character", "MAXIM")]
        rep = run(self._v(refs), {"byd": byd(cast=("KELLY", "MAXIM"), thay={"MAXIM": "lung"})}, kind="video")
        self.assertEqual(codes(rep), {("character", "MAXIM"): "chi_thay_lung"})
        self.assertIn("MAXIM stays with the back to the camera", rep["goi_gon"]["prompt"])


class Report(unittest.TestCase):
    def test_families_and_byd_coverage(self):
        p = pkg([ref("place_render", "P"), ref("character", "KELLY")], prompt=REAL_IMAGE)
        rep = run(p, {"byd": byd()})
        fam = {f["ma"]: f["quyet"] for f in rep["cau_cu"]}
        self.assertEqual(fam["plate_lead"], "DOI")
        self.assertEqual(fam["anchor_rule"], "BO")
        self.assertEqual(fam["weapon_scale"], "GIU")
        self.assertEqual(fam["identity_lock"], "BO")
        self.assertTrue(set(L.SENTENCE_FAMILIES) >= set(fam) - {"khac"})          # khac = chữ shot / câu lạ
        cov = rep["phu_byd"]
        self.assertEqual(cov["provenance"], "byd_v2")
        self.assertIn("may.co", cov["da_noi"])
        silent = {x["truong"]: x["ly_do"] for x in cov["khong_con_noi"]}
        self.assertIn("truyen.muc_dich", silent)
        self.assertIn("thanh_phan[].vung", silent)
        self.assertIn("noi_chon.thoi_gian", silent)
        self.assertEqual(rep["that"]["refs"], 2)
        self.assertIn("ty_le_chars", rep)

    def test_multi_shot_clip_is_said(self):
        p = pkg([ref("start_frame", None, param="image_path")], model="seedance-2.5",
                prompt="One clip with 2 shots cut in this order, hard cuts between shots. Shot 1 words.")
        rep = run(p, {"byd": byd()}, kind="video")
        self.assertIn("nhieu_shot", [w["ma"] for w in rep["canh_bao"]])
        self.assertIn("One clip with 2 shots", rep["goi_gon"]["prompt"])       # GIỮ: cấu trúc clip

    def test_bad_package_never_raises(self):
        rep = L.shadow("{not json", {}, kind="image", job_id=1)
        self.assertIn("loi", rep)
        rep = L.shadow(None, {}, kind="video", job_id=1)
        self.assertIn("loi", rep)


REAL = json.load(open(os.path.join(ROOT, "tests", "fixtures", "byd_vat_v1_p30_p31.json"), encoding="utf-8"))["cases"]


def real_case(project, idx):
    return next(c for c in REAL if c["project"] == project and c["idx"] == idx)


class ReviewFixes(unittest.TestCase):
    """Rà C-M210 (@d021c1fb): VỪA-1 dạng 'thuong' = mặc định; THẤP: thanh_phan có vật, enabled() ném lỗi."""

    def test_real_p30_shot3_default_form_is_not_a_form_change(self):
        c = real_case(30, 3)                                 # thanh_phan KELLY dang "thuong", vat ["BOM_KEO"] (v1)
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("object", "BOM_KEO")])
        rep = run(p, {"byd": c["byd"]})
        self.assertNotIn("doi_dang", rep["the"])
        self.assertEqual(rep["loai"], "anh_co_vat")
        line = rep["goi_gon"]["role_lines"][1]
        self.assertNotIn("NOT the clothes", line)
        self.assertIn("outfit", line)

    def test_real_p31_idx33_form_by_beat_names_the_special_form(self):
        c = real_case(31, 33)                                # KELLY dang {bat_dau: bong_mo_song_song, ket_thuc: thuong}
        p = pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("character_form", "KELLY")])
        rep = run(p, {"byd": c["byd"]})
        self.assertIn("doi_dang", rep["the"])
        self.assertIn("bong mo song song", rep["goi_gon"]["role_lines"][2])     # không lấy 'thuong' làm tên dạng
        vrep = run(pkg([ref("start_frame", None, param="image_path"), ref("character", "KELLY"), ref("character_form", "KELLY")],
                       model="seedance-2.5"), {"byd": c["byd"]}, kind="video")
        self.assertEqual(vrep["ref_bo"], [])                 # biến hình theo nhịp: giữ ảnh dạng

    def test_default_form_dict_and_list_are_not_forms(self):
        for dang in ("thuong", ["thuong"], {"bat_dau": "thuong", "ket_thuc": "thuong"}, "Thường"):
            self.assertFalse(L.has_form({"dang": dang}), dang)
        self.assertTrue(L.has_form({"dang": ["thuong", "bong_mo"]}))

    def test_props_in_thanh_phan_are_not_people(self):
        b = byd(cast=("KELLY", "BOM_KEO", "THUNG_GO"), vat=[{"vat": "BOM_KEO", "kho_id": 3, "nguoi": "KELLY", "cach": "nem"}])
        data = {"byd": b, "blocking": {"objects": [{"key": "KELLY", "kind": "nguoi"}, {"key": "THUNG_GO", "kind": "vat"}]}}
        rep = run(pkg([ref("place_render", "P"), ref("character", "KELLY")]), data)
        self.assertNotIn("nhieu_nguoi", rep["the"])
        self.assertNotIn("never swap", rep["goi_gon"]["prompt"])

    def test_enabled_raising_is_said_and_never_breaks(self):
        from core import runner
        notes = []

        class Stub(runner.ImageRunner):
            def __init__(s):
                pass

            def _diag(s, job, severity, code, message):
                notes.append((severity, code, message))
        with mock.patch.object(L, "enabled", side_effect=RuntimeError("cờ hỏng")), mock.patch.object(L, "shadow") as sh:
            Stub()._say_package({"id": 1, "project_id": 1, "scene_id": 1}, [])
        sh.assert_not_called()
        self.assertEqual([(n[0], n[1]) for n in notes], [("warn", "lean_package")])
        self.assertIn("cờ hỏng", notes[0][2])


class RealSendLoop(unittest.TestCase):
    """Vòng gửi THẬT (ImageRunner.submit_pending + provider giả): cờ BẬT ≠ đổi gì đã gửi; chỉ thêm tệp + một dòng ⚙."""

    def _send(self, env):
        from core.db import connect
        from core.pipeline import Pipeline
        from core.providers import MockImageProvider
        from core.runner import ImageRunner
        tmp = tempfile.mkdtemp()
        p = Pipeline(connect(os.path.join(tmp, "t.db")))
        pid = p.create_project("m210", max_retry=2)
        scene = p.create_scene(pid, 1, "S1")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "Kelly đứng ở bậc thang.", "byd": byd()},
                                                                          ensure_ascii=False), scene))
        p.conn.commit()
        job = p.create_job(scene)
        prov = MockImageProvider()
        calls = []
        orig = prov.submit

        def spy(*a, **k):
            calls.append((a, dict(k)))
            return orig(*a, **k)
        prov.submit = spy
        data = os.path.join(tmp, "projects")
        os.makedirs(data)
        with mock.patch.dict(os.environ, env):
            ImageRunner(p, prov, data).submit_pending(pid)
        pkg_row = json.loads(p.conn.execute("SELECT sent_package FROM jobs WHERE id=?", (job,)).fetchone()[0])
        notes = p.conn.execute("SELECT code FROM diag_events WHERE code=?", (L.DIAG_CODE,)).fetchall()
        files = os.path.exists(os.path.join(data, "lean_package", str(pid), f"job_{job}.json"))
        p.conn.close()
        return calls, {k: v for k, v in pkg_row.items() if k not in ("at", "external_id")}, len(notes), files

    def test_flag_on_changes_nothing_sent(self):
        off = self._send(OFF)
        on = self._send(ON)
        self.assertEqual(len(off[0]), 1)
        self.assertEqual(off[0], on[0])                      # đúng một lần gửi, cùng đối số
        self.assertEqual(off[1], on[1])                      # gói thật giống hệt (trừ giờ / mã task)
        self.assertEqual((off[2], off[3]), (0, False))       # TẮT: không ⚙, không tệp
        self.assertEqual((on[2], on[3]), (1, True))          # BẬT: một ⚙ + một tệp


def _db(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.executescript("CREATE TABLE scenes (id INTEGER PRIMARY KEY, project_id INTEGER, idx INTEGER, data TEXT);"
                    "CREATE TABLE jobs (id INTEGER PRIMARY KEY, project_id INTEGER, scene_id INTEGER, type TEXT, state TEXT,"
                    " sent_package TEXT);")
    return c


class RunnerHook(unittest.TestCase):
    def setUp(self):
        from core import runner
        self.tmp = tempfile.mkdtemp()
        self.conn = _db(":memory:")
        self.pkg = json.dumps(pkg([ref("place_render", "P"), ref("character", "KELLY"), ref("character", "KELLY", param="r2")],
                                  prompt=REAL_IMAGE), ensure_ascii=False)
        self.conn.execute("INSERT INTO scenes VALUES (5, 31, 3, ?)", (json.dumps({"byd": byd()}),))
        self.conn.execute("INSERT INTO jobs VALUES (7, 31, 5, 'image_gen', 'running', ?)", (self.pkg,))
        notes = self.notes = []

        class Stub(runner.ImageRunner):
            def __init__(s):
                s.p = mock.Mock(conn=self.conn)
                s.data_dir = self.tmp

            def _diag(s, job, severity, code, message):
                notes.append((severity, code, message))
        self.r = Stub()
        self.job = {"id": 7, "project_id": 31, "scene_id": 5}

    def test_flag_off_calls_nothing(self):
        with mock.patch.dict(os.environ, OFF), mock.patch.object(L, "shadow") as sh:
            self.r._say_package(self.job, [])
        sh.assert_not_called()
        self.assertEqual(self.notes, [])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "lean_package")))

    def test_flag_on_writes_file_and_one_note_package_unchanged(self):
        with mock.patch.dict(os.environ, ON):
            self.r._say_package(self.job, [])
        out = os.path.join(self.tmp, "lean_package", "31", "job_7.json")
        rep = json.load(open(out, encoding="utf-8"))
        self.assertEqual(rep["job_id"], 7)
        self.assertEqual([n[1] for n in self.notes], [L.DIAG_CODE])
        self.assertIn("KHÔNG gửi", self.notes[0][2])
        self.assertEqual(self.conn.execute("SELECT sent_package FROM jobs WHERE id=7").fetchone()[0], self.pkg)

    def test_flag_on_error_is_said_not_raised(self):
        with mock.patch.dict(os.environ, ON), mock.patch.object(L, "shadow", side_effect=RuntimeError("hỏng")):
            self.r._say_package(self.job, ["cảnh báo gói"])
        self.assertEqual([n[1] for n in self.notes], ["sent_package", L.DIAG_CODE])
        self.assertIn("hỏng", self.notes[1][2])


class Tool(unittest.TestCase):
    def test_tool_reads_db_readonly_and_writes_summary(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("lean_package_shadow", os.path.join(ROOT, "tools", "lean_package_shadow.py"))
        T = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(T)
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, "db"))
        dbp = os.path.join(tmp, "db", "p.db")
        c = _db(dbp)
        c.execute("INSERT INTO scenes VALUES (5, 31, 3, ?)", (json.dumps({"byd": byd()}),))
        c.execute("INSERT INTO jobs VALUES (7, 31, 5, 'image_gen', 'succeeded', ?)",
                  (json.dumps(pkg([ref("place_render", "P"), ref("character", "KELLY")], prompt=REAL_IMAGE)),))
        c.execute("INSERT INTO jobs VALUES (8, 31, 5, 'video_gen', 'succeeded', ?)",
                  (json.dumps(pkg([ref("start_frame", None, param="image_path"), ref("location", "P")], model="seedance-2.5")),))
        c.execute("INSERT INTO jobs VALUES (9, 31, 5, 'video_gen', 'failed', NULL)")
        c.commit()
        c.close()
        before = hashlib.sha256(open(dbp, "rb").read()).hexdigest()
        out = os.path.join(tmp, "out")
        self.assertEqual(T.main(["--db", dbp, "--project", "31", "--out", out]), 0)
        self.assertEqual(hashlib.sha256(open(dbp, "rb").read()).hexdigest(), before)
        self.assertTrue(os.path.exists(os.path.join(out, "job_7.json")) and os.path.exists(os.path.join(out, "job_8.json")))
        summary = json.load(open(os.path.join(out, "tong_hop.json"), encoding="utf-8"))
        self.assertEqual(summary["so_goi"], {"image_gen": 1, "video_gen": 1})
        self.assertIn("image_gen", summary["tb"])
        self.assertTrue(os.path.exists(os.path.join(out, "tong_hop.md")))
        # rà C-M210 THẤP: --out dưới thư mục CSDL / data/ của repo → từ chối, không ghi gì
        bad = os.path.join(tmp, "db", "out")
        self.assertEqual(T.main(["--db", dbp, "--project", "31", "--out", bad]), 2)
        self.assertFalse(os.path.exists(bad))
        self.assertEqual(T.main(["--db", dbp, "--project", "31", "--out", os.path.join(ROOT, "data", "lean_x")]), 2)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "data", "lean_x")))


if __name__ == "__main__":
    unittest.main()
