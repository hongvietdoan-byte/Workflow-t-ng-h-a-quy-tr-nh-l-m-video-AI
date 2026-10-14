"""Cờ motion_prose (thử D6 #28/#29 14/10): bản CODE ghép phần chuyển động của prompt video viết như B (Claude) — diễn xuất thành câu kể
thay vì nhãn rời "Acting — face: …; eyes: …", máy "track" nói rõ chiều so với nhân vật khi chữ shot cho biết (không biết → giữ nguyên).
Dữ liệu dựng từ scenes.data thật #28 (scene 292 shot 1 chạy cầu thang về phía máy, 294 núp quay lưng, 295 chạy sang trái máy sau lưng),
đọc chỉ-đọc từ D:\\AI-Video-Pipeline\\data\\manifest.sqlite 14/10."""
import os
import unittest

from core import seedance_refs as sr

# scene 292 (#28 shot 1) — đúng các trường thật
RUN_TOWARD = {"size": "WS", "angle": "eye", "camera_move": "track", "characters": ["KELLY"],
              "action": "Kelly chạy nước rút từ chân cầu thang lên phía máy quay, tay vung mạnh, mắt nhìn thẳng cảnh giác.",
              "motion_en": {"action": "KELLY sprints from the foot of the stairs toward the camera, arms pumping hard, eyes locked "
                                      "straight ahead, alert."},
              "performance": {"intensity": 3, "face": "tense focus, jaw set", "eyes": "fixed forward, scanning ahead",
                              "body": "full sprint, arms pumping, weight driving forward",
                              "timing": "constant sprint throughout the shot"},
              "blocking": "Kelly center-frame, small in the distance at the bottom of a stone outdoor stairway, facing the camera, "
                          "already mid-sprint, running up the stairs toward the camera.",
              "shot": "wide shot, eye angle, track"}
# scene 295 (#28 shot 4) — máy game sau lưng, chạy sang trái
RUN_BEHIND = {"size": "GAME_TPS", "angle": "high", "camera_move": "track", "characters": ["KELLY"],
              "action": "Kelly chạy nhanh 5 bước sang trái rồi ném bom keo thứ hai.",
              "motion_en": {"action": "KELLY dashes 5 steps to the left and throws a second glue bomb."},
              "performance": {"intensity": 3, "face": "focused, determined", "eyes": "forward on the new spot",
                              "body": "running then throwing in one continuous motion", "timing": "quick continuous movement, no pause"},
              "blocking": "Kelly frame-right, just pushing off from behind the first wall, beginning to run left, camera behind her.",
              "shot": "third-person game camera behind the character, slightly above the shoulder, high angle, track"}
# scene 294 (#28 shot 3) — quay lưng, máy đứng yên
HIDE_BACK = {"size": "GAME_TPS", "angle": "high", "camera_move": "static", "characters": ["KELLY"],
             "action": "Kelly núp sát bên trái tường keo thứ nhất, ló đầu ra quan sát xung quanh tìm địch.",
             "motion_en": {"action": "KELLY crouches tight against the left side of the first glue wall, peeking out to scan the "
                                     "surroundings for enemies."},
             "performance": {"intensity": 3, "face": "wary, eyes narrowed", "eyes": "darting side to side, scanning for threat",
                             "body": "crouched low, one hand braced on the wall",
                             "timing": "holds still, head leans out then pulls back slightly"},
             "blocking": "Kelly crouched at the left edge of the white glue wall, seen from behind and above over her shoulder.",
             "shot": "third-person game camera behind the character, slightly above the shoulder, high angle, static"}


class _Flag(unittest.TestCase):
    def flag(self, value: bool, name: str = "MOTION_PROSE"):
        key = "FEATURE_" + name
        old = os.environ.get(key)
        os.environ[key] = "1" if value else "0"
        self.addCleanup(lambda: os.environ.__setitem__(key, old) if old is not None else os.environ.pop(key, None))


class MotionProseOn(_Flag):
    def setUp(self):
        self.flag(True)

    def test_acting_is_a_told_sentence_not_labels(self):
        text = sr.shot_motion(RUN_TOWARD)
        self.assertNotIn("Acting —", text)
        self.assertNotIn("face:", text)
        self.assertNotIn("eyes:", text)
        self.assertIn("KELLY acts it out — full sprint, arms pumping, weight driving forward, constant sprint throughout the shot; "
                      "the face shows tense focus, jaw set, eyes fixed forward, scanning ahead.", text)

    def test_track_toward_camera_says_the_camera_backs_up(self):
        text = sr.shot_motion(RUN_TOWARD)
        self.assertIn("camera tracks backward ahead of KELLY, holding the same distance as KELLY comes toward it", text)
        self.assertNotIn("camera track;", text)

    def test_track_behind_says_the_camera_follows(self):
        text = sr.shot_motion(RUN_BEHIND)
        self.assertIn("camera follows behind KELLY, moving along with KELLY at the same distance", text)

    def test_back_view_keeps_face_out(self):
        self.flag(True, "BACK_VIEW_GUARD")              # bật ở máy chính (#28 job 933 có câu 'stays with the back to the camera')
        text = sr.shot_motion(HIDE_BACK)
        self.assertIn("KELLY acts it out — crouched low, one hand braced on the wall, holds still, head leans out then pulls back "
                      "slightly.", text)
        self.assertNotIn("face shows", text)
        self.assertIn("camera static", text)             # not a track: the camera words stay as they were

    def test_unknown_direction_keeps_track(self):
        d = dict(RUN_TOWARD, blocking="Kelly center-frame on the stairs.", motion_en={"action": "KELLY sprints up the stairs."},
                 action="Kelly chạy lên cầu thang.")
        self.assertIn("camera track;", sr.shot_motion(d))   # no toward / behind words: never guess a direction

    def test_track_without_travel_keeps_track(self):
        d = dict(HIDE_BACK, camera_move="track")
        self.assertIn("camera track;", sr.shot_motion(d))   # nobody runs or walks: "track" is not a follow of a runner


class MotionProseOff(_Flag):
    def test_off_is_the_old_text(self):
        self.flag(False)
        text = sr.shot_motion(RUN_TOWARD)
        self.assertIn("Acting — face: tense focus, jaw set; eyes: fixed forward, scanning ahead;", text)
        self.assertIn("camera track;", text)


if __name__ == "__main__":
    unittest.main()
