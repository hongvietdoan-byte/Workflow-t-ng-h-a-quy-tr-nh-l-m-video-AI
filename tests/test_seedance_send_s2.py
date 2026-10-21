"""Phiên S2 (rà gốc video #27 13/10, docs/handoff/RA_GOC_VIDEO_P27_2026-10-13.md): công thức gói gửi video Seedance — V1 (render 3D
không thắng khung đầu), V5 (không dấu trên mắt, kể cả khung đầu / sau từ chối), V8 (nhóm không gen lại shot người đã duyệt), V10 (trạng
thái nhân vật chỉ có trong chữ), V13 (ảnh tham chiếu sai luật tỉ lệ bắt trước khi gửi). Dữ liệu giả, không gọi API."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import prompt_formula, seedance_refs, shots
from core.db import connect
from core.pipeline import Pipeline
from tests import test_seedance_refs as base   # module, not the class: pytest would run its tests twice


def textured(path, seed=1, size=(640, 360)):
    rng = np.random.default_rng(seed)
    small = rng.integers(0, 255, (size[1] // 8, size[0] // 8, 3), dtype=np.uint8)
    Image.fromarray(small).resize(size, Image.NEAREST).save(path)
    return path


def red_box(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    ys, xs = np.nonzero((a[..., 0] > 180) & (a[..., 1] < 60) & (a[..., 2] < 60))
    h, w = a.shape[:2]
    return (xs.min() / w, ys.min() / h) if len(xs) else None


def env(**flags):
    return mock.patch.dict(os.environ, {"FEATURE_" + k.upper(): "1" if v else "0" for k, v in flags.items()})


OLD_PLACE = ("It decides architecture over conflicting text or storyboard details; people, outfits and starting framing still follow "
             "their own references.")


class PlaceSentenceV1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _prompt(self, view=None):
        return seedance_refs.prompt([("Kelly crouches behind the wall.", 2.0)], [("KELLY", "k.png")],
                                    places=[{"path": "p.png", "shots": [1], "view": view}])

    def test_place_text_never_overrides_storyboard(self):
        with env(plate_view_sentence=False):
            off = self._prompt()
        self.assertIn(OLD_PLACE, off)                                    # flag off: the old sentence, word for word
        with env(plate_view_sentence=True):
            unknown, same = self._prompt(None), self._prompt("same")
        for text in (unknown, same):
            self.assertNotIn("decides architecture", text)
            self.assertIn("The storyboard frame decides framing, camera distance, angle and what is in view", text)
            self.assertIn("never pull back or re-frame to match this render", text)
            self.assertIn("Image 3 is the 3D PLACE render for Shot 1", text)   # 1 frame + 1 identity → render is Image 3
        self.assertIn("from ANOTHER camera position", unknown)           # not measured → the careful sentence, never 'same'
        self.assertNotIn("ANOTHER camera", same)
        self.assertIn("keep exactly these shapes", same)

    def test_plate_view_measures_the_camera(self):
        plate = textured(os.path.join(self.tmp, "plate.png"), seed=3)
        im = Image.open(plate)
        near = im.crop((16, 9, 624, 351)).resize(im.size)               # the same view, 5 % tighter
        near.save(os.path.join(self.tmp, "near.png"))
        textured(os.path.join(self.tmp, "other.png"), seed=99)
        self.assertEqual(seedance_refs.plate_view(plate, os.path.join(self.tmp, "near.png"))["view"], "same")
        self.assertEqual(seedance_refs.plate_view(plate, os.path.join(self.tmp, "other.png"))["view"], "other")
        self.assertIsNone(seedance_refs.plate_view(plate, None)["view"])  # no start frame: not measured, said in "why"
        self.assertTrue(seedance_refs.plate_view(plate, None)["why"])

    def test_place_pictures_carry_the_measured_view(self):
        plate = textured(os.path.join(self.tmp, "plate.png"), seed=3)
        other = textured(os.path.join(self.tmp, "other.png"), seed=99)
        rows = [{"id": 1, "data": {}}, {"id": 2, "data": {}}]
        with env(place_render_refs=True, plate_view_sentence=True), \
                mock.patch("core.place_refs.shot_ref", return_value={"path": plate}):
            same = seedance_refs.place_pictures(self.tmp, 1, rows, starts={1: plate, 2: plate})
            mixed = seedance_refs.place_pictures(self.tmp, 1, rows, starts={1: plate, 2: other})
            unmeasured = seedance_refs.place_pictures(self.tmp, 1, rows)
        self.assertEqual(same[0]["view"], "same")
        self.assertEqual(mixed[0]["view"], "other")                      # one shot of another camera → the render is not 'same'
        self.assertNotIn("view", unmeasured[0])
        with env(place_render_refs=True, plate_view_sentence=False), \
                mock.patch("core.place_refs.shot_ref", return_value={"path": plate}):
            self.assertEqual(seedance_refs.place_pictures(self.tmp, 1, rows, starts={1: plate}), [{"path": plate, "shots": [1, 2]}])


class MarksV5(unittest.TestCase):
    setUp = base.SeedanceRefTests.setUp
    _ready = base.SeedanceRefTests._ready

    def test_start_frame_never_eye_marked(self):
        vr = self._ready()
        frame = shots.approved_image_path(self.p.conn, self.data, self.pid, self.ids[0])
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        with env(ref_mark_off_face=True):
            marked = seedance_refs.mark(frame, out, "eye_plus")         # a caller still asking for the eye mark (quality_samples)
        self.assertTrue(marked.endswith("_marked_corner_plus.png"))
        x, y = red_box(marked)
        self.assertGreater(x, 0.8)
        self.assertGreater(y, 0.85)
        with env(ref_mark_off_face=False):
            self.assertTrue(seedance_refs.mark(frame, out, "eye_plus").endswith("_marked.png"))   # flag off: as before
        del vr

    def test_refusal_never_returns_to_eye_plus_on_face(self):
        from core import model_router
        from core.adapters.clipai import REAL_PERSON
        with env(ref_mark_off_face=True):
            vr = self._ready()
            leader = self.p.job(self.p.create_job(self.ids[0], "video_gen"))
            self.p.conn.execute("UPDATE jobs SET model='seedance-2.5' WHERE id=?", (leader["id"],))
            self.assertFalse(seedance_refs.step_mark_back(self.p.conn, self.ids))
            self.assertTrue(vr._on_refused(self.p.job(leader["id"]), REAL_PERSON, "may contain real person"))
            self.assertIsNone(shots.group_of(self.p.conn, self.ids[0]))   # the route ladder at once, no eye-mark step
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")
            self.assertIn("seedance", model_router.scene_choice(self.p.conn, self.ids[0])["model"])
            d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (self.ids[0],)).fetchone()["data"])
            d[seedance_refs.MARK_KEY] = "eye_plus"                        # an old row written before V5
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), self.ids[0]))
            self.assertEqual(seedance_refs.mark_style(self.p.conn, self.ids), "corner_plus")
            refs = vr._submit_kwargs(self.p.job(leader["id"]))["reference_only"]
            self.assertTrue(refs and all(p.endswith("_marked_corner_plus.png") for p in refs))


class GroupKeepsApprovedV8(unittest.TestCase):
    setUp = base.SeedanceRefTests.setUp
    _ready = base.SeedanceRefTests._ready

    def _approved_clip(self, sid, who="user"):
        conn = self.p.conn
        img = conn.execute("SELECT id FROM jobs WHERE scene_id=? AND type='image_gen' AND state='approved' ORDER BY id DESC LIMIT 1",
                           (shots.image_scene(conn, sid),)).fetchone()["id"]
        jid = self.p.create_job(sid, "video_gen")
        conn.execute("UPDATE jobs SET state='approved', source_job_id=?, input_hash=NULL WHERE id=?", (img, jid))
        conn.execute("INSERT INTO review_log (job_id, reviewer_type, decision, note, decided_at) VALUES (?,?,?,?,?)",
                     (jid, who, "approve", None, "2026-10-13T20:00:00"))
        conn.commit()
        return jid

    def _group_ids(self):
        g = shots.group_of(self.p.conn, self.ids[0]) or []
        return [r["id"] for r in g]

    def test_approved_member_is_not_regenerated(self):
        self._ready()
        self._approved_clip(self.ids[1])
        with env(group_keep_approved=False):
            self.assertEqual(self._group_ids(), self.ids)               # flag off: the group as before
        with env(group_keep_approved=True):
            self.assertEqual(self._group_ids(), [])                      # every shot goes alone; the approved take stays
            self.assertEqual(seedance_refs.person_kept(self.p.conn, self.pid, self.ids), {self.ids[1]})

    def test_machine_approval_or_changed_motion_does_not_keep(self):
        self._ready()
        jid = self._approved_clip(self.ids[1], who="ai_agent")
        with env(group_keep_approved=True):
            self.assertEqual(self._group_ids(), self.ids)               # QC / autopilot approval is not the person's
            self.p.conn.execute("UPDATE review_log SET reviewer_type='user' WHERE job_id=?", (jid,))
            self.p.conn.execute("UPDATE jobs SET input_hash='old-motion' WHERE id=?", (jid,))
            self.p.conn.commit()
            self.assertEqual(self._group_ids(), self.ids)               # the motion changed since: that take is outdated

    def test_whole_group_approved_stays_a_group(self):
        self._ready()
        for sid in self.ids:
            self._approved_clip(sid)
        with env(group_keep_approved=True):
            self.assertEqual(self._group_ids(), self.ids)               # the final upgrade is per group clip (quality_tier)


class CharacterStateV10(unittest.TestCase):
    DATA = {"characters": ["KELLY"], "size": "MS", "camera_move": "static", "duration_s": 3,
            "image_prompt": "KELLY, a blurred translucent ghost, crouches behind the tall glue wall.",
            "action": "Kelly crouches lower and looks left."}

    def test_character_state_locked_for_whole_clip(self):
        with env(character_state_lock=False):
            off = seedance_refs.shot_motion(dict(self.DATA))
        self.assertNotIn("stays", off)
        with env(character_state_lock=True):
            on = seedance_refs.shot_motion(dict(self.DATA))
            group = seedance_refs.prompt([(on, 3.0), (on.replace("looks left", "looks right"), 3.0)], [("KELLY", "k.png")])
            lint = prompt_formula.state_issues(on, dict(self.DATA))
        self.assertEqual(on.replace("KELLY stays a blurred translucent ghost for the whole shot, first to last frame — the identity "
                                    "picture shows the normal look; keep this state, not the picture. ", ""), off)   # only that added
        self.assertEqual(group.count("KELLY stays a blurred translucent ghost"), 1)      # a group says it once (shared line)
        self.assertEqual([i["part"] for i in lint], ["trang_thai_nv"])
        self.assertIn("ảnh danh tính là dạng thường", lint[0]["msg"])
        self.assertNotIn("chưa có câu giữ", lint[0]["msg"])

    def test_vietnamese_state_and_given_field(self):
        with env(character_state_lock=True):
            vi = seedance_refs.character_states({"characters": ["KELLY"], "blocking": "KELLY dạng bóng mờ đứng sau tường"})
            given = seedance_refs.character_states({"characters": ["KELLY"], "character_state": {"KELLY": "bóng mờ"}})
            passing = seedance_refs.character_states({"characters": ["KELLY"],
                                                      "action": "Kelly watches a translucent ghost glide past her face."})
            lint = prompt_formula.state_issues("Kelly crouches.", {"characters": ["KELLY"], "character_state": {"KELLY": "bóng mờ"}})
        self.assertEqual(vi, {"KELLY": "a blurred translucent ghost"})
        self.assertEqual(given, {"KELLY": "a blurred translucent ghost"})
        self.assertEqual(passing, {})                                    # a ghost passing by is not Kelly's state
        self.assertIn("chưa có câu giữ", lint[0]["msg"])


class ReferenceRuleV13(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.p = Pipeline(connect())
        self.pid = self.p.create_project("v13")

    def test_narrow_reference_padded_to_rule(self):
        narrow = os.path.join(self.tmp, "kelly_narrow.png")
        Image.new("RGB", (488, 1280), (200, 200, 200)).save(narrow)
        with env(ref_rule_early=False):
            self.assertEqual(seedance_refs._rule_ok_picture(self.p.conn, self.pid, "KELLY", [narrow]), narrow)   # as before
        with env(ref_rule_early=True), mock.patch.object(seedance_refs, "PAD_DIR", os.path.join(self.tmp, "pad")):
            out = seedance_refs._rule_ok_picture(self.p.conn, self.pid, "KELLY", [narrow])
        w, h = Image.open(out).size
        self.assertNotEqual(out, narrow)
        self.assertTrue(0.4 <= w / h <= 2.5 and min(w, h) >= 300)
        self.assertEqual(h, 1280)                                        # padded, not squeezed
        codes = {r[0] for r in self.p.conn.execute("SELECT code FROM diag_events")}
        self.assertIn("identity_picture_padded", codes)                  # said, not silent

    def test_rule_breaking_reference_is_red_before_queueing(self):
        base_case = base.SeedanceRefTests("test_a_group_every_shot_draws_its_own_picture")
        base_case.setUp()
        self.addCleanup(base_case.doCleanups)
        base_case._ready()
        tiny = os.path.join(self.tmp, "tiny.png")
        Image.new("RGB", (120, 120)).save(tiny)
        sid = base_case.ids[0]
        with mock.patch("core.seedance_refs.identity_pictures", return_value=[("KELLY", tiny)]):
            with env(ref_rule_early=False):
                self.assertFalse([x for x in prompt_formula.red_issues(base_case.p.conn, sid, "motion") if "Ảnh tham chiếu" in x])
            with env(ref_rule_early=True):
                red = [x for x in prompt_formula.red_issues(base_case.p.conn, sid, "motion") if "Ảnh tham chiếu" in x]
        self.assertEqual(len(red), 1)
        self.assertIn("120×120", red[0])


class AfterReviewS2(unittest.TestCase):
    """Vòng sửa sau rà 13/10 (docs/handoff/RA_S1_S2_2026-10-13.md mục 6–8)."""
    setUp = base.SeedanceRefTests.setUp
    _ready = base.SeedanceRefTests._ready

    def test_note_sent_follows_the_real_mark_style(self):
        """Mục 6: lượt gửi đánh dấu tại chỗ ghi đúng kiểu dấu thật (cờ bật = corner_plus), không ghi 'eye_plus' mặc định."""
        vr = self._ready()
        frame = shots.approved_image_path(self.p.conn, self.data, self.pid, self.ids[0])
        sid = self.ids[0]
        with env(ref_mark_off_face=True), mock.patch.object(seedance_refs, "mark", side_effect=lambda p, o, s: p), \
                mock.patch.object(type(vr), "_hosted_pictures", return_value=None):
            vr._pregen_deferred = [{"pictures": [("KELLY", frame)], "clean": False, "mark_fallback": True, "scene_ids": [sid],
                                    "local": []}]
            vr._finish_kwargs({"project_id": self.pid}, {})
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])
        self.assertEqual(d.get(seedance_refs.SENT_KEY), "corner_plus")

    def test_skin_room_only_when_the_prompt_has_a_skill_object(self):
        """Mục 7: +140 ký tự chỗ câu skin chỉ khi prompt nói tới vật kỹ năng (không cắt câu kích thước mọi prompt)."""
        from core import skill_objects
        with env(skill_object_guard=True):
            plain = skill_objects.reserve(self.p.conn, self.pid, "Kelly runs to the gate.")
            wall = skill_objects.reserve(self.p.conn, self.pid, "Kelly throws the glue grenade; the glue wall stands.")
            old = skill_objects.reserve()
        self.assertEqual(wall - plain, skill_objects.SKIN_ROOM)
        self.assertEqual(old, wall)                                      # no text given: room for everything, as before
        with env(skill_object_guard=False):
            self.assertEqual(skill_objects.reserve(self.p.conn, self.pid, "the glue wall"), 0)

    def test_padded_copy_goes_to_the_running_data_folder(self):
        """Mục 8: bản đệm ghi vào thư mục data đang chạy (cạnh CSDL / PIPELINE_DATA), không theo chỗ đặt mã nguồn."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        narrow = os.path.join(tmp, "narrow.png")
        Image.new("RGB", (100, 400), (50, 50, 50)).save(narrow)
        self.enterContext(mock.patch.object(seedance_refs, "PAD_DIR", None))    # đường MẶC ĐỊNH (conftest đặt PAD_DIR = tmp cho mọi test khác)
        with mock.patch.dict(os.environ, {"PIPELINE_DATA": os.path.join(tmp, "data", "projects")}):
            out = seedance_refs.pad_to_rule(narrow, self.p.conn)                 # in-memory DB: PIPELINE_DATA's parent
        self.assertEqual(os.path.normcase(os.path.dirname(out)), os.path.normcase(os.path.join(tmp, "data", "ref_padded")))
        os.makedirs(os.path.join(tmp, "other"))
        conn = connect(os.path.join(tmp, "other", "manifest.sqlite"))
        self.addCleanup(conn.close)
        out2 = seedance_refs.pad_to_rule(narrow, conn)                          # a file DB: next to it
        self.assertEqual(os.path.normcase(os.path.dirname(out2)), os.path.normcase(os.path.join(tmp, "other", "ref_padded")))


if __name__ == "__main__":
    unittest.main()
