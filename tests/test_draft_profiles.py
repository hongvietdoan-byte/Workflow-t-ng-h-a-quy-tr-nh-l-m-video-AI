"""T1 — tools/draft_profiles.py: free checks (near-duplicate pictures, roles, other looks, missing profiles) and Claude drafts that are
never approved and never write an age under 18."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import draft_profiles  # noqa: E402

from core import assets, llm_io  # noqa: E402
from core.db import connect  # noqa: E402


def png(color, size=(64, 128), dot=None):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, color)
    if dot:
        ImageDraw.Draw(im).rectangle(dot, fill=(255, 255, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class DraftProfileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = mock.patch.dict(os.environ, {"ASSET_DIR": self.dir})
        self.env.start()
        self.conn = connect()
        self.kelly = assets.create(self.conn, "FF", "character", "KELLY", "sprinter")
        assets.add_image(self.conn, self.kelly, "a.png", png((200, 40, 40), dot=(10, 10, 30, 60)))
        assets.add_image(self.conn, self.kelly, "b.png", png((201, 41, 40), dot=(10, 10, 30, 60)))      # the same picture again
        assets.add_image(self.conn, self.kelly, "c.png", png((20, 40, 200), size=(128, 64), dot=(70, 5, 120, 20)))
        self.kenta = assets.create(self.conn, "FF", "character", "KENTA", "swordsman")
        self.ob55 = assets.create(self.conn, "FF", "character", "KENTA OB55", "rework")
        self.conn.execute("UPDATE asset_images SET status='approved'")
        self.conn.execute("UPDATE asset_images SET role=NULL")                     # pictures synced before roles existed
        self.conn.commit()

    def tearDown(self):
        self.env.stop()

    def test_report_finds_duplicates_other_looks_and_missing_profiles(self):
        rep = draft_profiles.report(self.conn, "FF")
        self.assertEqual([d["entry"] for d in rep["duplicates"]], ["KELLY"])
        self.assertEqual([(lk["entry"]["name"], lk["base"]["name"]) for lk in rep["looks"]], [("KENTA OB55", "KENTA")])
        self.assertEqual({c["name"] for c in rep["missing"]}, {"KELLY", "KENTA", "KENTA OB55"})
        guesses = {u["image"]["id"]: u["guess"] for u in rep["unlabelled"]}
        self.assertIn("full_body", guesses.values())                                 # 64x128: a standing figure

    def test_apply_holds_duplicates_without_deleting_and_writes_roles(self):
        rep = draft_profiles.report(self.conn, "FF")
        res = draft_profiles.apply_free(self.conn, rep)
        self.assertEqual(res["held"], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM asset_images WHERE asset_id=?", (self.kelly,)).fetchone()[0], 3)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM asset_images WHERE status='pending'").fetchone()[0], 1)
        self.assertGreaterEqual(res["roles"], 1)

    def test_a_draft_is_saved_unapproved_and_an_age_under_18_is_refused(self):
        class Client:
            def __init__(self):
                self.answers = [json.dumps({"identity": "Kelly — 17-year-old sprinter", "must_keep": "bob", "forbidden": "ponytail"}),
                                json.dumps({"identity": "Kelly — young sprinter, not yet 20", "must_keep": "bob", "may_change": "pose",
                                            "forbidden": "ponytail", "height_m": 1.7, "build": "slim"})]
                self.calls = 0

            def complete(self, prompt, images=()):
                self.calls += 1
                self.last_prompt = prompt
                from core.llm_runner import LlmReply
                return LlmReply(self.answers.pop(0), 10, 10)

        client = Client()
        entry = assets.get(self.conn, self.kelly)
        out = draft_profiles.draft(self.conn, [entry], client)
        self.assertEqual(client.calls, 2)                                            # the answer with "17-year-old" was sent back
        self.assertIn("not yet 20", client.last_prompt + json.dumps(out))
        prof = assets.get_profile(self.conn, self.kelly)
        self.assertFalse(prof["approved"])
        self.assertEqual(prof["height_m"], 1.7)
        self.assertNotRegex(prof["identity"], r"1[0-7][- ]year")


if __name__ == "__main__":
    unittest.main()
