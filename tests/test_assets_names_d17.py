"""Đ17v3: matcher/tên mới/cảnh báo dùng CSDL bộ nhớ, 0 USD."""
import json
from unittest import mock

import pytest

from core import assets, features, prompt_rewrite
from core.db import connect
from core.pipeline import Pipeline


@pytest.fixture
def p(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_SETTINGS_FILE", str(tmp_path / "none.json"))
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "0")
    obj = Pipeline(connect())
    yield obj
    obj.conn.close()


def test_plain_english_never_folds_to_vietnamese_but_explicit_alias_does(p, monkeypatch):
    bow = assets.create(p.conn, "FF", "weapon", "Nỏ")
    gun = assets.create(p.conn, "FF", "weapon", "Gùn")
    place = assets.create(p.conn, "FF", "location", "Tháp Đồng Hồ")
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    assert not assets.find_in_text(p.conn, "no gun, not here", "FF")
    assert {a["id"] for a in assets.find_in_text(p.conn, "di toi thap dong ho", "FF")} == {place}
    assets.update(p.conn, bow, "Nỏ", "crossbow, no", "")
    assert {a["id"] for a in assets.find_in_text(p.conn, "no", "FF")} == {bow}
    assert {a["id"] for a in assets.find_in_text(p.conn, "Nỏ Gùn", "FF")} == {bow, gun}


def test_create_requires_english_alias_when_enabled_and_suggests_without_paid_call(p, monkeypatch):
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    with pytest.raises(assets.AssetError, match="tiếng Anh"):
        assets.create(p.conn, "FF", "prop", "Cổng đỏ", require_english=True)       # the two Kho forms
    aid = assets.create(p.conn, "FF", "prop", "Cổng đỏ", aliases="red torii gate", require_english=True)
    assert assets.get(p.conn, aid)["aliases"] == "red torii gate"
    assert assets.suggest_english_name("Cổng đỏ", "A red torii gate") == "torii gate"
    assert assets.suggest_english_name("KELLY", "") == "KELLY"
    assert not assets.suggest_english_name("Cổng lạ", "")


def test_new_guards_off_keep_existing_creation_and_fold_bytes(p):
    aid = assets.create(p.conn, "FF", "weapon", "Nỏ")
    assert {a["id"] for a in assets.find_in_text(p.conn, "no", "FF")} == {aid}
    pid = p.create_project("t", game="FF")
    assets.attach(p.conn, pid, aid)
    assert assets.reference_gaps(p.conn, pid, {"image_prompt": "no", "characters": []}) == []


def test_project_description_anchor_and_mentioned_style_warn_without_characters(p, monkeypatch):
    pid = p.create_project("t", game="FF")
    gate = assets.create(p.conn, "FF", "prop", "Cổng đỏ", "A red torii gate")
    style = assets.create(p.conn, "FF", "style", "Parallel sky")
    assets.attach(p.conn, pid, gate)
    assets.attach(p.conn, pid, style)
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    data = {"image_prompt": "Wide shot at a torii gate beneath Parallel sky"}
    gaps = assets.reference_gaps(p.conn, pid, data)
    assert any("Cổng đỏ" in g and "khớp tên" in g for g in gaps)
    assert any("Parallel sky" in g and "chỉ dùng bằng chữ" in g for g in gaps)
    assert [assets.gap_severity(g) for g in gaps if "Cổng đỏ" in g] == ["warn"]
    assert [assets.gap_severity(g) for g in gaps if "Parallel sky" in g] == ["info"]     # rà 12/10: a film-wide style is a note
    assert not assets.reference_gaps(p.conn, pid, {"image_prompt": "a red wall"})
    assert not assets.reference_gaps(p.conn, pid, {"text": "LỜI DẪN: Parallel sky at a torii gate"})


def test_direct_retry_success_records_done_after_old_fallback(p):
    pid = p.create_project("t")
    sid = p.create_scene(pid, 1, "S01")
    p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps({"image_prompt": "Old red gate"}), sid))
    p.conn.commit()
    jid = p.create_job(sid, "image_gen")
    job = p.job(jid)
    prompt_rewrite._fallback(p, job, RuntimeError("Thiếu cấu hình thử"))
    result = prompt_rewrite.RewriteResult("New white gate", old_prompt="Old red gate")
    with mock.patch.object(prompt_rewrite, "propose_rewrite", return_value=result):
        prompt_rewrite.rewrite_for_retry(p, job, note="white")
    row = p.conn.execute("SELECT code, stage FROM diag_events WHERE scene_id=? AND code IN (?,?) "
                         "ORDER BY last_at DESC,id DESC LIMIT 1", (sid, prompt_rewrite.FALLBACK_CODE, prompt_rewrite.DONE_CODE)).fetchone()
    assert row["code"] == prompt_rewrite.DONE_CODE
    assert row["stage"] == "image"


def test_experimental_preset_never_enables_guard(p, monkeypatch):
    monkeypatch.delenv("FEATURE_ASSET_ENGLISH_NAMES", raising=False)
    with mock.patch.object(features, "settings", return_value={"preset": "experimental", "flags": {}, "modes": {}}):
        assert not features.on("asset_english_names")


def test_automatic_ff_sync_creates_the_row_and_says_the_missing_english_name(p, monkeypatch):
    """Rà 12/10: the VN site gives no aliases — skipping the row every month lost it; it is created and said."""
    from core import ff_site
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    items = [{"kind": "prop", "name": name, "text": "", "aliases": "", "images": []}
             for name in ("Cổng lạ", "KELLY")]
    with mock.patch.object(ff_site, "collect", return_value=items), mock.patch.object(ff_site, "sync_articles", return_value=0):
        report = ff_site.sync(p.conn, "FF", None, lambda url: "", lambda url: b"")
    assert report["created"] == 2 and report["skipped"] == 0 and not report.get("name_errors")
    row = p.conn.execute("SELECT message FROM diag_events WHERE code='asset_english_name'").fetchone()
    assert row and "Cổng lạ" in row["message"] and "tiếng Anh" in row["message"]


def test_automatic_paths_without_a_name_box_are_never_refused(p, monkeypatch, tmp_path):
    """Rà 12/10 (CAO): reference / outfit uploads, chat, 3D renders, folder sync have no box for an English name."""
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    aid = assets.create(p.conn, "FF", "character", "Cô gái")
    assert assets.get(p.conn, aid)["name"] == "Cô gái"
    assert p.conn.execute("SELECT COUNT(*) FROM diag_events WHERE code='asset_english_name'").fetchone()[0] == 1


def test_qc_enum_is_not_refused_by_the_name_notes(p, monkeypatch):
    """Rà 12/10 (CAO): core.qc_observe refuses on any reference gap — the D17 name / style notes must not count there."""
    pid = p.create_project("t", game="FF")
    style = assets.create(p.conn, "FF", "style", "Parallel sky")
    assets.attach(p.conn, pid, style)
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    data = {"image_prompt": "Wide shot beneath Parallel sky", "characters": []}
    assert assets.reference_gaps(p.conn, pid, data)
    assert assets.reference_gaps(p.conn, pid, data, named=False) == []
    import inspect
    from core import qc_observe
    assert all(assets.is_name_note(g) for g in assets.reference_gaps(p.conn, pid, data))
    assert "is_name_note" in inspect.getsource(qc_observe)


def test_costume_without_english_name_is_not_refused_and_alias_never_chains(p, monkeypatch, tmp_path):
    """Rà 12/10: no box to type a name on the costume screen → not refused (said by assets.create); the English name of an earlier
    outfit set ("Girl outfit 1") gives "Girl outfit 2", never "Girl outfit 1 outfit 2"."""
    import re as _re
    src = open(costume_path(), encoding="utf-8").read()
    assert "require_english_name" not in src
    assert _re.sub(r"(\s+outfit\s+\d+)+\s*$", "", "Girl outfit 1 outfit 2", flags=_re.I) == "Girl"


def costume_path():
    from core import costume
    return costume.__file__

def test_whole_vietnamese_phrase_without_accents_survives_english_guard(p, monkeypatch):
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    assert assets.name_spans("Cổng đỏ", assets._said_words("cong do")) == [(0, 2)]
    assert assets.name_spans("Đèn đỏ", assets._said_words("den do")) == [(0, 2)]
    assert not assets.name_spans("Nỏ", assets._said_words("no"))


@pytest.mark.parametrize("race", [False, True])
@pytest.mark.parametrize("collision", ["alias", "name"])
def test_costume_alias_collision_keeps_two_submits_and_saves_unique_set(p, monkeypatch, tmp_path, race, collision):
    from core import costume
    from core.providers import MockImageProvider
    monkeypatch.setenv("ASSET_DIR", str(tmp_path / "assets"))
    monkeypatch.setenv("FEATURE_ASSET_ENGLISH_NAMES", "1")
    pid = p.create_project("t")
    assets.create(p.conn, "FF", "character", "CÔ GÁI · trang phục 1" if collision == "alias" else "KELLY · trang phục 2",
                  aliases="KELLY outfit 1" if collision == "alias" else "Old costume", project_id=pid)
    p.conn.execute("INSERT INTO characters(project_id,name,description) VALUES (?,?,?)", (pid, "KELLY", "A person"))
    p.conn.commit()
    provider = MockImageProvider(polls_to_finish=1)
    slot = mock.Mock()
    slot.send.side_effect = lambda fn, *args: fn(*args)
    gate = mock.MagicMock()
    gate.__enter__.return_value = slot
    original_create = assets.create
    injected = False
    def create_with_race(*args, **kwargs):
        nonlocal injected
        if race and not injected:
            injected = True
            original_create(*args, **kwargs)
        return original_create(*args, **kwargs)
    with mock.patch.object(assets, "find_same", wraps=assets.find_same) as same:
        def spend_checked(*args, **kwargs):
            assert same.call_count > 0, "Phải kiểm tên và alias trước cổng tiền"
            return gate
        with mock.patch.object(costume.spend_gate, "spend", side_effect=spend_checked), mock.patch.object(assets, "create", side_effect=create_with_race):
            result = costume.make_character_set(p, pid, "KELLY", provider, str(tmp_path), sleep=lambda _: None)
    assert len(provider.prompts) == 2
    assert slot.record.call_count == 2
    saved = assets.get(p.conn, result["asset_id"])
    expected_n = (2 if collision == "alias" else 3) + int(race)
    assert saved["aliases"] == f"KELLY outfit {expected_n}"
    assert len(saved["images"]) == 2
    assert assets.link_characters(p.conn, pid, ["KELLY"])["KELLY"]["id"] == result["asset_id"]
