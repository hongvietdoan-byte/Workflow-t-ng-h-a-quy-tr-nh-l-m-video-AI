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
import warnings

from PIL import Image, ImageDraw, ImageFont
from . import blockout as bo
from . import stage_grid as sg

COLORS = {"do": (215, 67, 67), "vang": (235, 180, 45), "ok": (146, 162, 176)}
SIZE = (1200, 1000)
# Lưới chuẩn mục 2.3 (N = 20, c = 1 m, O ở góc Tây-Nam ô K11) — tên ô lấy từ stage_grid, một nguồn với solver/Director.
GRID = sg.make_stage([0, 0, 0])


def _edges(span, step=1.0):
    """Mốc đường lưới trên một trục sàn [-span/2, span/2]: bội số nguyên của `step` tính từ O, cộng hai mép sàn."""
    half = span / 2
    inner = [k * step for k in range(math.floor(-half / step) + 1, math.ceil(half / step))]
    return [-half] + [v for v in inner if -half < v < half] + [half]


def _standing_xy(at):
    """Chỗ đứng [x,y] hoặc {"tam": [x,y]} (như check_geometry nhận) → [x,y]; dạng khác → None."""
    p = at.get("tam") if isinstance(at, dict) else at
    return list(p) if bo._vector(p, 2) else None


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

    draw.text((50, 35), "Sơ đồ khối · nhìn từ trên · +x Đông / +y Bắc · đơn vị m", font=font, fill="#172b3a")
    cells, cell_boxes, off_grid = [], [], 0
    # Đường lưới phụ 0,25 m và ô 1 m đều neo vào mét nguyên quanh O (mục 2.3), không neo góc sàn:
    # sàn 8×6 hay 7×5 vẫn gọi ô chứa (0,5; 0,5) là K11 như stage_grid; ô biên bị cắt khi mép sàn không trùng mét nguyên.
    for axis, span in ((0, width), (1, depth)):
        for value in _edges(span, .25):
            ends = (point(value, -depth / 2), point(value, depth / 2)) if axis == 0 else (point(-width / 2, value), point(width / 2, value))
            draw.line(ends, fill="#e8edf1")
    xs, ys = _edges(width), _edges(depth)
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            a, b = point(x0, y0), point(x1, y1)
            draw.rectangle((a[0], b[1], b[0], a[1]), outline="#d1d8de")
            label = sg.cell_name(GRID, (x0 + x1) / 2, (y0 + y1) / 2)
            if label is None:   # sàn rộng hơn lưới chuẩn 20×20 m: không bịa tên
                off_grid += 1
                continue
            draw.text((a[0] + 2, b[1] + 2), label, font=small, fill="#687782")
            cells.append(label)
            cell_boxes.append({"name": label, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    if off_grid:
        issues.append(bo._issue("vang", "san.kich_thuoc", f"{off_grid} ô nằm ngoài lưới chuẩn 20×20 m — không có tên ô", "off_grid"))
    blocks = []
    for i, block in enumerate(plan["khoi"]):
        matched = [issue for issue in issues if i in [int(n) for n in re.findall(r"khoi\[(\d+)\]", issue["path"])]]
        level = "do" if any(q["muc"] == "do" for q in matched) else ("vang" if matched else "ok")
        size = bo._size(block)
        polygon = [point(*p) for p in bo._rect(block["tam"], size, block["huong"])]
        color = COLORS[level]
        shape = "ellipse" if block["loai"] in ("tru", "cot") else "polygon"
        if shape == "ellipse":
            # Ellipse xoay cùng chân đế (cột tròn có hai kích thước bằng nhau).
            a = math.radians(block["huong"])
            cx, cy = block["tam"]
            oval = [point(cx + size[0]/2*math.cos(t)*math.cos(a) - size[1]/2*math.sin(t)*math.sin(a),
                          cy + size[0]/2*math.cos(t)*math.sin(a) + size[1]/2*math.sin(t)*math.cos(a))
                    for t in [n*math.tau/64 for n in range(64)]]
            draw.polygon(oval, fill=color, outline="#273743")
        else:
            draw.polygon(polygon, fill=color, outline="#273743")
        label = f"{block['id']} · {block['loai']} · {'×'.join(f'{v:g}' for v in size)} m"
        # Mép sàn gần mép ảnh: giữ toàn bộ nhãn trong canvas, có bounds để QA.
        tx, ty = point(*block["tam"])
        bb = draw.textbbox((0, 0), label, font=small)
        tx = max(4-bb[0], min(tx-(bb[2]-bb[0])/2, SIZE[0]-4-bb[2]))
        ty = max(4-bb[1], min(ty-(bb[3]-bb[1])/2, SIZE[1]-4-bb[3]))
        label_box = draw.textbbox((tx, ty), label, font=small)
        draw.text((tx, ty), label, font=small, fill="#172b3a")
        blocks.append({"id": block["id"], "label": label, "label_box":label_box,
                       "polygon": polygon, "shape": shape, "level": level, "color": color})
    standing = []
    for i, at in enumerate(cho_dung or []):
        xy = _standing_xy(at)
        if xy is None:   # không giả vờ đã vẽ, cũng không bỏ im lặng
            issues.append(bo._issue("vang", f"cho_dung[{i}]",
                                    f"không vẽ được chỗ đứng {i + 1}: cần [x,y] hoặc {{\"tam\": [x,y]}}, nhận {type(at).__name__}",
                                    "standing_not_drawn"))
            continue
        x, y = point(*xy)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#245ccd")
        draw.text((x + 8, y), f"Đứng {i + 1}", font=small, fill="#245ccd")
        standing.append({"at": xy, "label": f"Đứng {i + 1}"})
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
    return {"size": SIZE, "cells": cells, "cell_boxes": cell_boxes, "blocks": blocks, "standing": standing,
            "issues": issues, "light_direction": plan["huong_sang"], "out_png": str(output)}


def _check_approval(nguoi_duyet, phien_ban):
    if not isinstance(nguoi_duyet, str) or not nguoi_duyet.strip():
        raise ValueError("cần người duyệt")
    if not isinstance(phien_ban, int) or isinstance(phien_ban, bool) or phien_ban < 1:
        raise ValueError("phiên bản phải là số nguyên dương")


def to_location_pack(plan, nguoi_duyet, phien_ban):
    """Đóng gói thuần dữ liệu; geometry ĐỎ không được duyệt, VÀNG được giữ để người duyệt biết."""
    _check_approval(nguoi_duyet, phien_ban)
    issues = bo.check_geometry(plan)
    if any(i["muc"] == "do" for i in issues):
        raise ValueError("plan có issue ĐỎ: " + "; ".join(i["loi"] for i in issues if i["muc"] == "do"))
    return {"kind": "blockout", "schema_version": 1, "phien_ban": phien_ban,
            "nguoi_duyet": nguoi_duyet.strip(), "ngay": datetime.now(timezone.utc).isoformat(),
            "issues": deepcopy(issues), "sha256": _sha(plan), "plan": deepcopy(plan)}


def read_location_pack(pack):
    """Đọc gói đúng schema và SHA (toàn vẹn, nghiêm); không sửa gói gốc hay khóa model3d.

    `issues` trong gói là BẢN GHI LỊCH SỬ lúc duyệt, không phải điều kiện đọc: luật kiểm trong blockout.py đổi thì gói cũ vẫn đọc
    được nhưng kèm cảnh báo VÀNG "luật kiểm đã đổi, cần duyệt lại" (can_duyet_lai) và báo rõ nếu kiểm hiện tại có ĐỎ (co_do).
    """
    if not isinstance(pack, dict) or pack.get("kind") != "blockout" or pack.get("schema_version") != 1:
        raise ValueError("không phải location_pack blockout schema 1")
    if "plan" not in pack or pack.get("sha256") != _sha(pack["plan"]):
        raise ValueError("sha256 của plan không khớp")
    _check_approval(pack.get("nguoi_duyet"), pack.get("phien_ban"))
    try:
        datetime.fromisoformat(pack["ngay"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("ngày duyệt không hợp lệ") from error
    recorded = pack.get("issues")
    if not isinstance(recorded, list) or not all(isinstance(i, dict) and i.get("muc") == "vang" for i in recorded):
        raise ValueError("issues lúc duyệt phải là danh sách issue VÀNG (gói ĐỎ không được duyệt)")
    current = bo.check_geometry(pack["plan"])
    red = [i for i in current if i.get("muc") == "do"]
    warning = ""
    if current != recorded:
        warning = (f"luật kiểm đã đổi, cần duyệt lại: lúc duyệt {len(recorded)} issue, kiểm hiện tại {len(current)} issue"
                   + (" — có ĐỎ: " + "; ".join(f"{i['path']}: {i['loi']}" for i in red) if red else ""))
    return {"plan": deepcopy(pack["plan"]), "can_duyet_lai": bool(warning), "canh_bao": warning, "co_do": bool(red),
            "issues_luc_duyet": deepcopy(recorded), "issues_hien_tai": current}


def from_location_pack(pack):
    """Trả plan của gói (xem read_location_pack); luật kiểm đổi → vẫn trả plan nhưng phát UserWarning, không im lặng."""
    info = read_location_pack(pack)
    if info["canh_bao"]:
        warnings.warn(info["canh_bao"], UserWarning, stacklevel=2)
    return info["plan"]
