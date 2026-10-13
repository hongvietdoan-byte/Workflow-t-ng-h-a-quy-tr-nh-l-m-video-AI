"""Lỗi hệ thống 1 sau #27 tập 1 (13/10, docs/handoff/P27_TAP1_TONG_KET_2026-10-13.md mục 6): ảnh vẽ không bám render 3D (shot 17/21).

Ca thật (manifest #27, đọc chỉ-đọc 13/10): job 893 (shot 17, BỊ TỪ CHỐI) gửi render ở ảnh 7/8, prompt Director có câu "Clock tower plaza,
low retaining walls, red-roof houses in far background" → ảnh tháp xa giữa khung + cầu thang + nhà mái đỏ; render cho thấy chân tháp sát
nhân vật, cắt mép trên. Job 910/911 (ĐÃ DUYỆT) là bản người dùng tự viết tay câu nền đúng. Cờ `plate_anchored_image`:
  (a) chữ tả nền của Đạo diễn bị bỏ (VÀNG), câu nền sinh từ plate + mốc 3D thay vào;
  (b) render là ảnh 1 + câu "giữ đúng nền ảnh 1";
  (c) kiểm sau vẽ bằng code: hai tín hiệu lệch → ĐỎ, một → VÀNG, không đo được → VÀNG (không im lặng).
Kiểm sau vẽ trên ảnh thật (tests/fixtures/p27_plate_anchor): tests/test_plate_layout_qc.py."""
import os
from unittest import mock

import pytest
from PIL import Image

from core import plate_anchor as pa
from core import plate_layout_qc as qc

ON = {"FEATURE_PLATE_ANCHORED_IMAGE": "1", "FEATURE_PLACE_RENDER_REFS": "1"}

# câu Director của job 893 (rút gọn phần trang phục; giữ nguyên các câu nền / ánh sáng)
JOB_893 = ("Wide shot, high angle, 9:16 vertical frame, static camera. Foreground frame-left: Kelly, dark brown chin-length bob, crouched "
           "low behind a TALL Gloowall OB55 glue wall, about 1.7 m tall, holding her SKORP submachine gun. Background frame-right, far "
           "distance near the stone plaza of the Clock Tower, matching the actual 3D map background: four enemy characters in a chaotic "
           "firefight — small in frame, mid-action poses. Clock tower plaza, low retaining walls, red-roof houses in far background. "
           "Bright natural sunlight from the side, warm daylight tone, ~5600K, clear blue sky with a few white clouds.")
# shot 21 (scene 289): câu nền dính sau câu có người bằng dấu phẩy, rồi các vế ';'
SHOT_21 = ("Kelly firing her SKORP; the Gloowall OB55 skin glue wall she just burst out from standing at frame-left behind her, BACKGROUND "
           "= EXACTLY the 3D render picture of Tháp Đồng Hồ: the base of the tall stone Clock Tower stands CLOSE by; around it a wide, "
           "flat, empty grey stone plaza; NO staircase, NO red-roof houses, NO low walls in the middle distance - keep the tower's "
           "position; bright daylight, stylized proportions, everything in focus")
# plate thật của shot 17 (data/projects/27/plates/index.json "285", rút gọn) + model3d #263
REC_285 = {"camera": {"horizon_y": 0.115}, "clearance": {"background_m": 9.5, "background_top_m": 3.9},
           "subject_box": [0.187, 0.1476, 0.4976, 0.6268], "place": "Tháp Đồng Hồ",
           "camera_plan": {"location": [-220.453, 119.786, 11.153], "look_at": [-219.868, 121.762, 9.963], "lens": 24,
                           "subject": {"location": [-220.101, 121.831, 9.376], "height_m": 1.7}}}
ENTRY_263 = {"anchor": [-217.07, 132.04, 30.0]}


# ---- (a) chữ nền của Đạo diễn ---------------------------------------------------------------------------------------------------
def test_job_893_scenery_sentence_is_removed_people_props_light_kept():
    out, removed = pa.strip_scenery(JOB_893, ["KELLY"])
    assert removed == ["Clock tower plaza, low retaining walls, red-roof houses in far background"]
    assert "red-roof" not in out and "retaining walls" not in out
    for kept in ("behind a TALL Gloowall OB55 glue wall, about 1.7 m tall", "four enemy characters", "Bright natural sunlight",
                 "Wide shot, high angle"):
        assert kept in out
    assert "  " not in out and ". ." not in out


def test_shot_21_background_glued_after_a_person_clause_is_cut_and_punctuation_kept():
    out, removed = pa.strip_scenery(SHOT_21, ["KELLY", "XÚC TU ĐỎ"])
    assert len(removed) == 3 and removed[0].startswith("BACKGROUND = EXACTLY")
    assert "Clock Tower" not in out and "staircase" not in out
    assert "standing at frame-left behind her; bright daylight" in out


def test_kld22_far_scenery_phrase_inside_a_person_sentence_is_cut():
    """#22 KLD-6: 'dancing … in front of a clock tower and low red-roof house' — cụm nền xa bỏ, chỗ đứng (on the plaza) giữ."""
    out, removed = pa.strip_scenery("two stylized young characters dancing side by side on a flat stone plaza in front of a clock tower "
                                    "and low red-roof house, bright warm midday sunlight")
    assert removed == ["in front of a clock tower and low red-roof house"]
    assert out == "two stylized young characters dancing side by side on a flat stone plaza, bright warm midday sunlight"


def test_nothing_to_strip_returns_text_unchanged():
    text = "Kelly hides behind the low wall near the tower, rifle up. Soft dusk light."
    assert pa.strip_scenery(text, ["KELLY"]) == (text, [])


def test_background_sentence_is_computed_from_the_real_shot_17_plate():
    f = pa.landmark_facts(REC_285, ENTRY_263)
    assert f["known"] and f["in_frame"] and f["top_cut"]
    assert f["dist_subject_m"] == pytest.approx(10.6, abs=0.2)
    assert 0.33 < f["u"] < 0.67 and 0.15 < f["base_v"] < 0.3          # render: chân tháp ở ~22 % từ trên, tháp cắt mép trên
    text, notes = pa.background_sentence(REC_285, ENTRY_263, "Tháp Đồng Hồ")
    assert notes == []
    assert "about 11 m from the main character, in the middle of the frame" in text
    assert "rising past the top edge of the frame" in text and "horizon line at 12%" in text and "Image 1" in text


def test_landmark_behind_the_camera_and_missing_anchor_are_said():
    away = dict(REC_285, camera_plan=dict(REC_285["camera_plan"], look_at=[-221.0, 117.8, 10.9]))   # máy quay lưng về tháp
    assert pa.landmark_facts(away, ENTRY_263)["in_frame"] is False
    assert "outside this frame" in pa.background_sentence(away, ENTRY_263, "Tháp Đồng Hồ")[0]
    text, notes = pa.background_sentence(REC_285, {}, "Tháp Đồng Hồ")
    assert notes and "chưa có mốc" in notes[0]
    assert "Draw the background only as Image 1 shows it" in text


# ---- (b) render là ảnh 1 --------------------------------------------------------------------------------------------------------
def test_plate_first_and_keep_sentence_only_when_image_1_is_the_render():
    refs = [{"role": "character", "label": "KELLY"}, {"role": "object", "label": "Bom keo"}, {"role": "place_render", "label": "T"},
            {"role": "storyboard", "label": "s"}]
    first = pa.plate_first(refs)
    assert [r["role"] for r in first] == ["place_render", "character", "object", "storyboard"]
    assert pa.plate_first(refs[:2]) == refs[:2]
    assert pa.with_keep("P", first).startswith(pa.KEEP) and pa.with_keep("P", refs[:2]) == "P"


def test_flag_needs_place_render_refs():
    with mock.patch.dict(os.environ, {"FEATURE_PLATE_ANCHORED_IMAGE": "1", "FEATURE_PLACE_RENDER_REFS": "0"}):
        assert pa.enabled() is False
    with mock.patch.dict(os.environ, ON):
        assert pa.enabled() is True


# ---- luồng thật của ImageRunner (gói gửi, prompt, diag) ----------------------------------------------------------------------------
from tests.test_plate_package_single_angle import _Send          # noqa: E402 - cùng khung dữ liệu giả (render giả, Kho giả)
from tests.test_plate_stale_kld6 import OLD_FIELDS                 # noqa: E402

SCENERY = "Clock tower plaza, low retaining walls, red-roof houses in far background."


class RunnerSends(_Send):
    def setUp(self):
        super().setUp()
        self.set_data(dict(OLD_FIELDS, plate_spot="nha_lon_dong", image_prompt=OLD_FIELDS["image_prompt"] + ". " + SCENERY))
        import io
        from core import assets
        kelly = assets.create(self.p.conn, "FF", "character", "KELLY")   # người có ảnh → đường cũ xếp người TRƯỚC render
        buf = io.BytesIO()
        Image.new("RGB", (64, 96), (200, 180, 40)).save(buf, "PNG")
        assets.add_image(self.p.conn, kelly, "k.png", buf.getvalue())
        self.p.conn.execute("UPDATE asset_images SET status='approved'")
        self.p.conn.commit()
        assets.attach(self.p.conn, self.pid, kelly)
        self.render()

    def send(self, env):
        from core import place_refs
        with mock.patch.dict(os.environ, env), mock.patch.object(place_refs, "ensure_async"):
            self.p.create_job(self.sid, "image_gen")
            self.assertEqual(self.runner().submit_pending(self.pid), 1)
        return next(iter(self.provider.prompts.values()))

    def test_flag_on_render_first_keep_sentence_background_from_plate(self):
        prompt = self.send({"FEATURE_PLATE_ANCHORED_IMAGE": "1"})
        sent = self.sent()
        self.assertEqual([s["role"] for s in sent][:2], ["place_render", "character"])
        self.assertTrue(prompt.startswith(pa.KEEP))
        self.assertIn("Image 1 is the EXACT background", prompt)
        self.assertIn("Draw the background only as Image 1 shows it", prompt)
        self.assertNotIn("red-roof houses in far background", prompt)
        self.assertNotIn("in front of a clock tower and low red-roof house", prompt)
        words = self.diags(pa.CODE_WORDS)
        self.assertTrue(words and words[0]["severity"] == "warn" and "red-roof houses" in words[0]["message"])
        self.assertTrue(self.diags(pa.CODE_BACKGROUND))                # khung giả không có model3d.anchor → nói ra, không im lặng

    def test_flag_off_keeps_the_old_package(self):
        prompt = self.send({"FEATURE_PLATE_ANCHORED_IMAGE": "0"})
        roles = [s["role"] for s in self.sent()]
        self.assertEqual(roles[0], "character")
        self.assertIn("place_render", roles)
        self.assertFalse(prompt.startswith(pa.KEEP))
        self.assertIn("red-roof houses in far background", prompt)
        self.assertNotIn("Draw the background only as Image 1 shows it", prompt)
        self.assertFalse(self.diags(pa.CODE_WORDS))


def test_after_download_diag_red_from_check_strict(tmp_path):
    """Ảnh về: cờ bật + shot có render → check_strict (không cần camera_plan), ĐỎ ghi diag 'error'."""
    from core import camera_plan, place_refs
    from core.runner import ImageRunner
    r = ImageRunner.__new__(ImageRunner)
    r.data_dir = str(tmp_path)
    r.p = mock.Mock()
    said = []
    r._diag = lambda job, sev, code, msg: said.append((sev, code, msg))
    job = {"id": 744, "project_id": 27, "scene_id": 289, "retry_reason": None}
    with mock.patch.dict(os.environ, ON), mock.patch.object(place_refs, "shot_ref", return_value={"path": "p"}), \
            mock.patch.object(place_refs, "measure", return_value=("info", "x")), \
            mock.patch.object(place_refs, "resolution_of", return_value=(1152, 2048)), \
            mock.patch.object(camera_plan, "enabled", return_value=False), \
            mock.patch.object(qc, "check_strict", return_value=("error", "ĐỎ: nền ảnh lệch render 3D")), \
            mock.patch("core.qc_scene.shadow", return_value=False), mock.patch("core.qc_scene.enabled", return_value=False):
        r._after_download(job, "img.png")
    assert ("error", qc.CODE, "ĐỎ: nền ảnh lệch render 3D") in said
