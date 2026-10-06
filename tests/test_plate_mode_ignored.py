"""S14.44 (người dùng 06/10): S14.9 removed the green-screen plates. `plate_mode` of OLD rows is still read where it only keeps their
hash / grouping; no path may switch the green-screen behaviour (or another reference route) back on from it — not even when the
Director (Claude) writes it into a NEW project's shot JSON: it is not stored, and said once (diag `plate_mode_ignored`)."""
import json
import unittest

from core import lineage, seedance_refs, shots
from core.runner import build_image_prompt
from tests.test_v3 import kenta_project


def _shot(**kw):
    s = {"size": "MS", "angle": "eye", "camera_move": "static", "role": "dialogue", "duration_s": 3.0, "action": "Kelly nhìn Kenta",
         "image_prompt": "Kelly faces Kenta", "characters": ["KELLY"], "dialogue": []}
    s.update(kw)
    return s


def _plan(**shot_kw):
    return [{"idx": 1, "characters": ["KELLY"], "shots": [_shot(**shot_kw), _shot(size="CU", **shot_kw)]}]


class NewProjectDropsPlateMode(unittest.TestCase):
    def _store(self, **shot_kw):
        p, pid = kenta_project()
        shots.store_plan(p, pid, _plan(**shot_kw), force=True)
        return p, pid, [r["data"] for r in shots.shots_of(p, pid)]

    def _diags(self, p, pid):
        return p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='plate_mode_ignored' AND project_id=?",
                              (pid,)).fetchone()[0]

    def test_model_written_plate_mode_is_not_stored_and_said_once(self):
        p, pid, rows = self._store(plate_mode="green")
        self.assertTrue(rows)
        for d in rows:
            self.assertNotIn("plate_mode", d)
        self.assertEqual(self._diags(p, pid), 1, "said once per stored plan, not per shot and not silently")

    def test_scene_level_plate_mode_is_dropped_too(self):
        p, pid = kenta_project()
        plan = _plan()
        plan[0]["plate_mode"] = "green"
        shots.store_plan(p, pid, plan, force=True)
        for r in shots.shots_of(p, pid):
            self.assertNotIn("plate_mode", r["data"])
        self.assertEqual(self._diags(p, pid), 1)

    def test_prompts_and_refs_match_a_shot_without_the_field(self):
        p1, pid1, with_mode = self._store(plate_mode="green")
        p2, pid2, without = self._store()
        self.assertEqual(with_mode, without)
        self.assertEqual(self._diags(p2, pid2), 0, "no plate_mode, nothing to say")
        for a, b in zip(with_mode, without):
            self.assertEqual(build_image_prompt(p1.conn, pid1, a), build_image_prompt(p2.conn, pid2, b))
            self.assertEqual(seedance_refs.eligible(a), seedance_refs.eligible(b))

    def test_replace_from_drops_it_as_well(self):
        p, pid = kenta_project()
        shots.store_plan(p, pid, _plan(), force=True)
        shots.replace_from(p, pid, _plan(plate_mode="green"), 1)
        for r in shots.shots_of(p, pid):
            self.assertNotIn("plate_mode", r["data"])
        self.assertEqual(self._diags(p, pid), 1)


class OldRowsKeepHashNoGreenBehaviour(unittest.TestCase):
    OLD = {"story_scene": 1, "shot_no": 1, "sequence": 1, "size": "MS", "angle": "eye", "image_prompt": "x", "characters": [],
           "plate_mode": "green", "plate_spot": "tower"}

    def test_hash_of_an_old_row_is_unchanged(self):
        # pinned before S14.44: plate_mode stays in the image fingerprint so old pictures do not turn "cũ"
        self.assertIn("plate_mode", lineage.IMAGE_SHOT_KEYS)
        self.assertEqual(lineage.image_spec_hash(self.OLD, [], "9:16"), "9fda781e0528e42c")
        self.assertNotEqual(lineage.image_spec_hash(self.OLD, [], "9:16"),
                            lineage.image_spec_hash({k: v for k, v in self.OLD.items() if k != "plate_mode"}, [], "9:16"))

    def test_group_key_ignores_plate_mode(self):
        plain = {k: v for k, v in self.OLD.items() if k != "plate_mode"}
        self.assertEqual(shots._group_key(self.OLD), shots._group_key(plain))

    def test_green_plate_mode_does_not_change_the_reference_route(self):
        plain = {k: v for k, v in self.OLD.items() if k != "plate_mode"}
        self.assertEqual(seedance_refs.eligible(self.OLD), seedance_refs.eligible(plain))
        self.assertTrue(seedance_refs.eligible(self.OLD), "a green row is no longer pushed off the reference route")

    def test_old_green_row_in_groups_is_said_once(self):
        import os
        os.environ["FEATURE_SEEDANCE_REF_GROUPS"] = "1"
        self.addCleanup(os.environ.pop, "FEATURE_SEEDANCE_REF_GROUPS", None)
        p, pid = kenta_project()
        shots.store_plan(p, pid, _plan(), force=True)
        for r in shots.shots_of(p, pid):
            d = dict(r["data"], plate_mode="green")
            p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d, ensure_ascii=False), r["id"]))
        p.conn.commit()
        seedance_refs.groups(p.conn, pid)
        seedance_refs.groups(p.conn, pid)
        n = p.conn.execute("SELECT COALESCE(SUM(count),0) FROM diag_events WHERE code='plate_mode_ignored' AND project_id=?",
                           (pid,)).fetchone()[0]
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
