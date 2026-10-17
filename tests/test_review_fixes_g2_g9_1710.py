"""Rà quy ước 7 hai nhánh G2–G9 (17/10, #31) — mỗi lỗi rà một test. CSDL bộ nhớ, 0 USD.

Danh sách lỗi: docs/handoff/RA_NHANH_G2_G9_2026-10-17.md.
"""
import re
from unittest import mock

from core import (assets, character_forms, location_pack, plate_anchor, plate_choice, prompts, prop_lock, scene_establish,
                  scene_storyboard, seedance_refs, shot_normalize, shot_text_checks)
from core.runner import lock_note
from tests.test_forms_and_render_slot import GHOST, _png, _project, p  # noqa: F401 - fixture p


# ---- nhánh 1 ---------------------------------------------------------------------------------------------------------------------

def test_without_clothes_keeps_keep_never_prefix_and_hair():
    assert character_forms.without_clothes("keep yellow jacket, long hair; never red jacket, blonde hair") == \
        "keep long hair; never blonde hair"
    assert character_forms.without_clothes("hair tied on top, black cap") == "hair tied on top"
    assert character_forms.without_clothes("hair under a cap. White sneakers, slim build") == "hair under a cap; slim build"
    body = ("keep the face, hair and body build of the reference pictures; the clothes, cap and accessories come ONLY from the OUTFIT "
            "image, never from the everyday look")
    assert character_forms.without_clothes(body) == "keep the face, hair and body build of the reference pictures"


PLAIN = "Kelly runs past the hedge."


def test_qc_lock_several_shots_same_form_is_judged_on_the_form(p):
    pid = _project(p)
    both = prompts.lock_text(p.conn, pid, ["Kelly"], shots=[{"characters": ["Kelly"], "image_prompt": GHOST},
                                                           {"characters": ["Kelly"], "image_prompt": GHOST}])
    assert "dạng BÓNG MỜ" in both and "yellow" not in both
    mixed = prompts.lock_text(p.conn, pid, ["Kelly"], shots=[{"characters": ["Kelly"], "image_prompt": PLAIN},
                                                            {"characters": ["Kelly"], "image_prompt": GHOST}])
    assert "yellow" in mixed and "Shot 2:" in mixed and "dạng BÓNG MỜ" in mixed and "Shot 1:" not in mixed


def test_video_form_is_said_per_shot(p):
    pid = _project(p)
    rows = [{"data": {"characters": ["Kelly"], "image_prompt": PLAIN}}, {"data": {"characters": ["Kelly"], "image_prompt": GHOST}}]
    forms = character_forms.for_rows(p.conn, pid, rows)
    assert forms["KELLY"]["shots"] == [2] and forms["KELLY"]["all"] is False
    text = seedance_refs.prompt([(PLAIN, 3), (GHOST, 3)], [("Kelly", "k1.png")], forms=forms)
    assert "in Shot 2 Kelly is in the ghost form" in text and "in this clip Kelly" not in text
    assert "same characters throughout" in text and "characters and outfits throughout" not in text
    whole = character_forms.for_rows(p.conn, pid, [{"data": {"characters": ["Kelly"], "image_prompt": GHOST}}] * 2)
    assert whole["KELLY"]["all"] is True
    assert "in this clip Kelly is in the ghost form" in seedance_refs.prompt([(GHOST, 3), (GHOST, 3)], [("Kelly", "k1.png")],
                                                                              forms=whole)


def test_no_outfit_picture_for_a_person_in_a_form_all_clip(p, tmp_path):
    pid = _project(p)
    outfit = tmp_path / "outfit.png"
    outfit.write_bytes(_png((0, 0, 255)))
    ghost = [{"data": {"characters": ["Kelly"], "image_prompt": GHOST}}]
    plain = [{"data": {"characters": ["Kelly"], "image_prompt": PLAIN}}]
    with mock.patch.object(assets, "outfit_images", return_value=[{"path": str(outfit)}]), \
            mock.patch.object(seedance_refs, "_rule_ok_picture", side_effect=lambda c, pid_, who, paths: paths[0]):
        assert not [n for n, _ in seedance_refs.identity_pictures(p.conn, pid, ghost, 8) if n.endswith(seedance_refs.OUTFIT_TAG)]
        assert [n for n, _ in seedance_refs.identity_pictures(p.conn, pid, plain, 8) if n.endswith(seedance_refs.OUTFIT_TAG)]


def test_outfit_pictures_give_way_before_a_face_picture(p, tmp_path):
    pid = _project(p)
    outfit = tmp_path / "outfit.png"
    outfit.write_bytes(_png((0, 0, 255)))
    rows = [{"data": {"characters": ["Kelly"], "image_prompt": PLAIN}}]
    with mock.patch.object(assets, "outfit_images", return_value=[{"path": str(outfit)}]), \
            mock.patch.object(seedance_refs, "_rule_ok_picture", side_effect=lambda c, pid_, who, paths: paths[0]):
        got = seedance_refs.identity_pictures(p.conn, pid, rows, 1)
    assert [n for n, _ in got] == ["Kelly"]


def test_place_name_in_vietnamese_is_not_sent_to_the_image_model():
    with mock.patch.object(assets, "_landmark_heights", return_value=([], "")):
        text = assets.location_text(None, {"name": "Tháp đồng hồ", "aliases": "Clock Tower", "description": "Tháp đồng hồ rất cao. A tall tower."})
        assert text.startswith("Setting: Clock Tower") and "Tháp" not in text
        bare = assets.location_text(None, {"name": "Tháp đồng hồ", "aliases": "", "description": ""})
        assert "đồng" not in bare and "thap dong ho" in bare.lower()
        long_vi = "Mô tả rất dài tiếng Việt. " * 40 + "The English sentence."
        assert "The English sentence." in assets.location_text(None, {"name": "Tower", "aliases": "", "description": long_vi})


# ---- nhánh 2 ---------------------------------------------------------------------------------------------------------------------

def test_silhouette_of_a_person_or_monster_stays():
    for t in ("Kelly stands still, a hooded silhouette waiting in the background.",
              "Kelly runs, the tall dark silhouette of the Unseen looming far away."):
        assert plate_anchor.strip_scenery(t, ["Kelly"]) == (t, [])
    for t in ("Kelly runs, the villa silhouette faint in the far background between hedge tops.",
              "Kelly runs, the dark silhouette of the mansion in the distance."):
        assert plate_anchor.strip_scenery(t, ["Kelly"])[0] == "Kelly runs."


def test_vietnamese_weapon_scale_falls_to_the_next_source(p):
    sid = assets.create(p.conn, "FF", "weapon", "SKORP", aliases="", description="SMG gọn. Tỉ lệ: dài bằng nửa cánh tay người.")
    a = assets.get(p.conn, sid)
    assert "Tỉ lệ" in prop_lock.weapon_scale(p.conn, a) or "nửa" in prop_lock.weapon_scale(p.conn, a)
    sent = prop_lock.weapon_scale(p.conn, a, english=True)
    assert sent.startswith("Estimated SMG proportions") and not seedance_refs.has_vietnamese(sent)


def test_no_moonlight_sentence_indoors():
    data = {"characters": ["Kelly"], "practical_lights": []}
    assert "moonlight" in plate_choice.light_sentence([], True, "night", data)
    assert plate_choice.light_sentence([], True, "night", data, indoor=True) == ""
    with mock.patch.object(scene_establish, "enabled", return_value=True):
        assert "moonlight" in scene_establish.light_sentence({"time": "night"})
        indoor = scene_establish.light_sentence({"time": "night"}, indoor=True)
        assert "moonlight" not in indoor and "street" not in indoor and "indoors" in indoor


def test_held_prop_of_the_nearest_earlier_shot_follows_she_fires_it():
    def fake(conn, pid, data, limit=8, **kw):
        out = [{"path": "kelly.png", "label": "KELLY", "role": "character"}, {"path": "place.png", "label": "Cổng Trời", "role": "location"}]
        if "SKORP" in data.get("image_prompt", ""):
            out.append({"path": "skorp.png", "label": "SKORP", "role": "object"})
        if "pram" in data.get("image_prompt", ""):
            out.append({"path": "pram.png", "label": "XE NÔI", "role": "object"})
        if "ghost world" in data.get("image_prompt", ""):
            out.append({"path": "sky.png", "label": "BÓNG MỜ", "role": "atmosphere_sky"})
        return out[:limit]
    shots = [{"id": 1, "idx": 10, "data": {"characters": ["KELLY"], "image_prompt": "the pram glows in the ghost world"}},
             {"id": 2, "idx": 12, "data": {"characters": ["KELLY"], "image_prompt": "Kelly lifts the SKORP"}},
             {"id": 3, "idx": 13, "data": {"characters": ["KELLY"], "image_prompt": "she fires it at the shadow"}}]
    with mock.patch.object(assets, "scene_references", side_effect=fake):
        fires = [r["label"] for r in scene_storyboard.shared_references(None, 31, shots, cast_of=shots[2]["data"])]
        first = [r["label"] for r in scene_storyboard.shared_references(None, 31, shots, cast_of=shots[0]["data"])]
        lifts = [r["label"] for r in scene_storyboard.shared_references(None, 31, shots, cast_of=shots[1]["data"])]
    assert "SKORP" in fires and "XE NÔI" not in fires and "BÓNG MỜ" not in fires
    assert "SKORP" not in first and "BÓNG MỜ" in first
    assert "XE NÔI" not in lifts and "BÓNG MỜ" not in lifts


def test_weather_check_false_alarms():
    for t in ("heat haze over the sand", "a rain of sparks falls", "a snow-white dress"):
        assert shot_text_checks.time_weather_conflicts({"time": "day", "weather": "clear", "image_prompt": t}) == [], t
    assert shot_text_checks.time_weather_conflicts({"time": "day", "weather": "clear", "image_prompt": "heavy rain"})


def test_no_backspace_characters_in_regex_sources():
    for mod in (scene_storyboard, shot_normalize, assets, prop_lock, plate_anchor, location_pack):
        assert "\x08" not in open(mod.__file__, encoding="utf-8").read(), mod.__name__
    assert shot_normalize._POST_ONLY.search("an overlay is added later")      # was overlay: never matched
