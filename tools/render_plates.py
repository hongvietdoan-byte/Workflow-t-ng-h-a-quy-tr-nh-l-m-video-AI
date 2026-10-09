"""Render empty backgrounds ("plates") of a 3D place for the image model — run INSIDE Blender (no person, no AI, no credit).

    blender -b --factory-startup -P tools/render_plates.py -- --config plan.json
    (or, with the `bpy` module installed:  python tools/render_plates.py --config plan.json)

Why (docs/KE_HOACH_TONG_2026-09-24.md, "Dùng bản đồ 3D"): an in-game map screenshot is taken from one camera — usually high up — and
the image model copies that camera and the tiny people with it. In 3D the camera goes where the shot needs it (eye level, low, high)
and sizes are real metres, so a plate rendered from the shot's own camera can be a background reference without dragging a wrong
composition along. The Dashboard (core/plates3d.py) writes the plan, runs this script and puts the plates in the library's review
box; this script never touches the database.

Plan (JSON):
  model            path of .glb/.gltf/.fbx/.obj/.blend/.usd*/.stl
  out_dir          where plates + manifest.json go
  resolution       [1280, 720]
  engine           "auto" (EEVEE, else Cycles on CPU) | "eevee" | "cycles" | "workbench"
  samples          render samples (EEVEE / Cycles), default 16
  sky              {"mode": "A" | "B" | "C", "sun_elevation": 35, "sun_azimuth": 140, "strength": 0.35, "sun_strength": 2.5,
                    "exposure": -0.5, "view_transform": "Standard" | "AgX" (unset = Blender default), "look": e.g. "Medium High Contrast",
                    "white_balance": 7500 (K, above 6500 = warmer frame), "white_balance_tint": 0,
                    "hdri": path (mode B, or lighting of mode C), "hdri_rotation": 0}
                   A = Blender's physical sky (no download), B = HDRI picture, C = light from A/B but the sky left transparent
                   (the Dashboard puts an in-game sky picture behind it).
  real_height_m    true height of the model's tallest part (e.g. the clock tower) -> sets the scale; unset = guess the unit
  decimate         0.05..1 keeps that share of the triangles (heavy maps), default 1
  ground           true = add a large ground plane under the model (maps cut out of a bigger map end in the void)
  target           [x, y, z] in metres (after scaling) the preset cameras look at; default the model's centre
  presets          ["eye_000", "eye_090", "eye_180", "eye_270", "low_000", "high_045"] (angle = degrees around the target)
  cameras          [{"name", "location": [x,y,z], "look_at": [x,y,z], "lens": 35, "model_coords": false}] extra cameras in metres;
                   model_coords true = the points are in the raw model's own coordinates (they get the scale and the lift to z = 0)
  lens_mm          35; eye_height_m 1.6; depth true (also render a depth picture: near = white; its range is in the manifest)
  terrain          {"b": "Terrain_Ground_01", "r": …, "g": …, "tile_m": 6} how an in-game ground splat is rebuilt (fix_terrain; the
                   official FF map exports); false = leave the exported ground material as it is
  weather          {"snow": 0..1, "wet": 0..1, "fog": 0..1} static weather on the geometry (kế hoạch V4 1.6 step 3): snow on the faces
                   that look up, wet = darker + glossier everything; fog is only recorded (laid in 2D from the depth picture). Falling rain/snow/lightning are 2D layers
                   added after (core/plate_env.py) so the character gets them too.
  sky.sun_color    [r, g, b] of the sun / moon light (night = cold blue moonlight)
  camera.subject   {"location": [x, y, z] feet, "height_m": 1.7} — a stand-in of the character's size is put there for one more
                   picture, `shadow_<cam>.png`: the plate with the stand-in's shadow (the stand-in itself is invisible to the camera),
                   (used by the green-screen composite, removed in S14.9 — kept as a render option)
  heights          [[x, y] or [x, y, z_from], …] — no render: the ground height under each point (raw model frame), plants skipped;
                   z_from = start the ray there (a floor inside a house)
  rooms            [{"name", "lo": [x, y], "hi": [x, y], "floor_z"}] — no render: the best camera spot + view inside each house box
                   (a ceiling above, walls all round; farthest from walls, looking the deepest way)
  camera.indoor    {"exposure": +1.5, "fill_w": 400, "fill_color": [r, g, b], "fill_up_m": 0.9} a room: brighter view + a fill lamp for
                   this camera only (removed after)
  camera.lights    S5.7 — the shot's extra light sources chosen from the script (core/plate_choice.light_rigs):
                   [{"type": "POINT"|"AREA"|"SPOT", "location", "look_at", "color": [r,g,b], "energy": W, "size": m, "spot_deg": °}]
                   (model coordinates when the camera's are); they exist only while that camera renders
  probe            {"step": 2.0} — no render: rays straight down on a grid find the flat ground a character can stand on; the
                   flat areas (clustered by height) go to probe.json with their size and centre, in the model's own coordinates
                   (core/location_pack.propose_spots turns them into named spots)
Every number the local test should record (import time, triangles, render time per plate) is written to manifest.json.
"""
import json
import math
import os
import sys
import time

import bpy                                                          # noqa: E402 - only exists inside Blender / with the bpy module
from mathutils import Vector                                        # noqa: E402

IMPORTERS = {
    ".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
    ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
    ".stl": lambda p: bpy.ops.wm.stl_import(filepath=p),
    ".usd": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usda": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usdc": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usdz": lambda p: bpy.ops.wm.usd_import(filepath=p),
}
SKY_TYPES = ("MULTIPLE_SCATTERING", "SINGLE_SCATTERING", "NISHITA", "HOSEK_WILKIE", "PREETHAM")   # newest first (names differ by version)
DEFAULT_PRESETS = ["eye_000", "eye_090", "eye_180", "eye_270", "low_000", "high_045"]


def log(msg):
    print(f"[plates] {msg}", flush=True)


def args_config():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--config" not in argv:
        sys.exit("usage: ... -- --config plan.json")
    with open(argv[argv.index("--config") + 1], encoding="utf-8") as f:
        return json.load(f)


def enum_items(owner, prop):
    try:
        return [i.identifier for i in owner.bl_rna.properties[prop].enum_items]
    except (KeyError, AttributeError):
        return []


# ---- scene ---------------------------------------------------------------------------------------------------------------
def load_model(path, warnings):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    t0 = time.time()
    if ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for obj in dst.objects:
            if obj is not None and obj.type not in ("CAMERA", "LIGHT"):
                bpy.context.scene.collection.objects.link(obj)
    elif ext in IMPORTERS:
        IMPORTERS[ext](path)
    else:
        raise SystemExit(f"unsupported 3D file type: {ext}")
    for obj in [o for o in bpy.data.objects if o not in before and o.type in ("CAMERA", "LIGHT")]:
        bpy.data.objects.remove(obj, do_unlink=True)                  # the file's own cameras/lights would fight ours
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("the 3D file has no mesh")
    return meshes, time.time() - t0


def triangles(meshes):
    n = 0
    for o in meshes:
        m = o.data
        m.calc_loop_triangles()
        n += len(m.loop_triangles)
    return n


def bbox(meshes):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def normalise_scale(meshes, real_height, warnings):
    """Put the model in metres, standing on z = 0. A declared real height wins; else a model over 500 units tall is taken as
    centimetres (FBX exports often are) — both written to the manifest so the local test can check them against a door (~2 m)."""
    lo, hi = bbox(meshes)
    height = hi.z - lo.z
    factor = 1.0
    if real_height:
        factor = float(real_height) / height if height > 0 else 1.0
    elif height > 500:
        factor = 0.01
        warnings.append(f"model {height:.0f} units tall: assumed centimetres (x0.01) — give real_height_m to be sure")
    root = bpy.data.objects.new("PLATES_ROOT", None)
    bpy.context.scene.collection.objects.link(root)
    for o in bpy.context.scene.objects:
        if o is not root and o.parent is None:
            o.parent = root
    root.scale = (factor, factor, factor)
    bpy.context.view_layer.update()
    lo, hi = bbox(meshes)
    root.location = (0, 0, -lo.z)                                      # keep x/y, stand on the ground
    global LIFT_Z
    LIFT_Z = -lo.z
    bpy.context.view_layer.update()
    return factor, bbox(meshes)


LIFT_Z = 0.0   # how far the model was raised to stand on z = 0 (a camera given in the model's own coordinates needs it — 2026-09-25:
               # clock tower cameras placed from a probe of the raw model ended up 2,16 m under the ground)


def to_scene(point, factor):
    """A point in the model's own coordinates (as read from the raw file) -> where it is after scaling and lifting."""
    return [float(point[0]) * factor, float(point[1]) * factor, float(point[2]) * factor + LIFT_Z]


def add_ground(lo, hi):
    size = max(hi.x - lo.x, hi.y - lo.y, 50) * 20
    bpy.ops.mesh.primitive_plane_add(size=size, location=((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z - 0.02))
    plane = bpy.context.active_object
    plane.name = "PLATES_GROUND"
    mat = bpy.data.materials.new("PLATES_GROUND")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.32, 0.33, 0.30, 1)
        bsdf.inputs["Roughness"].default_value = 0.9
    plane.data.materials.append(mat)


def decimate(meshes, ratio):
    if ratio >= 0.999:
        return
    for o in meshes:
        mod = o.modifiers.new("PLATES_DECIMATE", "DECIMATE")
        mod.ratio = max(float(ratio), 0.01)


# ---- sky + light ----------------------------------------------------------------------------------------------------------
def setup_world(sky, warnings):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("PLATES_WORLD")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = float(sky.get("strength", 0.35))   # the physical sky is very bright next to a 1-W-ish sun
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    mode = (sky.get("mode") or "A").upper()
    elev, azim = math.radians(float(sky.get("sun_elevation", 35))), math.radians(float(sky.get("sun_azimuth", 140)))
    used = "A"
    hdri = sky.get("hdri")
    if hdri and mode in ("B", "C") and os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(hdri)
        coord, mapping = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value[2] = math.radians(float(sky.get("hdri_rotation", 0)))
        nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        used = "B"
    else:
        if mode == "B":
            warnings.append("sky B: no HDRI file found — using the physical sky (A)")
        try:
            tex = nt.nodes.new("ShaderNodeTexSky")
            kinds = enum_items(tex, "sky_type")
            pick = next((k for k in SKY_TYPES if k in kinds), None)
            if pick:
                tex.sky_type = pick
            for attr, value in (("sun_elevation", elev), ("sun_rotation", azim), ("sun_disc", False)):
                if hasattr(tex, attr):
                    setattr(tex, attr, value)
            nt.links.new(tex.outputs["Color"], bg.inputs["Color"])
            used = f"A ({pick or 'default'})"
        except Exception as e:  # noqa: BLE001 - never stop a render for the sky: a plain gradient-like colour instead
            bg.inputs["Color"].default_value = (0.55, 0.72, 0.95, 1)
            warnings.append(f"physical sky unavailable ({e}); plain sky colour used")
            used = "A (plain colour)"
    if sky.get("camera_strength") is not None or sky.get("ambient_tint"):
        # 30/09 (người dùng: tông ấm, trời nắng): the sky the CAMERA sees stays a bright blue (camera_strength) while the light the sky
        # throws on the place is dimmer and warmer (strength × ambient_tint) — a white balance warmed the whole frame, sky included
        try:
            lp, mix = nt.nodes.new("ShaderNodeLightPath"), nt.nodes.new("ShaderNodeMixShader")
            cam_bg = nt.nodes.new("ShaderNodeBackground")
            src = bg.inputs["Color"].links[0].from_socket if bg.inputs["Color"].is_linked else None
            if src is not None:
                nt.links.new(src, cam_bg.inputs["Color"])
                if sky.get("ambient_tint"):
                    tint = nt.nodes.new("ShaderNodeMix")
                    tint.data_type, tint.blend_type = "RGBA", "MULTIPLY"
                    tint.inputs[0].default_value = 1.0
                    nt.links.new(src, tint.inputs[6])
                    tint.inputs[7].default_value = (*[float(c) for c in sky["ambient_tint"][:3]], 1.0)
                    nt.links.new(tint.outputs[2], bg.inputs["Color"])
            else:
                cam_bg.inputs["Color"].default_value = bg.inputs["Color"].default_value
            cam_bg.inputs["Strength"].default_value = float(sky.get("camera_strength", sky.get("strength", 0.35)))
            nt.links.new(bg.outputs["Background"], mix.inputs[1])
            nt.links.new(cam_bg.outputs["Background"], mix.inputs[2])
            nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
            nt.links.new(mix.outputs[0], out.inputs["Surface"])
        except Exception as e:  # noqa: BLE001
            warnings.append(f"camera sky / ambient tint not applied: {e}")
    sun_data = bpy.data.lights.new("PLATES_SUN", "SUN")               # sharp shadows in the same direction as the sky's sun
    sun_data.energy = float(sky.get("sun_strength", 2.5))
    if sky.get("sun_color"):
        sun_data.color = tuple(float(c) for c in sky["sun_color"][:3])
    sun = bpy.data.objects.new("PLATES_SUN", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.pi / 2 - elev, 0, azim + math.pi / 2)
    scene.render.film_transparent = mode == "C"
    scene.view_settings.exposure = float(sky.get("exposure", -0.5))
    # 2026-09-29: the default AgX view washes colours out next to the in-game look (official FF map export) — a plan can ask for
    # "Standard" (+ a contrast look); unset = Blender's default, as before
    if sky.get("view_transform"):
        try:
            scene.view_settings.view_transform = sky["view_transform"]
            if sky.get("look"):
                scene.view_settings.look = sky["look"]
        except (TypeError, ValueError) as e:
            warnings.append(f"view transform {sky.get('view_transform')} / look {sky.get('look')} not available: {e}")
    if sky.get("white_balance"):                      # 30/09 (người dùng: tông ấm): above 6500 K the whole frame warms, shade included
        vs = scene.view_settings
        if hasattr(vs, "white_balance_temperature"):
            vs.use_white_balance = True
            vs.white_balance_temperature = float(sky["white_balance"])
            if sky.get("white_balance_tint") is not None:
                vs.white_balance_tint = float(sky["white_balance_tint"])
        else:
            warnings.append("white balance not available in this Blender — frame left as rendered")
    return used + (" + transparent sky" if mode == "C" else "")


# ---- in-game terrain (splat map) ------------------------------------------------------------------------------------------
TERRAIN_DEFAULT = {"g": "Terrain_Ground_01", "b": "Terrain_Ground_02", "r": "Terrain_Ground_03", "tile_m": 6.0,
                   "bare": [0.30, 0.28, 0.22]}


def _ground_texture(folder, prefix):
    """The colour picture of one ground layer: <prefix>_D*.png / .tga / .jpg in the model's folder, or None."""
    for f in sorted(os.listdir(folder)):
        low = f.lower()
        if low.startswith(prefix.lower() + "_d") and low.endswith((".png", ".tga", ".jpg", ".tif")):
            return os.path.join(folder, f)
    return None


def fix_terrain(conf, warnings):
    """2026-09-29, official Free Fire map export (ClockTower / Peak): the ground mesh's material holds ONE ground picture
    (Terrain_Ground_03 — rock) stretched over UVs that span the whole island (u 0.49–0.68), so the render showed a grey-blue smear.
    In the game the ground is a splat: AllTerrainMask.png (whole island, same UVs) says per channel which ground layer shows
    (checked on the clock tower's crop of the mask — the river and the road line up: G = grass, most of the land → Terrain_Ground_01;
    B = bare ground round the town → _02; R = rocky patches → _03; black = river bed). Rebuilt here: the mask read with the mesh UVs,
    each ground layer tiled every `tile_m` metres in world space, mixed bare → B → R → G. Layer per channel and tile size
    can be changed in the plan ("terrain"); the mapping is a best reading of the export, checked against showcase_0.jpg by eye."""
    conf = dict(TERRAIN_DEFAULT, **(conf or {}))
    fixed = []
    for mat in bpy.data.materials:
        bsdf = _principled(mat)
        if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
            continue
        node = bsdf.inputs["Base Color"].links[0].from_node
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        path = bpy.path.abspath(node.image.filepath)
        folder = os.path.dirname(path)
        if not os.path.basename(path).lower().startswith("terrain_ground") or not os.path.isdir(folder):
            continue
        mask = next((os.path.join(folder, f) for f in os.listdir(folder) if "terrainmask" in f.lower()), None)
        layers = {ch: _ground_texture(folder, conf[ch]) for ch in ("b", "r", "g")}
        if not mask or not all(layers.values()):
            warnings.append(f"terrain {mat.name}: no splat mask / ground layers next to {os.path.basename(path)} — left as exported")
            continue
        try:
            nt = mat.node_tree
            m = nt.nodes.new("ShaderNodeTexImage")
            m.image = bpy.data.images.load(mask, check_existing=True)
            m.image.colorspace_settings.name = "Non-Color"
            if node.inputs["Vector"].is_linked:                      # same UVs as the exported picture
                nt.links.new(node.inputs["Vector"].links[0].from_socket, m.inputs["Vector"])
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(m.outputs["Color"], sep.inputs[0])
            geo, mapping = nt.nodes.new("ShaderNodeNewGeometry"), nt.nodes.new("ShaderNodeMapping")
            nt.links.new(geo.outputs["Position"], mapping.inputs["Vector"])
            k = 1.0 / max(float(conf["tile_m"]), 0.1)
            mapping.inputs["Scale"].default_value = (k, k, k)
            colour = None
            for ch, sock in (("b", 2), ("r", 0), ("g", 1)):
                tex = nt.nodes.new("ShaderNodeTexImage")
                tex.image = bpy.data.images.load(layers[ch], check_existing=True)
                nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                if colour is None:
                    mix.inputs[6].default_value = (*conf["bare"], 1.0)
                else:
                    nt.links.new(colour, mix.inputs[6])
                layer = tex.outputs["Color"]
                if "nastc" in os.path.basename(layers[ch]).lower():
                    layer = _clamp_blue(nt, layer)
                nt.links.new(layer, mix.inputs[7])
                nt.links.new(sep.outputs[sock], mix.inputs[0])
                colour = mix.outputs[2]
            nt.links.new(colour, bsdf.inputs["Base Color"])
            fixed.append(mat.name)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"terrain {mat.name} not rebuilt: {e}")
    return {"materials": fixed, **{k: conf[k] for k in ("b", "r", "g", "tile_m")}}


def _clamp_blue(nt, colour_socket):
    """blue = min(blue, green). 2026-09-29: the grass layer Terrain_Ground_01_D_nastc.png (a decoded ASTC picture) has its dry blades
    in magenta (3 % of the pixels; tan in the game) — in green grass blue is already below green, so only those blades change (to
    tan)."""
    sep, cmb, low = nt.nodes.new("ShaderNodeSeparateColor"), nt.nodes.new("ShaderNodeCombineColor"), nt.nodes.new("ShaderNodeMath")
    low.operation = "MINIMUM"
    nt.links.new(colour_socket, sep.inputs[0])
    nt.links.new(sep.outputs[2], low.inputs[0])
    nt.links.new(sep.outputs[1], low.inputs[1])
    nt.links.new(sep.outputs[0], cmb.inputs[0])
    nt.links.new(sep.outputs[1], cmb.inputs[1])
    nt.links.new(low.outputs[0], cmb.inputs[2])
    return cmb.outputs[0]


def fix_foliage(warnings):
    """2026-09-29, official FF export: grass cards (plant_grass_B_New_D_A.png, RGB) get their shape from a separate mask
    (<name>_M.png: white blades on mid grey) that the FBX never links — at eye level every grass card rendered as an opaque square.
    A material with no Alpha link whose colour picture has a sibling "<stem without _D/_D_A>_M" picture: the mask becomes the Alpha
    (grey → clear, white → solid). Returns the names changed."""
    fixed = []
    for mat in bpy.data.materials:
        bsdf = _principled(mat)
        if bsdf is None or bsdf.inputs["Alpha"].is_linked or not bsdf.inputs["Base Color"].is_linked:
            continue
        node = bsdf.inputs["Base Color"].links[0].from_node
        img = getattr(node, "image", None)
        if img is None:
            continue
        path = bpy.path.abspath(img.filepath)
        stem, ext = os.path.splitext(os.path.basename(path))
        base = stem[:-4] if stem.lower().endswith("_d_a") else (stem[:-2] if stem.lower().endswith("_d") else None)
        mask = os.path.join(os.path.dirname(path), f"{base}_M{ext}") if base else None
        if not mask or not os.path.exists(mask):
            continue
        try:
            nt = mat.node_tree
            m = nt.nodes.new("ShaderNodeTexImage")
            m.image = bpy.data.images.load(mask, check_existing=True)
            m.image.colorspace_settings.name = "Non-Color"
            if node.inputs["Vector"].is_linked:
                nt.links.new(node.inputs["Vector"].links[0].from_socket, m.inputs["Vector"])
            rng = nt.nodes.new("ShaderNodeMapRange")
            rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.45, 0.7
            nt.links.new(m.outputs["Color"], rng.inputs["Value"])
            nt.links.new(rng.outputs["Result"], bsdf.inputs["Alpha"])
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "DITHERED"
            fixed.append(mat.name)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"foliage {mat.name} not fixed: {e}")
    return fixed


WATER_WORDS = ("water", "river", "ocean", "wave", "pool")


def fix_water(warnings, colour=(0.05, 0.42, 0.58)):
    """2026-09-29, official FF export (Peak's pools): the water's colour is a ripple NORMAL map (norm_T_Water_Ripple…, blue-violet) or
    missing (Blender's magenta) — the pools rendered purple. A water material (name has water / river / ocean / wave / pool) whose
    colour picture is missing, not linked or a normal map becomes clear blue, glossy water. Returns the names changed."""
    fixed = []
    for mat in bpy.data.materials:
        if not any(w in mat.name.lower() for w in WATER_WORDS):
            continue
        bsdf = _principled(mat)
        if bsdf is None:
            continue
        sock = bsdf.inputs["Base Color"]
        img = sock.links[0].from_node.image if sock.is_linked and getattr(sock.links[0].from_node, "image", None) else None
        stem = os.path.splitext(os.path.basename(bpy.path.abspath(img.filepath) if img else ""))[0].lower()
        normal_map = stem.startswith("norm_") or stem.endswith("_n") or "normal" in stem
        if img is not None and img.has_data and not normal_map:
            continue
        try:
            if sock.is_linked:
                mat.node_tree.links.remove(sock.links[0])
            sock.default_value = (*colour, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.05
            fixed.append(mat.name)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"water {mat.name} not fixed: {e}")
    return fixed


# ---- weather on the geometry ----------------------------------------------------------------------------------------------
def _principled(mat):
    if not mat or not mat.use_nodes:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _mix_into(nt, bsdf, socket_name, value, factor_socket):
    """bsdf.<socket> = mix(current input, value, factor) — keeps a texture that is linked to it."""
    sock = bsdf.inputs.get(socket_name)
    if sock is None:
        return
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA" if socket_name == "Base Color" else "FLOAT"
    a, b = (mix.inputs[6], mix.inputs[7]) if mix.data_type == "RGBA" else (mix.inputs[2], mix.inputs[3])
    if sock.is_linked:
        nt.links.new(sock.links[0].from_socket, a)
    elif mix.data_type == "RGBA":
        a.default_value = sock.default_value
    else:
        a.default_value = float(sock.default_value)
    b.default_value = value
    nt.links.new(factor_socket, mix.inputs[0])
    out = mix.outputs[2] if mix.data_type == "RGBA" else mix.outputs[0]
    nt.links.new(out, sock)


def apply_weather(weather, warnings):
    """Snow on up-facing faces, wet surfaces, fog in the air. Each material is changed on its own; one that cannot be changed is
    left as it is and named in the warnings (never stop a render for the weather)."""
    snow, wet, fog = (max(0.0, min(1.0, float(weather.get(k, 0) or 0))) for k in ("snow", "wet", "fog"))
    done = set()
    for mat in bpy.data.materials:
        bsdf = _principled(mat)
        if bsdf is None or mat.name in done:
            continue
        done.add(mat.name)
        nt = mat.node_tree
        try:
            if snow > 0:
                geo, sep, rng = nt.nodes.new("ShaderNodeNewGeometry"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeMapRange")
                nt.links.new(geo.outputs["Normal"], sep.inputs[0])
                nt.links.new(sep.outputs[2], rng.inputs["Value"])
                rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.55, 0.85
                rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.0, snow
                _mix_into(nt, bsdf, "Base Color", (0.92, 0.94, 0.97, 1.0), rng.outputs["Result"])
                _mix_into(nt, bsdf, "Roughness", 0.55, rng.outputs["Result"])
            if wet > 0:
                val = nt.nodes.new("ShaderNodeValue")
                val.outputs[0].default_value = wet
                _mix_into(nt, bsdf, "Base Color", (0.02, 0.02, 0.025, 1.0), _scaled(nt, val.outputs[0], 0.35))
                _mix_into(nt, bsdf, "Roughness", 0.08, val.outputs[0])
        except Exception as e:  # noqa: BLE001
            warnings.append(f"weather not applied to material {mat.name}: {e}")
    # fog is NOT a Blender volume: EEVEE treats a world volume as endless (the whole plate came out black, 2026-09-25). It is laid in
    # 2D from the depth picture instead (core/plate_env.finish_plate), which also keeps it the same on the character.
    return {"snow": snow, "wet": wet, "fog": fog, "materials": len(done)}


def _scaled(nt, socket, k):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    nt.links.new(socket, m.inputs[0])
    m.inputs[1].default_value = k
    return m.outputs[0]


def stand_in(location, height):
    """An invisible-to-camera body of the character's size that still casts a shadow (and shows in reflections)."""
    r = max(height * 0.13, 0.08)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=height * 0.8, location=(location[0], location[1], location[2] + height * 0.4))
    body = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=height * 0.07, location=(location[0], location[1], location[2] + height * 0.9))
    head = bpy.context.active_object
    for o in (body, head):
        o.name = "PLATES_STANDIN"
        if hasattr(o, "visible_camera"):
            o.visible_camera = False
    return [body, head]


def add_lights(specs):
    """S5.7: the shot's practical lights (lamp, fire, screen…), created for one camera and removed after it."""
    made = []
    for i, lt in enumerate(specs or []):
        kind = str(lt.get("type") or "POINT").upper()
        data = bpy.data.lights.new(f"PLATES_PRACTICAL_{i}", kind if kind in ("POINT", "AREA", "SPOT") else "POINT")
        data.energy = float(lt.get("energy") or 300.0)
        data.color = tuple(float(c) for c in (lt.get("color") or [1.0, 0.8, 0.5])[:3])
        if data.type == "SPOT":
            data.spot_size = math.radians(float(lt.get("spot_deg") or 35.0))
            data.spot_blend = 0.4
        elif data.type == "AREA":
            data.size = float(lt.get("size") or 0.5)
        elif hasattr(data, "shadow_soft_size"):
            data.shadow_soft_size = float(lt.get("size") or 0.1)
        obj = bpy.data.objects.new(f"PLATES_PRACTICAL_{i}", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = Vector(lt["location"])
        if lt.get("look_at"):
            # first render (29/09, covered yard): a lamp 2.8 m up sat INSIDE the ceiling slab and lit nothing. Walk the line from the
            # character's chest to the lamp; a wall / ceiling on the way stops the lamp 0.3 m in front of it
            origin = Vector(lt["look_at"])
            path = obj.location - origin
            dist = path.length
            if dist > 0.05:
                hit, where, *_ = bpy.context.scene.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, path.normalized(),
                                                            distance=dist + 0.3)
                if hit:
                    obj.location = origin + path.normalized() * max((where - origin).length - 0.3, 0.3)
        if lt.get("look_at"):
            look_at(obj, lt["look_at"])
        made.append(obj)
    return made


def add_props(specs):
    """V4 Sân khấu 3D (#24 người dùng 10/10): đạo cụ KHÔNG có trong mô hình (giếng) dựng thành khối thay thế đúng chỗ + đúng cỡ đã tính trên
    sân khấu, chỉ cho camera này (xóa sau khi chụp) — model ảnh vẽ đạo cụ thật lên đúng khuôn, không tự đặt theo chữ (gốc lỗi 'tỉ lệ giếng').
    spec = {"kind": "well", "at": [x, y, z chân] (scene), "radius", "height", "hollow", "sides"}."""
    made = []
    for i, p in enumerate(specs or []):
        if p.get("kind") != "well":
            continue
        x, y, z = (float(v) for v in p["at"])
        r, h, n = float(p["radius"]), float(p["height"]), int(p.get("sides") or 8)
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=h, location=(x, y, z + h / 2))
        wall = bpy.context.active_object
        wall.name = f"PLATES_PROP_{i}"
        stone = bpy.data.materials.new(f"PLATES_PROP_stone_{i}")
        stone.use_nodes = True
        bsdf = stone.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.13, 0.125, 0.12, 1)   # đá tối: 0,42 ra gần trắng dưới trăng + sương (10/10)
            bsdf.inputs["Roughness"].default_value = 0.9
        wall.data.materials.append(stone)
        made.append(wall)
        if p.get("hollow", True):                                        # miệng giếng tối (lòng giếng) ngay dưới mép
            bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r - 0.18, depth=0.02, location=(x, y, z + h + 0.005))
            hole = bpy.context.active_object
            hole.name = f"PLATES_PROP_{i}_hole"
            dark = bpy.data.materials.new(f"PLATES_PROP_dark_{i}")
            dark.use_nodes = True
            b2 = dark.node_tree.nodes.get("Principled BSDF")
            if b2 is not None:
                b2.inputs["Base Color"].default_value = (0.01, 0.01, 0.012, 1)
            hole.data.materials.append(dark)
            made.append(hole)
    return made


# ---- cameras --------------------------------------------------------------------------------------------------------------
def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def preset_cameras(names, lo, hi, target, eye_h):
    centre = Vector(target) if target else Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))
    span = max(hi.x - lo.x, hi.y - lo.y)
    height = hi.z - lo.z
    dist = span * 0.75 + 10
    out = []
    for name in names:
        kind, _, deg = name.partition("_")
        a = math.radians(float(deg or 0))
        ring = Vector((math.sin(a), -math.cos(a), 0))
        if kind == "eye":
            loc = centre + ring * dist + Vector((0, 0, eye_h))
            aim = centre + Vector((0, 0, eye_h))                         # a level camera: horizon mid-frame, like a person standing
            angle = "eye_level"
        elif kind == "low":
            loc = centre + ring * (dist * 0.6) + Vector((0, 0, 0.4))
            aim = centre + Vector((0, 0, height * 0.6))
            angle = "low_angle"
        elif kind == "high":
            loc = centre + ring * (dist * 1.2) + Vector((0, 0, height * 0.9 + 8))
            aim = centre + Vector((0, 0, height * 0.15))
            angle = "high_angle"
        else:
            continue
        out.append({"name": name, "location": list(loc), "look_at": list(aim), "angle": angle})
    return out


def _plate_camera():
    """core/plate_camera.py loaded by path (pure Python: math/re/typing only) — Blender's Python does not have the repo on sys.path."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "plate_camera.py")
    spec = importlib.util.spec_from_file_location("plate_camera_pure", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clearance(c, warnings):
    """P24 (#24 shots 4/5/7): rays round a shot camera that has a subject — is the camera inside / behind a wall on its sight line,
    and is a wall right behind the character filling a level / upward view? core/plate_camera.clearance_fix decides (step in front,
    rise over a low wall, or report a tall one). Returns the decision (notes / warnings) and moves c's location in place.
    rà P24: any error (module load, ray_cast, the decision) → the plate is rendered without the check and the manifest says so;
    the same-axis WIDE view (c["wide"]) is never moved, only warned; an indoor camera skips the wall-behind test (a room's back
    wall is the background there, and the downward ray would read the ceiling)."""
    try:
        return _clearance(c, _plate_camera())
    except Exception as e:  # noqa: BLE001 - never silent: the plate is rendered without the check, and the manifest says so
        warnings.append(f"clearance check skipped ({c.get('name')}): {type(e).__name__}: {e}")
        return {"skipped": f"{type(e).__name__}: {e}"}


def _clearance(c, pure):
    scene, dg = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
    loc, aim, feet = Vector(c["location"]), Vector(c["look_at"]), Vector(c["subject"]["location"])
    h = float(c["subject"].get("height_m") or 1.7)
    # from the character's body (at the camera's height, inside their own height) to the camera — not from the aim point: a look-down
    # shot aims at the ground beyond them (inside the well) and the rim is not a wall round the camera
    body = Vector((feet.x, feet.y, min(max(loc.z, feet.z + 0.5), feet.z + h)))
    back = loc - body
    block = None
    if back.length > 0.05:
        hit, where, *_ = scene.ray_cast(dg, body, back.normalized(), distance=back.length)
        if hit:
            block = (where - body).length
    bg = top = None
    flat = Vector((aim.x - loc.x, aim.y - loc.y, 0))
    if flat.length > 0.05 and not c.get("indoor"):
        hit, where, *_ = scene.ray_cast(dg, loc, flat.normalized(), distance=60.0)
        if hit:
            bg = (Vector((where.x, where.y, 0)) - Vector((loc.x, loc.y, 0))).length
            past = where + flat.normalized() * 0.05
            # taller than a "low wall"? a level ray just above that limit, along the same view — never a ray started inside a tall
            # wall (it would read the wall's bottom as its top)
            limit = feet.z + h + pure.LOW_WALL_EXTRA_M + 0.05
            tall = scene.ray_cast(dg, Vector((loc.x, loc.y, limit)), flat.normalized(), distance=bg + 0.3)
            # the top just past the face, from 3 m above the hit (not 40 m above the camera: a roof / canopy overhead is not the wall)
            up = scene.ray_cast(dg, Vector((past.x, past.y, where.z + 3.0)), Vector((0, 0, -1)), distance=6.0)
            top = up[1].z if up[0] else where.z
            if tall[0]:
                top = max(top, limit)
    fix = pure.clearance_fix(list(loc), list(aim), list(feet), h, block_m=block, bg_m=bg, bg_top_z=top, block_from=list(body),
                             move=not c.get("wide") and not c.get("locked"))   # máy Sân khấu 3D v2 đã đo bằng tia: không dời
    out = {"notes": fix["notes"], "warnings": fix["warnings"], "block_m": None if block is None else round(block, 2),
           "background_m": None if bg is None else round(bg, 2), "background_top_m": None if top is None else round(top - feet.z, 2)}
    if fix["location"] != [round(v, 3) for v in loc]:
        out["moved_from_m"] = [round(v, 3) for v in loc]
        c["location"] = fix["location"]
    return out


def camera_info(cam, target, res):
    d = Vector(target) - cam.location
    pitch = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    yaw = math.degrees(math.atan2(d.x, d.y))
    vfov = 2 * math.atan(math.tan(cam.data.angle / 2) * res[1] / max(res))
    horizon = 0.5 + 0.5 * math.tan(math.radians(pitch)) / math.tan(vfov / 2)
    return {"location_m": [round(v, 2) for v in cam.location], "look_at_m": [round(v, 2) for v in target],
            "height_m": round(cam.location.z, 2), "pitch_deg": round(pitch, 1), "yaw_deg": round(yaw, 1),
            "lens_mm": cam.data.lens, "vfov_deg": round(math.degrees(vfov), 1), "horizon_y": round(horizon, 3)}


def set_analysis(info, angle, sky_used):
    """The same fields Claude writes when it reads a background picture (core/layout.validate_set_analysis) — exact here, from the
    camera, so the Dashboard never pays to read a rendered plate."""
    h = max(min(info["horizon_y"], 3), -2)
    top = min(max(h + 0.02, 0.0), 0.97)
    return {"camera": {"eye_level": "eye", "low_angle": "low", "high_angle": "high"}.get(angle, "eye"), "horizon_y": round(h, 3),
            "camera_height_m": max(info["height_m"], 0.1), "ground": [[0, top], [1, top], [1, 1], [0, 1]], "landmarks": [],
            "light": f"3D render, sky {sky_used}", "notes": "rendered 3D plate (exact camera)", "source": "3d"}


# ---- render ---------------------------------------------------------------------------------------------------------------
def pick_engine(want, warnings):
    scene = bpy.context.scene
    items = enum_items(scene.render, "engine")
    eevee = next((e for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT") if e in items), None)
    order = {"eevee": [eevee], "cycles": ["CYCLES"], "workbench": ["BLENDER_WORKBENCH"]}.get(want, [eevee, "CYCLES"])
    for e in order:
        if e and e in items:
            scene.render.engine = e
            return e
    warnings.append(f"engine {want} not available ({items})")
    return scene.render.engine


def render_to(path, rgba):
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if rgba else "RGB"
    scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t0


def depth_material(far):
    mat = bpy.data.materials.new("PLATES_DEPTH")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    cam = nt.nodes.new("ShaderNodeCameraData")
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.1, far
    rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 1.0, 0.0     # near = white
    emit, out = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(cam.outputs["View Z Depth"], rng.inputs["Value"])
    nt.links.new(rng.outputs["Result"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def probe(cfg, meshes, factor, lo, hi):
    """Flat walkable areas: a down-ray every `step` metres; a hit whose normal points up (z > 0.9) is floor. Heights are grouped in
    0.4 m bands and each band split into connected grid areas. Coordinates are given back in the raw model's own frame."""
    step = float(cfg["probe"].get("step", 2.0))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    hits = {}
    nx, ny = int((hi.x - lo.x) / step) + 1, int((hi.y - lo.y) / step) + 1
    for i in range(nx):
        for j in range(ny):
            x, y = lo.x + i * step, lo.y + j * step
            ok, loc, normal, _, obj, _ = scene.ray_cast(depsgraph, Vector((x, y, hi.z + 5)), Vector((0, 0, -1)))
            if ok and normal.z > 0.9 and obj is not None and obj.name != "PLATES_GROUND":
                hits[(i, j)] = loc.z
    areas, seen = [], set()
    for cell, z in hits.items():
        if cell in seen:
            continue
        stack, members = [cell], []
        seen.add(cell)
        while stack:
            c = stack.pop()
            members.append(c)
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in hits and n not in seen and abs(hits[n] - hits[c]) < 0.4:
                    seen.add(n)
                    stack.append(n)
        if len(members) < 3:
            continue
        xs = [lo.x + m[0] * step for m in members]
        ys = [lo.y + m[1] * step for m in members]
        zs = [hits[m] for m in members]
        back = lambda v, lift=0.0: round((v - lift) / factor, 3)  # noqa: E731 - scene metres -> raw model units
        areas.append({"cells": len(members), "area_m2": round(len(members) * step * step, 1),
                      "centre": [back(sum(xs) / len(xs)), back(sum(ys) / len(ys)), back(sum(zs) / len(zs), LIFT_Z)],
                      "min": [back(min(xs)), back(min(ys))], "max": [back(max(xs)), back(max(ys))]})
    areas.sort(key=lambda a: -a["cells"])
    return {"step_m": step, "rays": nx * ny, "floor_hits": len(hits), "areas": areas[:40]}


PLANT_NAMES = ("tree", "greentree", "plant", "bush", "grass", "shrub", "coco", "leaf", "palm")


def heights(cfg, factor, hi):
    """Ground height under each [x, y] of cfg["heights"] (raw model frame): the first down-ray hit that is not a plant (trees, grass
    cards). 2026-09-29: to stand a character on the ground around a place (views of the surroundings), not only on probed flat
    areas. Each result: {"at": [x, y, z], "on": object hit, "flat": normal z ≥ 0.9} or {"at": [x, y], "miss": true}."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    out = []
    for pt in cfg["heights"]:
        x0, y0 = pt[0], pt[1]
        sx, sy, sz = to_scene((x0, y0, pt[2] if len(pt) > 2 else 0), factor)
        # a third number = start the ray there (just under a ceiling: the floor INSIDE a house, not its roof)
        origin, found = Vector((sx, sy, sz if len(pt) > 2 else hi.z + 5)), None
        for _ in range(12):                                        # step through plants
            ok, loc, normal, _, obj, _ = scene.ray_cast(depsgraph, origin, Vector((0, 0, -1)))
            if not ok or obj is None or obj.name == "PLATES_GROUND":
                break
            if any(k in obj.name.lower() for k in PLANT_NAMES):
                origin = loc - Vector((0, 0, 0.05))
                continue
            found = (loc, normal, obj.name)
            break
        if found is None:
            out.append({"at": [x0, y0], "miss": True})
        else:
            loc, normal, name = found
            out.append({"at": [x0, y0, round((loc.z - LIFT_Z) / factor, 3)], "on": name, "flat": normal.z >= 0.9,
                        "from_z": pt[2] if len(pt) > 2 else None})
    return out


def rooms(cfg, factor):
    """Camera spots INSIDE houses (2026-09-29 — guessed from furniture positions they landed outside walls / against them): for each
    {"name", "lo": [x, y], "hi": [x, y], "floor_z"} (raw model frame) a grid of points at eye height is tested — a ceiling within
    ceiling_m above (so it is indoors), rays in 16 directions for room size. The point farthest from its nearest wall wins; it looks
    along its longest free ray (the deepest view of the room). Result per room: {"name", "location", "look_at", "clear_m", "depth_m"}
    or {"name", "miss": reason}."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    out = []
    eye = float(cfg.get("eye_height_m", 1.6))
    for r in cfg["rooms"]:
        step, ceiling = float(r.get("step", 0.75)), float(r.get("ceiling_m", 5.0))
        diag = math.hypot(r["hi"][0] - r["lo"][0], r["hi"][1] - r["lo"][1]) * factor * 1.1     # a ray longer than this left the house
        best = None
        x = r["lo"][0]
        while x <= r["hi"][0]:
            y = r["lo"][1]
            while y <= r["hi"][1]:
                p = Vector(to_scene((x, y, float(r["floor_z"]) + eye), factor))
                up = scene.ray_cast(depsgraph, p, Vector((0, 0, 1)))
                down = scene.ray_cast(depsgraph, p, Vector((0, 0, -1)))
                if up[0] and (up[1].z - p.z) < ceiling and down[0] and (p.z - down[1].z) < eye + 0.4:
                    dists = []
                    for k in range(16):
                        a = 2 * math.pi * k / 16
                        d = Vector((math.cos(a), math.sin(a), 0))
                        hit = scene.ray_cast(depsgraph, p, d, distance=60.0)
                        dists.append((hit[1] - p).length if hit[0] else 60.0)
                    inside = [d for d in dists if d <= diag]
                    clear = min(dists)
                    if len(inside) >= 12 and (best is None or clear > best[0]):   # walls nearly all round = a room (doors allowed)
                        k_in = dists.index(max(inside))
                        k_out = dists.index(max(dists)) if max(dists) > diag else None
                        best = (clear, max(inside), (x, y), 2 * math.pi * k_in / 16,
                                None if k_out is None else (2 * math.pi * k_out / 16, dists[k_out]))
                y += step
            x += step
        if best is None:
            out.append({"name": r["name"], "miss": "no closed room with a ceiling found in that box"})
            continue
        clear, deep, (x, y), a, door = best
        z = float(r["floor_z"]) + eye
        far = min(deep / factor - 0.3, 12.0)                              # raw model units, like x / y
        item = {"name": r["name"], "location": [round(x, 3), round(y, 3), round(z, 3)],
                "look_at": [round(x + math.cos(a) * far, 3), round(y + math.sin(a) * far, 3), round(z - 0.4, 3)],
                "clear_m": round(clear / factor, 2), "depth_m": round(deep / factor, 2)}
        if door:                                                        # a view out through a door / window from inside
            ao = door[0]
            item["look_out"] = [round(x + math.cos(ao) * 12.0, 3), round(y + math.sin(ao) * 12.0, 3), round(z - 0.2, 3)]
        out.append(item)
    return out


def main():
    cfg = args_config()
    out_dir = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    warnings = []
    manifest = {"blender": bpy.app.version_string, "model": {"path": cfg["model"],
                "size_mb": round(os.path.getsize(cfg["model"]) / 1e6, 1)}, "plates": [], "warnings": warnings}
    meshes, import_sec = load_model(cfg["model"], warnings)
    manifest["model"].update({"objects": len(meshes), "triangles": triangles(meshes), "import_sec": round(import_sec, 1)})
    log(f"imported {len(meshes)} meshes, {manifest['model']['triangles']:,} triangles in {import_sec:.1f}s")
    factor, (lo, hi) = normalise_scale(meshes, cfg.get("real_height_m"), warnings)
    manifest["scale_factor"] = factor
    manifest["bbox_m"] = {"min": [round(v, 2) for v in lo], "max": [round(v, 2) for v in hi],
                          "size": [round(hi[i] - lo[i], 2) for i in range(3)]}
    if cfg.get("rooms"):
        manifest["rooms"] = rooms(cfg, factor)
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        log(f"rooms: {len(manifest['rooms'])}")
        return
    if cfg.get("heights"):
        manifest["heights"] = heights(cfg, factor, hi)
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        log(f"heights: {len(manifest['heights'])} points")
        return
    if cfg.get("probe"):
        manifest["probe"] = probe(cfg, meshes, factor, lo, hi)
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        log(f"probe: {len(manifest['probe']['areas'])} flat areas")
        return
    decimate(meshes, float(cfg.get("decimate", 1.0)))
    if cfg.get("ground", True):
        add_ground(lo, hi)
    sky = cfg.get("sky") or {}
    manifest["sky"] = dict(sky, used=setup_world(sky, warnings))
    if cfg.get("terrain", {}) is not False:                              # before the weather: snow / wet mix into the rebuilt colour
        manifest["terrain"] = fix_terrain(cfg.get("terrain"), warnings)
    manifest["water_fixed"] = fix_water(warnings)
    manifest["foliage_fixed"] = fix_foliage(warnings)
    if cfg.get("weather"):
        manifest["weather"] = apply_weather(cfg["weather"], warnings)
    scene = bpy.context.scene
    res = cfg.get("resolution") or [1280, 720]
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = int(res[0]), int(res[1]), 100
    engine = pick_engine((cfg.get("engine") or "auto").lower(), warnings)
    samples = int(cfg.get("samples", 16))
    for owner, attr in ((getattr(scene, "eevee", None), "taa_render_samples"), (getattr(scene, "cycles", None), "samples")):
        if owner is not None and hasattr(owner, attr):
            setattr(owner, attr, samples)
    if engine == "CYCLES" and hasattr(scene, "cycles") and hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = False                               # plates are references: speed over the last bit of noise
    manifest["engine"] = engine
    names = cfg.get("presets")
    if names is None or (not names and not cfg.get("cameras")):
        names = DEFAULT_PRESETS                                          # [] with shot cameras = those cameras only (location pack)
    cams = preset_cameras(names, lo, hi, cfg.get("target"), float(cfg.get("eye_height_m", 1.6)))
    for c in cfg.get("cameras") or []:
        if c.get("model_coords"):                                        # given in the raw model's coordinates (probe / Blender UI)
            c = dict(c, location=to_scene(c["location"], factor), look_at=to_scene(c["look_at"], factor))
            if c.get("subject"):
                c["subject"] = dict(c["subject"], location=to_scene(c["subject"]["location"], factor))
            if c.get("props"):
                c["props"] = [dict(pp, at=to_scene(pp["at"], factor)) for pp in c["props"]]
            if c.get("lights"):
                c["lights"] = [dict(lt, location=to_scene(lt["location"], factor),
                                    **({"look_at": to_scene(lt["look_at"], factor)} if lt.get("look_at") else {})) for lt in c["lights"]]
        cams.append(dict(c, angle=c.get("angle") or "eye_level"))
    manifest["lift_z"] = round(LIFT_Z, 3)
    span = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    for c in cams:
        data = bpy.data.cameras.new(c["name"])
        data.lens = float(c.get("lens") or cfg.get("lens_mm", 35))
        data.clip_end = max(1000.0, span * 20)
        cam = bpy.data.objects.new(c["name"], data)
        scene.collection.objects.link(cam)
        clr = clearance(c, warnings) if c.get("subject") else None     # P24: before placing — may move c["location"]
        if clr and clr.get("moved_from_m"):                              # rà P24: the caller re-frames the character from this
            loc = c["location"]
            clr["location_model"] = ([round((loc[0]) / factor, 4), round(loc[1] / factor, 4), round((loc[2] - LIFT_Z) / factor, 4)]
                                     if c.get("model_coords") else list(loc))
        cam.location = Vector(c["location"])
        look_at(cam, c["look_at"])
        scene.camera = cam
        practical = add_lights(c.get("lights"))
        props_made = add_props(c.get("props"))
        info = camera_info(cam, c["look_at"], res)
        plate = os.path.join(out_dir, f"plate_{c['name']}.png")
        indoor = c.get("indoor") or None                                 # 29/09: rooms lit only through windows came out black
        base_exposure, fill = scene.view_settings.exposure, None
        if indoor:
            scene.view_settings.exposure = base_exposure + float(indoor.get("exposure", 1.5))
            if float(indoor.get("fill_w", 0) or 0) > 0:
                lamp = bpy.data.lights.new(f"fill_{c['name']}", "POINT")
                lamp.energy = float(indoor["fill_w"])
                lamp.color = tuple(indoor.get("fill_color") or (1.0, 0.92, 0.8))
                lamp.shadow_soft_size = 1.0
                fill = bpy.data.objects.new(f"fill_{c['name']}", lamp)
                scene.collection.objects.link(fill)
                mid = (Vector(c["location"]) + Vector(c["look_at"])) / 2       # between the camera and what it looks at, near the ceiling
                fill.location = (mid.x, mid.y, Vector(c["location"]).z + float(indoor.get("fill_up_m", 0.9)))
        try:
            sec = render_to(plate, scene.render.film_transparent)
        except RuntimeError as e:
            if engine.startswith("BLENDER_EEVEE") and (cfg.get("engine") or "auto") == "auto":
                warnings.append(f"EEVEE failed ({e}); switched to Cycles")     # no GPU (e.g. a server): slower but works
                engine = pick_engine("cycles", warnings)
                manifest["engine"] = engine
                sec = render_to(plate, scene.render.film_transparent)
            else:
                raise
        item = {"name": c["name"], "angle": c["angle"], "file": os.path.basename(plate), "render_sec": round(sec, 2),
                "camera": info, "set_analysis": set_analysis(info, c["angle"], manifest["sky"]["used"])}
        if clr is not None:
            item["clearance"] = clr
        if cfg.get("depth", True) and engine != "BLENDER_WORKBENCH":
            far = max((Vector(p) - cam.location).length for p in ([lo.x, lo.y, lo.z], [hi.x, hi.y, hi.z],
                                                                  [lo.x, hi.y, hi.z], [hi.x, lo.y, lo.z]))
            layer = bpy.context.view_layer
            vs = scene.view_settings
            keep = (layer.material_override, vs.view_transform, scene.render.film_transparent, vs.exposure, vs.gamma, vs.look,
                    getattr(vs, "use_white_balance", None))
            layer.material_override = depth_material(far)
            vs.view_transform = "Standard"
            # 08/10 (#24, lỗi 14): the night exposure (-1.4) and the contrast look were applied to the depth picture too — every pixel came
            # out ~0.64 grey (read as ~127 m), the fog covered 97 % and the plate was flat. The depth is written with exposure 0, no look.
            vs.exposure, vs.gamma = 0.0, 1.0
            try:
                vs.look = "None"
            except (TypeError, ValueError):
                pass
            if keep[6] is not None:
                vs.use_white_balance = False
            scene.render.film_transparent = True
            depth = os.path.join(out_dir, f"depth_{c['name']}.png")
            item["depth_file"] = os.path.basename(depth)
            item["depth_sec"] = round(render_to(depth, True), 2)
            item["depth_range_m"] = [0.1, round(far, 2)]                  # white = 0.1 m, black = far: linear in between (sRGB-encoded PNG)
            item["depth_exposure"] = 0.0
            layer.material_override, vs.view_transform, scene.render.film_transparent = keep[:3]
            vs.exposure, vs.gamma = keep[3], keep[4]
            try:
                vs.look = keep[5]
            except (TypeError, ValueError):
                pass
            if keep[6] is not None:
                vs.use_white_balance = keep[6]
        if c.get("subject"):                                             # the character's shadow on this plate
            parts = stand_in(c["subject"]["location"], float(c["subject"].get("height_m") or 1.7))
            shadow = os.path.join(out_dir, f"shadow_{c['name']}.png")
            item["shadow_file"] = os.path.basename(shadow)
            item["shadow_sec"] = round(render_to(shadow, scene.render.film_transparent), 2)
            item["subject"] = {"location_m": [round(v, 3) for v in c["subject"]["location"]], "height_m": c["subject"].get("height_m")}
            for o in parts:
                bpy.data.objects.remove(o, do_unlink=True)
        if indoor:
            scene.view_settings.exposure = base_exposure
            item["indoor"] = indoor
            if fill is not None:
                bpy.data.objects.remove(fill, do_unlink=True)
        for o in props_made:
            bpy.data.objects.remove(o, do_unlink=True)
        if practical:
            item["lights"] = [{"type": o.data.type, "energy": o.data.energy, "location_m": [round(v, 3) for v in o.location]}
                              for o in practical]
            for o in practical:
                bpy.data.objects.remove(o, do_unlink=True)
        manifest["plates"].append(item)
        log(f"{c['name']}: {item['render_sec']}s")
    for a in cfg.get("animations") or []:                                # S5.1 / S5.6: camera moves through the place (frames)
        manifest.setdefault("animations", []).append(render_animation(a, cfg, factor, span, res, out_dir))
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    log(f"done: {len(manifest['plates'])} plates -> {out_dir}")


def _ease(u):
    return u * u * (3 - 2 * u)                                           # smooth start and stop, like a dolly / crane operator


def _lerp(a, b, u):
    return [a[i] + (b[i] - a[i]) * u for i in range(3)]


def clay_material():
    """White model (Seedance 2.5 'white-model' reference, ClipAI Blender add-on): one matte light-grey material on everything, so the
    video model reads space and movement without copying the textures."""
    mat = bpy.data.materials.new("clay")
    mat.use_nodes = True
    bsdf = _principled(mat)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.78, 0.78, 0.76, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.95
    return mat


def _flat_material(name, rgb):
    """A plain, clearly coloured matte material (an actor block of the white model: one colour per person)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = _principled(mat)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    return mat


def add_actor(actor, factor):
    """S10.6: one person of a coarse white model — a coloured upright block (cylinder, the person's height) with a small cone at chest
    height pointing where the person faces. Seedance 2.5 official (sd25-pe 粗粒度白模): every block is mapped to one person in the prompt."""
    h = float(actor.get("height", 1.8)) * factor
    r = float(actor.get("radius", 0.3)) * factor
    mat = _flat_material("actor_" + actor["name"], actor.get("color", (0.9, 0.1, 0.1)))
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(0, 0, 0))
    body = bpy.context.active_object
    body.name = "ACTOR_" + actor["name"]
    body.data.materials.append(mat)
    bpy.ops.mesh.primitive_cone_add(radius1=r * 0.55, depth=r * 1.6, location=(0, r * 1.1, h * 0.25), rotation=(-1.5708, 0, 0))
    nose = bpy.context.active_object
    nose.name = "ACTOR_NOSE_" + actor["name"]
    nose.data.materials.append(mat)
    nose.parent = body
    return body, h


def _place_actor(body, h, key_a, key_b, w):
    """Stand the block on its keyed ground point (eased) and turn its nose toward the keyed facing point."""
    loc = _lerp(key_a["location"], key_b["location"], w)
    body.location = Vector((loc[0], loc[1], loc[2] + h / 2))
    face_a, face_b = key_a.get("face"), key_b.get("face")
    if face_a and face_b:
        f = _lerp(face_a, face_b, w)
        d = Vector((f[0] - loc[0], f[1] - loc[1], 0))
        if d.length > 1e-6:
            import math
            body.rotation_euler = (0, 0, math.atan2(d.y, d.x) - math.pi / 2)


def _key_at(keys, u):
    k = next((i for i in range(len(keys) - 1) if keys[i]["t"] <= u <= keys[i + 1]["t"]), max(len(keys) - 2, 0))
    if len(keys) == 1:
        return keys[0], keys[0], 0.0
    span_u = max(keys[k + 1]["t"] - keys[k]["t"], 1e-6)
    return keys[k], keys[k + 1], _ease(min(max((u - keys[k]["t"]) / span_u, 0.0), 1.0))


def render_animation(a, cfg, factor, span, res, out_dir):
    """{"name", "fps", "seconds", "keys": [{"t": 0..1, "location", "look_at"}], "model_coords", "white", "lens"} → frames in
    anim_<name>/f_0001.png … (the Dashboard side joins them into an mp4 with ffmpeg). Keys are eased between (smooth moves)."""
    scene = bpy.context.scene
    keys = sorted(a["keys"], key=lambda k: k["t"])
    if a.get("model_coords"):
        keys = [dict(k, location=list(to_scene(k["location"], factor)), look_at=list(to_scene(k["look_at"], factor))) for k in keys]
    fps, seconds = int(a.get("fps", 24)), float(a.get("seconds", 5))
    n = max(int(round(fps * seconds)), 2)
    data = bpy.data.cameras.new("anim_" + a["name"])
    data.lens = float(a.get("lens") or cfg.get("lens_mm", 35))
    data.clip_end = max(1000.0, span * 20)
    cam = bpy.data.objects.new("anim_" + a["name"], data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    folder = os.path.join(out_dir, "anim_" + a["name"])
    os.makedirs(folder, exist_ok=True)
    layer = bpy.context.view_layer
    keep = layer.material_override
    actors = a.get("actors") or []
    swapped = []
    if a.get("white") and actors:        # coloured person blocks in a clay world: per-object clay (the view-layer override paints ALL)
        clay = clay_material()
        for ob in list(scene.objects):
            if ob.type == "MESH" and not ob.name.startswith("ACTOR"):
                for slot in ob.material_slots:
                    swapped.append((slot, slot.material))
                    slot.material = clay
                if not ob.material_slots:
                    ob.data.materials.append(clay)
    elif a.get("white"):
        layer.material_override = clay_material()
    placed = []
    for act in actors:
        akeys = sorted(act["keys"], key=lambda k: k["t"])
        if a.get("model_coords"):
            akeys = [dict(k, location=list(to_scene(k["location"], factor)),
                          **({"face": list(to_scene(k["face"], factor))} if k.get("face") else {})) for k in akeys]
        body, h = add_actor(act, factor)
        placed.append((body, h, akeys))
    t0 = time.time()
    for f in range(n):
        u = f / (n - 1)
        ka, kb, w = _key_at(keys, u)
        cam.location = Vector(_lerp(ka["location"], kb["location"], w))
        look_at(cam, _lerp(ka["look_at"], kb["look_at"], w))
        for body, h, akeys in placed:
            pa, pb, pw = _key_at(akeys, u)
            _place_actor(body, h, pa, pb, pw)
        render_to(os.path.join(folder, f"f_{f + 1:04d}.png"), scene.render.film_transparent)
    layer.material_override = keep
    for slot, mat in swapped:
        slot.material = mat
    sec = round(time.time() - t0, 1)
    log(f"animation {a['name']}: {n} frames in {sec}s")
    return {"name": a["name"], "folder": os.path.basename(folder), "frames": n, "fps": fps, "white": bool(a.get("white")),
            "actors": [x["name"] for x in actors], "render_sec": sec}


if __name__ == "__main__":
    main()
