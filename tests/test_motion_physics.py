"""S4.4 (after #8: feet sliding, bodies moving like cut-outs): one body-physics sentence per kind of action in the video prompt."""
import unittest

from core import motion_physics, seedance_refs


class MotionPhysicsTests(unittest.TestCase):
    def test_the_kind_of_action_picks_one_sentence(self):
        self.assertEqual(motion_physics.kind("Kenta sprints across the plaza"), "run")
        self.assertEqual(motion_physics.kind("Kelly chạy tới chỗ Maxim"), "run")
        self.assertEqual(motion_physics.kind("Maxim throws a punch while running"), "strike")     # the first kind in the order wins
        self.assertEqual(motion_physics.kind("Kelly ngồi xuống ghế"), "sit_stand")
        self.assertEqual(motion_physics.kind("She smiles and says hello"), None)
        self.assertEqual(motion_physics.sentence("He smiles"), "")

    def test_a_reference_shot_prompt_carries_it_once(self):
        text = seedance_refs.shot_motion({"size": "MS", "angle": "eye", "camera_move": "static", "action": "Kenta runs to the tower"})
        self.assertIn("no sliding", text)
        self.assertEqual(text.count("no sliding"), 1)
        still = seedance_refs.shot_motion({"size": "CU", "angle": "eye", "action": "Kelly looks at Maxim"})
        self.assertNotIn("weight", still)


if __name__ == "__main__":
    unittest.main()
