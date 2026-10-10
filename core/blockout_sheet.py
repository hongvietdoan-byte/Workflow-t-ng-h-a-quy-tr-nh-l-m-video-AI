"""12b.2: tấm duyệt 2D, gói blockout độc lập; chưa ghi Kho/nối pipeline hay chạy Blender.

Schema mới kind=blockout/schema_version=1, khác assets.profile.model3d hiện hành.
Gói giữ plan, SHA, người duyệt, phiên bản, thời điểm và issues khi duyệt.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont
from . import blockout as bo

COLORS = {"do": (215, 67, 67), "vang": (235, 180, 45), "ok": (146, 162, 176)}
SIZE = (1200, 1000)


def _sha(plan):
    return hashlib.sha256(json.dumps(plan, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _font(size):
    for name in ("C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def render_top_view(plan, cho_dung, out_png):
    """Vẽ PNG tại đường dẫn được giao; trả dữ liệu vẽ thật để kiểm nhãn/màu không cần OCR."""
    errors = bo.validate(plan)
    if errors:
        raise ValueError("; ".join(i["loi"] for i in errors))
    issues = bo.check_geometry(plan, cho_dung=cho_dung)
    width, depth = plan["san"]["kich_thuoc"]
    scale = min(800 / width, 800 / depth)
    image = Image.new("RGB", SIZE, "#f7f8fa")
    draw = ImageDraw.Draw(image)
    font, small = _font(14), _font(10)

    def point(x, y):
        return (450 + x * scale, 500 - y * scale)

    def column(n):
        name = ""
        while n >= 0:
            name = chr(65 + n % 26) + name
            n = n // 26 - 1
        return name

    draw.text((50, 35), "Sơ đồ khối · nhìn từ trên · +x Đông / +y Bắc · đơn vị m", font=font, fill="#172b3a")
    cells = []
    for axis, span in ((0, width), (1, depth)):
        for k in range(math.ceil(span * 4) + 1):
            value = -span / 2 + min(k / 4, span)
            ends = (point(value, -depth / 2), point(value, depth / 2)) if axis == 0 else (point(-width / 2, value), point(width / 2, value))
            draw.line(ends, fill="#e8edf1")
    # Ô 1 m; ô biên có thể nhỏ hơn 1 m khi sàn không nguyên mét.
    for i in range(math.ceil(width)):
        for j in range(math.ceil(depth)):
            x, y = -width / 2 + i, -depth / 2 + j
            a, b = point(x, y), point(min(x + 1, width / 2), min(y + 1, depth / 2))
            draw.rectangle((a[0], b[1], b[0], a[1]), outline="#d1d8de")
            label = f"{column(i)}{j + 1}"
            draw.text((a[0] + 2, b[1] + 2), label, font=small, fill="#687782")
            cells.append(label)
    blocks = []
    for i, block in enumerate(plan["khoi"]):
        matched = [issue for issue in issues if i in [int(n) for n in re.findall(r"khoi\[(\d+)\]", issue["path"])]]
        level = "do" if any(q["muc"] == "do" for q in matched) else ("vang" if matched else "ok")
        size = bo._size(block)
        polygon = [point(*p) for p in bo._rect(block["tam"], size, block["huong"])]
        color = COLORS[level]
        draw.polygon(polygon, fill=color, outline="#273743")
        label = f"{block['id']} · {block['loai']} · {'×'.join(f'{v:g}' for v in size)} m"
        draw.text(point(*block["tam"]), label, font=small, fill="#172b3a", anchor="mm")
        blocks.append({"id": block["id"], "label": label, "polygon": polygon, "level": level, "color": color})
    standing = []
    for i, at in enumerate(cho_dung or []):
        if not bo._vector(at, 2):
            continue  # lý do vẫn nằm trong issues, không giả vờ đã vẽ vị trí hỏng
        x, y = point(*at)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#245ccd")
        draw.text((x + 8, y), f"Đứng {i + 1}", font=small, fill="#245ccd")
        standing.append({"at": list(at), "label": f"Đứng {i + 1}"})
    ox, oy = point(0, 0)
    draw.text((ox + 8, oy + 8), "O", font=font, fill="#172b3a")
    a = math.radians(plan["huong_sang"])
    start, end = (930, 130), (930 + 65 * math.sin(a), 130 - 65 * math.cos(a))
    draw.line((start, end), fill="#b27c15", width=3)
    draw.ellipse((end[0] - 4, end[1] - 4, end[0] + 4, end[1] + 4), fill="#b27c15")
    draw.text((880, 175), f"Hướng sáng {plan['huong_sang']:g}°", font=font, fill="#172b3a")
    draw.text((880, 230), "ĐỎ: phải sửa · VÀNG: cần xem", font=small, fill="#172b3a")
    line_y = 265
    for issue in issues:
        text = f"{issue['path']}: {issue['loi']}"
        wrapped = textwrap.wrap(text, width=33)
        if line_y + len(wrapped) * 18 > 935:
            draw.text((880, 950), "Còn issue: xem danh sách dữ liệu trả về", font=small, fill=COLORS["do"])
            break
        for line in wrapped:
            draw.text((880, line_y), line, font=font, fill=COLORS[issue["muc"]])
            line_y += 18
        line_y += 10
    output = Path(out_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG")
    return {"size": SIZE, "cells": cells, "blocks": blocks, "standing": standing,
            "issues": issues, "light_direction": plan["huong_sang"], "out_png": str(output)}


def to_location_pack(plan, nguoi_duyet, phien_ban):
    """Đóng gói thuần dữ liệu; geometry ĐỎ không được duyệt, VÀNG được giữ để người duyệt biết."""
    if not isinstance(nguoi_duyet, str) or not nguoi_duyet.strip():
        raise ValueError("cần người duyệt")
    if not isinstance(phien_ban, int) or isinstance(phien_ban, bool) or phien_ban < 1:
        raise ValueError("phiên bản phải là số nguyên dương")
    issues = bo.check_geometry(plan)
    if any(i["muc"] == "do" for i in issues):
        raise ValueError("plan có issue ĐỎ: " + "; ".join(i["loi"] for i in issues if i["muc"] == "do"))
    return {"kind": "blockout", "schema_version": 1, "phien_ban": phien_ban,
            "nguoi_duyet": nguoi_duyet.strip(), "ngay": datetime.now(timezone.utc).isoformat(),
            "issues": deepcopy(issues), "sha256": _sha(plan), "plan": deepcopy(plan)}


def from_location_pack(pack):
    """Đọc gói đúng schema và SHA, không sửa gói gốc hay khóa model3d."""
    if not isinstance(pack, dict) or pack.get("kind") != "blockout" or pack.get("schema_version") != 1:
        raise ValueError("không phải location_pack blockout schema 1")
    if "plan" not in pack or pack.get("sha256") != _sha(pack["plan"]):
        raise ValueError("sha256 của plan không khớp")
    to_location_pack(pack["plan"], pack.get("nguoi_duyet"), pack.get("phien_ban"))
    try:
        datetime.fromisoformat(pack["ngay"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("ngày duyệt không hợp lệ") from error
    if pack.get("issues") != bo.check_geometry(pack["plan"]):
        raise ValueError("issues lúc duyệt không khớp plan")
    return deepcopy(pack["plan"])
