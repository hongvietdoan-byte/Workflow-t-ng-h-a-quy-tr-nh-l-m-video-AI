"""Meshy (core/meshy.py) + cắt bảng xoay (core/sheet_views.py) — máy chủ giả, 0 credit."""
import json
import os
import tempfile
import unittest

from core import assets, meshy, sheet_views
from core.adapters.http import HttpResponse
from core.db import connect
from core.providers import ProviderError

PROFILE = {"identity": "girl", "must_keep": "short black bob, yellow tracksuit, star emblem on the LEFT shoulder", "forbidden": "ponytail",
           "height_m": 1.7}


def plain_turnaround(path, figures=4, gap=60, w=90, h=400):
    """Four dark figures on a flat light-grey background — the 'plain' layout."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (figures * (w + gap) + gap, h + 100), (229, 229, 229))
    d = ImageDraw.Draw(img)
    for k in range(figures):
        x = gap + k * (w + gap)
        d.rectangle([x, 50, x + w, 50 + h], fill=(200, 160, 30))
    img.save(path)


class FakeMeshy:
    """Records every request; answers like the docs."""

    def __init__(self, balance=1000, create_status=200, network_error=False):
        self.calls, self.balance, self.create_status, self.network_error = [], balance, create_status, network_error
        self.tasks = {}

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "headers": headers, "body": json.loads(body) if body else None})
        if url.endswith("/balance"):
            return HttpResponse(200, json.dumps({"balance": self.balance}).encode())
        if method == "POST":
            if self.network_error:
                raise ProviderError("network error: reset", code="network", transient=True)
            if self.create_status != 200:
                return HttpResponse(self.create_status, json.dumps({"message": "Insufficient credits"}).encode())
            tid = f"task{len(self.tasks) + 1}"
            self.tasks[tid] = {"id": tid, "status": "IN_PROGRESS", "progress": 40}
            return HttpResponse(200, json.dumps({"result": tid}).encode())
        if url.startswith("https://assets.meshy.ai/"):
            return HttpResponse(200, b"FILE:" + url.encode())
        tid = url.rsplit("/", 1)[-1]
        return HttpResponse(200, json.dumps(self.tasks[tid]).encode())

    def finish_model(self, tid):
        a = "https://assets.meshy.ai/x/"
        self.tasks[tid] = {"id": tid, "status": "SUCCEEDED", "progress": 100, "consumed_credits": 30,
                           "model_urls": {"glb": a + "m.glb", "fbx": a + "m.fbx", "stl": a + "m.stl"},
                           "texture_urls": [{"base_color": a + "t.png"}],
                           "thumbnail_urls": {"front": a + "f.png", "back": a + "b.png", "left": a + "l.png", "right": a + "r.png"}}

    def finish_rig(self, tid):
        a = "https://assets.meshy.ai/r/"
        self.tasks[tid] = {"id": tid, "status": "SUCCEEDED", "consumed_credits": 5, "result": {
            "rigged_character_glb_url": a + "rig.glb", "rigged_character_fbx_url": a + "rig.fbx",
            "basic_animations": {"walking_glb_url": a + "w.glb", "running_armature_fbx_url": a + "ra.fbx"}}}


class MeshyTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self._env = {k: os.environ.get(k) for k in ("ASSET_DIR", "MESHY_USD_PER_CREDIT")}
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        os.environ["MESHY_USD_PER_CREDIT"] = "0.02"
        self.conn = connect(":memory:")
        self.aid = assets.create(self.conn, "FF", "character", "KELLY")
        assets.set_profile(self.conn, self.aid, PROFILE, approved=True)
        sheet = os.path.join(self.dir, "sheet.png")
        plain_turnaround(sheet)
        assets.add_image(self.conn, self.aid, "sheet.png", open(sheet, "rb").read(), role="design_sheet", status="approved")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def plan(self):
        return meshy.plan(self.conn, self.aid, work_dir=os.path.join(self.dir, "views"))

    def test_the_sheet_is_cut_into_four_views_front_first(self):
        p = self.plan()
        self.assertEqual([v["view"] for v in p["views"]], list(sheet_views.VIEWS))
        self.assertEqual(len(p["view_paths"]), 4)
        self.assertIn("LEFT shoulder", p["texture_prompt"])
        self.assertIn("Never: ponytail", p["texture_prompt"])
        self.assertEqual((p["credits"], p["usd"], p["problems"]), (30, 0.6, []))

    def test_a_plain_turnaround_keeps_whole_figures_and_the_real_sheets_cut_too(self):
        path = os.path.join(self.dir, "plain.png")
        plain_turnaround(path, h=400)
        for v in sheet_views.turnaround(path):
            self.assertGreaterEqual(v["box"][3] - v["box"][1], 400)
        for sheet in ("D:/AI-Video-Pipeline/data/assets/23/1.png", "D:/AI-Video-Pipeline/data/assets/33/1.png"):
            if os.path.exists(sheet):                                     # the team's sheets (Kelly, Maxim) — only on the user's PC
                views = sheet_views.turnaround(sheet)
                self.assertEqual([v["view"] for v in views], list(sheet_views.VIEWS))
                self.assertTrue(all(30 <= v["box"][1] and v["box"][3] <= 460 for v in views))   # no title, no labels

    def add_view(self, role, status="approved", variant="in-game nhiều góc", color=(40, 90, 200)):
        from PIL import Image
        path = os.path.join(self.dir, f"{role}_{status}.png")
        Image.new("RGB", (300, 700), color).save(path)
        return assets.add_image(self.conn, self.aid, os.path.basename(path), open(path, "rb").read(), role=role, status=status,
                                variant=variant, limit=40)

    def test_approved_in_game_views_beat_the_sheet_front_first_and_pending_ones_wait(self):
        self.add_view("full_body")
        self.add_view("back", status="pending")
        self.assertIn("cắt 4 hướng", self.plan()["source"])            # a front alone + a pending back: no set yet → the sheet
        self.conn.execute("UPDATE asset_images SET status='approved' WHERE role='back'")
        self.add_view("side")
        p = self.plan()
        self.assertIn("ảnh Kho đã duyệt", p["source"])
        self.assertEqual([v["view"] for v in p["views"]], ["front", "side", "back"])
        sheet_id = self.conn.execute("SELECT id FROM asset_images WHERE role='design_sheet'").fetchone()[0]
        self.assertIn("cắt 4 hướng", meshy.plan(self.conn, self.aid, sheet_image_id=sheet_id)["source"])   # the person's choice wins

    def test_joined_figures_are_not_guessed(self):
        path = os.path.join(self.dir, "joined.png")
        plain_turnaround(path, figures=4, gap=0)
        self.assertEqual(sheet_views.turnaround(path), [])

    def test_submit_writes_the_ledger_and_sends_four_data_uris_with_the_key_only_to_the_api(self):
        fake = FakeMeshy()
        c = meshy.Client("msy_secret", fake)
        r = meshy.submit_model(self.conn, c, self.plan())
        post = [x for x in fake.calls if x["method"] == "POST"][0]
        self.assertTrue(post["url"].endswith("/multi-image-to-3d"))
        self.assertEqual(len(post["body"]["image_urls"]), 4)
        self.assertTrue(post["body"]["image_urls"][0].startswith("data:image/png;base64,"))
        self.assertEqual(post["body"]["pose_mode"], "a-pose")
        row = meshy.tasks(self.conn)[0]
        self.assertEqual((row["status"], row["task_id"], row["credits_est"]), ("PENDING", r["task_id"], 30))
        self.assertNotIn("base64", row["request"])
        fake.finish_model(r["task_id"])
        notes = meshy.refresh(self.conn, c)
        self.assertIn("xong", notes[0])
        row = meshy.tasks(self.conn)[0]
        self.assertEqual((row["status"], row["credits"]), ("DOWNLOADED", 30))
        files = sorted(os.listdir(row["folder"]))
        self.assertIn("model.glb", files)
        self.assertIn("view_back.png", files)
        self.assertNotIn("model.stl", files)
        for call in fake.calls:
            if call["url"].startswith("https://assets.meshy.ai/"):
                self.assertNotIn("Authorization", call["headers"])          # signed links never get the key
        lib = meshy.views_to_library(self.conn, row["id"])
        self.assertEqual(sorted(lib["added"]), ["back", "front", "left", "right"])
        roles = {r["role"] for r in self.conn.execute("SELECT role, status FROM asset_images WHERE variant='3D Meshy'")}
        self.assertEqual(roles, {"full_body", "back", "side"})
        self.assertEqual({r[0] for r in self.conn.execute("SELECT status FROM asset_images WHERE variant='3D Meshy'")}, {"pending"})

    def test_rig_after_the_model_with_the_profiles_height(self):
        fake = FakeMeshy()
        c = meshy.Client("k", fake)
        r = meshy.submit_model(self.conn, c, self.plan())
        with self.assertRaises(meshy.MeshyError):
            meshy.submit_rig(self.conn, c, meshy.tasks(self.conn)[0]["id"])        # not downloaded yet
        fake.finish_model(r["task_id"])
        meshy.refresh(self.conn, c)
        rig = meshy.submit_rig(self.conn, c, meshy.tasks(self.conn)[0]["id"])
        body = [x for x in fake.calls if x["method"] == "POST"][-1]["body"]
        self.assertEqual(body, {"input_task_id": r["task_id"], "height_meters": 1.7})
        fake.finish_rig(rig["task_id"])
        meshy.refresh(self.conn, c)
        row = [t for t in meshy.tasks(self.conn) if t["kind"] == "rig"][0]
        self.assertEqual(sorted(os.listdir(row["folder"])), ["anim_running_armature.fbx", "anim_walking.glb", "rigged.fbx",
                                                             "rigged.glb", "task.json"])
        self.assertEqual(meshy.spent_credits(self.conn), 35)

    def test_remesh_then_rig_the_lighter_copy(self):
        fake = FakeMeshy()
        c = meshy.Client("k", fake)
        r = meshy.submit_model(self.conn, c, self.plan())
        fake.finish_model(r["task_id"])
        meshy.refresh(self.conn, c)
        model = meshy.tasks(self.conn)[0]["id"]
        rm = meshy.submit_remesh(self.conn, c, model)
        post = [x for x in fake.calls if x["method"] == "POST"][-1]
        self.assertTrue(post["url"].endswith("/remesh"))
        self.assertEqual(post["body"]["target_polycount"], meshy.REMESH_POLYCOUNT)
        fake.finish_model(rm["task_id"])
        meshy.refresh(self.conn, c)
        light = [t for t in meshy.tasks(self.conn) if t["kind"] == "remesh"][0]
        self.assertEqual(light["status"], "DOWNLOADED")
        self.assertIn("model.glb", os.listdir(light["folder"]))
        meshy.submit_rig(self.conn, c, light["id"])
        self.assertEqual([x for x in fake.calls if x["method"] == "POST"][-1]["body"]["input_task_id"], rm["task_id"])

    def test_caps_refuse_before_sending(self):
        c = meshy.Client("k", FakeMeshy(balance=10))
        with self.assertRaisesRegex(meshy.MeshyError, "còn 10 credit"):
            meshy.submit_model(self.conn, c, self.plan())
        meshy.save_settings(self.conn, cap_usd=0.5)                               # 30 credits ≈ $0.60
        with self.assertRaisesRegex(meshy.MeshyError, "vượt trần"):
            meshy.submit_model(self.conn, meshy.Client("k", FakeMeshy()), self.plan())
        self.assertEqual(meshy.tasks(self.conn), [])                              # nothing sent, nothing written

    def test_three_models_per_character_then_stop(self):
        fake = FakeMeshy()
        c = meshy.Client("k", fake)
        for _ in range(meshy.MAX_TRIES_PER_CHARACTER):
            meshy.submit_model(self.conn, c, self.plan())
        with self.assertRaisesRegex(meshy.MeshyError, "1 \\+ 2 làm lại"):
            meshy.submit_model(self.conn, c, self.plan())

    def test_an_unreadable_balance_stops_the_send(self):
        def broken(method, url, headers, body, timeout):
            return HttpResponse(500, b"{}")
        with self.assertRaisesRegex(meshy.MeshyError, "không đọc được số credit"):
            meshy.submit_model(self.conn, meshy.Client("k", broken), self.plan())

    def test_a_lost_answer_is_counted_and_never_resent(self):
        c = meshy.Client("k", FakeMeshy(network_error=True))
        with self.assertRaisesRegex(meshy.MeshyError, "UNKNOWN"):
            meshy.submit_model(self.conn, c, self.plan())
        row = meshy.tasks(self.conn)[0]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertEqual(meshy.spent_credits(self.conn), 30)

    def test_a_refused_send_costs_nothing(self):
        c = meshy.Client("k", FakeMeshy(create_status=402))
        with self.assertRaisesRegex(meshy.MeshyError, "402"):
            meshy.submit_model(self.conn, c, self.plan())
        self.assertEqual((meshy.tasks(self.conn)[0]["status"], meshy.spent_credits(self.conn)), ("FAILED", 0))

    def test_a_failed_task_gives_its_credits_back(self):
        fake = FakeMeshy()
        c = meshy.Client("k", fake)
        r = meshy.submit_model(self.conn, c, self.plan())
        fake.tasks[r["task_id"]] = {"status": "FAILED", "consumed_credits": 0, "task_error": {"message": "bad image"}}
        self.assertIn("bad image", meshy.refresh(self.conn, c)[0])
        self.assertEqual(meshy.spent_credits(self.conn), 0)

    def test_an_unapproved_profile_stops_it(self):
        assets.set_profile(self.conn, self.aid, PROFILE, approved=False)
        p = self.plan()
        self.assertTrue(p["problems"])
        own = meshy.plan(self.conn, self.aid, texture_override="White shirt, striped tie, white pants with black wing prints")
        self.assertEqual((own["problems"], own["texture_by_person"]), ([], True))
        self.assertTrue(own["texture_prompt"].startswith("White shirt"))
        with self.assertRaisesRegex(meshy.MeshyError, "hồ sơ chuẩn"):
            meshy.submit_model(self.conn, meshy.Client("k", FakeMeshy()), p)


if __name__ == "__main__":
    unittest.main()
