"""Định danh vai bằng CSDL giả; không ảnh, dữ liệu thật hay nhà cung cấp."""
import json
import os
import sqlite3
import unicodedata
from unittest import mock

import pytest

with mock.patch.object(os, "environ", {}):
    from core import change_audit, features, scene_storyboard


@pytest.fixture(autouse=True)
def isolate(tmp_path):
    with mock.patch.object(os, "environ", {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}), \
         mock.patch.object(features, "on", return_value=False), \
         mock.patch.object(scene_storyboard, "enabled", return_value=False), \
         mock.patch.object(change_audit, "_plate_rec", return_value=None):
        yield


@pytest.fixture
def conn():
    c=sqlite3.connect(":memory:"); c.row_factory=sqlite3.Row
    c.executescript("CREATE TABLE scenes(id INTEGER,project_id INTEGER,idx INTEGER,data TEXT);"
                    "CREATE TABLE assets(id INTEGER,kind TEXT,name TEXT,aliases TEXT,profile TEXT,project_id INTEGER);"
                    "CREATE TABLE characters(project_id INTEGER,name TEXT,ref_asset_id INTEGER);"
                    "CREATE TABLE project_assets(project_id INTEGER,asset_id INTEGER);"
                    "CREATE TABLE jobs(id INTEGER,scene_id INTEGER,type TEXT,state TEXT,sent_refs TEXT);")
    c.execute("INSERT INTO scenes VALUES(1,34,1,?)",(json.dumps({"characters":["RỐI ĐỎ"]}),))
    yield c
    c.close()


def asset(c,aid,name="RỐI ĐỎ",profile=None,kind="character",project=None,aliases=""):
    raw=json.dumps({"must_keep":"mặt nạ đỏ"}) if profile is None else profile
    c.execute("INSERT INTO assets VALUES(?,?,?,?,?,?)",(aid,kind,name,aliases,raw,project))


def findings(c,tmp_path):
    return [r for r in change_audit.audit_shot(c,str(tmp_path),34,1) if r["khau"] == "vai"]


def test_saved_id_wins_over_global_name_without_images(conn,tmp_path):
    asset(conn,454,profile='{}')
    asset(conn,900,"Red puppet")
    conn.execute("INSERT INTO characters VALUES(34,?,900)",(unicodedata.normalize("NFD","rối đỏ"),))
    assert findings(conn,tmp_path) == []


def test_saved_id_uses_profile_even_when_name_is_missing(conn,tmp_path):
    asset(conn,900,"Red puppet",profile='{}')
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',900)")
    result=findings(conn,tmp_path)
    assert len(result) == 1 and "#900" in result[0]["msg"] and "must_keep" in result[0]["msg"]


@pytest.mark.parametrize("saved,kind,project",[(999,"character",None),(0,"character",None),(900,"prop",None),(900,"character",35)])
def test_invalid_explicit_choice_does_not_fallback(conn,tmp_path,saved,kind,project):
    asset(conn,454)
    asset(conn,900,"Red puppet",kind=kind,project=project)
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',?)",(saved,))
    result=findings(conn,tmp_path)
    assert len(result) == 1 and result[0]["muc"] == "vang"


def test_other_project_character_does_not_override_this_project(conn,tmp_path):
    asset(conn,454)
    asset(conn,900,"Red puppet",profile='{}')
    conn.execute("INSERT INTO characters VALUES(35,'RỐI ĐỎ',900)")
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',NULL)")
    assert findings(conn,tmp_path) == []


def test_null_link_prefers_project_assets(conn,tmp_path):
    asset(conn,454,profile='{}')
    asset(conn,900)
    conn.execute("INSERT INTO project_assets VALUES(34,900)")
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',NULL)")
    assert findings(conn,tmp_path) == []


def test_duplicate_character_names_are_ambiguous(conn,tmp_path):
    asset(conn,454)
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',454)")
    conn.execute("INSERT INTO characters VALUES(34,'rối đỏ',454)")
    result=findings(conn,tmp_path)
    assert len(result) == 1 and result[0]["muc"] == "vang"


def test_global_name_fallback_never_picks_first_duplicate(conn,tmp_path):
    asset(conn,454)
    asset(conn,900)
    result=findings(conn,tmp_path)
    assert len(result) == 1 and result[0]["muc"] == "vang"


@pytest.mark.parametrize("legacy",["drop","no_link_column"])
def test_legacy_database_and_alias_match(conn,tmp_path,legacy):
    conn.execute("DROP TABLE characters")
    if legacy == "no_link_column":
        conn.execute("CREATE TABLE characters(project_id INTEGER,name TEXT)")
        conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ')")
    asset(conn,900,"Red puppet",aliases="Rối đỏ")
    assert findings(conn,tmp_path) == []


@pytest.mark.parametrize("profile",['{','[]','{"must_keep": 12}'])
def test_malformed_profile_is_yellow_without_crashing(conn,tmp_path,profile):
    asset(conn,900,profile=profile)
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',900)")
    result=findings(conn,tmp_path)
    assert len(result) == 1 and result[0]["muc"] == "vang"


def test_narrator_ignored_repeat_is_stable_and_readonly(conn,tmp_path):
    asset(conn,900,"Red puppet")
    conn.execute("INSERT INTO characters VALUES(34,'RỐI ĐỎ',900)")
    conn.execute("UPDATE scenes SET data=?",(json.dumps({"characters":["RỐI ĐỎ","LỜI DẪN"]}),))
    before=conn.total_changes
    first=findings(conn,tmp_path)
    assert first == findings(conn,tmp_path) == []
    assert conn.total_changes == before
