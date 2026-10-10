from html.parser import HTMLParser
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags = []; self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@pytest.mark.parametrize("name", ["video_3cot", "kho_nguon_dich"])
def test_mockups_offline_and_same_design_tokens(name):
    text = (ROOT / "mockup" / f"{name}.html").read_text(encoding="utf-8")
    tags = Tags(text).tags
    assert "12.5px" in text and "--primary:#4F46E5" in text
    assert "--bg:#F4F5F8" in text and 'lang="vi"' in text
    for tag, attrs in tags:
        for key in ("src", "href", "poster"):
            assert not re.match(r"https?:|//", attrs.get(key, ""))
    assert not re.search(r"fetch\(|XMLHttpRequest|url\(https?", text)
    paid = [a for t, a in tags if t == "button" and "data-paid" in a]
    assert paid and all("USD" in a.get("aria-label", "") for a in paid)


def test_video_has_all_review_inputs_and_nine_shots():
    text = (ROOT / "mockup/video_3cot.html").read_text(encoding="utf-8")
    tags = Tags(text).tags
    assert len([a for t, a in tags if "data-step" in a]) == 4
    assert len([a for t, a in tags if "data-shot" in a]) == 9
    assert len([a for t, a in tags if "data-check" in a]) == 4
    assert len([a for t, a in tags if "data-version" in a]) == 3
    assert "@image1 = Kelly · nhận diện" in text and "@image2 = nền 3D" in text
    assert "đang dùng" in text and "Xem prompt" in text
    assert all("open" not in a for t, a in tags if t == "details")
    assert "grid-template-columns:280px" in text


def test_library_pairs_and_mismatch_are_visible():
    text = (ROOT / "mockup/kho_nguon_dich.html").read_text(encoding="utf-8")
    assert "Nguồn" in text and "Đích" in text and "khai_bao_chu" in text
    assert "R1" in text and "đai đỏ" in text
