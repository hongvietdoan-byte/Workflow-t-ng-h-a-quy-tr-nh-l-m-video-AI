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

    def test_gunfire_is_not_a_melee_blow(self):
        # rà video #27 (12/10, lỗi code #2): "takes hits" / "is hit by a stray bullet" got the punch sentence (S18, S19/20)
        self.assertEqual(motion_physics.kind("Kelly fires continuously at RED TENTACLE, he takes hits"), "shoot")
        self.assertEqual(motion_physics.kind("Kelly xả súng vào Xúc Tu Đỏ"), "shoot")
        self.assertNotEqual(motion_physics.kind("the glue wall is hit by a stray bullet"), "strike")
        self.assertNotIn("blow", motion_physics.sentence("the glue wall is hit by a stray bullet"))
        self.assertNotIn("blow", motion_physics.sentence("Kelly fires continuously, he takes hits"))
        self.assertEqual(motion_physics.kind("he punches him"), "strike")
        self.assertEqual(motion_physics.kind("Kelly đấm Maxim"), "strike")
        self.assertIsNone(motion_physics.kind("Free Fire in-game, Kelly smiles"))         # the game's name is not gunfire
        self.assertIsNone(motion_physics.kind("nước bắn tung tóe quanh chân Kelly"))         # splashing water is not shooting

    def test_fire_and_glance_are_not_gunfire(self):
        # rà 12/10: a bare 'fire(s)' / 'shoots' gave the gun-recoil sentence to a campfire clip
        for text in ("Kelly stares at the fire", "the bonfire fires up sparks", "he shoots a glance at Kelly"):
            self.assertNotEqual(motion_physics.kind(text), "shoot", text)
        self.assertEqual(motion_physics.kind("Kelly opens fire on the enemy"), "shoot")
        self.assertEqual(motion_physics.kind("Maxim shoots at the tower"), "shoot")

    def test_a_reference_shot_prompt_carries_it_once(self):
        text = seedance_refs.shot_motion({"size": "MS", "angle": "eye", "camera_move": "static", "action": "Kenta runs to the tower"})
        self.assertIn("no sliding", text)
        self.assertEqual(text.count("no sliding"), 1)
        still = seedance_refs.shot_motion({"size": "CU", "angle": "eye", "action": "Kelly looks at Maxim"})
        self.assertNotIn("weight", still)


if __name__ == "__main__":
    unittest.main()
