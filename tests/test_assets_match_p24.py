"""08/10 dự án #24 (kịch bản thật tests/fixtures/p24_script.txt): gợi ý "Tài nguyên đi kèm kịch bản" và auto_attach ghép sai
- "Quảng Trường · Địa điểm · Đảo Thế Kỷ": kịch bản ghi "QUẢNG TRƯỜNG THÁP ĐỒNG HỒ" — danh từ chung chỉ khu vực của Tháp Đồng Hồ;
  auto_attach còn TỰ GẮN nó sau khi chạy Director (người dùng phải gỡ tay);
- "Đao · Vũ khí": "Đạo cụ:" / "ĐẠO CỤ" bỏ dấu thành "dao cu" khớp "Đao"."""
import os
import unittest

from core import assets
from core.db import connect
from core.pipeline import Pipeline

SCRIPT = open(os.path.join(os.path.dirname(__file__), "fixtures", "p24_script.txt"), encoding="utf-8").read()


class AssetMatchP24Tests(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline(connect())
        self.conn = self.p.conn
        self.pid = self.p.create_project("p24", game="FF")
        self.conn.execute("UPDATE projects SET script_text=? WHERE id=?", (SCRIPT, self.pid))
        self.conn.commit()
        make = lambda kind, name, aliases="": assets.create(self.conn, "FF", kind, name, aliases=aliases)  # noqa: E731
        self.kelly = make("character", "KELLY")
        self.square = make("location", "Quảng Trường")
        self.tower = make("location", "Tháp Đồng Hồ")
        self.blade = make("weapon", "Đao")
        self.well = make("prop", "GIẾNG ĐÁ CỔ")

    def suggested(self):
        return {a["id"] for a in assets.find_in_text(self.conn, SCRIPT, "FF", self.pid)}

    def test_suggestions_skip_the_area_word_and_the_accent_mismatch(self):
        got = self.suggested()
        self.assertIn(self.tower, got)
        self.assertIn(self.kelly, got)
        self.assertIn(self.well, got)
        self.assertNotIn(self.square, got)          # "QUẢNG TRƯỜNG THÁP ĐỒNG HỒ" = an area of Tháp Đồng Hồ
        self.assertNotIn(self.blade, got)           # "ĐẠO CỤ" ≠ "Đao"

    def test_auto_attach_never_attaches_the_area_word(self):
        assets.attach(self.conn, self.pid, self.tower)
        r = assets.auto_attach(self.conn, self.pid)
        attached = {a["id"] for a in assets.project_assets(self.conn, self.pid)}
        self.assertNotIn(self.square, attached)
        self.assertNotIn(self.blade, attached)
        self.assertIn("Quảng Trường", r["ambiguous"])          # said, not silently dropped (luật 1)
        self.assertIn(self.kelly, attached)

    def test_text_typed_without_accents_still_finds_names(self):
        got = {a["id"] for a in assets.find_in_text(self.conn, "Kelly di toi thap dong ho", "FF", self.pid)}
        self.assertIn(self.tower, got)

    def test_a_square_said_on_its_own_is_still_suggested(self):
        got = {a["id"] for a in assets.find_in_text(self.conn, "Kelly chạy qua Quảng Trường lúc trưa.", "FF", self.pid)}
        self.assertIn(self.square, got)


if __name__ == "__main__":
    unittest.main()
