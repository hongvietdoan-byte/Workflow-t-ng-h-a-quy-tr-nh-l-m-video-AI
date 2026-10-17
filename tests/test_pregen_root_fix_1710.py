"""Rà gộp 17/10 (quy ước 7) cho nhánh wizardly-elbakyan (sửa gốc kiểm trước gen #31) — mỗi lỗi một test.

A. place_refs.stale trả khóa -1 (không tính được kế hoạch) → cảnh báo "không so được nền 3D", không chặn "đang render lại" mãi.
B. Nền cũ chỉ chặn các shot lần bấm này sẽ gen (batch.image_targets), không chặn vì shot đã duyệt / ngoài pilot.
C. Trigger chép giờ theo đúng thứ tự plate_env.time_of (time_of_day trước time) — một câu trả lời với sync_noi_chon.
D. Trigger bản cũ được thay khi migrate (DROP trước CREATE).
E. change_events.after là bản đã chép noi_chon.
F. Render lại nền cũ chỉ khi index đổi từ lần trước; không thì nói "render không sửa được nền cũ".
G. Ước tính ảnh: min/max = total, QC chưa có giá không hiện 0.00, model chưa giá không lặp, Claude ngoài ước tính tách dòng."""
import json
import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from core import batch, cost, db, location_pack, place_refs, plate_env
from core.llm_io import update_scene
from tests.test_plate_stale_kld6 import Base


def _item(idx, why="đã dời máy"):
    return {"idx": idx, "old_spot": None, "new_spot": None, "why": why}


class GateTests(Base):
    def setUp(self):
        super().setUp()
        batch._STALE_MEMO.clear()
        self.assertTrue(place_refs.enabled())

    def test_a_plan_that_cannot_be_computed_warns_and_does_not_block(self):
        with mock.patch.object(location_pack, "stale_plates", side_effect=RuntimeError("thiếu gói")):
            gates = batch.image_gates(self.p, self.pid, self.data)
        self.assertFalse(any("nền 3D cũ" in b or "đang render lại" in b for b in gates["block"]), gates["block"])
        self.assertTrue(any("không so được nền 3D" in w and "thiếu gói" in w for w in gates["warn"]), gates["warn"])
        self.assertEqual(gates["plates_stale"], {})

    def test_only_the_shots_this_press_draws_are_held_by_an_old_background(self):
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        done = self.p.create_scene(self.pid, 2, "s2")
        job = self.p.create_job(done, "image_gen")
        self.p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (job,))
        self.p.conn.commit()
        self.assertEqual(batch.image_targets(self.p, self.pid), [self.sid])
        both = {self.sid: _item(1), done: _item(2)}
        with mock.patch.object(place_refs, "stale", return_value=dict(both)):
            every = batch.image_gates(self.p, self.pid, self.data)
            batch._STALE_MEMO.clear()
            mine = batch.image_gates(self.p, self.pid, self.data, scene_ids=batch.image_targets(self.p, self.pid))
            batch._STALE_MEMO.clear()
            with mock.patch.object(place_refs, "ensure_async"), self.assertRaises(batch.GateError) as e:
                batch.queue_images(self.p, self.pid, data_dir=self.data)
        self.assertEqual(set(every["plates_stale"]), {self.sid, done})             # None = every shot, as before
        self.assertEqual(set(mine["plates_stale"]), {self.sid})
        self.assertTrue(any("nền 3D cũ ở 1 shot (1)" in b for b in mine["block"]), mine["block"])
        self.assertIn("nền 3D cũ ở 1 shot (1)", str(e.exception))

    def test_the_render_starts_again_only_when_the_index_changed(self):
        calls = []
        path = location_pack._index_path(self.data, self.pid)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)

        def run(pid):
            calls.append(pid)

        def press():
            msg = batch.rerender_stale(self.p, self.pid, self.data, run=run)
            t = place_refs._RUNNING.get(self.pid)
            if t is not None:
                t.join(5)
            return msg

        self.assertIsNone(press())
        self.assertEqual(len(calls), 1)
        msg = press()                                                             # index unchanged: no Blender again, said
        self.assertEqual(len(calls), 1)
        self.assertIn("không sửa được nền cũ", msg)
        st = os.stat(path)
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))          # the render wrote the index
        self.assertIsNone(press())
        self.assertEqual(len(calls), 2)


class NoiChonTriggerTests(Base):
    def byd(self):
        return {"noi_chon": {"kho_id": self.place, "spot": "plaza_front", "thoi_gian": "dawn", "thoi_tiet": "clear"}}

    def test_trigger_follows_plate_env_time_of_order(self):
        data = dict(self.data_of(), time_of_day="dusk", time="night", byd=self.byd())
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid))
        got = self.data_of()
        self.assertEqual(plate_env.time_of(got), "dusk")
        self.assertEqual(got["byd"]["noi_chon"]["thoi_gian"], plate_env.time_of(got))
        idx = self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (self.sid,)).fetchone()[0]
        update_scene(self.p, self.pid, idx, {"time": "day"})                       # time_of_day still wins
        got = self.data_of()
        self.assertEqual(got["byd"]["noi_chon"]["thoi_gian"], plate_env.time_of(got))

    def test_migrate_replaces_an_old_trigger(self):
        conn = self.p.conn
        conn.executescript("DROP TRIGGER IF EXISTS trg_scene_noi_chon; CREATE TRIGGER trg_scene_noi_chon AFTER UPDATE OF data ON scenes "
                           "BEGIN UPDATE scenes SET data = json_set(data, '$.byd.noi_chon.thoi_gian', json_extract(data, '$.time')) "
                           "WHERE id = new.id; END;")
        conn.executescript(db.CHANGE_TRIGGERS)
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='trg_scene_noi_chon'").fetchone()[0]
        self.assertIn("time_of_day", sql)

    def test_change_event_after_holds_the_synced_copy(self):
        self.set_data({"time": "dawn", "weather": "clear", "byd": self.byd()})
        self.p.conn.execute("DELETE FROM change_events")
        data = dict(self.data_of(), time="night")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), self.sid))
        rows = self.p.conn.execute("SELECT after FROM change_events WHERE scene_id=?", (self.sid,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0][0])["byd"]["noi_chon"]["thoi_gian"], "night")


class EstimateTests(Base):
    def setUp(self):
        super().setUp()
        self.p.conn.execute("UPDATE scenes SET state='ready' WHERE id=?", (self.sid,))
        self.p.conn.commit()
        self.pricing = dict(cost.load_pricing(), per_image={"m": 0.05})

    def test_unpriced_qc_is_said_and_min_max_follow_the_total(self):
        with mock.patch.object(cost, "llm_estimate", return_value=None), \
                mock.patch.object(cost, "_picture_qc_calls", return_value=1), \
                mock.patch.dict(os.environ, {"FEATURE_DIRECTOR_REWRITE": "0", "FEATURE_CHANGE_REVIEW": "0"}):
            est = cost.estimate_images(self.p, self.pid, self.pricing, "m", data_dir=self.data)
        qc = [x for x in est["parts"] if "QC" in x["label"]][0]
        self.assertIsNone(qc["usd"])
        text = cost.format_estimate(est)
        self.assertIn("(chưa có giá)", text)
        self.assertNotIn("≈ 0.00", text)
        self.assertAlmostEqual(est["min"], est["total"])
        self.assertAlmostEqual(est["max"], est["total"] * (1 + est["max_retry"]))
        unknown = []
        with mock.patch.object(cost, "llm_estimate", return_value=None):
            cost.picture_qc_usd(self.p.conn, self.pid, 1, self.pricing, unknown)
            cost.picture_qc_usd(self.p.conn, self.pid, 1, self.pricing, unknown)
        self.assertEqual(len(unknown), 1)

    def test_claude_outside_the_estimate_is_a_separate_line(self):
        env = {"FEATURE_DIRECTOR_REWRITE": "1", "FEATURE_CHANGE_REVIEW": "1"}
        with mock.patch.dict(os.environ, env):
            est = cost.estimate_images(self.p, self.pid, self.pricing, "m", data_dir=self.data)
        self.assertIn("chưa tính", est["outside_note"])                           # no ledger figure: said with the #31 measure
        self.assertIn("director_rewrite 0,09", cost.format_estimate(est))
        at = datetime.now(timezone.utc).isoformat()
        for _ in range(4):
            self.p.conn.execute("INSERT INTO usage_events (project_id, kind, provider, model, tier, quantity, unit, at)"
                                " VALUES (?, 'image', 'clipai', 'm', 'x', 1, 'image', ?)", (self.pid, at))
        for st in ("director_rewrite", "change_review"):
            self.p.conn.execute("INSERT INTO usage_events (project_id, kind, provider, model, tier, quantity, unit, at, stage)"
                                " VALUES (?, 'llm', 'anthropic', 'c', 'input', 1000, 'token', ?, ?)", (self.pid, at, st))
        with mock.patch.dict(os.environ, env), mock.patch.object(cost, "llm_call_usd", return_value=0.02):
            est = cost.estimate_images(self.p, self.pid, self.pricing, "m", data_dir=self.data)
        part = [x for x in est["parts"] if "ngoài ước tính" in x["label"]]
        self.assertEqual(len(part), 1)
        self.assertAlmostEqual(part[0]["usd"], 2 * 0.02 * 1 / 4)                  # 1 call each per 4 pictures × 1 picture
        self.assertAlmostEqual(est["total"], round(sum(x["usd"] for x in est["parts"]), 4))
        self.assertEqual(est["outside_note"], "")


if __name__ == "__main__":
    unittest.main()
