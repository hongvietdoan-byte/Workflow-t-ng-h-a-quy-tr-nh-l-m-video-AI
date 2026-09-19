import json
import os
import tempfile
import unittest
import zipfile

from core.db import connect
from core.pipeline import Pipeline
from core.script_parser import import_scenes, parse_docx, split_scenes

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    fd, path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", xml)
    return path


SCRIPT = [
    "Trailer Ep.1",
    "CẢNH 1 - Đêm, rừng Elder",
    "Sương mù dày đặc.",
    "LYRA: Ta nghe thấy tiếng gì đó.",
    "KAEL: Cẩn thận.",
    "LYRA: Đi thôi.",
    "Cảnh 2 - Ngày, pháo đài",
    "Kael đứng trên tường thành.",
    "Ông Orin: Bọn chúng đến rồi.",
    "INT. HẦM NGẦM - ĐÊM",
    "Ánh nến chập chờn.",
]


class ScriptParserTests(unittest.TestCase):
    def test_splits_scenes_and_drops_title_preamble(self):
        scenes = split_scenes(SCRIPT)
        self.assertEqual([s.heading for s in scenes],
                         ["CẢNH 1 - Đêm, rừng Elder", "Cảnh 2 - Ngày, pháo đài", "INT. HẦM NGẦM - ĐÊM"])
        self.assertEqual([s.idx for s in scenes], [1, 2, 3])

    def test_detects_characters_by_frequency(self):
        scenes = split_scenes(SCRIPT)
        self.assertEqual(scenes[0].characters, ["LYRA", "KAEL"])
        self.assertEqual(scenes[1].characters, ["ÔNG ORIN"])

    def test_no_headings_gives_single_scene(self):
        scenes = split_scenes(["Một đoạn văn.", "Đoạn nữa."])
        self.assertEqual(len(scenes), 1)

    def test_reads_docx_and_imports_to_db(self):
        path = make_docx(SCRIPT)
        try:
            scenes = parse_docx(path)
        finally:
            os.remove(path)
        p = Pipeline(connect())
        pid = p.create_project("t")
        ids = import_scenes(p, pid, scenes)
        self.assertEqual(len(ids), 3)
        row = p.conn.execute("SELECT data FROM scenes WHERE id=?", (ids[0],)).fetchone()
        self.assertEqual(json.loads(row["data"])["characters"], ["LYRA", "KAEL"])


if __name__ == "__main__":
    unittest.main()
