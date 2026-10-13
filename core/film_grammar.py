"""Đ11v4: mở rộng continuity bằng hình học, 0 USD; cờ TẮT giữ đường cũ.

objects dùng nguyên dạng stage_solver.objects_from_blocking, cùng hệ tọa độ với
stage_camera. Không suy tọa độ từ chữ BYĐ. Thiếu số → VÀNG. Ngưỡng tạm.
"""
import math

from . import features, plate_camera


def _finite_object(obj):
    """Không cho NaN/Inf đi vào phép chiếu hay so hướng (so NaN dễ im lặng)."""
    xy = obj["xy"]
    if len(xy) != 2 or not all(math.isfinite(float(v)) for v in xy):
        raise ValueError
    for field in ("z", "H", "h", "facing"):
        if obj.get(field) is not None and not math.isfinite(float(obj[field])):
            raise ValueError
    if obj.get("H") is not None and float(obj["H"]) <= 0:
        raise ValueError


def _exception(shot, number, rule):
    words = {"jump": ("cắt nhảy", "jump cut", "30°"), "eyeline": ("hướng nhìn", "eyeline"),
             "lead": ("lead room", "khoảng trống phía trước"), "head": ("headroom", "khoảng trống trên đầu")}
    from .shot_intent import NGOAI_LE_LY_DO
    for e in (shot.get("byd") or {}).get("ngoai_le") or []:
        if not isinstance(e, dict) or e.get("ly_do") not in NGOAI_LE_LY_DO:
            continue
        if number not in (e.get("pham_vi") or []) or not all(e.get(k) for k in ("doi_tuong", "dieu_trai", "cach_hien")):
            continue
        text = str(e["dieu_trai"]).casefold()
        if any(w in text for w in words[rule]) and not any(w in text for w in ("không", "tránh", "đừng", "not ")):
            return True
    return False


def warnings(shots, objects=None, aspect=9 / 16):
    """(scene, shot_no, data) theo thứ tự phim; objects hoặc callback(scene, data).

    Adapter của màn camera có thể truyền vật từ blocking đã duyệt. Luồng đang có
    không lưu blocking trên shot: chỉ báo thiếu số, không giả kiểm được.
    """
    if not features.on("film_grammar_check"):
        return []
    out, prev = [], None
    for scene, number, s in shots:
        tag = f"shot {scene}·{number}"
        cam = s.get("stage_camera")
        objs = objects(scene, s) if callable(objects) else objects
        if not isinstance(cam, dict) or not objs:
            out.append(f"{tag}: không kiểm luật quay — thiếu máy hoặc tọa độ/hướng mặt sân khấu đã duyệt; bổ sung dàn cảnh")
            prev = None
            continue
        try:
            location, aim, lens = cam["location"], cam["look_at"], float(cam["lens"])
            if len(location) != 3 or len(aim) != 3 or lens <= 0 or aspect <= 0 or not all(math.isfinite(float(v)) for v in [*location, *aim, lens, aspect]):
                raise ValueError
            if math.dist(location, aim) < .01:
                raise ValueError
            args = (location, aim, lens, aspect)
            byd = s.get("byd") or {}
            # BYĐ do Claude viết có thể sai kiểu: báo VÀNG số/BYĐ không hợp lệ, không im lặng/không vỡ report (rà gộp Đ11).
            if not isinstance(byd, dict) or not isinstance(byd.get("hanh_dong") or [], list) or not isinstance(byd.get("may") or {}, dict):
                raise ValueError
            actors = {k: o for k, o in objs.items() if o.get("kind") == "nguoi"}
            actions = (s.get("byd") or {}).get("hanh_dong") or []
            if not actions:
                out.append(f"{tag}: không kiểm hướng nhìn/lead room/headroom — thiếu chủ thể BYĐ")
            declared = {h.get("ai") for h in actions if isinstance(h, dict) and isinstance(h.get("ai"), str)}
            for missing in sorted(declared - set(actors)):
                out.append(f"{tag}: không kiểm chủ thể {missing} — thiếu đúng người trong dàn cảnh")
            if not actors:
                out.append(f"{tag}: không kiểm — thiếu người trong dàn cảnh")
            for name, o in actors.items():
                if name not in [h.get("ai") for h in actions if isinstance(h, dict)]:
                    continue
                _finite_object(o)
                xy, z, height = o["xy"], float(o["z"]), float(o["H"])
                eye = [xy[0], xy[1], z + height * .93]
                top = plate_camera.project(*args, [xy[0], xy[1], z + height])
                point = plate_camera.project(*args, eye)
                if top is None or point is None:
                    out.append(f"{tag}: {name} sau máy — không kiểm khoảng trống/mắt; đổi vị trí máy")
                    continue
                size = str(s.get("size") or (s.get("byd") or {}).get("may", {}).get("co") or "").upper()
                if not _exception(s, number, "head"):
                    if not size:
                        out.append(f"{tag}: không kiểm headroom — thiếu cỡ cảnh")
                    elif size not in ("CU", "ECU", "INSERT") and not .01 <= top[1] <= .25:
                        out.append(f"{tag}: {name} khoảng trống trên đầu {top[1]:.0%} — đổi độ ngửa/cúi máy (ngưỡng chưa hiệu chỉnh)")
                facing = o.get("facing")
                if facing is None:
                    out.append(f"{tag}: không kiểm hướng nhìn/lead room của {name} — thiếu facing")
                    continue
                rad = math.radians(float(facing))
                forward = plate_camera.project(*args, [eye[0] + math.sin(rad), eye[1] + math.cos(rad), eye[2]])
                if forward is None:
                    out.append(f"{tag}: không kiểm hướng nhìn {name} — hướng mặt sau máy")
                    continue
                dx = forward[0] - point[0]
                if abs(dx) > .02 and not _exception(s, number, "lead"):
                    ahead = 1 - point[0] if dx > 0 else point[0]
                    behind = point[0] if dx > 0 else 1 - point[0]
                    if ahead + .05 < behind:
                        out.append(f"{tag}: {name} thiếu khoảng trống phía trước mặt — dời máy sang bên/đổi khung để chừa phía nhìn (ngưỡng chưa hiệu chỉnh)")
                action = next(h for h in actions if isinstance(h, dict) and h.get("ai") == name)
                target = (action.get("bat_dau") or {}).get("nhin")
                if not target and not _exception(s, number, "eyeline"):
                    out.append(f"{tag}: không kiểm hướng nhìn {name} — BYĐ chưa khai đích nhìn")
                if target and not _exception(s, number, "eyeline"):
                    dest = objs.get(target) if isinstance(target, str) else None
                    if not dest:
                        out.append(f"{tag}: không kiểm hướng nhìn {name} — chưa có tọa độ đích nhìn BYĐ")
                    else:
                        _finite_object(dest)
                        tx, ty = dest["xy"]
                        vx, vy = tx - eye[0], ty - eye[1]
                        norm = math.hypot(vx, vy)
                        if norm < .01:
                            out.append(f"{tag}: không kiểm hướng nhìn {name} — đích nhìn trùng vị trí")
                        elif (vx * math.sin(rad) + vy * math.cos(rad)) / norm < math.cos(math.radians(30)):
                            out.append(f"{tag}: hướng nhìn {name} không khớp đích {target} trong BYĐ — xoay mặt về đích (ngưỡng chưa hiệu chỉnh)")
            current = {h.get("ai") for h in actions if isinstance(h, dict)} & set(actors)
            if prev and prev[0] == scene and current & set(prev[1]) and not _exception(s, number, "jump"):
                name = sorted(current & set(prev[1]))[0]
                o = actors[name]
                a, b = [location[i] - o["xy"][i] for i in range(2)], prev[1][name]
                norm = math.hypot(*a) * math.hypot(*b)
                if norm < .01:
                    out.append(f"{tag}: không kiểm 30° — máy trùng chủ thể")
                else:
                    angle = math.degrees(math.acos(max(-1., min(1., sum(x * y for x, y in zip(a, b)) / norm))))
                    if angle < 30:
                        out.append(f"{tag}: đổi góc {angle:.1f}° < 30° cùng chủ thể {name} — đổi góc máy ≥30° để tránh cắt nhảy")
            prev = (scene, {name: [location[i] - actors[name]["xy"][i] for i in range(2)] for name in current})
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            out.append(f"{tag}: không kiểm luật quay — số hình học/BYĐ không hợp lệ; bổ sung số đã duyệt")
            prev = None
    return out
