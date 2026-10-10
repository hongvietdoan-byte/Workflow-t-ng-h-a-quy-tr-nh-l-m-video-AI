"""K3 (A17) lớp code kiểm video TRƯỚC gen — core/video_pregen.py, nối ở VideoRunner._pregen (cờ video_pregen, mặc định tắt).
Mỗi mục (1)–(6) có ca chặn + ca qua; cờ tắt y cũ; một shot ĐỎ không chặn shot khác trong cùng vòng gửi (đường lô / autopilot đều đi
qua submit_pending). CSDL tạm, provider giả, không gọi API, không đụng data/."""
import functools
import json
import os
import tempfile
import unittest
from unittest import mock

from core import llm_io, runner, sent_package, video_pregen
from core.db import connect
from core.pipeline import Pipeline
from core.providers import MockVideoProvider
from core.runner import VideoRunner
from tests._flags import flags_on

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def spy(provider):
    orig = provider.submit
    calls = []

    @functools.wraps(orig)
    def wrapper(*a, **k):
        calls.append((a, dict(k)))
        return orig(*a, **k)
    provider.submit = wrapper
    return calls


def byd(**over):
    b = {"shot": 1, "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}],
         "hanh_dong": [{"ai": "kelly", "bat_dau": {"tu_the": "dung"}}],
         "may": {"co": "MS", "do_cao": "ngang", "goc": "ngang", "chuyen_dong": "dung_yen"}, "noi_chon": {}}
    b.update(over)
    return b


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = Pipeline(connect(os.path.join(self.tmp, "t.db")))
        self.dir = os.path.join(self.tmp, "projects")
        os.makedirs(self.dir)
        self.pid = self.p.create_project("k3", max_retry=2)
        self.idx = 0

    def tearDown(self):
        self.p.conn.close()

    def on(self):
        flags_on(self, "video_pregen")

    def shot(self, prompt="she walks forward", data=None, duration=5, picture=True):
        self.idx += 1
        scene = self.p.create_scene(self.pid, self.idx, f"S{self.idx}")
        if data is not None:
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), scene))
            self.p.conn.commit()
        img = self.p.create_job(scene)
        self.p.start(img)
        self.p.succeed(img)
        self.p.approve(img)
        if picture:
            self.write(self.image_path(img), b"picture-" + str(img).encode())
        llm_io.store_motion_prompts(self.p, self.pid, {"scenes": [{"idx": self.idx, "motion_prompt": prompt, "duration_sec": duration}]})
        llm_io.approve_motion_prompt(self.p, scene)
        return scene, img

    def image_path(self, img):
        return os.path.join(self.dir, str(self.pid), "images", f"job_{img}.png")

    def write(self, path, body):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)
        return path

    def send(self):
        prov = MockVideoProvider()
        calls = spy(prov)
        VideoRunner(self.p, prov, self.dir, max_concurrent=5).submit_pending(self.pid)
        return calls

    def state(self, job):
        return self.p.job(job)["state"]

    def holds(self):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='video_pregen_hold'")]

    def yellows(self):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE code='video_pregen'")]

    def clip_done(self, job):
        """The send produced a clip (paid + result): the next gen of the shot is a REDO for N10."""
        self.p.conn.execute("UPDATE jobs SET state='succeeded', result_path='clip.mp4' WHERE id=?", (job,))
        self.p.conn.commit()

    def plan(self, scene, img, **over):
        """A plan like VideoRunner builds it (package from the real builder), for direct check() cases."""
        path = self.image_path(img)
        args = (path, "she walks forward", None, over.pop("duration", 5), over.pop("model", "kling"))
        kwargs = over.pop("kwargs", {})
        pkg, _ = sent_package.safe_build(MockVideoProvider().submit, args, kwargs, kind="video", provider=MockVideoProvider(),
                                         external_id=None)
        job = {"id": over.pop("job_id", 999), "project_id": self.pid}
        plan = video_pregen.plan_of(job, args, kwargs, pkg, self.dir, over.pop("group_ids", []))
        plan.update(over)
        return plan

    def reds(self, issues, ma=None):
        return [i for i in issues if i["muc"] == "do" and (ma is None or i["ma"] == ma)]


class FlagOff(Base):
    def test_flag_off_sends_like_before(self):
        """Cờ tắt: y cũ — kể cả khi lớp kiểm sẽ chặn (ảnh khung đầu không có tệp)."""
        scene, _ = self.shot(picture=False)
        job = self.p.create_job(scene, "video_gen")
        self.assertFalse(video_pregen.enabled())
        self.assertEqual(len(self.send()), 1)
        self.assertEqual(self.state(job), "running")
        self.assertEqual(self.holds(), [])


class StartFrame(Base):                       # (1)
    def test_pass_current_approved_picture(self):
        self.on()
        scene, _ = self.shot(data={"byd": byd()})
        job = self.p.create_job(scene, "video_gen")
        self.assertEqual(len(self.send()), 1)
        self.assertEqual(self.state(job), "running")
        self.assertEqual(self.holds(), [])

    def test_block_missing_file_is_held_waiting_for_person(self):
        self.on()
        scene, _ = self.shot(picture=False)
        job = self.p.create_job(scene, "video_gen")
        self.assertEqual(self.send(), [])
        self.assertEqual(self.state(job), "queued")                  # chờ người, không đốt lượt
        self.assertIn("không đọc được tệp ảnh khung đầu", runner.wait_reason(job) or "")
        self.assertTrue(any("khung đầu" in m for m in self.holds()))

    def test_block_picture_replaced_after_last_send(self):
        self.on()
        scene, img = self.shot(data={"byd": byd()})
        first = self.p.create_job(scene, "video_gen")
        self.assertEqual(len(self.send()), 1)
        self.clip_done(first)
        self.write(self.image_path(img), b"another picture, same name")      # thay tệp, không duyệt lại
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she runs forward' WHERE scene_id=?", (scene,))
        self.p.conn.commit()
        second = self.p.create_job(scene, "video_gen")
        self.assertEqual(self.send(), [])
        self.assertEqual(self.state(second), "queued")
        self.assertTrue(any("đã bị thay" in m for m in self.holds()))

    def test_block_not_the_current_approved_picture(self):
        scene, old = self.shot()
        new = self.p.create_job(scene)
        self.p.start(new)
        self.p.succeed(new)
        self.p.approve(new)
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, old))
        self.assertTrue(self.reds(got, "khung_dau"), got)
        self.assertIn(f"job {new}", self.reds(got, "khung_dau")[0]["ly_do"])

    def test_block_no_approved_picture(self):
        scene, img = self.shot()
        self.p.conn.execute("UPDATE jobs SET state='rejected' WHERE id=?", (img,))     # bỏ duyệt
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img))
        self.assertIn("ĐÃ DUYỆT", self.reds(got, "khung_dau")[0]["ly_do"])


class EndFrame(Base):                         # (2)
    def end_frame(self, scene, img, state="ready"):
        path = self.write(os.path.join(self.tmp, f"end_{scene}.png"), b"end")
        self.p.conn.execute("INSERT INTO end_frames (project_id, scene_id, start_job_id, state, path, created_at, updated_at) "
                            "VALUES (?,?,?,?,?,datetime('now'),datetime('now'))", (self.pid, scene, img, state, path))
        self.p.conn.commit()
        return path

    def test_pass_ready_end_frame_matching_byd(self):
        b = byd(hanh_dong=[{"ai": "kelly", "bat_dau": {"tu_the": "dung"}, "dinh": {"tu_the": "quy"}, "ket_thuc": {"tu_the": "nga_ngua"}}])
        scene, img = self.shot(data={"byd": b})
        path = self.end_frame(scene, img)
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"last_frame": path}))
        self.assertEqual([i for i in got if i["ma"] == "khung_cuoi"], [])

    def test_block_end_frame_not_approved(self):
        scene, img = self.shot(data={"byd": byd()})
        path = self.end_frame(scene, img, state="rejected")
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"last_frame": path}))
        self.assertTrue(self.reds(got, "khung_cuoi"), got)

    def test_block_end_frame_drawn_from_old_start(self):
        scene, img = self.shot(data={"byd": byd()})
        path = self.end_frame(scene, img - 1000)
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"last_frame": path}))
        self.assertTrue(self.reds(got, "khung_cuoi"), got)

    def test_block_byd_says_no_change(self):
        b = byd(hanh_dong=[{"ai": "kelly", "bat_dau": {"tu_the": "dung"}, "dinh": {"tu_the": "dung"}, "ket_thuc": {"tu_the": "dung"}}])
        scene, img = self.shot(data={"byd": b})
        path = self.end_frame(scene, img)
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"last_frame": path}))
        self.assertTrue(self.reds(got, "khung_cuoi"), got)

    def test_no_byd_is_yellow_not_red(self):
        scene, img = self.shot()
        path = self.end_frame(scene, img)
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"last_frame": path}))
        self.assertEqual(self.reds(got), [])
        self.assertTrue(any(i["ma"] == "byd" and i["muc"] == "vang" and "chưa có BYĐ" in i["ly_do"] for i in got))


class Duration(Base):                         # (3)
    def test_pass_fits_model(self):
        scene, img = self.shot(data={"byd": byd()})
        self.assertEqual(self.reds(video_pregen.check(self.p.conn, scene, self.plan(scene, img, duration=5)), "thoi_luong"), [])

    def test_block_longer_than_model(self):
        scene, img = self.shot(data={"byd": byd()})
        got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, duration=20))
        self.assertIn("tối đa 15", self.reds(got, "thoi_luong")[0]["ly_do"])

    def test_block_voice_longer_than_clip(self):
        scene, img = self.shot(data={"byd": byd(), "dialogue": [{"speaker": "Kelly", "text": "đi thôi"}]})
        audio = self.write(os.path.join(self.tmp, "line.wav"), b"wav")
        plan = self.plan(scene, img, duration=5, kwargs={"reference_audio": [audio]})
        with mock.patch("core.ffmpeg_studio.probe_duration", return_value=9.0):
            got = video_pregen.check(self.p.conn, scene, plan)
        self.assertTrue(self.reds(got, "thoi_luong"), got)
        with mock.patch("core.ffmpeg_studio.probe_duration", return_value=4.8):
            self.assertEqual(self.reds(video_pregen.check(self.p.conn, scene, plan), "thoi_luong"), [])


class References(Base):                       # (4)
    def video(self, info):
        path = self.write(os.path.join(self.tmp, "ref.mp4"), b"mp4")
        return path, mock.patch("core.adapters.clipai._probe_video", return_value=info)

    def test_pass_kling_reference_video_by_rules(self):
        scene, img = self.shot(data={"byd": byd()})
        path, probe = self.video({"width": 1280, "height": 720, "sar": "1:1", "fps": 30.0, "duration": 4.0})
        with probe:
            got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"reference_video": {"path": path}}))
        self.assertEqual(self.reds(got, "tham_chieu"), [])

    def test_block_kling_reference_video_too_short_narrow_or_sar(self):
        scene, img = self.shot(data={"byd": byd()})
        for info, word in (({"width": 1280, "height": 720, "sar": "1:1", "duration": 2.2}, "2.2 s"),
                           ({"width": 600, "height": 600, "sar": "1:1", "duration": 4.0}, "600 px"),
                           ({"width": 1280, "height": 720, "sar": "4:3", "duration": 4.0}, "SAR")):
            path, probe = self.video(info)
            with probe:
                got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"reference_video": {"path": path}}))
            self.assertTrue(any(word in i["ly_do"] for i in self.reds(got, "tham_chieu")), (word, got))

    def test_block_reference_video_not_measurable(self):
        scene, img = self.shot(data={"byd": byd()})
        path, probe = self.video({})
        with probe:
            got = video_pregen.check(self.p.conn, scene, self.plan(scene, img, kwargs={"reference_video": {"path": path}}))
        self.assertTrue(any("không đo được" in i["ly_do"] for i in self.reds(got, "tham_chieu")))

    def pictures(self, n, same=False):
        return [self.write(os.path.join(self.tmp, f"r{k}.png"), b"same" if same else f"pic{k}".encode()) for k in range(n)]

    def test_seedance_picture_cap(self):
        scene, img = self.shot(data={"byd": byd()})
        ok = video_pregen.check(self.p.conn, scene, self.plan(scene, img, model="seedance", kwargs={"reference_only": self.pictures(9)}))
        self.assertEqual(self.reds(ok, "tham_chieu"), [])
        bad = video_pregen.check(self.p.conn, scene, self.plan(scene, img, model="seedance", kwargs={"reference_only": self.pictures(10)}))
        self.assertTrue(any("tối đa 9" in i["ly_do"] for i in self.reds(bad, "tham_chieu")), bad)

    def test_seedance_one_asset_one_role(self):
        scene, img = self.shot(data={"byd": byd()})
        a, b = self.pictures(2)
        ok = video_pregen.check(self.p.conn, scene, self.plan(scene, img, model="seedance", kwargs={"last_frame": a}))
        self.assertEqual(self.reds(ok, "tham_chieu"), [])
        same = self.write(os.path.join(self.tmp, "copy.png"), open(self.image_path(img), "rb").read())   # khung đầu gửi lại làm khung cuối
        bad = video_pregen.check(self.p.conn, scene, self.plan(scene, img, model="seedance", kwargs={"last_frame": same}))
        self.assertTrue(any("mỗi tài sản một vai" in i["ly_do"] for i in self.reds(bad, "tham_chieu")), bad)


class Motion(Base):                           # (5)
    def test_pass_full_beats_and_enum_move(self):
        b = byd(hanh_dong=[{"ai": "kelly", "bat_dau": {"tu_the": "dung"}, "dinh": {"tu_the": "quy"}, "ket_thuc": {"tu_the": "nga_ngua"}}],
                may={"co": "MS", "chuyen_dong": {"kieu": "tien", "m": 1.0}})
        scene, img = self.shot(data={"byd": b})
        self.assertEqual(self.reds(video_pregen.check(self.p.conn, scene, self.plan(scene, img)), "chuyen_dong"), [])

    def test_block_move_outside_enum(self):
        scene, img = self.shot(data={"byd": byd(may={"co": "MS", "chuyen_dong": "lia_ngang"})})
        self.assertTrue(self.reds(video_pregen.check(self.p.conn, scene, self.plan(scene, img)), "chuyen_dong"))

    def test_block_change_without_peak(self):
        b = byd(hanh_dong=[{"ai": "kelly", "bat_dau": {"tu_the": "dung"}, "ket_thuc": {"tu_the": "nga_ngua"}}])
        scene, img = self.shot(data={"byd": b})
        got = self.reds(video_pregen.check(self.p.conn, scene, self.plan(scene, img)), "chuyen_dong")
        self.assertTrue(any("đỉnh" in i["ly_do"] for i in got), got)

    def test_regression_p24_golden_byd_not_flagged(self):
        """Ca hồi quy #24 (tests/golden): BYĐ shot 4 / shot 8 một tư thế, máy đứng yên — lớp (5) không được báo nhầm."""
        from tests.golden import load_cases
        cases = [c for c in load_cases() if c["id"].startswith("p24_") and c.get("byd")]
        self.assertGreaterEqual(len(cases), 2)
        for c in cases:
            scene, img = self.shot(data={"byd": c["byd"]})
            got = video_pregen.check(self.p.conn, scene, self.plan(scene, img))
            self.assertEqual(self.reds(got, "chuyen_dong"), [], c["id"])


class Fingerprint(Base):                      # (6)
    def test_block_same_package_after_a_clip(self):
        self.on()
        scene, _ = self.shot(data={"byd": byd()})
        first = self.p.create_job(scene, "video_gen")
        self.assertEqual(len(self.send()), 1)
        self.clip_done(first)
        again = self.p.create_job(scene, "video_gen")
        self.assertEqual(self.send(), [])
        self.assertEqual(self.state(again), "queued")
        self.assertTrue(any("gen lại phải đổi đầu vào" in m for m in self.holds()), self.holds())

    def test_pass_changed_input(self):
        self.on()
        scene, _ = self.shot(data={"byd": byd()})
        first = self.p.create_job(scene, "video_gen")
        self.send()
        self.clip_done(first)
        self.p.conn.execute("UPDATE motion_prompts SET motion_prompt='she walks forward slowly, then stops' WHERE scene_id=?", (scene,))
        self.p.conn.commit()
        again = self.p.create_job(scene, "video_gen")
        self.assertEqual(len(self.send()), 1)
        self.assertEqual(self.state(again), "running")

    def test_provider_failure_without_clip_resends_yellow(self):
        self.on()
        scene, _ = self.shot(data={"byd": byd()})
        first = self.p.create_job(scene, "video_gen")
        self.send()
        self.p.fail(first, "server_error: boom")
        again = self.p.create_job(scene, "video_gen")
        self.assertEqual(len(self.send()), 1)
        self.assertEqual(self.state(again), "running")
        self.assertTrue(any("hỏng ở nhà cung cấp" in m for m in self.yellows()))

    def test_fingerprint_ignores_time_and_task_id(self):
        a = {"v": 1, "call": "submit", "prompt": "x", "refs": [{"param": "image_path", "role": "start_frame", "sha256": "s", "path": "a"}],
             "model": "kling", "params": {"duration_sec": 5}, "external_id": "t1", "at": "2026-10-10T00:00:00+00:00"}
        b = dict(a, external_id="t2", at="2026-10-11T00:00:00+00:00")
        self.assertEqual(video_pregen.fingerprint(a), video_pregen.fingerprint(json.dumps(b)))
        self.assertNotEqual(video_pregen.fingerprint(a), video_pregen.fingerprint(dict(a, prompt="y")))
        self.assertIsNone(video_pregen.fingerprint("not json"))


class Batch(Base):
    def test_one_red_shot_does_not_stop_the_others(self):
        """Lô / autopilot (cùng gọi VideoRunner.submit_pending): shot ĐỎ giữ lại, các shot khác vẫn gửi trong cùng vòng."""
        self.on()
        s1, _ = self.shot(data={"byd": byd()})
        s2, _ = self.shot(data={"byd": byd()}, picture=False)          # ĐỎ (1)
        s3, _ = self.shot(data={"byd": byd()})
        jobs = [self.p.create_job(s, "video_gen") for s in (s1, s2, s3)]
        self.assertEqual(len(self.send()), 2)
        self.assertEqual([self.state(j) for j in jobs], ["running", "queued", "running"])

    def test_check_crash_holds_with_reason(self):
        self.on()
        scene, _ = self.shot(data={"byd": byd()})
        job = self.p.create_job(scene, "video_gen")
        with mock.patch("core.video_pregen.check", side_effect=RuntimeError("boom")):
            self.assertEqual(self.send(), [])
        self.assertEqual(self.state(job), "queued")
        self.assertTrue(any("lớp kiểm trước gen lỗi" in m for m in self.holds()))


class Registry(unittest.TestCase):
    def test_flag_default_off_and_declared(self):
        from core import features
        self.assertIn("video_pregen", features.FEATURES)
        self.assertFalse(features.FEATURES["video_pregen"]["verified"])
        with open(os.path.join(ROOT, "devsys", "decisions.json"), encoding="utf-8") as f:
            items = {d["id"]: d for d in json.load(f)["items"]}
        self.assertEqual(items["d100"]["where"], "core/video_pregen.py:check")


if __name__ == "__main__":
    unittest.main()
