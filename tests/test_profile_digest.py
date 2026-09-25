"""Kế hoạch V4 4.4: short forms of an approved profile (lock_short ≤ 200, lock_medium ≤ 500) made by code, checked (length, no age
under 18, no word that is only FORBIDDEN), renewed when the profile changes; the profile's change log is kept."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import assets, profile_digest as pd
from core.db import connect
from core.pipeline import Pipeline

# the approved library profiles after the age fix of 2026-09-25 (assets #23, #24)
KELLY = {"identity": "Kelly — young female sprinter, not yet 20: slim athletic young woman, dark brown chin-length bob with straight blunt "
                     "bangs, black choker, bright yellow track suit with grey star-print stripes",
         "must_keep": "dark brown chin-length bob with straight blunt bangs (hair down, never tied), black choker, white crop top under a "
                      "bright yellow zip-up track jacket with a high collar, grey sleeve stripes with small black stars and thin black edge "
                      "lines, matching bright yellow track pants with a black side stripe, white sneakers, youthful face with light makeup",
         "may_change": "pose, expression, camera angle, lighting, the weapon she holds (usually a sniper rifle)",
         "forbidden": "tying the hair up or into a ponytail, changing hair length or color, changing the yellow track suit to another color "
                      "or into shorts or another jacket, removing the choker, looking older than 20 or like a child",
         "build": "slim athletic sprinter, long legs, 54 kg", "height_m": 1.7, "approved": True}
KENTA = {"identity": "Kenta (OB55 rework) — 38-year-old swordsman: tall strong man, messy black hair in a high ponytail tied with a navy "
                     "band and a broad silver-white streak through the front of the hair, stern face with stubble, blue scarf",
         "must_keep": "messy black high ponytail tied with a navy band, broad silver-white streak through the front of the hair and the "
                      "tail, stern angular face with light stubble and a faint diagonal scar, blue scarf wrapped around the neck, blue "
                      "short-sleeved open coat with a torn long hem and lavender straps with silver rings on the chest, black fitted top, "
                      "glowing purple-cyan star emblem on the LEFT shoulder, RIGHT arm: black sleeve, forearm wrapped in a white-grey "
                      "bandage, black fingerless glove; LEFT arm: bare upper arm with a brown leather armband and red wound marks, "
                      "forearm in a black armored gauntlet with silver plates and a full black glove; brown leather belts, black trousers "
                      "with knee guards, black open-toe sandals",
         "forbidden": "the old pre-OB55 look (purple armor, purple cape with white flame pattern, high black collar), boots instead of "
                      "sandals, swapping the gauntlet and the bandage to the other arm",
         "height_m": 1.85, "approved": True}


class DigestTests(unittest.TestCase):
    def test_the_short_forms_fit_and_pass_their_checks(self):
        for prof in (KELLY, KENTA):
            d = pd.build(prof)
            self.assertLessEqual(len(d["lock_short"]), pd.SHORT)
            self.assertLessEqual(len(d["lock_medium"]), pd.MEDIUM)
            self.assertEqual(pd.check(prof, d), [])
            self.assertTrue(d["lock_medium"].endswith(f"about {prof['height_m']:g} m tall"))
        kelly = pd.build(KELLY)
        self.assertNotIn("Kelly —", kelly["lock_short"])                 # the "Name — " head goes: the prompt names the person itself
        self.assertIn("chin-length bob", kelly["lock_short"])
        self.assertIn("never tied", kelly["lock_medium"])

    def test_the_emphasised_detail_is_kept_first(self):
        medium = pd.build(KENTA)["lock_medium"]
        self.assertIn("LEFT shoulder", medium)                            # the person wrote LEFT / RIGHT because a model got it wrong
        self.assertIn("RIGHT arm", medium)

    def test_a_forbidden_only_word_or_a_minor_age_is_caught(self):
        self.assertIn("ponytail", pd.forbidden_only_words(KELLY))
        self.assertNotIn("ponytail", pd.forbidden_only_words(KENTA))      # Kenta's ponytail is what must be KEPT
        self.assertNotIn("white", pd.forbidden_only_words(KENTA))         # "silver-white" in the kept look
        bad = {"lock_short": "Kelly with a high ponytail, 17-year-old", "lock_medium": "x" * 501}
        problems = " | ".join(pd.check(KELLY, bad))
        self.assertIn("ponytail", problems)
        self.assertIn("tuổi dưới 18", problems)
        self.assertIn("501 > 500", problems)
        young = dict(KELLY, identity="Kelly — 17-year-old sprinter: slim athletic young woman")
        self.assertNotIn("17", pd.build(young)["lock_short"])             # the age never reaches the short form

    def test_a_hand_written_digest_is_kept_until_the_profile_changes(self):
        manual = {"hash": pd.source_hash(KELLY), "lock_short": "sprinter, dark brown bob, yellow track suit", "lock_medium": "same",
                  "source": "manual"}
        self.assertEqual(pd.current(dict(KELLY, digest=manual)), manual)
        changed = dict(KELLY, must_keep=KELLY["must_keep"] + ", red wristband", digest=manual)
        self.assertEqual(pd.current(changed)["source"], "code")


class StoredDigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"ASSET_DIR": os.path.join(self.tmp, "assets")})
        env.start()
        self.addCleanup(env.stop)
        self.p = Pipeline(connect(os.path.join(self.tmp, "m.sqlite")))
        self.pid = self.p.create_project("digest")
        self.aid = assets.create(self.p.conn, "FF", "character", "KELLY", "", "", None, "x")
        from tests.test_costume import picture
        assets.add_image(self.p.conn, self.aid, "kelly.png", picture(550, 800, 30))    # a library entry is linked by its pictures
        assets.attach(self.p.conn, self.pid, self.aid)
        self.p.conn.execute("INSERT INTO characters (project_id, name, description) VALUES (?, 'Kelly', '')", (self.pid,))
        self.p.conn.commit()

    def test_set_profile_keeps_the_change_log(self):
        assets.set_profile(self.p.conn, self.aid, KELLY, approved=True, reason="bỏ số tuổi dưới 18")
        saved = assets.set_profile(self.p.conn, self.aid, dict(KELLY, build="slim"), approved=True)
        self.assertEqual([h["why"] for h in saved["history"]], ["bỏ số tuổi dưới 18"])

    def test_the_digest_is_stored_and_renewed_when_the_profile_changes(self):
        assets.set_profile(self.p.conn, self.aid, KELLY, approved=True)
        short = pd.for_character(self.p.conn, self.pid, "Kelly", "lock_short")
        self.assertIn("chin-length bob", short)
        self.assertEqual(assets.get_profile(self.p.conn, self.aid)["digest"]["lock_short"], short)
        assets.set_profile(self.p.conn, self.aid, dict(KELLY, identity="Kelly — sprinter: tall athletic young woman, red cap"),
                           approved=True)
        self.assertIn("red cap", pd.for_character(self.p.conn, self.pid, "Kelly", "lock_short"))

    def test_a_draft_profile_gives_no_digest(self):
        assets.set_profile(self.p.conn, self.aid, KELLY, approved=False)
        self.assertIsNone(pd.for_character(self.p.conn, self.pid, "Kelly"))

    def test_the_picture_prompt_uses_the_medium_form_only_when_the_feature_is_on(self):
        from core.runner import lock_note
        assets.set_profile(self.p.conn, self.aid, KELLY, approved=True)
        with mock.patch.dict(os.environ, {"FEATURE_PROFILE_DIGEST": "0"}):
            full = lock_note(self.p.conn, self.pid, ["Kelly"])
        with mock.patch.dict(os.environ, {"FEATURE_PROFILE_DIGEST": "1"}):
            short = lock_note(self.p.conn, self.pid, ["Kelly"])
            from core import prompts
            block = prompts.short_lock_block(self.p.conn, self.pid)
        self.assertIn("never tying the hair", full)                     # the full Lock names what is forbidden
        self.assertNotIn("ponytail", short)                             # the short form never does
        self.assertLess(len(short), len(full))
        self.assertIn("Nhận diện ngắn", block)


if __name__ == "__main__":
    unittest.main()
