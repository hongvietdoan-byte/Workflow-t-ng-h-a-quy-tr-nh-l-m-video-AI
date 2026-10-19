"""G2 + G3 (17/10, #31). CSDL bộ nhớ, 0 USD.

G2 — dạng nhân vật theo phong cách: Kelly ở thế giới song song là DẠNG BÓNG MỜ (Kho style khai "Dạng của nhân vật: KELLY"), shot nhắc
"ghost form" nhưng khóa vẫn gửi áo khoác vàng + "The costume follows the profile above" + "ignore any clothing … words" → model bỏ dạng.
G3 — render 3D của shot bị đẩy khỏi gói khi 8 ảnh người lấp trần; câu địa điểm bằng chữ còn chữ Việt.
"""
import io
import json

import pytest
from PIL import Image

from core import assets, character_forms, place_refs, prompts, seedance_refs
from core.db import connect
from core.pipeline import Pipeline
from core.runner import lock_note

RULES = {"must_keep": "dark brown chin-length bob with straight bangs, black choker, bright yellow zip-up track jacket, "
                      "matching yellow track pants, white sneakers, youthful face",
         "forbidden": "changing hair color", "height_m": 1.7}
GHOST = "Kelly in her ghost form — translucent body glowing purple-blue — steps through the hedge gap."


def _png(colour) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 96), colour).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def p(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(tmp_path / "none.json"))
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    monkeypatch.setenv("ASSET_DIR", str(tmp_path / "assets"))
    obj = Pipeline(connect())
    yield obj
    obj.conn.close()


def _project(p, declare=True, form_picture=True):
    pid = p.create_project("t", game="FF")
    p.conn.execute("INSERT INTO characters (project_id, name, description, lock_rules) VALUES (?,?,?,?)",
                   (pid, "Kelly", "x", json.dumps(RULES)))
    p.conn.commit()
    kelly = assets.create(p.conn, "FF", "character", "KELLY", aliases="Kelly new")
    assets.add_image(p.conn, kelly, "k1.png", _png((250, 220, 0)))
    assets.add_image(p.conn, kelly, "k2.png", _png((240, 210, 0)))
    assets.attach(p.conn, pid, kelly)
    desc = ("[Halloween OB55] Người chơi ở thế giới song song: thân trong suốt phát sáng tím–xanh lam. "
            "Translucent purple-blue glowing body with a red outline; still a human shape."
            + ("\nDạng của nhân vật: KELLY" if declare else ""))
    sid = assets.create(p.conn, "FF", "style", "BÓNG MỜ THẾ GIỚI SONG SONG", aliases="dạng bóng mờ, ghost form", description=desc)
    assets.add_image(p.conn, sid, "hud.png", _png((200, 0, 0)))                     # in-game screenshot with HUD: never sent
    if form_picture:
        assets.add_image(p.conn, sid, "form.png", _png((90, 60, 230)), role=character_forms.ROLE)
    assets.attach(p.conn, pid, sid)
    return pid


# ---- G2 -------------------------------------------------------------------------------------------------------------------------

def test_named_form_drops_the_costume_lock_keeps_face_and_hair(p):
    pid = _project(p)
    note = lock_note(p.conn, pid, ["Kelly"], {"characters": ["Kelly"], "image_prompt": GHOST})
    assert "ghost form" in note and "Translucent purple-blue" in note
    assert "yellow" not in note and "track jacket" not in note and "sneakers" not in note
    assert "dark brown chin-length bob" in note and "changing hair color" in note
    assert "The costume follows the profile above" not in note
    assert "thế giới" not in note and "Người" not in note                         # no Vietnamese words to the image model


def test_form_not_named_or_not_declared_keeps_the_old_lock(p):
    pid = _project(p)
    plain = lock_note(p.conn, pid, ["Kelly"], {"characters": ["Kelly"], "image_prompt": "Kelly runs past the hedge."})
    assert "bright yellow zip-up track jacket" in plain and "The costume follows the profile above" in plain
    spoken = {"characters": ["Kelly"], "text": "LỜI DẪN: ghost form", "image_prompt": "Kelly runs."}
    assert "bright yellow" in lock_note(p.conn, pid, ["Kelly"], spoken)


def test_style_without_declaration_is_not_a_form(p):
    pid = _project(p, declare=False)
    assert "bright yellow" in lock_note(p.conn, pid, ["Kelly"], {"characters": ["Kelly"], "image_prompt": GHOST})
    assert character_forms.for_shot(p.conn, pid, {"characters": ["Kelly"], "image_prompt": GHOST}) == {}
    refs = assets.scene_references(p.conn, pid, {"characters": ["Kelly"], "image_prompt": GHOST})
    assert [r["role"] for r in refs] == ["character", "character"]


def test_form_picture_sent_and_reference_note_frees_the_clothes(p):
    pid = _project(p)
    refs = assets.scene_references(p.conn, pid, {"characters": ["Kelly"], "image_prompt": GHOST})
    roles = [r["role"] for r in refs]
    assert roles[:2] == ["character", character_forms.ROLE]
    assert not any(r["path"].endswith("hud.png") or "hud" in r["path"].lower() for r in refs)
    assert all(r.get("form") == "ghost form" for r in refs if r["label"] == "KELLY")
    note = assets.reference_note(refs)
    assert "outfit and its colors" not in note
    assert "NOT the clothes or their colours" in note and "Exception: KELLY" in note
    assert "in the ghost form of this shot" in note
    gaps = assets.reference_gaps(p.conn, pid, {"characters": ["Kelly"], "image_prompt": GHOST})
    assert not any("BÓNG MỜ" in g and "chỉ dùng bằng chữ" in g for g in gaps)


def test_form_without_clean_picture_sends_none_and_says_words_only(p):
    pid = _project(p, form_picture=False)
    scene = {"characters": ["Kelly"], "image_prompt": GHOST}
    assert [r["role"] for r in assets.scene_references(p.conn, pid, scene)] == ["character", "character"]
    assert "ghost form" in lock_note(p.conn, pid, ["Kelly"], scene)              # the lock is still freed
    assert any("BÓNG MỜ" in g and "chỉ dùng bằng chữ" in g for g in assets.reference_gaps(p.conn, pid, scene))


def test_no_form_reference_note_unchanged(p):
    pid = _project(p)
    refs = assets.scene_references(p.conn, pid, {"characters": ["Kelly"], "image_prompt": "Kelly runs."})
    assert [r["role"] for r in refs] == ["character", "character"] and not any("form" in r for r in refs)
    note = assets.reference_note(refs)
    assert "outfit and its colors" in note and "Exception:" not in note


def test_video_prompt_and_qc_lock_follow_the_form(p):
    pid = _project(p)
    scene = {"characters": ["Kelly"], "image_prompt": GHOST}
    forms = character_forms.for_shot(p.conn, pid, scene)
    text = seedance_refs.prompt([("Kelly runs.", 4)], [("Kelly", "k1.png")], forms=forms)
    assert "NOT the clothes" in text and "ghost form" in text and "identity only (face, hair, outfit)" not in text
    assert "identity only (face, hair, outfit)" in seedance_refs.prompt([("Kelly runs.", 4)], [("Kelly", "k1.png")])
    qc = prompts.lock_text(p.conn, pid, ["Kelly"], shots=[scene])
    assert "dạng BÓNG MỜ" in qc and "yellow" not in qc


def test_clothes_clauses_only():
    body = "dark brown bob (hair down, never tied), black choker, white crop top under a yellow track jacket, youthful face, 1.7 m"
    assert character_forms.without_clothes(body) == "dark brown bob (hair down, never tied), youthful face, 1.7 m"


# ---- G3 -------------------------------------------------------------------------------------------------------------------------

def _people():
    out = []
    for who in ("KELLY", "LINH", "YEU NU"):
        out += [{"path": f"{who}1", "label": who, "role": "character"}, {"path": f"{who}2", "label": who, "role": "character"}]
    return out + [{"path": "SG", "label": "SU GIA", "role": "character"}, {"path": "XT", "label": "XUC TU", "role": "character"}]


def test_render_keeps_its_slot_over_eight_people():
    render = {"path": "plate.png", "label": "Cổng Trời", "role": "place_render", "_rec": {}}
    out = place_refs.swap_in(_people(), render, 8)
    assert len(out) == 8 and any(r["role"] == "place_render" for r in out)
    assert "YEU NU2" not in [r["path"] for r in out]                              # 2nd picture of the person listed last goes first
    assert [r["path"] for r in out][:5] == ["KELLY1", "KELLY2", "LINH1", "LINH2", "YEU NU1"]
    assert "_rec" not in next(r for r in out if r["role"] == "place_render")


def test_render_within_the_cap_cuts_as_before():
    few = _people()[:4] + [{"path": "loc", "label": "P", "role": "location"}, {"path": "prev", "label": "x", "role": "previous_scene"}]
    out = place_refs.swap_in(few, {"path": "plate.png", "label": "P", "role": "place_render"}, 5)
    assert [r["path"] for r in out] == ["KELLY1", "KELLY2", "LINH1", "LINH2", "plate.png"]


def test_skill_frame_and_model_cap_never_cut_the_render(tmp_path, monkeypatch):
    from core import runner, skill_dossier
    render = {"path": "plate.png", "label": "P", "role": "place_render"}
    seven = _people()[:7] + [render]
    out = skill_dossier.add_reference(seven, {"path": "skill.png", "label": "KELLY", "role": skill_dossier.ROLE}, 8)
    assert any(r["role"] == "place_render" for r in out)
    monkeypatch.setattr("core.adapters.deepix.reference_problem", lambda path: None)
    kept, dropped = runner.sendable_references(_people() + [render], None, limit=8)
    assert len(kept) == 8 and kept[-1]["role"] == "place_render" and "YEU NU2" not in [r["path"] for r in kept]
    assert len(dropped) == 1 and "quá 8 ảnh" in dropped[0]
    few, _ = runner.sendable_references(_people()[:3] + [render], None, limit=8)
    assert [r["path"] for r in few] == ["KELLY1", "KELLY2", "LINH1", "plate.png"]


def test_place_words_for_the_image_model_have_no_vietnamese():
    from core.seedance_refs import has_vietnamese
    place = {"name": "Tháp Đồng Hồ", "images": [],
             "description": "[ff.garena.com] Khu vực trên bản đồ Đảo Quân Sự. Real map: the clock tower stands on a wide stone plaza."}
    text = assets.location_text(None, place)
    assert "Real map: the clock tower stands on a wide stone plaza." in text
    assert not has_vietnamese(text.replace("Tháp Đồng Hồ", "")) and "ff.garena.com" not in text
    assert "Khu vực" in assets.location_text(None, place, for_llm=True)             # Claude (QC) still reads it


# ---- G27 (19/10, #31): the VIDEO package sends the form picture and the library objects the shot names ----------------------------

def _with_prop(p, pid):
    gun = assets.create(p.conn, "FF", "weapon", "SKORP", aliases="skorp")
    assets.add_image(p.conn, gun, "skorp.png", _png((200, 30, 30)))
    assets.attach(p.conn, pid, gun)


def test_video_pictures_carry_the_form_and_the_named_object(p):
    pid = _project(p)
    _with_prop(p, pid)
    rows = [{"id": 1, "data": {"characters": ["Kelly"], "image_prompt": GHOST + " The red-glowing SKORP in her hands."}}]
    ids = seedance_refs.identity_pictures(p.conn, pid, rows, 8)
    names = [n for n, _ in ids]
    assert "KELLY" in [seedance_refs.base_name(n).upper() for n in names if seedance_refs.is_person(n)]
    assert any(n.endswith(seedance_refs.FORM_TAG) for n in names), names           # #31 shot 28: the ghost form picture now goes
    assert any(n.endswith(seedance_refs.OBJECT_TAG) and "SKORP" in n for n in names), names
    forms = character_forms.for_rows(p.conn, pid, rows)
    text = seedance_refs.prompt([(GHOST, 4)], ids, forms=forms)
    assert "ghost form in this clip: draw Kelly's whole body" in text.replace("KELLY", "Kelly")
    assert "the object SKORP: whenever it appears, draw it exactly as this picture shows" in text


def test_over_the_room_objects_go_before_the_form_and_the_face_stays(p):
    pid = _project(p)
    _with_prop(p, pid)
    rows = [{"id": 1, "data": {"characters": ["Kelly"], "image_prompt": GHOST + " SKORP."}}]
    two = [n for n, _ in seedance_refs.identity_pictures(p.conn, pid, rows, 2)]
    assert len(two) == 2 and any(n.endswith(seedance_refs.FORM_TAG) for n in two)
    assert not any(n.endswith(seedance_refs.OBJECT_TAG) for n in two)
    one = [n for n, _ in seedance_refs.identity_pictures(p.conn, pid, rows, 1)]
    assert len(one) == 1 and seedance_refs.is_person(one[0])


def test_no_form_picture_in_the_library_sends_none(p):
    pid = _project(p, form_picture=False)
    rows = [{"id": 1, "data": {"characters": ["Kelly"], "image_prompt": GHOST}}]
    names = [n for n, _ in seedance_refs.identity_pictures(p.conn, pid, rows, 8)]
    assert not any(n.endswith(seedance_refs.FORM_TAG) for n in names)            # the runner's lint holds the send (ĐỎ)


def test_an_accented_object_name_leaves_no_vietnamese_in_the_video_prompt(p):
    pid = _project(p)
    pram = assets.create(p.conn, "FF", "prop", "XE NÔI BỊ NGUYỀN", aliases="cursed pram")
    assets.add_image(p.conn, pram, "pram.png", _png((20, 20, 20)))
    assets.attach(p.conn, pid, pram)
    rows = [{"id": 1, "data": {"characters": ["Kelly"], "image_prompt": GHOST + " Beside her stands the XE NÔI BỊ NGUYỀN."}}]
    ids = seedance_refs.identity_pictures(p.conn, pid, rows, 8)
    assert any(n.endswith(seedance_refs.OBJECT_TAG) for n, _ in ids), ids
    text = seedance_refs.prompt([(GHOST + " Beside her stands the XE NÔI BỊ NGUYỀN.", 4)], ids,
                                forms=character_forms.for_rows(p.conn, pid, rows))
    assert "XE NOI BI NGUYEN" in text and "NÔI" not in text
