"""V3.1 M2.7 (DP9) — kiểm ẢNH TRƯỚC gen, mức SHADOW: core/image_pregen.py + bộ mã chung core/pregen_codes.py, nối ở ImageRunner._pregen
(cờ image_pregen, mặc định tắt). Mỗi mã một ca ĐỎ / VÀNG / đạt; shadow chỉ ghi ⚙ Chẩn đoán, KHÔNG giữ job; cờ tắt y cũ (không gọi
check); điểm chặn cũ (nền 3D lẫn máy, _blocked) giữ nguyên lời. CSDL tạm, provider giả, không mạng, không đụng data/."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import assets, image_pregen, location_pack, place_refs, pregen_codes, prompt_formula, stage_facts, video_pregen
from core.db import connect
from core.pipeline import Pipeline
from tests._flags import flags_on
from tests.test_plate_package_single_angle import _Send
from tests.test_plate_stale_kld6 import plate_png

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Unit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.p = Pipeline(connect(os.path.join(self.tmp, "t.db")))
        self.addCleanup(self.p.conn.close)
        self.pid = self.p.create_project("m27")
        self.sid = self.p.create_scene(self.pid, 1, "S1")
        self.data({"image_prompt": "Kelly runs", "byd": {"shot": 1}})

    def data(self, d):
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), self.sid))
        self.p.conn.commit()

    def pic(self, name="a.png", body=b"\x89PNG-picture"):
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as f:
            f.write(body)
        return path

    def plan(self, **over):
        p = {"job_id": 99, "project_id": self.pid, "data_dir": self.tmp, "prompt": "Kelly runs", "references": [], "size": None,
             "model": None, "storyboard": None, "sent": [], "dropped": [], "package": {"call": "submit", "prompt": "Kelly runs", "refs": []}}
        p.update(over)
        return p

    def codes(self, plan=None):
        with mock.patch.object(location_pack, "plate_of", return_value=None):
            return [(i["ma"], i["muc"]) for i in image_pregen.check(self.p.conn, self.sid, plan or self.plan())]

    def test_clean_plan_passes(self):
        self.assertEqual(self.codes(), [])

    # ---- nen_3d: lời cũ của plate_package_mixed, không đổi chữ -------------------------------------------------------------------
    def test_plate_of_another_camera_is_red_with_the_old_words(self):
        sent = [{"role": place_refs.ROLE, "plate_key": "zzz", "file": "plate.png"}]
        with mock.patch.object(place_refs, "package_problem", return_value="plate.png khóa zzz = nền của góc máy KHÁC"):
            issues = image_pregen.check(self.p.conn, self.sid, self.plan(sent=sent))
        hit = [i for i in issues if i["ma"] == "nen_3d"]
        self.assertEqual(hit[0]["muc"], pregen_codes.DO)
        self.assertEqual(hit[0]["ly_do"], "CẦN BẠN SỬA: plate.png khóa zzz = nền của góc máy KHÁC — ảnh GIỮ CHỜ, không gửi (0 USD); "
                                          "render lại nền 3D / sửa góc máy rồi sẽ tự gửi")

    def test_no_sent_list_no_plate_check(self):
        with mock.patch.object(place_refs, "package_problem") as pp:
            image_pregen.check(self.p.conn, self.sid, self.plan())
        pp.assert_not_called()

    # ---- bo_cuc_kho / cong_thuc: cùng hàm + cùng lời _blocked --------------------------------------------------------------------
    def test_layout_and_formula_red(self):
        with mock.patch.object(assets, "missing_layout", return_value="thiếu bố cục tháp"), \
                mock.patch.object(prompt_formula, "red_issues", return_value=["thiếu phần ánh sáng"]):
            issues = image_pregen.check(self.p.conn, self.sid, self.plan())
        got = {i["ma"]: i for i in issues}
        self.assertEqual(got["bo_cuc_kho"]["ly_do"], "thiếu bố cục tháp")
        self.assertEqual(got["cong_thuc"]["ly_do"], "prompt ảnh sai công thức — sửa ở Bước 1/2: thiếu phần ánh sáng")
        self.assertEqual({got["bo_cuc_kho"]["muc"], got["cong_thuc"]["muc"]}, {pregen_codes.DO})

    # ---- tham_chieu --------------------------------------------------------------------------------------------------------------
    def test_unreadable_reference_red_readable_passes(self):
        good = self.pic()
        self.assertEqual(self.codes(self.plan(references=[good])), [])
        self.assertIn(("tham_chieu", "do"), self.codes(self.plan(references=[good, os.path.join(self.tmp, "missing.png")])))

    def test_more_pictures_than_the_model_takes_is_red(self):
        refs = [self.pic(f"{i}.png") for i in range(3)]
        with mock.patch("core.image_models.max_refs", return_value=2):
            issues = image_pregen.check(self.p.conn, self.sid, self.plan(references=refs, model="m"))
        self.assertTrue(any(i["ma"] == "tham_chieu" and i["muc"] == "do" and "trần 2" in i["ly_do"] for i in issues))

    def test_dropped_picture_is_yellow(self):
        issues = image_pregen.check(self.p.conn, self.sid, self.plan(dropped=["KELLY (file rỗng)"]))
        self.assertEqual([(i["ma"], i["muc"]) for i in issues], [("tham_chieu", "vang")])
        self.assertIn("KELLY (file rỗng)", issues[0]["ly_do"])

    # ---- van_tay (N10) -----------------------------------------------------------------------------------------------------------
    def previous(self, pkg, approved=True):
        job = self.p.create_job(self.sid, "image_gen")
        self.p.start(job)
        if approved:
            self.p.succeed(job)
            self.p.approve(job)
        else:
            self.p.fail(job, "provider error")
        self.p.conn.execute("UPDATE jobs SET sent_package=? WHERE id=?", (json.dumps(pkg), job))
        self.p.conn.commit()
        return job

    def test_same_package_as_a_picture_already_made_is_red(self):
        pkg = self.plan()["package"]
        old = self.previous(dict(pkg, at="yesterday", external_id="t1"))
        issues = image_pregen.check(self.p.conn, self.sid, self.plan())
        hit = [i for i in issues if i["ma"] == "van_tay"]
        self.assertEqual(hit[0]["muc"], "do")
        self.assertIn(f"job {old}", hit[0]["ly_do"])

    def test_same_package_after_a_provider_failure_is_yellow_and_a_changed_one_passes(self):
        pkg = self.plan()["package"]
        self.previous(pkg, approved=False)
        self.assertIn(("van_tay", "vang"), self.codes())
        self.assertEqual(self.codes(self.plan(package=dict(pkg, prompt="Kelly runs, rim light"))), [])

    def test_no_package_is_red(self):
        self.assertIn(("van_tay", "do"), self.codes(self.plan(package=None)))

    # ---- byd / byd_draft ---------------------------------------------------------------------------------------------------------
    def test_missing_byd_yellow_and_draft_byd_yellow(self):
        self.data({"image_prompt": "x"})
        self.assertEqual(self.codes(), [("byd", "vang")])
        self.data({"image_prompt": "x", "byd": {"shot": 2, "_p": {"by": "code", "draft": True, "from": 41}}})
        issues = image_pregen.check(self.p.conn, self.sid, self.plan())
        self.assertEqual([(i["ma"], i["muc"]) for i in issues], [("byd_draft", "vang")])
        self.assertIn("#41", issues[0]["ly_do"])

    # ---- khoi_giu_cho (G1) -------------------------------------------------------------------------------------------------------
    def test_block_in_the_render_without_its_sentence_is_red(self):
        fact = {"kind": "stand_in", "name": "black flying corpse",
                "prompt": "The grey block in the background render is a placeholder for black flying corpse."}
        sent = [{"role": place_refs.ROLE, "plate_key": "k", "file": "plate.png"}]
        with mock.patch.object(stage_facts, "for_shot", return_value={"facts": [fact], "missing": None}), \
                mock.patch.object(place_refs, "package_problem", return_value=None):
            bad = image_pregen.check(self.p.conn, self.sid, self.plan(sent=sent, prompt="Kelly runs"))
            good = image_pregen.check(self.p.conn, self.sid, self.plan(sent=sent, prompt="Kelly runs. " + fact["prompt"]))
            no_render = image_pregen.check(self.p.conn, self.sid, self.plan(sent=[{"role": "character", "file": "k.png"}]))
        self.assertEqual([(i["ma"], i["muc"]) for i in bad], [("khoi_giu_cho", "do")])
        self.assertIn("black flying corpse", bad[0]["ly_do"])
        self.assertEqual(good, [])
        self.assertEqual(no_render, [])

    # ---- loi_kiem: một lớp hỏng nói rõ, các lớp khác vẫn chạy -------------------------------------------------------------------
    def test_a_broken_check_is_red_and_the_others_still_run(self):
        self.data({"image_prompt": "x"})
        with mock.patch.object(assets, "missing_layout", side_effect=RuntimeError("kho hỏng")):
            issues = image_pregen.check(self.p.conn, self.sid, self.plan())
        got = {i["ma"]: i for i in issues}
        self.assertEqual(got["loi_kiem"]["muc"], "do")
        self.assertIn("RuntimeError: kho hỏng", got["loi_kiem"]["ly_do"])
        self.assertIn("layout", got["loi_kiem"]["ly_do"])
        self.assertIn("byd", got)

    def test_plan_of_reads_the_real_submit_call(self):
        job = {"id": 5, "project_id": self.pid}
        plan = image_pregen.plan_of(job, ("p", ["/a.png"]), {"size": "1x1", "model": "m", "_x": 1}, json.dumps({"call": "submit"}),
                                    self.tmp, sent=[{"role": "r"}], dropped=["d"])
        self.assertEqual((plan["prompt"], plan["references"], plan["size"], plan["model"]), ("p", ["/a.png"], "1x1", "m"))
        self.assertEqual((plan["sent"], plan["dropped"], plan["package"]), ([{"role": "r"}], ["d"], {"call": "submit"}))

    def test_shadow_line_says_review_and_the_enforced_level(self):
        line = image_pregen.shadow_line({"ma": "nen_3d", "muc": "do", "ly_do": "x"})
        self.assertTrue(line.startswith("REVIEW (shadow, không giữ — sẽ là ĐỎ"))
        self.assertIn("[nen_3d] x", line)

    def test_preview_reads_shot_data_only(self):
        self.data({"image_prompt": "x"})
        with mock.patch.object(prompt_formula, "red_issues", return_value=["thiếu phần ánh sáng"]):
            out = image_pregen.preview(self.p.conn, self.pid, self.tmp)
        self.assertEqual(out[0]["idx"], 1)
        self.assertEqual({i["ma"] for i in out[0]["issues"]}, {"cong_thuc", "byd"})


class Codes(unittest.TestCase):
    def test_video_uses_the_shared_constants_unchanged(self):
        self.assertEqual((video_pregen.DO, video_pregen.VANG), ("do", "vang"))
        self.assertIs(video_pregen.DO, pregen_codes.DO)

    def test_every_error_id_is_in_the_error_book(self):
        with open(os.path.join(ROOT, "devsys", "errors.json"), encoding="utf-8") as f:
            ids = {i["id"] for i in json.load(f)["items"]}
        for ma, refs in pregen_codes.ERRORS.items():
            self.assertIn(ma, pregen_codes.CODES)
            self.assertLessEqual(set(refs), ids, ma)

    def test_every_code_the_checks_write_is_known(self):
        import inspect
        src = inspect.getsource(image_pregen) + inspect.getsource(video_pregen)
        import re
        for ma in set(re.findall(r'_issue\("([a-z_0-9]+)"', src)) | {"loi_kiem"}:
            self.assertIn(ma, pregen_codes.CODES, ma)


class RunnerShadow(_Send):
    """ImageRunner._pregen: cờ tắt = y cũ (check không được gọi); cờ bật = REVIEW trong ⚙ Chẩn đoán, job VẪN GỬI; điểm chặn cũ giữ."""

    def send(self):
        self.render()
        self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async"):
            return self.runner().submit_pending(self.pid)

    def test_flag_off_never_runs_the_check(self):
        flags_on(self, "image_pregen", value=False)
        with mock.patch.object(image_pregen, "check") as chk:
            self.assertEqual(self.send(), 1)
        chk.assert_not_called()
        self.assertEqual(self.diags(image_pregen.DIAG_CODE), [])

    def test_flag_on_writes_review_lines_and_still_sends(self):
        flags_on(self, "image_pregen")
        self.assertEqual(self.send(), 1)                                 # shadow never holds
        self.assertEqual(self.job_row()["state"], "running")
        lines = [d["message"] for d in self.diags(image_pregen.DIAG_CODE)]
        self.assertTrue(lines)
        self.assertTrue(all(m.startswith("REVIEW (shadow") for m in lines))
        self.assertTrue(any("[byd]" in m for m in lines))               # this shot has no BYĐ: VÀNG byd

    def test_flag_on_with_a_red_issue_still_sends(self):
        flags_on(self, "image_pregen")
        red = [{"ma": "van_tay", "muc": "do", "ly_do": "gói trùng"}]
        with mock.patch.object(image_pregen, "check", return_value=red) as chk:
            self.assertEqual(self.send(), 1)
        plan = chk.call_args[0][2]
        self.assertTrue(plan["prompt"])                                  # the real prompt about to leave
        self.assertTrue(plan["references"])
        self.assertTrue(any(s.get("role") == place_refs.ROLE for s in plan["sent"]))
        self.assertEqual(plan["package"]["call"], "submit")
        self.assertIn("[van_tay] gói trùng", self.diags(image_pregen.DIAG_CODE)[0]["message"])

    def test_a_check_that_raises_is_said_and_the_send_goes_on(self):
        flags_on(self, "image_pregen")
        with mock.patch.object(image_pregen, "check", side_effect=RuntimeError("boom")):
            self.assertEqual(self.send(), 1)
        msg = self.diags(image_pregen.DIAG_CODE)[0]["message"]
        self.assertIn("[loi_kiem]", msg)
        self.assertIn("RuntimeError: boom", msg)

    def test_old_plate_hold_unchanged_and_shadow_also_says_it(self):
        """Mọi mức cờ: nền 3D của máy khác vẫn GIỮ như trước (plate_package_mixed, cùng lời); cờ bật thêm dòng REVIEW nen_3d."""
        from core.runner import WAIT_REASONS
        flags_on(self, "image_pregen")
        self.render()
        bad_wide = {"path": plate_png(os.path.join(self.tmp, "old.png")), "label": "w", "role": place_refs.WIDE_ROLE, "plate_key": "zzz"}
        job = self.p.create_job(self.sid, "image_gen")
        with mock.patch.object(place_refs, "ensure_async"), mock.patch.object(place_refs, "wide_ref", return_value=bad_wide):
            self.assertEqual(self.runner().submit_pending(self.pid), 0)
        self.assertEqual(self.job_row()["state"], "queued")
        self.assertTrue(WAIT_REASONS[job][0].startswith("CẦN BẠN SỬA: "))
        self.assertTrue(WAIT_REASONS[job][0].endswith("render lại nền 3D / sửa góc máy rồi sẽ tự gửi"))
        self.assertTrue(self.diags("plate_package_mixed"))
        self.assertTrue(any("[nen_3d]" in d["message"] and "zzz" in d["message"] for d in self.diags(image_pregen.DIAG_CODE)))

    def test_blocked_words_unchanged(self):
        r = self.runner()
        job = {"id": 1, "project_id": self.pid, "scene_id": self.sid}
        with mock.patch.object(assets, "missing_layout", return_value="thiếu bố cục"):
            self.assertEqual(r._blocked(job), "thiếu bố cục")
        with mock.patch.object(assets, "missing_layout", return_value=None), \
                mock.patch.object(prompt_formula, "red_issues", return_value=["a", "b"]):
            self.assertEqual(r._blocked(job), "prompt ảnh sai công thức — sửa ở Bước 1/2: a · b")
        with mock.patch.object(assets, "missing_layout", return_value=None), mock.patch.object(prompt_formula, "red_issues", return_value=[]):
            self.assertIsNone(r._blocked(job))


if __name__ == "__main__":
    unittest.main()
