"""Schema A v1 thuần JSON, không I/O. Xem docs/STAGE_REGISTRY_A_PROTOCOL.md."""
import math
import re
from datetime import datetime

COLLECTIONS = ("stages", "segments", "states", "cameras", "shots")
ENVELOPE = {"schema_version", "project_id", "id", "revision", "parent_revision", "author_id", "created_at_utc", "reason", "source", "provenance", "_user_locked"}
FIELDS = {
    "stages": {"source_asset_id", "asset_revision", "world_frame", "geometry", "spots", "objects"},
    "segments": {"stage", "time", "initial_state", "continuation_from_state"},
    "states": {"segment", "parent_state", "story_time", "beat", "patches"},
    "cameras": {"stage", "state", "spot_id", "location", "target", "lens_mm", "sensor_mm", "aspect", "angles", "pov_subject_id", "move"},
    "shots": {"scene_id", "stage", "segment", "state_start", "state_end", "spot_id", "camera", "private_camera", "beats", "time_clip"},
}
MESSAGES = {"budget": "Dữ liệu vượt giới hạn tài nguyên.", "type": "Sai kiểu dữ liệu.", "field": "Trường không thuộc hợp đồng hoặc thiếu trường bắt buộc.", "number": "Số phải hữu hạn và không phải boolean.", "scope": "Tham chiếu khác phạm vi dự án hoặc sân khấu.", "pin": "Không tìm thấy đúng ID và revision đã ghim.", "reference": "Tham chiếu không tồn tại trong phạm vi.", "duplicate": "ID và revision bị trùng.", "cycle": "Quan hệ trạng thái có chu trình.", "units": "Hệ tọa độ hoặc đơn vị không đúng hợp đồng.", "unknown": "Thiếu kích thước, scale hoặc hình học đã xác minh.", "lifecycle": "Thao tác không hợp lệ với vòng đời đối tượng.", "time": "Thời gian hoặc thứ tự revision không hợp lệ."}


class RegistryValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Dữ liệu registry A không hợp lệ.")


def issue(path, code):
    return {"path": path, "code": code, "message": MESSAGES[code]}


def validate_bundle(bundle, *, max_nodes=50000, max_depth=48, max_string=4096):
    try:
        return _validate_bundle(bundle, max_nodes=max_nodes, max_depth=max_depth, max_string=max_string)
    except RegistryValidationError as exc:
        return {"errors": exc.errors, "warnings": []}
    except (TypeError, KeyError, ValueError, OverflowError):
        return {"errors": [issue("$", "type")], "warnings": []}


def _validate_bundle(bundle, *, max_nodes, max_depth, max_string):
    """Trả errors/warnings; path chỉ chứa tên schema và chỉ số, không echo payload."""
    errors, warnings = [], []
    if any(type(v) is not int or v < 1 for v in (max_nodes, max_depth, max_string)) or max_nodes > 50000 or max_depth > 48 or max_string > 4096:
        return {"errors": [issue("$", "budget")], "warnings": []}
    def bad(p, c): errors.append(issue(p, c))
    # Quét lặp trước deepcopy/JSON/hash: chặn cycle container và nesting quá sâu.
    stack, count, seen = [(bundle, 0)], 0, set()
    while stack:
        obj, depth = stack.pop(); count += 1
        if count > max_nodes or depth > max_depth:
            return {"errors": [issue("$", "budget")], "warnings": []}
        if isinstance(obj, (dict, list)):
            if id(obj) in seen:
                # JSON cây thuần; alias Python cũng không phải wire payload JSON.
                return {"errors": [issue("$", "type")], "warnings": []}
            seen.add(id(obj))
            if len(obj) > max_nodes: return {"errors": [issue("$", "budget")], "warnings": []}
            values = list(obj.values()) + list(obj.keys()) if isinstance(obj, dict) else obj
            stack.extend((v, depth + 1) for v in values)
        elif isinstance(obj, str):
            if len(obj) > max_string: return {"errors": [issue("$", "budget")], "warnings": []}
        elif type(obj) is int and obj.bit_length() > 1024: bad("$", "number")
        elif isinstance(obj, float) and not math.isfinite(obj): bad("$", "number")
        elif obj is not None and not isinstance(obj, (str, int, float, bool)): bad("$", "type")
    if errors: return {"errors": errors, "warnings": warnings}

    def shape(o, required, optional, p):
        if not isinstance(o, dict): bad(p, "type"); return False
        if set(o) - required - optional or required - set(o): bad(p, "field"); return False
        return True
    def ident(v, p):
        if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", v): bad(p, "type")
    def author(v, p):
        if not isinstance(v, str) or not v.strip() or len(v) > 320 or any(ord(c) < 32 for c in v): bad(p, "type")
    def number(v, p, positive=False):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): bad(p, "number")
        elif positive and v <= 0: bad(p, "number")
    def revision(v, p):
        if type(v) is not int or not 1 <= v <= 2**63 - 1: bad(p, "number")
    def vector(v, n, p):
        if not isinstance(v, list) or len(v) != n: bad(p, "type")
        else:
            for i, x in enumerate(v): number(x, f"{p}[{i}]")
    def utc(v, p):
        try:
            if not isinstance(v, str) or not v.endswith("Z"): raise ValueError
            datetime.fromisoformat(v[:-1] + "+00:00")
        except (ValueError, TypeError): bad(p, "type")
    if not shape(bundle, {"schema_version", "project_id", *COLLECTIONS}, set(), "$"):
        return {"errors": errors, "warnings": warnings}
    if bundle["schema_version"] != 1 or type(bundle["schema_version"]) is not int: bad("$.schema_version", "type")
    revision(bundle["project_id"], "$.project_id")
    indices = {}; paths = {}
    for kind in COLLECTIONS:
        indices[kind] = {}
        if not isinstance(bundle[kind], list): bad(f"$.{kind}", "type"); continue
        for i, row in enumerate(bundle[kind]):
            p = f"$.{kind}[{i}]"
            if not shape(row, ENVELOPE | FIELDS[kind], set(), p): continue
            ident(row["id"], p + ".id"); revision(row["revision"], p + ".revision")
            if row["schema_version"] != 1 or type(row["schema_version"]) is not int: bad(p, "type")
            revision(row["project_id"], p + ".project_id")
            if row["project_id"] != bundle["project_id"]: bad(p, "scope")
            author(row["author_id"], p + ".author_id"); utc(row["created_at_utc"], p + ".created_at_utc")
            if not isinstance(row["reason"], str) or not row["reason"].strip(): bad(p + ".reason", "type")
            if row["parent_revision"] is not None:
                revision(row["parent_revision"], p + ".parent_revision")
                if type(row["parent_revision"]) is int and type(row["revision"]) is int and row["parent_revision"] >= row["revision"]: bad(p, "time")
            for key in ("source", "provenance", "_user_locked"):
                if not isinstance(row[key], dict): bad(p + "." + key, "type")
            if isinstance(row["_user_locked"], dict):
                for j, (lock_path, lock) in enumerate(row["_user_locked"].items()):
                    if not isinstance(lock_path, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]{1,6}\])*", lock_path) or re.split(r"[.\[]", lock_path)[0] not in FIELDS[kind]: bad(p + "._user_locked", "field")
                    cursor=row
                    valid_path=True
                    if isinstance(lock_path,str):
                        for field,index in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)|\[([0-9]+)\]",lock_path):
                            if field:
                                if not isinstance(cursor,dict) or field not in cursor: valid_path=False; break
                                cursor=cursor[field]
                            else:
                                if not isinstance(cursor,list) or int(index)>=len(cursor): valid_path=False; break
                                cursor=cursor[int(index)]
                    else: valid_path=False
                    if not valid_path: bad(p + "._user_locked", "field")
                    lp = p + f"._user_locked[{j}]"
                    if shape(lock, {"author_id", "created_at_utc", "reason"}, set(), lp):
                        author(lock["author_id"], lp); utc(lock["created_at_utc"], lp)
                        if not isinstance(lock["reason"], str) or not lock["reason"].strip(): bad(lp, "type")
            if isinstance(row["id"], str) and type(row["revision"]) is int:
                key = (row["id"], row["revision"])
                if key in indices[kind]: bad(p, "duplicate")
                indices[kind][key] = row; paths[(kind, key)] = p
    if errors: return {"errors": errors, "warnings": warnings}

    def ref(pin, kind, p, nullable=False):
        if pin is None and nullable: return None
        if not shape(pin, {"id", "revision"}, set(), p): return None
        ident(pin["id"], p + ".id"); revision(pin["revision"], p + ".revision")
        if not isinstance(pin["id"], str) or type(pin["revision"]) is not int: return None
        row = indices[kind].get((pin["id"], pin["revision"]))
        if row is None: bad(p, "pin")
        return row
    def same(a, b, p):
        if a != b: bad(p, "scope")
    def confidence(o, p):
        if o.get("confidence") not in ("measured", "assumed", "unknown"): bad(p, "type")
        if not isinstance(o.get("source"), str): bad(p, "type")
        if o.get("confidence") == "measured" and not o.get("source"): bad(p, "type")
    def geometry(g, p):
        if not shape(g, {"dimensions", "confidence", "source"}, {"shapes", "transform", "stand_in", "raw"}, p): return
        confidence(g, p)
        if g["confidence"] != "measured" or g["dimensions"] is None: warnings.append(issue(p, "unknown"))
        if g["dimensions"] is None:
            if g["confidence"] != "unknown": bad(p, "type")
        else:
            vector(g["dimensions"], 3, p + ".dimensions")
            if isinstance(g["dimensions"], list):
                for value in g["dimensions"]: number(value, p, True)
        if "transform" in g: vector(g["transform"], 16, p + ".transform")
        if "stand_in" in g and type(g["stand_in"]) is not bool: bad(p + ".stand_in", "type")
        if "shapes" in g:
            if not isinstance(g["shapes"], list): bad(p + ".shapes", "type")
            else:
                for i, descriptor in enumerate(g["shapes"]):
                    gp = p + f".shapes[{i}]"
                    if shape(descriptor, {"kind", "dimensions", "confidence", "source"}, {"transform", "raw"}, gp):
                        if not isinstance(descriptor["kind"], str) or not descriptor["kind"].strip(): bad(gp, "type")
                        geometry(descriptor_without_kind(descriptor), gp)
    def descriptor_without_kind(d):
        return {k: v for k, v in d.items() if k != "kind"}
    stage_ids = {}
    for key, stage in indices["stages"].items():
        p = paths[("stages", key)]
        revision(stage["source_asset_id"], p + ".source_asset_id"); revision(stage["asset_revision"], p + ".asset_revision")
        w = stage["world_frame"]
        if shape(w, {"units", "east", "north", "up", "facing", "scale"}, set(), p + ".world_frame"):
            if [w[k] for k in ("units", "east", "north", "up", "facing")] != ["m", "+x", "+y", "+z", "clockwise_from_+y"]: bad(p, "units")
            scale = w["scale"]
            if shape(scale, {"value", "confidence", "source"}, set(), p + ".world_frame.scale"):
                confidence(scale, p)
                if scale["value"] is None:
                    if scale["confidence"] != "unknown": bad(p, "type")
                    warnings.append(issue(p + ".world_frame.scale", "unknown"))
                else: number(scale["value"], p, True)
                if scale["value"] is not None and scale["confidence"] != "measured": warnings.append(issue(p + ".world_frame.scale", "unknown"))
        geometry(stage["geometry"], p + ".geometry")
        stage_ids[key] = {}
        for group in ("spots", "objects"):
            found = set(); stage_ids[key][group] = found
            if not isinstance(stage[group], list): bad(p + "." + group, "type"); continue
            for i, obj in enumerate(stage[group]):
                op = p + f".{group}[{i}]"
                req = {"id", "xyz", "facing"} if group == "spots" else {"id", "kind"}
                opt = {"label", "region", "transform", "provenance"} if group == "spots" else {"label", "asset_id", "asset_revision", "look_id", "look_revision", "height", "geometry", "provenance", "actor_id"}
                if not shape(obj, req, opt, op): continue
                ident(obj["id"], op)
                if isinstance(obj["id"], str):
                    if obj["id"] in found: bad(op, "duplicate")
                    found.add(obj["id"])
                if group == "spots": vector(obj["xyz"], 3, op + ".xyz"); number(obj["facing"], op + ".facing")
                elif obj["kind"] not in ("actor", "prop", "structure"): bad(op, "type")
                for prefix in ("asset", "look"):
                    if (prefix + "_id" in obj) != (prefix + "_revision" in obj): bad(op, "field")
                    if prefix + "_id" in obj: revision(obj[prefix + "_id"], op); revision(obj.get(prefix + "_revision"), op)
                if group == "objects":
                    if obj.get("height") is None: warnings.append(issue(op + ".height", "unknown"))
                    if "geometry" in obj: geometry(obj["geometry"], op + ".geometry")
                    else: warnings.append(issue(op + ".geometry", "unknown"))
                    if "actor_id" in obj: revision(obj["actor_id"], op + ".actor_id")
                for text_key in ("label", "region"):
                    if text_key in obj and not isinstance(obj[text_key], str): bad(op, "type")
                if "provenance" in obj and not isinstance(obj["provenance"], dict): bad(op, "type")
                if "height" in obj and obj["height"] is not None: number(obj["height"], op, True)
                if "transform" in obj: vector(obj["transform"], 16, op)
    def stage_for_state(state):
        segment = ref(state["segment"], "segments", "$.states.segment")
        return segment["stage"] if segment else None
    edges = {}
    for key, seg in indices["segments"].items():
        p = paths[("segments", key)]; ref(seg["stage"], "stages", p + ".stage")
        vector(seg["time"], 2, p + ".time")
        if isinstance(seg["time"], list) and len(seg["time"]) == 2 and all(type(t) in (int, float) for t in seg["time"]) and seg["time"][0] > seg["time"][1]: bad(p, "time")
        initial = ref(seg["initial_state"], "states", p + ".initial_state")
        if initial:
            same(initial["segment"], {"id": key[0], "revision": key[1]}, p)
            if initial["parent_state"] is not None: bad(p, "reference")
        cont = ref(seg["continuation_from_state"], "states", p + ".continuation_from_state", True)
        if cont:
            same(stage_for_state(cont), seg["stage"], p)
            if isinstance(seg["time"], list) and seg["time"] and type(seg["time"][0]) in (int, float) and type(cont["story_time"]) in (int, float) and cont["story_time"] > seg["time"][0]: bad(p, "time")
    for key, state in indices["states"].items():
        p = paths[("states", key)]; seg = ref(state["segment"], "segments", p + ".segment")
        parent = ref(state["parent_state"], "states", p + ".parent_state", True)
        number(state["story_time"], p + ".story_time")
        if not isinstance(state["beat"], str): bad(p + ".beat", "type")
        if seg and state["parent_state"] is None and {"id": key[0], "revision": key[1]} != seg["initial_state"]: bad(p, "reference")
        if parent:
            same(parent["segment"], state["segment"], p)
            if type(state["story_time"]) in (int, float) and type(parent["story_time"]) in (int, float) and state["story_time"] < parent["story_time"]: bad(p, "time")
        predecessor = state["parent_state"] or (seg["continuation_from_state"] if seg else None)
        edges[key] = (predecessor["id"], predecessor["revision"]) if predecessor and isinstance(predecessor, dict) and isinstance(predecessor.get("id"), str) and type(predecessor.get("revision")) is int else None
        if seg and type(state["story_time"]) in (int, float) and isinstance(seg["time"], list) and len(seg["time"]) == 2 and all(type(t) in (int, float) for t in seg["time"]):
            if not seg["time"][0] <= state["story_time"] <= seg["time"][1]: bad(p, "time")
        objects = stage_ids.get((seg["stage"]["id"], seg["stage"]["revision"]), {}).get("objects", set()) if seg and isinstance(seg["stage"], dict) and isinstance(seg["stage"].get("id"), str) and type(seg["stage"].get("revision")) is int else set()
        if not isinstance(state["patches"], list): bad(p + ".patches", "type"); continue
        touched = set()
        for i, patch in enumerate(state["patches"]):
            pp = p + f".patches[{i}]"
            if not shape(patch, {"object_id", "op"}, {"xyz", "facing", "pose", "hidden", "relation"}, pp): continue
            if not isinstance(patch["object_id"], str) or patch["object_id"] not in objects: bad(pp, "reference")
            elif patch["object_id"] in touched: bad(pp, "duplicate")
            else: touched.add(patch["object_id"])
            if patch["op"] not in ("spawn", "update", "despawn"): bad(pp, "type")
            if patch["op"] == "despawn" and len(patch) != 2: bad(pp, "field")
            if "xyz" in patch: vector(patch["xyz"], 3, pp + ".xyz")
            if "facing" in patch: number(patch["facing"], pp + ".facing")
            if "hidden" in patch and type(patch["hidden"]) is not bool: bad(pp, "type")
            if "pose" in patch and (not isinstance(patch["pose"], str) or not patch["pose"]): bad(pp, "type")
            if "relation" in patch and shape(patch["relation"], set(), {"in", "cover", "held_by"}, pp + ".relation"):
                for target in patch["relation"].values():
                    if target is not None and (not isinstance(target, str) or target not in objects or target == patch["object_id"]): bad(pp, "reference")
    # DAG một cạnh vào: duyệt lặp O(nodes), gồm cả continuation của đoạn.
    done = set()
    for node in edges:
        trail = set(); cursor = node
        while cursor is not None and cursor not in done:
            if cursor in trail: bad("$.states", "cycle"); break
            trail.add(cursor); cursor = edges.get(cursor)
        done.update(trail)
    ancestor_cache = {}
    ancestor_work = [max_nodes * 4]
    def ancestors(pin):
        key = (pin.get("id"), pin.get("revision"))
        if key not in ancestor_cache:
            lineage = set(); cursor = key
            while cursor in edges and cursor not in lineage:
                ancestor_work[0] -= 1
                if ancestor_work[0] < 0: raise RegistryValidationError([issue("$", "budget")])
                lineage.add(cursor); cursor = edges[cursor]
            ancestor_cache[key] = lineage
        return ancestor_cache[key]
    for kind in ("cameras", "shots"):
        scenes = set()
        for key, row in indices[kind].items():
            p = paths[(kind, key)]; stage = ref(row["stage"], "stages", p + ".stage")
            known = stage_ids.get((stage["id"], stage["revision"]), {}) if stage else {}
            if row["spot_id"] is not None and (not isinstance(row["spot_id"], str) or row["spot_id"] not in known.get("spots", set())): bad(p + ".spot_id", "reference")
            if kind == "cameras":
                state = ref(row["state"], "states", p + ".state")
                if state: same(stage_for_state(state), row["stage"], p)
                _camera(row, p, known.get("objects", set()), shape, vector, number, bad)
            else:
                revision(row["scene_id"], p + ".scene_id")
                scene_key = (row["scene_id"], row["revision"]) if type(row["scene_id"]) is int else None
                if scene_key in scenes: bad(p, "duplicate")
                scenes.add(scene_key)
                seg = ref(row["segment"], "segments", p + ".segment")
                if seg: same(seg["stage"], row["stage"], p)
                vector(row["time_clip"], 2, p + ".time_clip")
                if isinstance(row["time_clip"], list) and len(row["time_clip"]) == 2 and all(type(t) in (int, float) for t in row["time_clip"]) and row["time_clip"][0] > row["time_clip"][1]: bad(p, "time")
                states = [row["state_start"], row["state_end"]]
                if isinstance(row["beats"], list): states += row["beats"]
                else: bad(p + ".beats", "type")
                for i, pin in enumerate(states):
                    state = ref(pin, "states", p + f".states[{i}]")
                    if state: same(state["segment"], row["segment"], p)
                if (row["camera"] is None) == (row["private_camera"] is None): bad(p, "field")
                camera = ref(row["camera"], "cameras", p + ".camera", True)
                if camera:
                    same(camera["stage"], row["stage"], p)
                    same(camera["state"], row["state_start"], p + ".camera.state")
                # Mốc phải đi theo đúng một lineage đầu → nhịp → cuối.
                ordered = [row["state_start"]] + (row["beats"] if isinstance(row["beats"], list) else []) + [row["state_end"]]
                previous = None
                for pin in ordered:
                    if not isinstance(pin, dict) or not isinstance(pin.get("id"), str) or type(pin.get("revision")) is not int: continue
                    current = (pin["id"], pin["revision"])
                    if previous is not None and previous not in ancestors(pin): bad(p + ".beats", "time")
                    previous = current
                if row["private_camera"] is not None:
                    pc = row["private_camera"]
                    req = {"location", "target", "lens_mm", "sensor_mm", "aspect", "angles", "pov_subject_id", "move"}
                    if shape(pc, req, set(), p + ".private_camera"): _camera(pc, p, known.get("objects", set()), shape, vector, number, bad)
    return {"errors": errors, "warnings": warnings}


def _camera(row, p, objects, shape, vector, number, bad):
    for key in ("location", "target", "angles"): vector(row[key], 3, p + "." + key)
    vector(row["sensor_mm"], 2, p + ".sensor_mm")
    if isinstance(row["sensor_mm"], list):
        for n in row["sensor_mm"]: number(n, p, True)
    for key in ("lens_mm", "aspect"): number(row[key], p + "." + key, True)
    if row["pov_subject_id"] is not None and (not isinstance(row["pov_subject_id"], str) or row["pov_subject_id"] not in objects): bad(p + ".pov_subject_id", "reference")
    if row["move"] is not None and shape(row["move"], {"end_location", "end_target", "seconds", "path"}, set(), p + ".move"):
        mv = row["move"]; vector(mv["end_location"], 3, p + ".move.end_location"); vector(mv["end_target"], 3, p + ".move.end_target"); number(mv["seconds"], p + ".move.seconds", True)
        if not isinstance(mv["path"], list): bad(p + ".move.path", "type")
        else:
            for i, point in enumerate(mv["path"]): vector(point, 3, p + f".move.path[{i}]")
