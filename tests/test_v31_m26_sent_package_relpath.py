"""C-M26 — V3.1 M2.6 (G5): sổ gói gửi gán nhãn ảnh theo ĐƯỜNG DẪN (rel_path, + asset_id khi có), không theo tên tệp — hai mục Kho
cùng `2.png` (#443, #367) khác thư mục từng chung một nhãn. Cờ `sent_package_relpath` TẮT = gói giống byte (prompt gửi model chưa bao giờ
sai — chỉ SỔ). Thiết kế docs/V3_1_M2_THIET_KE_CON_LAI_2026-10-20.md mục 2."""
import json
import os
import tempfile
from unittest import mock

import pytest

from core import sent_package

ON = mock.patch.dict(os.environ, {"FEATURE_SENT_PACKAGE_RELPATH": "1"})
OFF = mock.patch.dict(os.environ, {"FEATURE_SENT_PACKAGE_RELPATH": ""})


def submit(prompt, references=None):            # the signature build() binds against (an image provider)
    return "t1"


@pytest.fixture
def two_same_names():
    d = tempfile.mkdtemp()
    out = []
    for asset, label in ((443, "KELLY"), (367, "THÁP ĐỒNG HỒ")):
        os.makedirs(os.path.join(d, str(asset)))
        p = os.path.join(d, str(asset), "2.png")
        with open(p, "wb") as f:
            f.write(f"picture of {label}".encode("utf-8"))
        out.append({"path": p, "label": label, "role": "character" if asset == 443 else "place", "asset_id": asset})
    return out


def _pkg(refs, meta):
    text, warns = sent_package.build(submit, ("p", [r["path"] for r in refs]), {}, kind="image", provider=object(), external_id="t1",
                                     meta=meta)
    return json.loads(text), warns


def test_two_pictures_with_the_same_name_keep_their_own_label(two_same_names):
    with ON:
        meta = [sent_package.meta_entry(r) for r in two_same_names]
        pkg, warns = _pkg(two_same_names, meta)
    assert [(r["label"], r["asset_id"]) for r in pkg["refs"]] == [("KELLY", 443), ("THÁP ĐỒNG HỒ", 367)]
    assert pkg["v"] == 2 and warns == []


def test_old_meta_with_only_file_unique_name_still_labels(two_same_names):
    one = two_same_names[:1]
    with ON:
        pkg, warns = _pkg(one, [{"label": "KELLY", "role": "character", "file": "2.png"}])
    assert pkg["refs"][0]["label"] == "KELLY" and warns == []


def test_old_meta_with_a_shared_name_is_not_guessed(two_same_names):
    old = [{"label": r["label"], "role": r["role"], "file": "2.png"} for r in two_same_names]
    with ON:
        pkg, warns = _pkg(two_same_names, old)
    assert [r["label"] for r in pkg["refs"]] == [None, None]
    assert any("cùng tên 2.png" in w and "không gán nhãn theo tên" in w for w in warns)


def test_flag_off_is_byte_for_byte_the_old_package(two_same_names):
    old_meta = [{"label": r["label"], "role": r["role"], "file": "2.png"} for r in two_same_names]
    with OFF:
        assert sent_package.meta_entry(two_same_names[0]) == {"label": "KELLY", "role": "character", "file": "2.png"}
        with mock.patch.object(sent_package.datetime, "datetime") as dt:
            dt.now.return_value.isoformat.return_value = "T"
            new, _ = sent_package.build(submit, ("p", [r["path"] for r in two_same_names]), {}, kind="image", provider=object(),
                                        external_id="t1", meta=[sent_package.meta_entry(r) for r in two_same_names])
            old, _ = sent_package.build(submit, ("p", [r["path"] for r in two_same_names]), {}, kind="image", provider=object(),
                                        external_id="t1", meta=old_meta)
    assert new == old
    pkg = json.loads(new)
    assert pkg["v"] == 1 and [r["label"] for r in pkg["refs"]] == ["KELLY", "KELLY"]   # cái sai cũ còn nguyên khi TẮT (G5)
    assert "asset_id" not in pkg["refs"][0]


def test_every_meta_site_uses_the_shared_entry():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("core/runner.py", "core/end_frames.py"):
        src = open(os.path.join(root, rel), encoding="utf-8").read()
        assert '"file": os.path.basename(r["path"])' not in src, rel
        assert "meta_entry(" in src, rel
