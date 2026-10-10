"""Đợt 2: kiểm hình học người nộm bằng bpy giả, không chạy Blender."""
import math
from copy import deepcopy
from types import SimpleNamespace

import pytest
from tools import stage_grid as tool
from core import stage_grid as sg


class Bpy:
    def __init__(self):
        self.objects = []
        self.context = SimpleNamespace(active_object=None)
        self.ops = SimpleNamespace(mesh=SimpleNamespace(**{
            f"primitive_{kind}_add": self.add(kind)
            for kind in ("cube", "cylinder", "uv_sphere", "cone")}))

    def add(self, kind):
        def run(**kw):
            obj = SimpleNamespace(kind=kind, args=kw, rotation_euler=(0, 0, 0),
                                  data=SimpleNamespace(materials=[]))
            self.objects.append(obj)
            self.context.active_object = obj
        return run


def render(p):
    bpy = Bpy()
    tool.add_person(bpy, p, (2, 3, 4), lambda name, color: color)
    return bpy.objects


def test_lying_east_matches_solver_center_and_extents():
    p = dict(name="K", height=1.8, tu_the="nam", body_length=1.8, body_height=.3, facing=90)
    body, head = render(p)
    assert body.kind == "cube"
    assert body.dimensions == pytest.approx((.3, 1.8, .3))
    assert body.args["location"] == pytest.approx((2, 3, 4.15))
    assert body.rotation_euler == pytest.approx((0, 0, -math.pi / 2))
    o = dict(kind="nguoi", xy=[2, 3], z=4, H=1.8, **{k: p[k] for k in ("tu_the", "body_length", "body_height", "facing")})
    assert head.args["location"] == pytest.approx(sg.lying_point(o, .45, sg.EYE))


def test_fallen_back_tilts_with_same_solver_envelope():
    body, _ = render(dict(name="K", height=1.8, tu_the="nga_ngua", body_length=1.8, body_height=.81, facing=0))
    angle = body.rotation_euler[0]
    assert angle > 0
    _, length, height = body.dimensions
    assert length * math.cos(angle) + height * math.sin(angle) == pytest.approx(1.8)
    assert length * math.sin(angle) + height * math.cos(angle) == pytest.approx(.81)


@pytest.mark.parametrize("pose", ["dung", "ngoi", "quy", "bo"])
def test_old_upright_numbers(pose):
    body, head, nose = render(dict(name="K", height=1.2, facing=90, tu_the=pose))
    assert body.args == dict(vertices=24, radius=.19, depth=1.2 - .13, location=(2, 3, 4 + (1.2 - .13) / 2))
    assert head.args == dict(radius=.12, location=(2, 3, 4 + 1.2 - .13))
    assert nose.args["location"] == pytest.approx((2.2, 3, 5.07))


def test_variants_keep_pose_and_dimensions():
    base = dict(key="k", kind="nguoi", xy=[0, 0], z=0, H=1.8, facing=90)
    beats = {pose: {"k": dict(deepcopy(base), tu_the=pose, body_length=1.8, body_height=.3)}
             for pose in ("nam", "nga_ngua")}
    props = tool.blender_props(beats)
    assert len(props) == 2
    assert {p["tu_the"] for p in props} == {"nam", "nga_ngua"}
    assert all(p["body_length"] == 1.8 and p["body_height"] == .3 for p in props)


def test_lying_missing_facing_refused():
    with pytest.raises(ValueError, match="facing"):
        render(dict(name="K", height=1.8, tu_the="nam", body_length=1.8, body_height=.3))
