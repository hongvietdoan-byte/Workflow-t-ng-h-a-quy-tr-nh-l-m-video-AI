"""Resolve revision pins thành snapshot độc lập, không đọc head/storage/provider."""
import copy
import hashlib
import json
import re

from core.stage_registry_schema import COLLECTIONS, RegistryValidationError, issue, validate_bundle


def _prepare(bundle):
    result = validate_bundle(bundle)
    if result["errors"]: raise RegistryValidationError(result["errors"])
    index = {kind: {(r["id"], r["revision"]): r for r in bundle[kind]} for kind in COLLECTIONS}
    warnings = []
    for warning in result["warnings"]:
        match = re.match(r"\$\.stages\[([0-9]+)\](.*)", warning["path"])
        if match:
            stage = bundle["stages"][int(match[1])]
            warnings.append({**warning, "path": "$.stage" + match[2], "stage": {"id": stage["id"], "revision": stage["revision"]}})
    return index, warnings


def _key(pin):
    return pin["id"], pin["revision"]


def _get(index, kind, pin):
    if not isinstance(pin, dict) or set(pin) != {"id", "revision"} or not isinstance(pin.get("id"), str) or type(pin.get("revision")) is not int:
        raise RegistryValidationError([issue("$.request", "pin")])
    result = index[kind].get(_key(pin))
    if result is None: raise RegistryValidationError([issue("$.request", "pin")])
    return result


def _charge(work, amount=1):
    work[0] -= amount
    if work[0] < 0: raise RegistryValidationError([issue("$", "budget")])


def _weight(value):
    count, stack = 0, [value]
    while stack:
        node = stack.pop(); count += 1
        if isinstance(node, dict): stack.extend(node.values())
        elif isinstance(node, list): stack.extend(node)
    return count


def _state(index, pin, cache, work):
    row = _get(index, "states", pin)
    requested = _key(pin)
    if requested in cache:
        _charge(work, _weight(cache[requested][0]) + sum(_weight(v) for v in cache[requested][1].values()))
        return copy.deepcopy(cache[requested][0]), cache[requested][1].copy()
    chain, dependencies = [], {}
    base = None
    while row:
        _charge(work)
        if (row["id"], row["revision"]) in cache:
            base = cache[(row["id"], row["revision"])]
            _charge(work, _weight(base[0]) + sum(_weight(v) for v in base[1].values()))
            dependencies.update(base[1]); break
        chain.append(row); dependencies[("states", row["id"], row["revision"])] = row
        segment = _get(index, "segments", row["segment"])
        dependencies[("segments", segment["id"], segment["revision"])] = segment
        stage = _get(index, "stages", segment["stage"])
        dependencies[("stages", stage["id"], stage["revision"])] = stage
        parent = row["parent_state"] or segment["continuation_from_state"]
        row = _get(index, "states", parent) if parent else None
    objects, locks = (copy.deepcopy(base[0]["objects"]), copy.deepcopy(base[0]["locks"])) if base else ({}, [])
    for row in reversed(chain):
        _charge(work, len(objects) + len(row["patches"]))
        if row["_user_locked"]:
            locks.append({"state": {"id": row["id"], "revision": row["revision"]}, "fields": copy.deepcopy(row["_user_locked"])})
        for patch in row["patches"]:
            ident, op = patch["object_id"], patch["op"]
            if op == "spawn":
                if ident in objects: raise RegistryValidationError([issue("$.states.patches", "lifecycle")])
                objects[ident] = {}
            elif ident not in objects: raise RegistryValidationError([issue("$.states.patches", "lifecycle")])
            if op == "despawn": del objects[ident]; continue
            obj = objects[ident]
            for field, value in patch.items():
                if field in ("object_id", "op"): continue
                if field == "relation":
                    rel = obj.setdefault("relation", {})
                    for name, target in value.items():
                        if target is None: rel.pop(name, None)
                        else: rel[name] = target
                else: obj[field] = copy.deepcopy(value)
        # Quan hệ phải trỏ tới vật hiện hữu; hidden vẫn giữ presence.
        edges = {}
        for ident, obj in objects.items():
            targets = list(obj.get("relation", {}).values())
            _charge(work, len(targets))
            if any(target not in objects for target in targets): raise RegistryValidationError([issue("$.states.relation", "reference")])
            edges[ident] = targets
        # DAG nhiều quan hệ, dùng stack rõ ràng thay vì đệ quy Python.
        visited, active = set(), set()
        for ident in edges:
            stack = [(ident, False)]
            while stack:
                node, exit_node = stack.pop()
                if exit_node: active.discard(node); visited.add(node); continue
                if node in active: raise RegistryValidationError([issue("$.states.relation", "cycle")])
                if node in visited: continue
                active.add(node); stack.append((node, True))
                stack.extend((target, False) for target in edges[node])
    target = _get(index, "states", pin)
    target_segment = _get(index, "segments", target["segment"])
    target_stage = _get(index, "stages", target_segment["stage"])
    _charge(work, _weight(target_stage["objects"]))
    definitions = {o["id"]: copy.deepcopy(o) for o in target_stage["objects"]}
    for ident, obj in objects.items():
        obj["definition"] = definitions[ident]
    result = ({"state": {"id": target["id"], "revision": target["revision"]}, "story_time": target["story_time"], "beat": target["beat"], "objects": objects, "locks": locks}, dependencies)
    _charge(work, _weight(result[0]) + sum(_weight(v) for v in dependencies.values()))
    cache[requested] = (copy.deepcopy(result[0]), dependencies.copy())
    return result


def _finish(snapshot, dependencies, warnings):
    snapshot["dependencies"] = [{"kind": key[0], "revision_data": copy.deepcopy(value)} for key, value in sorted(dependencies.items())]
    used = {(key[1], key[2]) for key in dependencies if key[0] == "stages"}
    snapshot["warnings"] = sorted((copy.deepcopy(w) for w in warnings if _key(w["stage"]) in used), key=lambda w: (_key(w["stage"]), w["path"]))
    snapshot["measurement"] = "unknown" if snapshot["warnings"] else "unverified"
    wire = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    snapshot["hash"] = hashlib.sha256(wire.encode("utf-8")).hexdigest()
    return copy.deepcopy(snapshot)


def _work(max_work):
    if type(max_work) is not int or not 1 <= max_work <= 1000000:
        raise RegistryValidationError([issue("$", "budget")])
    return [max_work]


def validate_registry(bundle, *, max_work=100000):
    """Cổng nhận dữ liệu 4b: cấu trúc + mọi lifecycle/quan hệ, lỗi sanitize."""
    try:
        index, warnings = _prepare(bundle)
        cache, work = {}, _work(max_work)
        for key in index["states"]:
            _state(index, {"id": key[0], "revision": key[1]}, cache, work)
        for shot in index["shots"].values():
            start, _ = _state(index, shot["state_start"], cache, work)
            camera = _get(index, "cameras", shot["camera"]) if shot["camera"] else shot["private_camera"]
            if camera["pov_subject_id"] is not None and camera["pov_subject_id"] not in start["objects"]:
                raise RegistryValidationError([issue("$.camera.pov_subject_id", "reference")])
        return {"errors": [], "warnings": warnings}
    except RegistryValidationError as exc:
        return {"errors": exc.errors, "warnings": []}


def resolve_state(bundle, state_id, revision, *, max_work=100000):
    """Pin bắt buộc; kết quả độc lập, không thay đổi bundle của caller."""
    index, warnings = _prepare(bundle)
    state, deps = _state(index, {"id": state_id, "revision": revision}, {}, _work(max_work))
    return _finish({"schema_version": 1, "project_id": bundle["project_id"], **state}, deps, warnings)


def resolve_shot(bundle, shot_id, revision, *, max_work=100000):
    """Snapshot đầu/cuối/nhịp, máy và toàn bộ dependency thực sự được đọc."""
    index, warnings = _prepare(bundle)
    cache, work = {}, _work(max_work)
    shot = _get(index, "shots", {"id": shot_id, "revision": revision})
    deps = {("shots", shot["id"], shot["revision"]): shot}
    start, sd = _state(index, shot["state_start"], cache, work)
    deps.update(sd)
    beats = []
    for pin in shot["beats"]:
        beat, bd = _state(index, pin, cache, work); beats.append(beat); deps.update(bd)
    end, ed = _state(index, shot["state_end"], cache, work); deps.update(ed)
    camera = shot["private_camera"]
    if shot["camera"]:
        camera = _get(index, "cameras", shot["camera"])
        deps[("cameras", camera["id"], camera["revision"])] = camera
        _, cd = _state(index, camera["state"], cache, work); deps.update(cd)
    if camera["pov_subject_id"] is not None and camera["pov_subject_id"] not in start["objects"]:
        raise RegistryValidationError([issue("$.camera.pov_subject_id", "reference")])
    return _finish({"schema_version": 1, "project_id": bundle["project_id"], "scene_id": shot["scene_id"], "shot": {"id": shot_id, "revision": revision}, "start": start, "end": end, "beats": beats, "camera": copy.deepcopy(camera)}, deps, warnings)
