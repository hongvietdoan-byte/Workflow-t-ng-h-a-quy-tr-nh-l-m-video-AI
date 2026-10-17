"""17/10 (#31, trước khi gen ảnh 36 shot): ba lỗi lọt qua bước kiểm + lệnh kiểm trước gen dùng chung (0 USD).

1. Hai định nghĩa "nền 3D cũ": change_audit so stage_camera với camera_plan của index (máy THẬT đã render) và báo cũ; ensure_plates so
   khóa cache (máy KẾ HOẠCH) nên dùng lại bản render cũ đã dời máy đã khóa (render trước luật 15/10, SCRIPT_VERSION giữ nguyên) —
   7 shot phải `--fresh-shot` tay. Nay MỘT câu trả lời (location_pack.render_moved trong stale_plates / ensure_plates / change_audit),
   và nền cũ CHẶN nút Gen (batch.image_gates, đỏ) — không chỉ vàng ở Tổ rà soát.
2. byd.noi_chon.thoi_gian / thoi_tiet không theo time / weather (shot 27–30 dawn/clear so với night/fog) — nay time/weather là nguồn
   duy nhất, chép ở CSDL cho mọi đường ghi; việc chép không tạo thay đổi để rà.
3. Nút Gen ≈ 2,13 (ảnh) và ô 💰 ≈ 5,0 (+ D6) — nay một con số (ảnh + khung cuối + toàn cảnh + D6 + QC Claude) có dòng tách phần.
4. tools/pregen_check.check gọi đúng các hàm đó."""
import inspect
import json
import os
import sys
import unittest
from unittest import mock

from core import batch, change_audit, cost, features, location_pack, place_refs
from core.llm_io import update_scene

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from tests.test_plate_stale_kld6 import Base  # noqa: E402

STAGE = {"location": [12.68, -23.0, 27.4], "look_at": [12.68, -19.0, 26.8], "lens": 35.0, "source": "stage_v2"}
MOVED = [12.68, -21.4, 27.4]


class StageBase(Base):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"FEATURE_STAGE_CAMERA": "1"})
        env.start()
        self.addCleanup(env.stop)
        self.assertTrue(features.on("stage_camera"))
        self.set_data({"plate_spot": "plaza_front", "stage_camera": dict(STAGE), "image_prompt": "wide shot, Kelly on the plaza"})
        self.res = place_refs.resolution_of(self.p.project(self.pid))

    def rec(self):
        return location_pack.index(self.data, self.pid)[str(self.sid)]

    def old_moved_render(self):
        """The cache entry as a render made before the 15/10 rules left it: Blender pulled the LOCKED camera, no rule mark."""
        key = self.rec()["key"]
        meta = os.path.join(location_pack.cache_root(self.tmp), key, "meta.json")
        with open(meta, encoding="utf-8") as f:
            m = json.load(f)
        m.pop("locked_rule", None)
        m["clearance"] = {"moved_from_m": STAGE["location"], "location_model": MOVED, "look_at_model": STAGE["look_at"],
                          "notes": ["máy nằm trong/sau vật cản → đưa máy tiến 1.6 m"]}
        with open(meta, "w", encoding="utf-8") as f:
            json.dump(m, f)
        return key


class OneDefinitionTests(StageBase):
    def test_render_moved_only_for_a_locked_camera_moved_by_an_old_render(self):
        cam = dict(STAGE, locked=True)
        rec = {"clearance": {"location_model": MOVED, "look_at_model": STAGE["look_at"]}}
        self.assertIn("đã dời máy Sân khấu 3D", location_pack.render_moved(rec, cam))
        self.assertIsNone(location_pack.render_moved(dict(rec, locked_rule=location_pack.LOCKED_RULE), cam))   # current rules: no loop
        self.assertIsNone(location_pack.render_moved(rec, dict(STAGE)))                                       # unlocked: Blender may move
        self.assertIsNone(location_pack.render_moved({"clearance": {}}, cam))

    def test_a_fresh_render_is_marked_and_matches_the_stage_camera(self):
        self.render()
        rec = self.rec()
        self.assertEqual(rec.get("locked_rule"), location_pack.LOCKED_RULE)
        self.assertEqual([round(v, 2) for v in rec["camera_plan"]["location"]], STAGE["location"])
        self.assertEqual(location_pack.stale_plates(self.p.conn, self.pid, self.data, self.res), {})
        self.assertFalse(any(f["khau"] == "nen" for f in change_audit.audit_shot(self.p.conn, self.data, self.pid, self.sid)))

    def test_ensure_plates_renders_again_an_old_render_that_moved_the_locked_camera(self):
        """#31 shot 20–25, 33: `location_pack render` (ensure_plates) used to reuse it — only `--fresh-shot` helped."""
        self.render()
        self.old_moved_render()
        self.render()                      # the old code reused the cache here and wrote the moved camera into the index
        before = self.renders
        self.p.conn.commit()
        rec = self.rec()
        # the same render (index written from the moved cache) must be judged old by ALL three — then rendered again
        if [round(v, 2) for v in rec["camera_plan"]["location"]] != STAGE["location"]:
            self.fail("ensure_plates reused an old render that moved the locked camera")
        self.assertEqual(before, 2)
        self.assertEqual(rec.get("locked_rule"), location_pack.LOCKED_RULE)

    def test_stale_plates_change_audit_and_gate_agree_on_the_old_render(self):
        self.render()
        self.old_moved_render()
        with mock.patch.object(location_pack, "render_moved", return_value=None):
            self.render()                  # index written from the moved cache (what #31 had before --fresh-shot)
        self.assertNotEqual([round(v, 2) for v in self.rec()["camera_plan"]["location"]], STAGE["location"])
        stale = location_pack.stale_plates(self.p.conn, self.pid, self.data, self.res)
        self.assertIn(self.sid, stale)
        self.assertIn("đã dời máy Sân khấu 3D", stale[self.sid]["why"])
        audit = [f for f in change_audit.audit_shot(self.p.conn, self.data, self.pid, self.sid) if f["khau"] == "nen"]
        self.assertTrue(audit and audit[0]["muc"] == "do" and "đã dời máy Sân khấu 3D" in audit[0]["msg"], audit)
        self.assertTrue(location_pack.refresh_due(self.data, self.pid))           # the autopilot renders it again too
        gates = batch.image_gates(self.p, self.pid, self.data)
        self.assertIn(self.sid, gates["plates_stale"])
        self.assertTrue(any("nền 3D cũ" in b for b in gates["block"]), gates["block"])
        self.assertEqual(batch.image_gates(self.p, self.pid)["block"], [])          # no data_dir: the old gates only
        self.render()                                                               # rendered again → nothing old anywhere
        self.assertEqual(location_pack.stale_plates(self.p.conn, self.pid, self.data, self.res), {})
        self.assertEqual(batch.image_gates(self.p, self.pid, self.data)["block"], [])

    def test_queue_images_blocks_and_starts_the_free_render(self):
        self.render()
        self.old_moved_render()
        with mock.patch.object(location_pack, "render_moved", return_value=None):
            self.render()
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        self.p.conn.commit()
        with mock.patch.object(place_refs, "ensure_async") as ens:
            with self.assertRaises(batch.GateError) as e:
                batch.queue_images(self.p, self.pid, data_dir=self.data)
        self.assertIn("nền 3D cũ", str(e.exception))
        ens.assert_called_once()

    def test_a_failed_render_of_the_moved_camera_is_not_sent_nor_rendered_every_tick(self):
        self.render()
        key = self.old_moved_render()
        fail = os.path.join(location_pack.cache_root(self.tmp), key, "failed.json")
        with open(fail, "w", encoding="utf-8") as f:
            json.dump({"reason": "Blender không trả về góc máy", "transient": False, "at": 0, "tries": 1}, f)
        n = self.renders
        self.render()
        self.assertEqual(self.renders, n)                                           # not again at every tick
        self.assertIn("failed", self.rec())                                         # held, never the moved render


class NoiChonTests(Base):
    def byd(self, t="dawn", w="clear"):
        return {"noi_chon": {"kho_id": self.place, "spot": "plaza_front", "thoi_gian": t, "thoi_tiet": w, "anh_sang": "x"}}

    def test_update_scene_time_change_follows_into_noi_chon(self):
        self.set_data({"time": "dawn", "weather": "clear", "byd": self.byd()})
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (self.sid,)).fetchone()[0]
        update_scene(self.p, self.pid, idx, {"time": "đêm khuya"})                 # Vietnamese words normalised (plate_env.time_of)
        nc = self.data_of()["byd"]["noi_chon"]
        self.assertEqual((nc["thoi_gian"], nc["thoi_tiet"], nc["anh_sang"]), ("night", "clear", "x"))

    def test_every_write_path_syncs_and_the_copy_is_not_a_change_to_review(self):
        self.set_data({"time": "dawn", "weather": "clear", "byd": self.byd()})
        self.p.conn.execute("DELETE FROM change_events")
        data = dict(self.data_of(), time="night", weather="fog")                     # #31 shot 27–30: written straight
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid))
        nc = self.data_of()["byd"]["noi_chon"]
        self.assertEqual((nc["thoi_gian"], nc["thoi_tiet"]), ("night", "fog"))
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM change_events WHERE scene_id=?", (self.sid,)).fetchone()[0], 1)
        new = self.p.create_scene(self.pid, 2, "s2")                                 # a new shot (Director insert) too
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"time": "dusk", "byd": self.byd()}), new))
        got = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (new,)).fetchone()[0])["byd"]["noi_chon"]
        self.assertEqual((got["thoi_gian"], got["thoi_tiet"]), ("dusk", "clear"))

    def test_unknown_weather_is_not_copied(self):
        self.set_data({"time": "day", "weather": "mưa phùn", "byd": self.byd()})
        self.assertEqual(self.data_of()["byd"]["noi_chon"]["thoi_tiet"], "clear")


class PriceTests(Base):
    def test_one_total_with_parts_used_by_button_and_box(self):
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        self.p.conn.commit()
        pricing = dict(cost.load_pricing(), per_image={"m": 0.05})
        with mock.patch.object(cost, "chat_prompt_estimate", return_value=0.08), \
                mock.patch.object(cost, "picture_qc_usd", return_value=0.1):
            est = cost.estimate_images(self.p, self.pid, pricing, "m", data_dir=self.data)
        self.assertEqual(est["items"], 1)
        self.assertAlmostEqual(est["total"], 0.05 + 0.08 + 0.1 * cost.LLM_MARGIN)
        self.assertAlmostEqual(sum(x["usd"] for x in est["parts"]), est["total"])
        # rà gộp 17/10 (lỗi G): min / max = the same total (× retries) — before, min left QC out and differed from the button
        self.assertAlmostEqual(est["min"], est["total"])
        text = cost.format_estimate(est)
        self.assertIn(f"{est['total']:.2f}", text)
        for label in ("ảnh khung đầu", "D6", "QC"):
            self.assertIn(label, text)
        from dashboard.design.screens import storyboard_cards
        self.assertIn(f"{est['total']:.2f}", storyboard_cards.estimate_short(est))
        from dashboard.steps import step2
        src = inspect.getsource(step2.step2)
        self.assertIn('img_price = est.get("total")', src)                          # the button = the box

    def test_run_estimate_keeps_the_same_picture_qc(self):
        src = inspect.getsource(cost._estimate_run)
        self.assertIn("picture_qc_usd(conn, project_id, img[\"items\"]", src)
        self.assertNotIn("_picture_qc_calls(conn, project_id, img[\"items\"])", src)


class PregenCheckTests(StageBase):
    def test_check_reports_price_gate_and_old_plate(self):
        import pregen_check
        self.render()
        self.old_moved_render()
        with mock.patch.object(location_pack, "render_moved", return_value=None):
            self.render()
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        self.p.conn.commit()
        res = pregen_check.check(self.p.conn, self.pid, self.data)
        self.assertTrue(res["blocked"])
        self.assertTrue(any("nền 3D cũ" in b for b in res["gates"]["block"]))
        self.assertEqual([(p["idx"], p["state"]) for p in res["plates"]], [(1, "cũ")])
        self.assertEqual(res["estimate"]["items"], 1)
        self.assertIn("gồm", res["estimate_text"])

    def test_the_command_reads_the_button_functions_not_a_copy(self):
        import pregen_check
        src = inspect.getsource(pregen_check.check)
        # rà gộp 17/10 (lỗi B): the command passes the button's own shot list (batch.image_targets) — same call as Step 2
        for call in ("batch.image_gates(pipe, pid, data_dir, scene_ids=batch.image_targets(pipe, pid, include_queued=True))", "change_review.blocking(conn, r[\"id\"], data_dir)",
                     "cost.estimate_images(", "place_refs.broken("):
            self.assertIn(call, src)


if __name__ == "__main__":
    unittest.main()
