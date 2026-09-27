"""Trial #8 (2026-09-27): 12/33 location-pack frames came out as a rectangle pasted on the 3D plate — the image model drew a whole place
(a Big-Ben-like tower, sky, paving) instead of the green backdrop. Causes: place words left in the green prompt, the storyboard anchor
sent as the COMPOSITED picture with "same place" in the story text, and no check that the picture had any green before keying it."""
import os
import tempfile
import unittest

from core import composite, location_pack


def picture(path, top_green: bool):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (90, 160), (0, 255, 0) if top_green else (90, 140, 210))
    ImageDraw.Draw(im).rectangle([25, 30, 65, 160], fill=(200, 180, 40))            # the character
    im.save(path)
    return path


class GreenGuardTests(unittest.TestCase):
    def test_green_share_tells_a_green_picture_from_a_drawn_place(self):
        d = tempfile.mkdtemp()
        self.assertGreater(composite.green_share(picture(os.path.join(d, "g.png"), True)), composite.MIN_GREEN_BORDER)
        self.assertLess(composite.green_share(picture(os.path.join(d, "s.png"), False)), composite.MIN_GREEN_BORDER)

    def test_place_clauses_leave_the_green_prompt_but_the_people_stay(self):
        text = ("wide shot of three characters running side by side across the stone plaza at the foot of the clock tower on Military "
                "Island, KENTA on the left with his blue scarf, the stone clock tower and low parapet walls behind, clear sky, "
                "close-up on KELLY at night in a shadowed corner of Đảo Quân Sự military island, bright daylight")
        out = location_pack.place_free(text)
        for gone in ("tower", "plaza", "parapet", "island", "sky"):
            self.assertNotIn(gone, out.lower())
        for kept in ("three characters running side by side", "KENTA on the left with his blue scarf", "close-up on KELLY",
                     "bright daylight"):
            self.assertIn(kept, out)

    def test_a_waist_up_character_keeps_its_cut_edge_on_the_frame_bottom(self):
        """#8 S2·4: the head was drawn lower than the camera box said — lining the head up lifted the picture and the torso floated."""
        import numpy as np
        alpha = np.zeros((160, 90))
        alpha[60:, 20:70] = 1.0                                     # head low, body cut by the bottom of the picture
        place = composite.placement(alpha, (0.3, 0.05, 0.7, 1.2), (90, 160))
        self.assertTrue(place["cut"])
        self.assertGreaterEqual(place["dy"] + 160 * place["scale"], 160 - 0.5)

    def test_the_storyboard_anchor_is_the_green_picture_in_green_mode(self):
        import json
        from core import scene_storyboard
        from core.db import connect
        from core.pipeline import Pipeline
        p = Pipeline(connect())
        pid = p.create_project("g", aspect="9:16")
        sid = p.create_scene(pid, 1, "s")
        p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"story_scene": 1, "shot_no": 1}), sid))
        jid = p.create_job(sid, "image_gen")
        p.conn.execute("UPDATE jobs SET state='approved' WHERE id=?", (jid,))
        p.conn.commit()
        data = tempfile.mkdtemp()
        os.makedirs(os.path.join(data, str(pid), "images"))
        for name in (f"job_{jid}.png", f"job_{jid}_green.png"):
            open(os.path.join(data, str(pid), "images", name), "wb").close()
        self.assertTrue(scene_storyboard.anchor_picture(p.conn, data, pid, sid, green=True).endswith("_green.png"))
        self.assertTrue(scene_storyboard.anchor_picture(p.conn, data, pid, sid).endswith(f"job_{jid}.png"))


if __name__ == "__main__":
    unittest.main()
