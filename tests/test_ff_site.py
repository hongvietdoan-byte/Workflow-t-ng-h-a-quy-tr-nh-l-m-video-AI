import json
import os
import shutil
import struct
import tempfile
import unittest
import zlib

from core import assets, ff_site
from core.db import connect


def png(seed: int) -> bytes:
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"\x00" + bytes([seed, 0, 0]) * 4
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def page(data) -> str:
    return "<html><script>window.__NUXT__=" + json.dumps({"data": data}) + ";</script></html>"


RAY = {"id": 796, "name": "Ray", "abstract": "Kẻ Phán Quyết", "en_name": "Ray", "sex": 1, "age": 24, "birthday": 1276941832, "introduction": "<p>Mệt mỏi với chiến đấu.</p>",
       "ability": "Phán Quyết", "ability_introduction": "Hạ gục ngay khi địch ít HP.", "cover_img": "https://c/r1.png", "head_icon": "https://c/r2.png",
       "character_pc": "https://c/r0.png", "awaken": 0, "next_char": {"id": 786, "name": "Morse"}}
MORSE = {"id": 786, "name": "Morse ", "abstract": "Điệp Viên Tàng Hình", "en_name": "Morse", "sex": 1, "age": 20, "introduction": "Tĩnh lặng.", "cover_img": "https://c/mo1.png",
         "awaken": 1, "awaken_name": "Morse Thức Tỉnh", "awaken_introduction": "Tàng hình lâu hơn.", "next_char": None}
PAGES = {
    f"{ff_site.BASE}/maps/": page([{}, {"mapList": [{"id": 1, "name": "Đảo Bình Minh", "abstract": "Thành phố cảng.", "map": "https://c/m1.jpg", "thumbnail": "https://c/t1.jpg",
                                                     "map_parts": [{"name": "Trạm Công Nghệ", "img": "https://c/a1.jpg", "img_zoom": "https://c/a1z.jpg", "abstract": ""},
                                                                   {"name": "Thác Nước", "img": "https://c/a2.jpg"}]}]}]),
    f"{ff_site.BASE}/pets/": page([{}, {"list": [{"id": 5, "name": "Kactus"}]}]),
    f"{ff_site.BASE}/pets/5/": page([{"petDetail": {"id": 5, "name": "Kactus", "abstract": "Cùng nhau sinh sôi!", "biography": "https://c/bio.png", "skill_name": "Tự cung tự cấp",
                                                    "skill_desc": "Hồi 10EP mỗi giây.", "pic4detail": "https://c/p2.png", "next_pet": {"id": 6, "name": "Fang"}}}]),
    f"{ff_site.BASE}/pets/6/": page([{"petDetail": {"id": 6, "name": "Fang", "abstract": "Trung thành", "pic4list": "https://c/p3.png", "next_pet": None}}]),
    f"{ff_site.BASE}/weapons/": page([{}, {}, {"data": [], "count": 0, "weapon_category": [{"id": -1, "name": "TẤT CẢ"}, {"id": 162, "name": "SR"}, {"id": 43, "name": "LMG"}]}]),
    f"{ff_site.BASE}/weapons/162/": page([{}, {}, {"data": [{"id": 9, "name": "VSK94", "abstract": "Súng ngắm nhẹ", "damage": 91, "range": 62, "tags": ["Tầm xa"],
                                                             "normal_img": "https://c/w1.png"}], "count": 1}]),
    f"{ff_site.BASE}/chars/": page([{}, {"list": [{"id": 796, "name": "Ray"}]}]),
    f"{ff_site.BASE}/chars/796/": page([{"charDetail": RAY}]),
    f"{ff_site.BASE}/chars/786/": page([{"charDetail": MORSE}]),
}


def getter(url):
    if url not in PAGES:
        raise ff_site.FfSiteError("404")
    return PAGES[url]


def download(url):
    return png(sum(map(ord, url)) % 250)


@unittest.skipUnless(shutil.which("node"), "cần Node.js")
class FfSiteTests(unittest.TestCase):
    def setUp(self):
        ff_site.PAUSE = 0
        self.dir = tempfile.mkdtemp()
        os.environ["ASSET_DIR"] = os.path.join(self.dir, "assets")
        self.conn = connect(os.path.join(self.dir, "m.sqlite"))

    def tearDown(self):
        os.environ.pop("ASSET_DIR", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def names(self):
        return {(a["kind"], a["name"]): a for a in assets.list_assets(self.conn, "FF", None, None, shared_only=True)}

    def test_maps_areas_pets_weapons_and_characters_are_read_from_the_public_pages(self):
        report = ff_site.sync(self.conn, "FF", "x@garena.vn", getter, download)
        got = self.names()
        self.assertIn(("location", "Đảo Bình Minh"), got)
        self.assertIn(("location", "Trạm Công Nghệ"), got)                              # every area of a map is its own entry
        self.assertIn("Các khu vực: Trạm Công Nghệ, Thác Nước", got[("location", "Đảo Bình Minh")]["description"])
        self.assertIn(("pet", "Kactus"), got)
        self.assertIn(("pet", "Fang"), got)                                              # reached by following the "next" link of the previous pet
        self.assertIn("Hồi 10EP mỗi giây.", got[("pet", "Kactus")]["description"])
        self.assertNotIn("https://c/bio.png", got[("pet", "Kactus")]["description"])     # a picture link is not text
        self.assertIn("sát thương 91", got[("weapon", "VSK94")]["description"])
        self.assertIn("(SR)", got[("weapon", "VSK94")]["description"])
        ray = got[("character", "Ray")]
        self.assertIn("Kỹ năng Phán Quyết: Hạ gục ngay khi địch ít HP.", ray["description"])
        self.assertIn("Mệt mỏi với chiến đấu.", ray["description"])                      # HTML tags are stripped
        self.assertIn("24 tuổi", ray["description"])
        self.assertEqual(len(ray["images"]), 3)
        self.assertIn(("character", "Morse"), got)                                       # reached by following "next" from Ray
        self.assertIn("Thức tỉnh Morse Thức Tỉnh", got[("character", "Morse")]["description"])
        self.assertEqual(report["created"], 8)

    def test_running_it_again_changes_nothing(self):
        ff_site.sync(self.conn, "FF", None, getter, download)
        before = {k: (a["description"], len(a["images"])) for k, a in self.names().items()}
        report = ff_site.sync(self.conn, "FF", None, getter, download)
        self.assertEqual((report["created"], report["enriched"], report["pictures"]), (0, 0, 0))
        self.assertEqual(before, {k: (a["description"], len(a["images"])) for k, a in self.names().items()})

    def test_an_existing_entry_keeps_what_was_written_and_gets_a_replaceable_block(self):
        aid = assets.create(self.conn, "FF", "character", "RAY", "Áo khoác đen, tóc bạc", "", None, "x")
        assets.add_image(self.conn, aid, "ray.png", png(200))
        ff_site.sync(self.conn, "FF", None, getter, download)
        a = assets.get(self.conn, aid)
        self.assertTrue(a["description"].startswith("Áo khoác đen, tóc bạc"))
        self.assertEqual(a["description"].count(ff_site.MARK), 1)
        self.assertEqual(len(assets.list_assets(self.conn, "FF", "character", None, shared_only=True)), 2)   # not duplicated: RAY + Morse
        self.assertEqual(len(a["images"]), 4)                                            # the Drive picture stays, official pictures are added
        PAGES_KEY = f"{ff_site.BASE}/chars/796/"
        old = PAGES[PAGES_KEY]
        try:
            PAGES[PAGES_KEY] = page([{"charDetail": dict(RAY, ability_introduction="Hạ gục ngay và hồi máu.")}])
            ff_site.sync(self.conn, "FF", None, getter, download)
        finally:
            PAGES[PAGES_KEY] = old
        a = assets.get(self.conn, aid)
        self.assertEqual(a["description"].count(ff_site.MARK), 1)                        # the block was replaced, not stacked
        self.assertIn("hồi máu", a["description"])
        self.assertTrue(a["description"].startswith("Áo khoác đen, tóc bạc"))

    def test_a_failing_download_is_skipped_and_the_rest_is_kept(self):
        def flaky(url):
            if "m1" in url:
                raise ff_site.FfSiteError("boom")
            return download(url)
        report = ff_site.sync(self.conn, "FF", None, getter, flaky)
        self.assertGreaterEqual(report["skipped"], 1)
        self.assertIn(("location", "Đảo Bình Minh"), self.names())

    def test_the_monthly_refresh_waits_a_month_and_never_starts_by_surprise(self):
        db = os.path.join(self.dir, "m.sqlite")
        os.environ["FF_SITE_AUTO"] = "1"
        try:
            self.assertFalse(ff_site.maybe_monthly(db))                                  # empty library: nothing to refresh
            from core import lessons
            lessons.set_meta(self.conn, "ff_site_last", ff_site._now())
            self.assertFalse(ff_site.maybe_monthly(db))                                  # done just now
        finally:
            os.environ["FF_SITE_AUTO"] = "0"


if __name__ == "__main__":
    unittest.main()
