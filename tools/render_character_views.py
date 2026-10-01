"""Blender (background): render a character .glb from 6 directions with its texture (core/meshy.render_views).
blender -b --factory-startup -P render_char_views.py -- <model.glb> <out_dir>
glTF characters face +Z (glTF) = -Y in Blender; the character's own LEFT is +X (seen from the front, on the image's right)."""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
model, out = argv[0], argv[1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=model)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (lo + hi) / 2
height = hi.z - lo.z
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x, scene.render.resolution_y = 768, 1152
scene.render.film_transparent = False
world = bpy.data.worlds.new("w")
scene.world = world
world.color = (0.85, 0.85, 0.85)
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.85, 0.85, 0.85)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = height * 1.12
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
# direction the camera stands in (from the character), name = what the picture shows
views = {"front": (0, -1), "back": (0, 1), "left_side": (1, 0), "right_side": (-1, 0),
         "front_left_34": (0.7071, -0.7071), "front_right_34": (-0.7071, -0.7071)}
dist = height * 3
for name, (dx, dy) in views.items():
    cam.location = center + Vector((dx * dist, dy * dist, 0))
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(out, f"{name}.png")
    bpy.ops.render.render(write_still=True)
print("DONE", height, len(objs))
