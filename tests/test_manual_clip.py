"""GĐ-A3: a clip uploaded by hand never overwrites a (paid) generated clip without keeping it, and never writes outside the folder."""
import os
import tempfile
import unittest

from core import final_cut, trash


class ManualClipTest(unittest.TestCase):
    def test_the_old_clip_goes_to_the_trash_and_folders_in_the_name_are_ignored(self):
        data = tempfile.mkdtemp()
        folder = os.path.dirname(final_cut.clip_path(data, 7, 0))
        os.makedirs(folder)
        with open(os.path.join(folder, "01.mp4"), "wb") as f:
            f.write(b"PAID")
        dest = final_cut.save_manual_clip(data, 7, "..\\\\..\\\\evil/01.mp4", b"MINE")
        self.assertEqual(dest, os.path.join(folder, "01.mp4"))
        self.assertEqual(open(dest, "rb").read(), b"MINE")
        kept = os.listdir(trash.trash_dir(data, 7, "videos"))
        self.assertTrue(any(n.startswith("01__") for n in kept))
        with self.assertRaises(ValueError):
            final_cut.save_manual_clip(data, 7, "notes.txt", b"x")


if __name__ == "__main__":
    unittest.main()
