"""12/10 dự án #27: TÁCH shot 6 (trong phòng → ngoài trời) thành 2 shot — chèn MỘT shot mới ngay sau shot `after_idx`
(core.llm_io.insert_scene_after); shot sau dời +1 mà không vỡ gì: continuity_from theo số shot dời theo, ảnh đã duyệt giữ duyệt và
KHÔNG thành '⚠ cũ', âm thanh neo theo số shot (anchor_idx) dời theo, tệp đặt tên theo số shot (videos/NN.mp4, layouts/SNN.png) hay
video đang chạy → TỪ CHỐI (nói rõ lý do)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from core import audio_lib, lineage, llm_io, scene_storyboard
from core.db import connect
from core.pipeline import Pipeline

NEW = {"image_prompt": "Kelly bước ra khỏi cửa, ngoài trời", "action": "Kelly bước ra ngoài", "duration_s": 3,
       "plate_spot": "ngoai_troi"}


def project(n=21):
    """n shots: story scene 3 = shots 5..8 (shot_no 1..4), others alone; continuity_from 15→18, 3→2."""
    p = Pipeline(connect(":memory:"))
    pid = p.create_project("p27")
    p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?,?,?)", (pid, "KELLY", "cô gái"))
    ids = {}
    for i in range(1, n + 1):
        sid = p.create_scene(pid, i, f"CẢNH {i} · shot 1")
        story, no = (3, i - 4) if 5 <= i <= 8 else (i, 1)
        d = {"story_scene": story, "shot_no": no, "sequence": story, "characters": ["KELLY"], "image_prompt": f"shot {i}",
             "action": f"hành động {i}", "duration_s": 3, "size": "MS"}
        if i == 18:
            d["continuity_from"] = 15
        if i == 3:
            d["continuity_from"] = 2
        title = f"CẢNH 3 · shot {i - 4}" if 5 <= i <= 8 else f"CẢNH {i} · shot 1"
        p.conn.execute("UPDATE scenes SET state='ready', title=?, data=? WHERE id=?", (title, json.dumps(d, ensure_ascii=False), sid))
        ids[i] = sid
    p.conn.commit()
    return p, pid, ids


def approve_picture(p, pid, sid):
    j = p.create_job(sid, "image_gen")
    p.conn.execute("UPDATE jobs SET state='approved', input_hash=? WHERE id=?",
                   (lineage.current_image_hash(p.conn, pid, sid), j))
    p.conn.commit()
    return j


def strip_idx(scan):
    return {sid: {k: v for k, v in row.items() if k != "idx"} for sid, row in scan.items()}


class InsertSceneTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.p, self.pid, self.ids = project()

    def idx_of(self, sid):
        return self.p.conn.execute("SELECT idx FROM scenes WHERE id=?", (sid,)).fetchone()["idx"]

    def data_of(self, sid):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE id=?", (sid,)).fetchone()["data"])

    def insert(self, after, fields=None, **kw):
        return llm_io.insert_scene_after(self.p, self.pid, after, dict(fields or NEW), data_dir=self.data, **kw)

    def test_later_shots_move_up_by_one_and_the_new_shot_takes_the_gap(self):
        new = self.insert(6)
        self.assertEqual(new, 7)
        self.assertEqual([self.idx_of(self.ids[i]) for i in (1, 6, 7, 21)], [1, 6, 8, 22])
        rows = self.p.conn.execute("SELECT idx FROM scenes WHERE project_id=? ORDER BY idx", (self.pid,)).fetchall()
        self.assertEqual([r["idx"] for r in rows], list(range(1, 23)))
        row = self.p.conn.execute("SELECT id, title, data FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()
        d = json.loads(row["data"])
        self.assertEqual((d["story_scene"], d["shot_no"], d["sequence"]), (3, 3, 3))       # shot 6 = Cảnh 3 · shot 2
        self.assertEqual((d["image_prompt"], d["action"], d["duration_s"]), (NEW["image_prompt"], NEW["action"], 3))
        self.assertEqual(row["title"], "CẢNH 3 · shot 3")
        self.assertTrue({"image_prompt", "action", "duration_s"} <= set(d["_user_locked"]))   # set by hand: a Director run keeps it
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE scene_id=?", (row["id"],)).fetchone()[0], 0)
        # the later shots of the same script scene: shot_no follows (no two 'S03·3')
        self.assertEqual((self.data_of(self.ids[7])["shot_no"], self.data_of(self.ids[8])["shot_no"]), (4, 5))
        self.assertEqual(self.p.conn.execute("SELECT title FROM scenes WHERE id=?", (self.ids[8],)).fetchone()["title"], "CẢNH 3 · shot 5")
        self.assertEqual(self.data_of(self.ids[9])["shot_no"], 1)                              # another script scene: untouched

    def test_continuity_from_follows_the_shift(self):
        self.insert(6)
        self.assertEqual(self.data_of(self.ids[18])["continuity_from"], 16)   # 15→18 becomes 16→19
        self.assertEqual(self.idx_of(self.ids[18]), 19)
        self.assertEqual(self.data_of(self.ids[3])["continuity_from"], 2)     # 3→2 kept
        self.assertEqual(self.idx_of(self.ids[3]), 3)

    def test_approved_pictures_stay_approved_and_not_outdated(self):
        jobs = {i: approve_picture(self.p, self.pid, self.ids[i]) for i in (3, 7, 15, 18)}
        before = strip_idx(lineage._scan(self.p.conn, self.pid))
        self.assertFalse(any(before[self.ids[i]]["image_stale"] for i in jobs))
        self.insert(6)
        after = strip_idx(lineage._scan(self.p.conn, self.pid))
        new_id = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        self.assertEqual({k: v for k, v in after.items() if k != new_id}, before)
        for i, j in jobs.items():
            self.assertEqual(self.p.conn.execute("SELECT state FROM jobs WHERE id=?", (j,)).fetchone()["state"], "approved")
            self.assertEqual(after[self.ids[i]]["image_job_id"], j)
        self.assertIsNone(after[new_id]["image_job_id"])

    def test_renumbering_is_not_queued_for_a_paid_change_review(self):
        start = self.p.conn.execute("SELECT COALESCE(MAX(id), 0) FROM change_events").fetchone()[0]   # the set-up's own edits
        self.insert(6)
        pending = self.p.conn.execute("SELECT scene_id FROM change_events WHERE state='pending' AND id>?", (start,)).fetchall()
        new_id = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        self.assertEqual({r["scene_id"] for r in pending}, {new_id})          # the new shot = one hand edit, nothing else
        skipped = self.p.conn.execute("SELECT scene_id FROM change_events WHERE state='skipped' AND id>?", (start,)).fetchall()
        self.assertIn(self.ids[18], {r["scene_id"] for r in skipped})

    def test_after_the_last_shot(self):
        self.assertEqual(self.insert(21), 22)
        self.assertEqual(self.idx_of(self.ids[21]), 21)
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=22", (self.pid,)).fetchone()["data"])
        self.assertEqual((d["story_scene"], d["shot_no"]), (21, 2))

    def test_unknown_shot_is_refused_and_nothing_changes(self):
        with self.assertRaises(KeyError):
            self.insert(30)
        self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0], 21)

    def test_bad_or_missing_fields_are_refused_and_nothing_moves(self):
        no_spot = {k: v for k, v in NEW.items() if k != "plate_spot"}
        for bad in ({"action": "x", "duration_s": 3, "plate_spot": "a"},           # no image prompt
                    no_spot,                                                        # no plate_spot (storyboard anchor / own camera)
                    dict(NEW, camera_move="bay_lượn"),                              # not a move
                    dict(NEW, characters=["AI_ĐÓ"]),                                # not in the Character Bible (update_scene check)
                    dict(NEW, stage_camera={"x": 1}),                               # a solved 3D camera is never copied by hand
                    dict(NEW, continuity_from=99)):                                 # no such shot
            with self.assertRaises(llm_io.SchemaError, msg=str(bad)):
                self.insert(6, bad)
            self.assertEqual(self.idx_of(self.ids[7]), 7)
            self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0], 21)
            self.assertEqual(self.data_of(self.ids[18])["continuity_from"], 15)

    def test_new_shot_continuity_from_uses_the_new_numbering(self):
        self.insert(6, dict(NEW, continuity_from=19))                                # = old shot 18
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["data"])
        self.assertEqual(d["continuity_from"], 19)

    def test_sound_anchored_to_a_shot_number_moves_with_it(self):
        directory = audio_lib.assets_dir(self.data, self.pid)
        audio_lib._save(directory, [{"kind": "sound_effect", "label": "AI: cửa", "anchor_idx": 9, "offset": 0.5},
                                    {"kind": "sound_effect", "label": "AI: gió", "anchor_idx": 4, "offset": 0.0},
                                    {"kind": "tts", "scene_id": self.ids[12], "scene_idx": 12, "line": 1}])
        self.insert(6)
        items = audio_lib.load(directory)
        self.assertEqual([e.get("anchor_idx") for e in items], [10, 4, None])
        self.assertEqual(items[2]["scene_idx"], 13)

    def test_files_named_by_shot_number_refuse(self):
        for sub, name in (("videos", "09.mp4"), ("videos", "12_raw.mp4"), ("layouts", "S07.png")):
            folder = os.path.join(self.data, str(self.pid), sub)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, name)
            open(path, "wb").write(b"x")
            with self.assertRaises(llm_io.SchemaError) as e:
                self.insert(6)
            self.assertIn(name, str(e.exception))
            self.assertEqual(self.idx_of(self.ids[7]), 7)
            os.remove(path)
        folder = os.path.join(self.data, str(self.pid), "videos")
        open(os.path.join(folder, "05.mp4"), "wb").write(b"x")                    # a clip of a shot that does not move: fine
        self.assertEqual(self.insert(6), 7)

    def test_a_trashed_clip_of_a_moving_shot_refuses(self):
        folder = os.path.join(self.data, str(self.pid), "trash", "videos")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "trash.json"), "w", encoding="utf-8") as f:
            json.dump([{"file": "10__x.mp4", "original": "videos/10.mp4", "scene_idx": 10}], f)
        with self.assertRaises(llm_io.SchemaError) as e:
            self.insert(6)
        self.assertIn("videos/10.mp4", str(e.exception))

    def test_a_running_video_of_a_shot_that_does_not_move_does_not_refuse(self):
        j = self.p.create_job(self.ids[3], "video_gen")                           # #27: the Kling clip of shot 3
        self.p.conn.execute("UPDATE jobs SET state='running' WHERE id=?", (j,))
        self.p.conn.commit()
        self.assertEqual(self.insert(6), 7)

    def test_a_running_video_of_a_moving_shot_refuses(self):
        j = self.p.create_job(self.ids[8], "video_gen")
        self.p.conn.execute("UPDATE jobs SET state='running' WHERE id=?", (j,))
        self.p.conn.commit()
        with self.assertRaises(llm_io.SchemaError):
            self.insert(6)
        self.assertEqual(self.idx_of(self.ids[7]), 7)
        self.assertFalse(self.p.conn.in_transaction)

    def test_a_running_group_clip_with_a_moving_follower_refuses(self):
        lead = self.p.create_job(self.ids[5], "video_gen")                        # leader shot 5 stays, follower shot 7 moves
        fol = self.p.create_job(self.ids[7], "video_gen")
        self.p.conn.execute("UPDATE jobs SET state='running' WHERE id=?", (lead,))
        self.p.conn.execute("UPDATE jobs SET state='queued', group_leader=? WHERE id=?", (lead, fol))
        self.p.conn.commit()
        with self.assertRaises(llm_io.SchemaError) as e:
            self.insert(6)
        self.assertIn(str(lead), str(e.exception))

    def test_shot_numbers_written_in_text_follow_and_nothing_turns_outdated(self):
        d18 = self.data_of(self.ids[18])
        d18["blocking"] = "a few metres behind her, as in shot 15; S07 too"         # #27 shot 15/17: "as in shot 18"
        d2 = self.data_of(self.ids[2])
        d2["action"] = "chạy tới (cùng chỗ shot 2, sau đó shot 9)"
        for sid, d in ((self.ids[18], d18), (self.ids[2], d2)):
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), sid))
        self.p.conn.commit()
        img = approve_picture(self.p, self.pid, self.ids[18])
        img2 = approve_picture(self.p, self.pid, self.ids[2])
        for sid, prompt, job in ((self.ids[18], "same spot as shot 15, S03·2 label", img), (self.ids[2], "toward shot 9", img2)):
            self.p.conn.execute("INSERT INTO motion_prompts (scene_id, motion_prompt, state, image_job_id, spec_hash) VALUES (?,?,?,?,?)",
                                (sid, prompt, "approved", job, lineage.motion_spec_hash(self.data_of(sid))))
        self.p.conn.commit()
        before = strip_idx(lineage._scan(self.p.conn, self.pid))
        self.assertFalse(before[self.ids[18]]["image_stale"] or before[self.ids[18]]["motion_stale"])
        self.insert(6)
        self.assertEqual(self.data_of(self.ids[18])["blocking"], "a few metres behind her, as in shot 16; S08 too")
        self.assertEqual(self.data_of(self.ids[2])["action"], "chạy tới (cùng chỗ shot 2, sau đó shot 10)")
        mp = lambda sid: self.p.conn.execute("SELECT * FROM motion_prompts WHERE scene_id=?", (sid,)).fetchone()  # noqa: E731
        self.assertEqual(mp(self.ids[18])["motion_prompt"], "same spot as shot 16, S03·2 label")   # the script-scene label kept
        self.assertEqual(mp(self.ids[2])["motion_prompt"], "toward shot 10")
        self.assertEqual(mp(self.ids[18])["state"], "approved")
        after = strip_idx(lineage._scan(self.p.conn, self.pid))
        for sid in (self.ids[18], self.ids[2]):
            self.assertEqual(after[sid], before[sid])                                 # not outdated (picture, motion)

    def test_a_picture_already_outdated_stays_outdated(self):
        approve_picture(self.p, self.pid, self.ids[18])
        d = self.data_of(self.ids[18])
        d["image_prompt"] = "đã sửa sau khi duyệt"                                   # outdated BEFORE the insert
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), self.ids[18]))
        self.p.conn.commit()
        self.assertTrue(lineage._scan(self.p.conn, self.pid)[self.ids[18]]["image_stale"])
        self.insert(6)                                                                # its continuity_from 15->16 changes too
        self.assertTrue(lineage._scan(self.p.conn, self.pid)[self.ids[18]]["image_stale"])

    def test_another_edit_during_the_insert_is_not_swallowed(self):
        other = self.p.create_project("khác")
        osid = self.p.create_scene(other, 1, "x")
        self.p.conn.commit()
        real = lineage.place_key

        def edit_elsewhere(conn, project_id, data):                                   # a hand edit landing inside the transaction
            conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "sửa tay"}), osid))
            return real(conn, project_id, data)
        with mock.patch.object(lineage, "place_key", edit_elsewhere):
            self.insert(6)
        states = {r["state"] for r in self.p.conn.execute("SELECT state FROM change_events WHERE scene_id=?", (osid,))}
        self.assertEqual(states, {"pending"})

    def test_storyboard_anchor_is_said(self):
        self.insert(6, dict(NEW, size="WS"))                                          # wider than the MS shots of scene 3
        new_id = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        self.assertEqual(scene_storyboard.group_of(self.p.conn, self.pid, new_id)["anchor"]["id"], new_id)
        msg = self.p.conn.execute("SELECT message FROM diag_events WHERE code='insert_scene' ORDER BY id DESC").fetchone()["message"]
        self.assertIn("ẢNH NEO", msg)
        self.assertIn("trước là shot 3", msg)                                # fixture: shot 3 is story scene 3 too (MS, first)

    def test_storyboard_anchor_kept_when_not_wider(self):
        self.insert(6)
        new_id = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["id"]
        self.assertEqual(scene_storyboard.group_of(self.p.conn, self.pid, new_id)["anchor"]["id"], self.ids[3])   # MS tie → lowest idx

    def test_sequence_can_be_set_for_the_new_shot(self):
        self.insert(6, dict(NEW, sequence=9))
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=7", (self.pid,)).fetchone()["data"])
        self.assertEqual(d["sequence"], 9)

    def test_trash_labels_follow(self):
        folder = os.path.join(self.data, str(self.pid), "trash", "images")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "trash.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{"file": "job_1__x.png", "original": "images/job_1.png", "scene_idx": 10},
                       {"file": "job_2__x.png", "original": "images/job_2.png", "scene_idx": 4}], f)
        self.insert(6)
        with open(path, encoding="utf-8") as f:
            self.assertEqual([e["scene_idx"] for e in json.load(f)], [11, 4])
        self.assertEqual([n for n in os.listdir(folder) if n.endswith(".tmp")], [])

    def test_data_dir_is_needed(self):
        with self.assertRaises(ValueError):
            llm_io.insert_scene_after(self.p, self.pid, 6, dict(NEW))


if __name__ == "__main__":
    unittest.main()
