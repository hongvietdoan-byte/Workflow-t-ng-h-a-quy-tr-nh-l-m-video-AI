"""G0 (kế hoạch đặt máy 3D 09/10): Director lập sơ đồ cảnh + bộ góc máy (cờ director_camera_plan, TẮT mặc định), code tính số từ
setup (cùng setup + cùng cỡ = cùng camera = cùng cache, render một lần), Director duyệt render nền (model khai quan sát enum, CODE kết
luận, ≤ 2 vòng rồi báo người), QC bố cục bằng code sau khi vẽ ảnh. Không gọi API thật: Claude giả (client .complete), Blender giả."""
import json
import os
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from core import camera_plan, diag, features, location_pack, plate_camera, plate_layout_qc
from core.llm_io import SchemaError
from core.llm_runner import LlmReply
from tests.test_location_pack import H, W, PackTests

ON = {"FEATURE_DIRECTOR_CAMERA_PLAN": "1", "FEATURE_SETTINGS_FILE": os.path.join(os.path.dirname(__file__), "_no_feature_settings.json")}
OFF = {"FEATURE_DIRECTOR_CAMERA_PLAN": "", "FEATURE_SETTINGS_FILE": ON["FEATURE_SETTINGS_FILE"]}

SHOTS = (  # (size, angle, action) — #24 kiểu rút gọn: Kelly ở quảng trường, giếng phía tây nam
    ("WS", "eye", "Kelly walks into the plaza towards the old well"),
    ("MS", "eye", "Kelly stops beside the well, hesitant"),
    ("MS", "eye", "Kelly leans over the rim and peers down into the well"),
    ("MCU", "eye", "Kelly hears a sound, eyes wide"),
)


def answer(setups=None, shots=None, **extra):
    obj = {"props": [{"name": "giếng đá", "bearing_deg": 225, "distance_m": 2.5, "why": "kịch bản: giếng giữa quảng trường"}],
           "beats": [{"shots": [1, 2], "who": "KELLY", "bearing_deg": 225, "distance_m": 1.0, "facing_deg": 225, "what": "đi tới giếng"}],
           "axis": {"from": "KELLY", "to": "tháp", "bearing_deg": 180, "camera_side": "left", "why": "Kelly đứng giữa giếng và tháp"},
           "setups": setups or [
               {"id": "A", "intent": "toàn cảnh về tháp", "why": "giới thiệu nơi", "azimuth_deg": 180, "angle": "eye", "tilt": "level",
                "landmark_in_frame": "yes"},
               {"id": "B", "intent": "ngược về dãy nhà", "why": "phản ứng của Kelly", "azimuth_deg": 0, "angle": "eye", "tilt": "level",
                "landmark_in_frame": "no"},
               {"id": "C", "intent": "qua vai cúi nhìn giếng", "why": "thấy điều Kelly thấy", "azimuth_deg": 200, "angle": "ots",
                "tilt": "down", "landmark_in_frame": "no"}],
           "shots": shots or [{"idx": 1, "setup": "A", "size": "WS", "angle": "eye", "why": "mở cảnh"},
                              {"idx": 2, "setup": "A", "size": "WS", "angle": "eye", "why": "cùng nền shot mở"},
                              {"idx": 3, "setup": "C", "size": "MS", "angle": "ots", "why": "cúi nhìn giếng"},
                              {"idx": 4, "setup": "B", "size": "MCU", "angle": "eye", "why": "mặt Kelly"}]}
    obj.update(extra)
    return obj


class FakeClaude:
    """Claude giả: trả lần lượt các câu trả lời JSON; ghi lại prompt + ảnh đã gửi."""
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts, self.images = [], []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        self.images.append(list(images))
        obj = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return LlmReply("```json\n" + json.dumps(obj, ensure_ascii=False) + "\n```", 1000, 200)


class G0Base(unittest.TestCase):
    """Fixture of test_location_pack.PackTests (place + fake model + fake Blender) without re-running its tests."""
    tearDown = PackTests.tearDown
    fake_render = PackTests.fake_render

    def setUp(self):
        PackTests.setUp(self)
        # tháp (anchor) ở phía nam chỗ đứng plaza_front (phương vị 180°)
        location_pack.set_model3d(self.p.conn, self.place, self.model,
                                  {"plaza_front": {"at": [12.68, -19.0, 25.93], "facing": 0, "label": "quảng trường trước tháp"},
                                   "houses": {"at": [12.68, -5.0, 25.93], "facing": 0, "label": "dãy nhà mái đỏ"}},
                                  "plaza_front", anchor=[12.68, -31.13, 33.5])
        self.data = os.path.join(self.tmp, "projects")

    def scene(self, shots=SHOTS, extra=None, aspect="9:16"):
        pid = self.p.create_project(f"g0-{len(self.calls)}-{id(shots)}-{os.urandom(3).hex()}", aspect=aspect)
        for i, (size, angle, action) in enumerate(shots, 1):
            sid = self.p.create_scene(pid, i, f"s{i}")
            d = {"size": size, "angle": angle, "characters": ["KELLY"], "location_asset": self.place, "time": "day",
                 "plate_spot": "plaza_front", "story_scene": 1, "action": action, "image_prompt": f"Kelly shot {i}"}
            d.update((extra or {}).get(i, {}))
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        self.p.conn.commit()
        return pid

    def shot(self, pid, idx):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()["data"])

    def diags(self, pid, code):
        return [r["message"] for r in self.p.conn.execute("SELECT message FROM diag_events WHERE project_id=? AND code=?", (pid, code))]


# ---- cờ TẮT: luồng cũ y nguyên ------------------------------------------------------------------------------------------------
class FlagOffTests(G0Base):
    def test_flag_is_off_by_default_and_listed(self):
        self.assertIn("director_camera_plan", features.FEATURES)
        self.assertFalse(features.FEATURES["director_camera_plan"]["verified"])
        with mock.patch.dict(os.environ, OFF):
            self.assertFalse(camera_plan.enabled())

    def test_off_the_plan_and_cache_keys_are_the_same_as_before(self):
        with mock.patch.dict(os.environ, OFF):
            pid = self.scene()
            before = location_pack.plan(self.p.conn, pid)
            # dữ liệu sơ đồ còn sót lại trên shot (bật rồi tắt cờ) không đổi gì khi cờ tắt
            for i in (1, 2):
                self.p.conn.execute("UPDATE scenes SET data=json_set(data, '$.plate_setup', 'A') WHERE project_id=? AND idx=?", (pid, i))
            self.p.conn.commit()
            after = location_pack.plan(self.p.conn, pid)
        strip = lambda items: [{k: v for k, v in it.items() if k != "entry"} for it in items]   # noqa: E731
        self.assertEqual(strip(before), strip(after))

    def test_off_nothing_is_asked_and_nothing_written(self):
        client = FakeClaude(answer())
        with mock.patch.dict(os.environ, OFF):
            pid = self.scene()
            res = camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
            rev = camera_plan.after_plates(self.p.conn, pid, self.data, self.tmp, client=client, render=self.fake_render, blender="x")
        self.assertIsNone(res)
        self.assertIsNone(rev)
        self.assertEqual(client.prompts, [])
        self.assertFalse(os.path.exists(camera_plan.plan_path(self.data, pid)))
        self.assertNotIn("plate_setup", self.shot(pid, 1))

    def test_off_the_layout_qc_does_nothing(self):
        with mock.patch.dict(os.environ, OFF):
            self.assertIsNone(plate_layout_qc.check_job(self.p.conn, self.data, 1, 1, 1, "x.png"))


# ---- 1–2: sơ đồ cảnh + bộ setup -----------------------------------------------------------------------------------------------
class PlanTests(G0Base):
    def test_facts_give_landmark_bearing_and_say_what_is_missing(self):
        entry = location_pack.model3d(self.p.conn, self.place)
        facts = camera_plan.place_facts(entry, location_pack.spot_for(entry, {"plate_spot": "plaza_front"}))
        self.assertEqual(facts["landmark_bearing_deg"], 180.0)
        self.assertEqual([s["name"] for s in facts["spots"]], ["houses"])
        self.assertEqual(facts["spots"][0]["bearing_deg"], 0.0)
        no_anchor = dict(entry, anchor=None)
        facts = camera_plan.place_facts(no_anchor, location_pack.spot_for(no_anchor, {"plate_spot": "plaza_front"}))
        self.assertNotIn("landmark_bearing_deg", facts)
        self.assertTrue(any("anchor" in m for m in facts["missing"]))

    def test_prompt_has_rules_with_reasons_shots_facts_and_says_no_topview(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            group = camera_plan.groups(self.p.conn, pid)[0]
            text, images, notes = camera_plan.build_prompt(self.p.conn, pid, group, self.data)
        self.assertTrue(text.startswith(camera_plan.PLAN_HEAD))
        for words in ("trục 180", "cúi", "tường chắn", "shot mở", "vì", "180°"):
            self.assertIn(words, text)
        self.assertIn("peers down into the well", text)
        self.assertEqual(images, [])
        self.assertTrue(any("topview" in n or "sơ đồ nhìn từ trên" in n for n in notes))
        self.assertIn("không có ảnh sơ đồ nhìn từ trên", text)

    def test_topview_is_sent_when_it_exists(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            top = os.path.join(self.data, str(pid), "plates", "top_view.png")
            os.makedirs(os.path.dirname(top))
            Image.new("RGB", (20, 20)).save(top)
            group = camera_plan.groups(self.p.conn, pid)[0]
            _, images, _ = camera_plan.build_prompt(self.p.conn, pid, group, self.data)
        self.assertEqual(images[0][1], top)

    def test_validate_refuses_unusable_answers(self):
        idxs = [1, 2, 3, 4]
        camera_plan.validate(answer(), idxs)
        bad = answer(shots=[{"idx": 1, "setup": "Z", "size": "WS", "angle": "eye", "why": "x"}])
        with self.assertRaises(SchemaError):
            camera_plan.validate(bad, idxs)                       # setup lạ + thiếu shot 2–4
        bad = answer()
        bad["setups"][0]["azimuth_deg"] = "về tháp"
        with self.assertRaises(SchemaError):
            camera_plan.validate(bad, idxs)
        bad = answer()
        bad["setups"][0]["angle"] = "dutch"
        with self.assertRaises(SchemaError):
            camera_plan.validate(bad, idxs)

    def test_code_checks_axis_family_and_look_down(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            group = camera_plan.groups(self.p.conn, pid)[0]
        # setup D: máy bên kia trục, không lý do; shot 3 nhìn xuống nhưng gán setup ngang tầm mắt
        plan = answer(setups=answer()["setups"] + [{"id": "D", "intent": "ngang", "why": "đổi nhịp", "azimuth_deg": 135, "angle": "eye",
                                                     "tilt": "level", "landmark_in_frame": "any"}],
                      shots=[{"idx": 1, "setup": "A", "size": "WS", "angle": "eye", "why": "mở"},
                             {"idx": 2, "setup": "D", "size": "MS", "angle": "eye", "why": "x"},
                             {"idx": 3, "setup": "A", "size": "MS", "angle": "eye", "why": "x"},
                             {"idx": 4, "setup": "B", "size": "MCU", "angle": "eye", "why": "x"}])
        fixed, notes = camera_plan.check(plan, group)
        text = " | ".join(notes)
        self.assertIn("vượt trục", text)                                         # D bên kia trục, không ghi lý do
        self.assertIn("nền chưa giới thiệu", text)                              # D lệch cả shot mở lẫn hướng ngược
        shot3 = next(s for s in fixed["shots"] if s["idx"] == 3)
        self.assertNotEqual(shot3["setup"], "A")                                 # tách setup cúi riêng, A giữ nguyên cho shot 1
        derived = next(s for s in fixed["setups"] if s["id"] == shot3["setup"])
        self.assertEqual((derived["angle"], derived["tilt"], derived["azimuth_deg"]), ("high", "down", 180.0))
        self.assertIn("nhìn xuống", text)

    def test_same_setup_different_angle_takes_the_setup_angle(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            group = camera_plan.groups(self.p.conn, pid)[0]
        plan = answer()
        plan["shots"][1]["angle"] = "low"
        fixed, notes = camera_plan.check(plan, group)
        self.assertEqual(next(s for s in fixed["shots"] if s["idx"] == 2)["angle"], "eye")
        self.assertTrue(any("angle" in n for n in notes))

    def test_run_estimates_asks_once_per_scene_applies_and_keeps_the_plan(self):
        client = FakeClaude(answer())
        with mock.patch.dict(os.environ, ON):
            pid = self.scene(extra={4: {"size": "CU", "_user_locked": ["size"]}})
            res = camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
            again = camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 1)                                 # một lượt / cảnh; lần sau dùng sơ đồ đã lưu
        self.assertEqual(res["planned"], ["1"])
        self.assertEqual(again["planned"], [])
        self.assertTrue(os.path.exists(camera_plan.plan_path(self.data, pid)))
        s1, s3, s4 = self.shot(pid, 1), self.shot(pid, 3), self.shot(pid, 4)
        self.assertEqual(s1["plate_setup"], "A")
        self.assertEqual(s1["plate_view"]["background"], 180.0)
        self.assertIn("setup A", s1["plate_view"]["why"])
        self.assertEqual((s3["plate_setup"], s3["angle"]), ("C", "ots"))
        self.assertEqual(s4["size"], "CU")                                       # cỡ do người khóa: giữ nguyên
        self.assertTrue(any("ước tính" in m for m in self.diags(pid, "director_camera_plan")))
        self.assertTrue(any("shot 2: sơ đồ đổi cỡ cảnh MS→WS" in m for m in self.diags(pid, "director_camera_plan")))
        self.assertTrue(any("shot 4: giữ size" in m for m in self.diags(pid, "director_camera_plan")))

    def test_a_failing_claude_is_not_paid_again_at_every_autopilot_tick(self):
        class Broken:
            calls = 0

            def complete(self, prompt, images=()):
                Broken.calls += 1
                return LlmReply("không phải JSON", 10, 5)
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            for _ in range(4):
                camera_plan.before_plates(self.p.conn, pid, self.data, client=Broken())
        self.assertEqual(Broken.calls, 2 * camera_plan.MAX_TRIES)               # ask_json hỏi lại 1 lần / lượt; tối đa 2 lượt
        self.assertTrue(any("hết lượt tự thử" in m for m in self.diags(pid, "director_camera_plan")))
        self.assertNotIn("plate_setup", self.shot(pid, 1))

    def test_the_mock_model_gives_a_usable_plan(self):
        from core.llm_runner import MockLlm
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            res = camera_plan.before_plates(self.p.conn, pid, self.data, client=MockLlm())
        self.assertEqual(res["planned"], ["1"])
        self.assertEqual(self.shot(pid, 2)["plate_view"]["background"], 180.0)

    def test_autopilot_hook_does_nothing_when_off(self):
        from core import autopilot
        with mock.patch.dict(os.environ, OFF), mock.patch.object(camera_plan, "before_plates") as bp, \
                mock.patch.object(camera_plan, "after_plates") as ap:
            autopilot._camera_plan(self.p, 1, mock.Mock(data_dir=self.data), "before")
            autopilot._camera_plan(self.p, 1, mock.Mock(data_dir=self.data), "after", (W, H))
        bp.assert_not_called()
        ap.assert_not_called()

    def test_no_claude_is_said_and_the_old_flow_goes_on(self):
        with mock.patch.dict(os.environ, dict(ON, LLM_PROVIDER="", ANTHROPIC_API_KEY="")):
            pid = self.scene()
            res = camera_plan.before_plates(self.p.conn, pid, self.data)
        self.assertEqual(res["planned"], [])
        self.assertTrue(any("Claude" in m for m in self.diags(pid, "director_camera_plan")))
        self.assertNotIn("plate_setup", self.shot(pid, 1))


# ---- 3: cùng setup + cùng cỡ = cùng camera = render một lần ------------------------------------------------------------------
class SameCameraTests(G0Base):
    def test_shots_of_one_setup_and_size_share_camera_key_and_one_render(self):
        client = FakeClaude(answer())
        with mock.patch.dict(os.environ, ON):
            pid = self.scene(extra={2: {"characters": ["MAXIM"]}})           # nhân vật khác chiều cao vẫn cùng máy của setup
            camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
            items = {it["idx"]: it for it in location_pack.plan(self.p.conn, pid, (W, H))}
            self.assertEqual(items[1]["key"], items[2]["key"])
            self.assertEqual(items[1]["camera"]["location"], items[2]["camera"]["location"])
            self.assertNotEqual(items[1]["key"], items[4]["key"])
            location_pack.ensure_plates(self.p.conn, pid, self.data, self.tmp, (W, H), blender="x", render=self.fake_render)
        names = [c["name"] for call in self.calls for c in call["cameras"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names.count("k" + items[1]["key"]), 1)                  # shot 1 và 2: một lần render
        # máy của setup A nhìn về phương vị 180° (về tháp)
        cam = items[1]["camera"]
        self.assertLess(cam["look_at"][1] - cam["location"][1], 0)

    def test_setup_bearing_turns_into_the_plate_view_camera(self):
        data = {"size": "MS", "angle": "eye", "plate_view": {"background": 0.0, "why": "setup B"}}
        entry = {"anchor": [0, -10, 0], "spots": {"p": {"at": [0, 0, 0], "facing": 0}}, "default_spot": "p"}
        from core import plate_choice
        v = plate_choice.view_of(entry, location_pack.spot_for(entry, {}), data)
        cam = plate_camera.camera_for(data, [0, 0, 0], v["facing_deg"])["camera"]
        self.assertGreater(cam["look_at"][1] - cam["location"][1], 0)           # nhìn về +y = phương vị 0°


# ---- 4: Director duyệt render nền — model khai quan sát, CODE kết luận --------------------------------------------------------
class JudgeTests(unittest.TestCase):
    SETUP = {"id": "C", "azimuth_deg": 200.0, "angle": "ots", "tilt": "down", "landmark_in_frame": "no"}

    def test_code_decides_not_the_model(self):
        ok = camera_plan.judge(["camera_tilted_down", "landmark_not_visible", "ground_dominant"], self.SETUP, False, 180.0, 180.0)
        self.assertTrue(ok["ok"])
        bad = camera_plan.judge(["camera_level", "landmark_visible"], self.SETUP, False, 180.0, 180.0)
        self.assertFalse(bad["ok"])
        self.assertTrue(any("cúi" in r for r in bad["reasons"]))
        self.assertTrue(any("tháp" in r or "mốc" in r for r in bad["reasons"]))
        self.assertEqual(bad["fix"]["angle"], "high")

    def test_low_angle_against_a_near_wall_is_raised(self):
        low = dict(self.SETUP, angle="low", tilt="up", landmark_in_frame="any")
        res = camera_plan.judge(["wall_near_blocking"], low, False, 180.0, 180.0)
        self.assertFalse(res["ok"])
        self.assertEqual(res["fix"]["angle"], "eye")

    def test_background_unlike_the_opening_and_contradictions(self):
        a = {"id": "D", "azimuth_deg": 190.0, "angle": "eye", "tilt": "level", "landmark_in_frame": "any"}
        res = camera_plan.judge(["background_differs_from_opening"], a, False, 180.0, 180.0)
        self.assertFalse(res["ok"])
        self.assertEqual(res["fix"]["azimuth_deg"], 180.0)
        res = camera_plan.judge(["landmark_visible", "landmark_not_visible"], a, False, 180.0, 180.0)
        self.assertFalse(res["ok"])
        self.assertIsNone(res["fix"])                                             # tự mâu thuẫn: không đoán, báo người
        self.assertIsNone(camera_plan.judge(["mystery"], a, False, 180.0, 180.0)["fix"])


class ReviewTests(G0Base):
    def review(self, *answers):
        plan_client = FakeClaude(answer())
        look = FakeClaude(*answers)
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=plan_client)
            location_pack.ensure_plates(self.p.conn, pid, self.data, self.tmp, (W, H), blender="x", render=self.fake_render)
            res = camera_plan.after_plates(self.p.conn, pid, self.data, self.tmp, client=look, render=self.fake_render, blender="x",
                                           resolution=(W, H))
        return pid, look, res

    GOOD = {"A": ["landmark_visible", "camera_level", "background_same_as_opening"],
            "B": ["landmark_not_visible", "camera_level"], "C": ["camera_tilted_down", "landmark_not_visible", "ground_dominant"]}

    @staticmethod
    def obs(setup, items, ok=True):
        return {"setup": setup, "observations": items, "verdict": "khớp" if ok else "không khớp", "note": "giả lập"}

    def test_all_fine_one_look_per_setup_with_its_render_and_intent(self):
        pid, look, res = self.review(*[self.obs(k, v) for k, v in self.GOOD.items()])
        self.assertEqual(len(look.prompts), 3)
        self.assertTrue(all(p.startswith(camera_plan.REVIEW_HEAD) for p in look.prompts))
        self.assertIn("qua vai cúi nhìn giếng", look.prompts[2])
        self.assertTrue(all(os.path.exists(path) for imgs in look.images for _, path in imgs))
        self.assertEqual(res["needs_person"], [])
        plans = camera_plan.load_plans(self.data, pid)
        self.assertTrue(plans["1"]["setups"][0]["review"]["ok"])

    def test_model_says_ok_but_code_finds_a_fault_then_fixes_and_rerenders(self):
        wrong_c = self.obs("C", ["camera_level", "landmark_visible"], ok=True)   # model nói "khớp" — code không tin
        pid, look, res = self.review(self.obs("A", self.GOOD["A"]), self.obs("B", self.GOOD["B"]), wrong_c,
                                     self.obs("C", self.GOOD["C"]))
        self.assertEqual(len(look.prompts), 4)                                    # C xem lại sau khi sửa
        c = next(s for s in camera_plan.load_plans(self.data, pid)["1"]["setups"] if s["id"] == "C")
        self.assertEqual(c["angle"], "high")
        self.assertEqual(c["review"]["rounds"], 1)
        self.assertTrue(c["review"]["ok"])
        self.assertEqual(self.shot(pid, 3)["angle"], "high")

    def test_still_wrong_after_two_rounds_is_said_to_the_person(self):
        wall = self.obs("B", ["wall_near_blocking", "landmark_not_visible"])
        pid, look, res = self.review(self.obs("A", self.GOOD["A"]), wall, wall, wall, self.obs("C", self.GOOD["C"]))
        self.assertEqual(len([p for p in look.prompts if "ngược về dãy nhà" in p]), 3)   # lần đầu + 2 vòng sửa, rồi dừng
        self.assertEqual(res["needs_person"], ["1·B"])
        self.assertTrue(any("2 vòng" in m for m in self.diags(pid, "director_plate_review")))


# ---- 5: QC bố cục bằng code sau khi vẽ ảnh ---------------------------------------------------------------------------------------
def picture(path, horizon=0.45, wall=False, stripes=True):
    h, w = 256, 144
    a = np.zeros((h, w), np.float32)
    a[: int(h * horizon)] = 0.85
    a[int(h * horizon):] = 0.35
    if stripes:
        for x in range(10, w, 24):
            a[int(h * horizon) - 40:int(h * horizon), x:x + 6] = 0.15        # nhà / cột trên đường chân trời
    if wall:
        a[:, :] = 0.5                                                            # tường phẳng che kín khung
        a[int(h * 0.92):] = 0.3
    Image.fromarray((a * 255).astype("uint8")).convert("RGB").save(path)
    return path


class LayoutQcTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def test_the_same_layout_is_not_flagged(self):
        plate = picture(os.path.join(self.tmp, "p.png"))
        img = picture(os.path.join(self.tmp, "i.png"))
        res = plate_layout_qc.compare(img, plate, [0.4, 0.4, 0.6, 0.95])
        self.assertFalse(res["mismatch"], res)

    def test_moved_horizon_or_a_wall_is_flagged_with_reasons(self):
        plate = picture(os.path.join(self.tmp, "p.png"), horizon=0.40)
        res = plate_layout_qc.compare(picture(os.path.join(self.tmp, "i.png"), horizon=0.75), plate)
        self.assertTrue(res["mismatch"])
        self.assertTrue(any("chân trời" in r for r in res["reasons"]))
        res = plate_layout_qc.compare(picture(os.path.join(self.tmp, "w.png"), wall=True), plate)
        self.assertTrue(res["mismatch"])
        self.assertTrue(any("tường" in r or "phẳng" in r for r in res["reasons"]))

    def test_unreadable_files_are_said_not_flagged(self):
        res = plate_layout_qc.compare(os.path.join(self.tmp, "none.png"), os.path.join(self.tmp, "none2.png"))
        self.assertFalse(res["mismatch"])
        self.assertIn("không đọc", res["reasons"][0])


class LayoutJobTests(G0Base):
    def test_flag_on_the_drawn_picture_is_compared_and_marked_only(self):
        client = FakeClaude(answer())
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
            location_pack.ensure_plates(self.p.conn, pid, self.data, self.tmp, (W, H), blender="x", render=self.fake_render)
            sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()["id"]
            img = picture(os.path.join(self.tmp, "drawn.png"), wall=True)
            sev, words = plate_layout_qc.check_job(self.p.conn, self.data, pid, sid, 77, img)
        self.assertIn("nền lệch render", words)
        self.assertEqual(sev, "warn")
        with open(plate_layout_qc.record_path(self.data, pid), encoding="utf-8") as f:
            rows = json.load(f)
        self.assertEqual(rows[0]["job_id"], 77)
        self.assertTrue(rows[0]["mismatch"])


# ---- rà G0 (09/10): 7 lỗi phiên rà độc lập ---------------------------------------------------------------------------------------
class ReviewFixTests(G0Base):
    def keys(self, pid):
        return {it["idx"]: it["key"] for it in location_pack.plan(self.p.conn, pid, (W, H))}

    def test_1_same_setup_and_size_but_look_down_is_not_merged(self):
        shots = [{"idx": 1, "setup": "A", "size": "WS", "angle": "eye"}, {"idx": 2, "setup": "C", "size": "MS", "angle": "ots"},
                 {"idx": 3, "setup": "C", "size": "MS", "angle": "ots"}, {"idx": 4, "setup": "B", "size": "MCU", "angle": "eye"}]
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()                                   # shot 3 cúi nhìn giếng, shot 2 không
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer(shots=shots)))
            k = self.keys(pid)
        self.assertEqual((self.shot(pid, 2)["plate_setup"], self.shot(pid, 3)["plate_setup"]), ("C", "C"))
        self.assertNotEqual(k[2], k[3])

    def test_1_setup_A_of_two_plans_is_two_cameras(self):
        one = lambda idx, az: answer(setups=[{"id": "A", "intent": "x", "why": "y", "azimuth_deg": az, "angle": "eye",  # noqa: E731
                                              "tilt": "level", "landmark_in_frame": "any"}],
                                     shots=[{"idx": idx, "setup": "A", "size": "MS", "angle": "eye"}])
        with mock.patch.dict(os.environ, ON):
            pid = self.scene(shots=(("MS", "eye", "Kelly waits"), ("MS", "eye", "Kelly waits")),
                             extra={1: {"story_scene": None}, 2: {"story_scene": None}})
            res = camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(one(1, 180), one(2, 0)))
            k = self.keys(pid)
        self.assertEqual(sorted(res["planned"]), ["shot1", "shot2"])
        self.assertNotEqual(k[1], k[2])

    def test_2_a_locked_camera_field_keeps_its_own_camera_and_shot_words(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene(extra={2: {"plate_view": {"background": 90, "why": "người dùng"}, "shot": "chữ của tôi",
                                        "_user_locked": ["plate_view", "shot"]}})
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer()))
            k = self.keys(pid)
        s2 = self.shot(pid, 2)
        self.assertNotIn("plate_setup", s2)
        self.assertEqual(s2["plate_view"]["background"], 90)
        self.assertEqual(s2["shot"], "chữ của tôi")
        self.assertNotEqual(k[1], k[2])
        self.assertTrue(any("máy riêng" in m for m in self.diags(pid, "director_camera_plan")))

    def test_3_a_failed_rerender_never_pays_to_look_at_the_old_render(self):
        wrong_c = {"observations": ["camera_level", "landmark_visible"]}
        good = [{"observations": v} for v in ReviewTests.GOOD.values()]
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer()))
            location_pack.ensure_plates(self.p.conn, pid, self.data, self.tmp, (W, H), blender="x", render=self.fake_render)
            look = FakeClaude(good[0], good[1], wrong_c, good[2])
            with mock.patch.object(location_pack, "ensure_plates", side_effect=RuntimeError("Blender chết")):
                camera_plan.after_plates(self.p.conn, pid, self.data, self.tmp, client=look, render=self.fake_render, blender="x",
                                         resolution=(W, H))
        self.assertEqual(len(look.prompts), 3)
        c = next(s for s in camera_plan.load_plans(self.data, pid)["1"]["setups"] if s["id"] == "C")
        self.assertFalse(c["review"]["done"])
        self.assertEqual(c["review"]["rounds"], 1)

    def test_4_cli_review_uses_the_project_size_and_counts_failed_scenes(self):
        import importlib.util
        import io
        from contextlib import redirect_stdout
        from core import formats
        spec = importlib.util.spec_from_file_location("tools_location_pack_g0",
                                                      os.path.join(os.path.dirname(__file__), "..", "tools", "location_pack.py"))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        with mock.patch.dict(os.environ, ON):
            pid = self.scene(aspect="16:9")
            camera_plan._save_plans(self.data, pid, {"1": {"failed": "x", "tries": 1}})
            a = mock.Mock(project=pid, yes=True, review=True, force=False)
            out = io.StringIO()
            with mock.patch.object(tool, "DATA", self.data), mock.patch.object(camera_plan, "before_plates", return_value={}), \
                    mock.patch.object(tool.location_pack, "ensure_plates") as ep, \
                    mock.patch.object(camera_plan, "after_plates", return_value={}) as ap, redirect_stdout(out),                     mock.patch("core.adapters.check.load_dashboard_env") as env:
                tool.run_camera_plan(self.p.conn, a)
        # 09/10 chạy thật #24: the CLI must load dashboard.env (LLM_PROVIDER) from the repo root, not the cwd
        self.assertTrue(env.call_args.args[0].endswith("dashboard.env"))
        self.assertTrue(os.path.isabs(env.call_args.args[0]))
        want = tuple(int(v) for v in formats.spec("16:9")["deepix"].lower().split("x"))
        self.assertIn("1 cảnh cần sơ đồ", out.getvalue())
        self.assertIn(want, list(ep.call_args.args) + list(ep.call_args.kwargs.values()))
        self.assertEqual(ap.call_args.kwargs.get("resolution"), want)

    def test_5_the_estimate_says_the_worst_case(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer()))
        self.assertTrue(any(f"tối đa ×{2 * camera_plan.MAX_TRIES}" in m for m in self.diags(pid, "director_camera_plan")))

    def test_6_a_scene_with_a_drawn_picture_is_not_replanned(self):
        client = FakeClaude(answer())
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=2", (pid,)).fetchone()["id"]
            self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, result_path, created_at, updated_at) "
                                "VALUES (?,?,'image_gen','done','x.png','t','t')", (pid, sid))
            self.p.conn.commit()
            res = camera_plan.before_plates(self.p.conn, pid, self.data, client=client)
        self.assertEqual(client.prompts, [])
        self.assertEqual(res["drawn"], ["1"])
        self.assertNotIn("plate_setup", self.shot(pid, 1))
        self.assertTrue(any("đã có ảnh" in m for m in self.diags(pid, "director_camera_plan")))

    def test_6_a_forced_replan_that_fails_keeps_the_old_plan(self):
        class Broken:
            def complete(self, prompt, images=()):
                return LlmReply("không phải JSON", 10, 5)
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer()))
            camera_plan.before_plates(self.p.conn, pid, self.data, client=Broken(), force=True)
        plan = camera_plan.load_plans(self.data, pid)["1"]
        self.assertNotIn("failed", plan)
        self.assertTrue(plan["setups"])
        self.assertIn("error", plan["last_error"])

    def test_7_a_render_not_ready_is_said_once_not_every_tick(self):
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            camera_plan.before_plates(self.p.conn, pid, self.data, client=FakeClaude(answer()))
            for _ in range(3):                                   # ba vòng autopilot, chưa render
                camera_plan.after_plates(self.p.conn, pid, self.data, self.tmp, client=FakeClaude({"observations": []}),
                                         resolution=(W, H))
        rows = self.p.conn.execute("SELECT message, count FROM diag_events WHERE project_id=? AND code=?",
                                   (pid, camera_plan.REVIEW_CODE)).fetchall()
        self.assertTrue(rows)
        self.assertTrue(all(r["count"] == 1 for r in rows), [(r["message"][:60], r["count"]) for r in rows])

    def test_7b_a_repeated_state_is_still_printed_at_the_cli(self):
        """09/10 chạy thật #24: the 2nd CLI run printed nothing (the 'no Claude' line was already in diag)."""
        with mock.patch.dict(os.environ, ON):
            pid = self.scene()
            seen = []
            for _ in range(2):
                camera_plan._say_new(self.p.conn, pid, "warn", "Chưa cấu hình Claude", log=seen.append)
        self.assertEqual(seen, ["Chưa cấu hình Claude"] * 2)
        n = self.p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE project_id=? AND message=?",
                                (pid, "Chưa cấu hình Claude")).fetchone()[0]
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
