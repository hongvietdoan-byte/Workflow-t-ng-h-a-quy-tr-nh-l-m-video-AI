"""17/10 (#31): ảnh không khí SẠCH của một phong cách (bầu trời / bối cảnh thế giới song song) được gửi làm ảnh ref cho shot nhắc tên
phong cách đó — ảnh phong cách khác vẫn chỉ dùng bằng chữ. CSDL bộ nhớ, 0 USD."""
import io

import pytest
from PIL import Image

from core import assets
from core.db import connect
from core.pipeline import Pipeline


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


def _world(p, roles=("atmosphere_sky", "atmosphere_place")):
    pid = p.create_project("t", game="FF")
    sid = assets.create(p.conn, "FF", "style", "CỔNG TRỜI THẾ GIỚI SONG SONG", aliases="Parallel world at Cổng Trời")
    for i, role in enumerate(roles):
        assets.add_image(p.conn, sid, f"{role}.png", _png((10 * i, 20, 30)), role=role)
    assets.add_image(p.conn, sid, "hud.png", _png((200, 0, 0)))                      # a screenshot: no atmosphere role → never sent
    assets.attach(p.conn, pid, sid)
    return pid, sid


def test_named_style_sends_sky_then_place_with_note(p):
    pid, _ = _world(p)
    scene = {"image_prompt": "Kelly runs. Parallel world at Cổng Trời, matching the in-game look: storm clouds.", "characters": []}
    refs = assets.scene_references(p.conn, pid, scene)
    assert [r["role"] for r in refs] == ["atmosphere_sky", "atmosphere_place"]
    note = assets.reference_note(refs)
    assert "SKY of CỔNG TRỜI THẾ GIỚI SONG SONG" in note and "not its camera" in note
    assert "LOOK of CỔNG TRỜI THẾ GIỚI SONG SONG" in note and "never its camera" in note
    assert not any("chỉ dùng bằng chữ" in g for g in assets.reference_gaps(p.conn, pid, scene))


def test_unnamed_or_spoken_only_style_sends_nothing(p):
    pid, _ = _world(p)
    assert assets.scene_references(p.conn, pid, {"image_prompt": "Kelly at the clock tower", "characters": []}) == []
    spoken = {"text": "LỜI DẪN: Parallel world at Cổng Trời", "image_prompt": "Kelly", "characters": []}
    assert assets.scene_references(p.conn, pid, spoken) == []


def test_style_without_atmosphere_pictures_stays_words_only(p):
    pid, _ = _world(p, roles=())
    scene = {"image_prompt": "Parallel world at Cổng Trời, dark sky", "characters": []}
    assert assets.scene_references(p.conn, pid, scene) == []
    assert any("chỉ dùng bằng chữ" in g for g in assets.reference_gaps(p.conn, pid, scene))


def test_atmosphere_respects_the_slot_limit(p):
    pid, _ = _world(p)
    scene = {"image_prompt": "Parallel world at Cổng Trời", "characters": []}
    assert len(assets.scene_references(p.conn, pid, scene, limit=1)) == 1
    assert assets.scene_references(p.conn, pid, scene, limit=2, reserve=2) == []


def test_named_prop_keeps_its_slot_atmosphere_takes_only_spare(p):
    # rà 17/10 (B): trước đây ảnh không khí chen trước extras và lấy mất slot của đạo cụ được nhắc tên
    pid, _ = _world(p)
    prop = assets.create(p.conn, "FF", "prop", "XE NÔI BỊ NGUYỀN", aliases="cursed pram")
    assets.add_image(p.conn, prop, "pram.png", _png((1, 2, 3)))
    assets.attach(p.conn, pid, prop)
    scene = {"image_prompt": "The cursed pram glows. Parallel world at Cổng Trời", "characters": []}
    refs = assets.scene_references(p.conn, pid, scene, limit=2)
    assert [r["role"] for r in refs] == ["object", "atmosphere_sky"]


def test_accent_aware_matching_no_false_hit(p):
    # rà 17/10 (D): alias bỏ dấu "Mây" không được khớp "máy"
    pid = p.create_project("t", game="FF")
    sid = assets.create(p.conn, "FF", "style", "Mây", aliases="")
    assets.add_image(p.conn, sid, "sky.png", _png((5, 5, 5)), role="atmosphere_sky")
    assets.attach(p.conn, pid, sid)
    assert assets.atmosphere_refs(p.conn, pid, {"image_prompt": "máy quay đứng yên"}) == []
    assert len(assets.atmosphere_refs(p.conn, pid, {"image_prompt": "trời đầy Mây đen"})) == 1


def test_video_and_qc_drop_atmosphere(p):
    # rà 17/10 (A, C): video Seedance đọc mọi ảnh không phải nơi là NGƯỜI; QC không chấm khung theo ảnh trời
    refs = [{"path": "a", "label": "KELLY", "role": "character"}, {"path": "b", "label": "W", "role": "atmosphere_sky"},
            {"path": "c", "label": "W", "role": "atmosphere_place"}]
    assert assets.without_atmosphere(refs) == refs[:1]
    import inspect
    from core import claude_tasks, prompts, qc_observe, runner
    for mod in (runner, qc_observe, prompts, claude_tasks):
        assert "without_atmosphere" in inspect.getsource(mod), mod.__name__


def test_anchor_only_style_keeps_the_words_only_note(p):
    # rà 17/10 (E): style chỉ khớp qua từ mốc tiếng Anh (không nhắc tên) → không gửi ảnh nên vẫn phải báo "chỉ dùng bằng chữ"
    pid = p.create_project("t", game="FF")
    sid = assets.create(p.conn, "FF", "style", "Đền ma", "a haunted shrine at night")
    assets.add_image(p.conn, sid, "sky.png", _png((5, 5, 5)), role="atmosphere_sky")
    assets.attach(p.conn, pid, sid)
    scene = {"image_prompt": "Kelly walks to the shrine", "characters": []}
    assert assets.atmosphere_refs(p.conn, pid, scene) == []
    assert any("chỉ dùng bằng chữ" in g for g in assets.reference_gaps(p.conn, pid, scene))
