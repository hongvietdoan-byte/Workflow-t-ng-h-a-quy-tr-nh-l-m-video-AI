"""Lỗi 11 (#27): Kho chủ thể ClipAI đầy 100/100 → nhận diện rõ, không ghi 'failed' vĩnh viễn, đề xuất dọn + xóa có kiểm lại."""
import json
import os
import tempfile
import unittest

from core import subjects
from core.access import AccessDenied
from core.adapters.clipai_subjects import ClipAISubjectLibrary, MockSubjectLibrary, is_library_full
from core.db import connect
from core.pipeline import Pipeline
from core.providers import ProviderError
from tests.test_adapters import TOKEN, FakeTransport, HttpResponse, ok

FULL_MSG = "Each user can upload up to 100 assets"


def image(name="pic.png", data=b"\x89PNG-fake"):
    path = os.path.join(tempfile.mkdtemp(), name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def asset(i, status="active", name=None):
    return {"id": i, "asset_id": f"asset-{i}", "asset_uri": f"asset://asset-{i}" if status == "active" else None,
            "name": name or f"n{i}", "provider_status": status, "asset_type": "image"}


class AdapterDeleteAndFullTests(unittest.TestCase):
    def setUp(self):
        self.t = FakeTransport()
        self.lib = ClipAISubjectLibrary(TOKEN, "https://clipai.example", self.t, sleep=lambda s: None, poll_sec=1, timeout_sec=5)
        self.assets = [asset(1), asset(2)]
        self.t.on("GET", "/api/kling/seedance-user-asset-list", lambda call: ok({"count": len(self.assets), "assets": list(self.assets)}))

    def test_delete_posts_the_provider_id_and_checks_the_list_after(self):
        def drop(call):
            body = json.loads(call["body"].decode("utf-8"))
            self.assets = [a for a in self.assets if a["asset_id"] != body["asset_id"]]
            return HttpResponse(200, json.dumps({"status": "success", "msg": "ok", "data": None}).encode())
        self.t.on("POST", "/api/kling/seedance-user-asset-delete", drop)
        gone = self.lib.delete("asset-1")
        self.assertEqual(gone["asset_id"], "asset-1")
        post = [c for c in self.t.calls if c["method"] == "POST"]
        self.assertEqual(json.loads(post[0]["body"].decode("utf-8")), {"asset_id": "asset-1"})
        self.assertEqual([a["asset_id"] for a in self.assets], ["asset-2"])

    def test_delete_that_left_the_asset_listed_is_an_error_not_silence(self):
        self.t.on("POST", "/api/kling/seedance-user-asset-delete", ok(None))
        with self.assertRaises(ProviderError) as e:
            self.lib.delete("asset-1")
        self.assertEqual(e.exception.code, "delete_unverified")

    def test_delete_of_an_unknown_or_numeric_id_sends_nothing(self):
        self.t.on("POST", "/api/kling/seedance-user-asset-delete", ok(None))
        for bad in ("asset-404", "7", ""):
            with self.assertRaises(ProviderError):
                self.lib.delete(bad)
        self.assertFalse([c for c in self.t.calls if c["method"] == "POST"])

    def test_upload_into_a_full_library_raises_library_full(self):
        self.t.on("POST", "/api/kling/seedance-user-asset-upload",
                  HttpResponse(200, json.dumps({"code": 400, "msg": FULL_MSG}).encode()))
        with self.assertRaises(ProviderError) as e:
            self.lib.upload(image(), "FF_KELLY_x")
        self.assertEqual(e.exception.code, "library_full")
        self.assertIn("100/100", str(e.exception))
        self.assertTrue(is_library_full(FULL_MSG))
        self.assertFalse(is_library_full("real person detected"))
        self.assertFalse(is_library_full("please upload an asset up to 30MB"))      # a file-size refusal is not 'library full'
        self.assertFalse(is_library_full("each user can upload files up to 10 MB per asset"))

    def test_mock_delete(self):
        lib = MockSubjectLibrary()
        self.assertEqual(lib.delete("asset-mock-abc")["asset_id"], "asset-mock-abc")
        with self.assertRaises(ProviderError):
            lib.delete("asset-other")


class FullLibrary:
    """Library double: holds assets, refuses uploads while full (the ClipAI answer)."""

    def __init__(self, assets=(), full=True):
        self.assets = {a["asset_id"]: a for a in assets}
        self.full, self.uploads, self.deleted = full, [], []

    def list_assets(self, asset_type=None, page_size=100):
        return list(self.assets.values())

    def get(self, asset_id):
        return self.assets.get(asset_id)

    def upload(self, path, name, wait=True):
        self.uploads.append(name)
        if self.full:
            raise ProviderError(f"API error (code=400): {FULL_MSG}", code="api_error")
        a = {"asset_id": f"asset-new-{len(self.uploads)}", "asset_uri": f"asset://new-{len(self.uploads)}", "name": name,
             "provider_status": "active"}
        self.assets[a["asset_id"]] = a
        return a

    def delete(self, asset_id):
        if asset_id not in self.assets:
            raise ProviderError("asset not found in your library", code="not_found")
        self.deleted.append(asset_id)
        return self.assets.pop(asset_id)


class FullLibraryPipelineTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()

    def test_full_library_is_not_remembered_as_refused_and_uploads_after_cleanup(self):
        lib = FullLibrary()
        path = image()
        with self.assertRaises(ProviderError) as e:
            subjects.ensure_picture(self.conn, lib, path, "FF_KELLY")
        self.assertEqual(e.exception.code, "library_full")
        self.assertIsNone(subjects.picture_row(self.conn, subjects.picture_sha(path)))   # never 'failed'
        lib.full = False                                                                  # someone cleaned the library
        self.assertTrue(subjects.ensure_picture(self.conn, lib, path, "FF_KELLY")["uploaded"])

    def test_picture_refs_says_the_library_is_full_and_stops_uploading(self):
        lib = FullLibrary()
        res = subjects.picture_refs(self.conn, lib, [("frame", image("f.png", b"1")), ("KELLY", image("k.png", b"2"))])
        self.assertIsNone(res["refs"])
        self.assertTrue(res["library_full"])
        self.assertIn("đầy", res["problems"][0])
        self.assertIn("100/100", res["problems"][0])
        self.assertEqual(len(lib.uploads), 1)                     # the second picture is not uploaded into a full library


class CleanupPlanTests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.live = self.p.create_project("đang làm")
        self.done = self.p.create_project("đã giao")
        self.conn.execute("UPDATE projects SET archived=1 WHERE id=?", (self.done,))
        self.conn.commit()
        subjects._pictures_table(self.conn)
        rows = [("s1", "live_pic", "asset-1", f"data/{self.live}/refs_clean/a.png", "2026-10-10 10:00:00"),
                ("s2", "done_pic", "asset-2", os.path.join("D:", os.sep, "x", "data", str(self.done), "frames", "b.png"),
                 "2026-10-01 10:00:00")]
        for sha, name, aid, path, at in rows:
            self.conn.execute("INSERT INTO seedance_subject_pictures (sha, name, asset_id, asset_uri, status, path, updated_at)"
                              " VALUES (?,?,?,?,?,?,?)", (sha, name, aid, f"asset://{aid}", "active", path, at))
        self.conn.execute("INSERT INTO characters (project_id, name, description, subject_asset_id, subject_asset_uri, subject_status) "
                          "VALUES (?,?,'',?,?,?)", (self.live, "Kelly", "asset-5", "asset://asset-5", "active"))
        self.conn.commit()
        self.lib = FullLibrary([asset(1), asset(2), asset(3), asset(4, "failed"), asset(5), asset(6)])

    def test_overview_classifies_and_orders_suggestions(self):
        ov = subjects.library_overview(self.conn, self.lib)
        self.assertEqual((ov["count"], ov["limit"]), (6, 100))
        cat = {a["asset_id"]: a["category"] for a in ov["assets"]}
        self.assertEqual(cat, {"asset-1": "in_use", "asset-2": "done_project", "asset-3": "orphan", "asset-4": "rejected",
                               "asset-5": "in_use", "asset-6": "orphan"})
        self.assertEqual(ov["suggested"], ["asset-4", "asset-3", "asset-6", "asset-2"])     # refused, unused oldest first, then done
        by = {a["asset_id"]: a for a in ov["assets"]}
        self.assertIn(f"#{self.live}", " ".join(by["asset-5"]["users"]))
        self.assertEqual(by["asset-2"]["last_used"], "2026-10-01 10:00:00")

    def test_real_layout_data_projects_and_the_P_label_decide_the_project(self):
        subjects._save_picture(self.conn, "s7", f"P{self.live}_S3_frame_abcdef123456", "active",
                               {"asset_id": "asset-7", "asset_uri": "asset://asset-7"}, None,
                               os.path.join("C:", os.sep, "elsewhere", "refs_clean", "x.png"))           # label only
        subjects._save_picture(self.conn, "s8", "pic_abcdef123456", "active", {"asset_id": "asset-8", "asset_uri": "asset://asset-8"},
                               None, os.path.join("D:", os.sep, "AI", "data", "projects", str(self.live), "frames", "y.png"))
        subjects._save_picture(self.conn, "s9", f"P{self.done}_KELLY_abcdef123456", "active",       # first used by a finished project,
                               {"asset_id": "asset-9", "asset_uri": "asset://asset-9"}, None,      # last by the live one
                               f"data/projects/{self.live}/refs_clean/z.png")
        lib = FullLibrary([asset(7), asset(8), asset(9)])
        cat = {a["asset_id"]: a["category"] for a in subjects.library_overview(self.conn, lib)["assets"]}
        self.assertEqual(cat, {"asset-7": "in_use", "asset-8": "in_use", "asset-9": "in_use"})
        with self.assertRaises(ValueError):
            subjects.delete_assets(self.conn, lib, ["asset-8"])

    def test_delete_refuses_in_use_and_cleans_rows_so_the_next_run_uploads_again(self):
        with self.assertRaises(ValueError):
            subjects.delete_assets(self.conn, self.lib, ["asset-1"])
        self.assertEqual(self.lib.deleted, [])
        res = subjects.delete_assets(self.conn, self.lib, ["asset-2", "asset-404"])
        self.assertEqual(res["deleted"], ["asset-2"])
        self.assertEqual([e[0] for e in res["errors"]], ["asset-404"])
        self.assertIsNone(subjects.picture_row(self.conn, "s2"))
        self.assertIsNotNone(subjects.picture_row(self.conn, "s1"))

    def test_delete_unlinks_characters_of_a_finished_project(self):
        self.conn.execute("INSERT INTO characters (project_id, name, description, subject_asset_id, subject_asset_uri, subject_status) "
                          "VALUES (?,?,'',?,?,?)", (self.done, "Kenta", "asset-6", "asset://asset-6", "active"))
        self.conn.commit()
        self.assertEqual({a["asset_id"]: a["category"] for a in subjects.library_overview(self.conn, self.lib)["assets"]}["asset-6"],
                         "done_project")
        subjects.delete_assets(self.conn, self.lib, ["asset-6"])
        row = self.conn.execute("SELECT subject_asset_id FROM characters WHERE name='Kenta'").fetchone()
        self.assertIsNone(row["subject_asset_id"])

    def test_delete_needs_the_assets_right(self):
        member = {"email": "a@b.vn", "role": "member", "perms": []}
        with self.assertRaises(AccessDenied):
            subjects.delete_assets(self.conn, self.lib, ["asset-3"], who=member)
        self.assertEqual(self.lib.deleted, [])
        subjects.delete_assets(self.conn, self.lib, ["asset-3"], who={**member, "perms": ["assets"]})
        self.assertEqual(self.lib.deleted, ["asset-3"])


class SubjectLibraryBoxUiTests(unittest.TestCase):
    """Khối «Kho chủ thể ClipAI» ở Kho tài nguyên: đọc khi bấm, số dùng/100, chọn theo gợi ý, xóa phải qua câu hỏi Có/Không."""

    def setUp(self):
        from unittest import mock
        tmp = tempfile.mkdtemp()
        self.db = os.path.join(tmp, "s.sqlite")
        env = mock.patch.dict(os.environ, {"PIPELINE_DB": self.db, "PIPELINE_DATA": os.path.join(tmp, "projects"),
                                           "DASHBOARD_AUTH": "off", "FEATURE_SETTINGS_FILE": os.path.join(tmp, "fs.json")})
        env.start()
        self.addCleanup(env.stop)
        Pipeline(connect(self.db)).create_project("đang làm")

    def test_read_count_suggest_and_delete_after_yes(self):
        from streamlit.testing.v1 import AppTest

        def page():
            import os
            import streamlit as st
            from core.adapters import factory
            from core.providers import ProviderError
            from dashboard import admin, common

            class Lib:
                def __init__(self):
                    self.assets = {a["asset_id"]: a for a in (
                        {"id": 3, "asset_id": "asset-3", "asset_uri": "asset://asset-3", "name": "n3", "provider_status": "active"},
                        {"id": 4, "asset_id": "asset-4", "asset_uri": None, "name": "n4", "provider_status": "failed"})}

                def list_assets(self, asset_type=None, page_size=100):
                    return list(self.assets.values())

                def delete(self, asset_id):
                    if asset_id not in self.assets:
                        raise ProviderError("not found", code="not_found")
                    st.session_state.setdefault("deleted_ids", []).append(asset_id)
                    return self.assets.pop(asset_id)
            factory.subject_library = Lib
            common.DB = os.environ["PIPELINE_DB"]
            admin.subject_library_box(admin.Pipeline(admin.connect(os.environ["PIPELINE_DB"])))
        at = AppTest.from_function(page, default_timeout=60).run()
        self.assertFalse(at.exception, at.exception)
        self.assertNotIn("subj_lib_pick", [m.key for m in at.multiselect])          # nothing read before the button
        at.button(key="subj_lib_read").click().run()
        self.assertIn("2 / 100", " ".join(i.value for i in at.info))
        at.button(key="subj_lib_suggest").click().run()
        self.assertEqual(at.multiselect(key="subj_lib_pick").value, ["asset-4", "asset-3"])
        at.button(key="subj_lib_del").click().run()
        self.assertNotIn("deleted_ids", at.session_state)                              # asked first, nothing deleted yet
        self.assertIn("KHÔNG hoàn tác", " ".join(w.value for w in at.warning))
        at.button(key="subj_lib_del_yes").click().run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["deleted_ids"], ["asset-4", "asset-3"])
        self.assertIn("Đã xóa 2 asset", " ".join(s.value for s in at.success))
        self.assertNotIn("subj_lib_pick", [m.key for m in at.multiselect])          # old table gone: read again to see the new count


if __name__ == "__main__":
    unittest.main()
