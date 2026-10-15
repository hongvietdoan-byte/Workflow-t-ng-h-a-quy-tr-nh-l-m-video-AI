"""Sân khấu 3D tự động (cờ stage_auto, kế hoạch docs/KE_HOACH_NOI_SAN_KHAU_3D_TU_DONG_2026-10-15.md mục 8). Không gọi API thật, không
chạy Blender: Claude giả (client .complete), K1 / K3+K4 giả (tools/stage_grid k1_run / v2_run thay bằng hàm dựng tệp)."""
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from core import autopilot, camera_plan, features, location_pack, stage_auto, stage_director, stage_solver
from core import stage_grid as sg
from core.llm_runner import LlmReply
from tests import test_location_pack as _tlp

SETTINGS = os.path.join(os.path.dirname(__file__), "_no_feature_settings.json")
ON = {"FEATURE_STAGE_AUTO": "1", "FEATURE_STAGE_CAMERA": "1", "FEATURE_DIRECTOR_CAMERA_PLAN": "", "FEATURE_SETTINGS_FILE": SETTINGS}
OFF = {"FEATURE_STAGE_AUTO": "", "FEATURE_SETTINGS_FILE": SETTINGS}
SPOTS = {"giua_phong": {"at": [3.4, 2.1, 0.0], "facing": 0, "label": "giữa phòng"},
         "can_cua": {"at": [2.95, 3.45, 0.0], "facing": 0, "label": "cạnh cửa 2"}}
PROFILE = {"height_m": 1.7, "approved": True}


def answer(shots, at=(0.0, 0.0), moved=None):
    """Câu trả lời Đạo diễn hợp lệ (prompt 29): Kelly ở `at`, mỗi shot một yêu cầu khung MS."""
    bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": list(at), "H": 1.7, "facing": 0, "label": "Kelly"}]}
    specs = [{"shot": s, "muc_dich": "thấy Kelly", "co": "MS", "do_cao": "ngang", "thanh_phan": [{"vat": "kelly", "vai": "chinh",
              "vung": "giua", "thay": "mat"}]} for s in shots]
    if moved:
        bl["beats"] = {"cuoi": {"kelly": {"at": list(moved), "_ly_do": "kịch bản: Kelly bước tới cửa"}}}
        specs[-1]["nhip"] = "cuoi"
    return {"blocking": bl, "shot_specs": specs}


class FakeClaude:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []

    def complete(self, prompt, images=()):
        self.prompts.append(prompt)
        obj = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return LlmReply("```json\n" + json.dumps(obj, ensure_ascii=False) + "\n```", 1000, 200)


def fake_k1(entry, spot, out):
    """K1 giả: sân khấu 20×20 ô quanh chỗ đứng, sàn phẳng, một vòng tường quanh phòng 7×7 m (ô ngoài tường cùng sàn = ngoài phòng)."""
    os.makedirs(out, exist_ok=True)
    st = sg.make_stage(entry["spots"][spot]["at"])
    cells = []
    for name, x, y in sg.cells(st):
        wall = max(abs(x), abs(y)) == 3.5
        cells.append({"cell": name, "x": x, "y": y, "status": "same", "floor_z": 0.0, "obstacle": wall})
    st["marks"] = {}
    with open(os.path.join(out, "stage.json"), "w", encoding="utf-8") as f:
        json.dump(st, f)
    with open(os.path.join(out, "grid.json"), "w", encoding="utf-8") as f:
        json.dump({"cells": cells}, f)


def fake_v2(bl, specs, rd, k1, m3=None, reach=False, log=print, fail=()):
    """K3 + K4 giả: máy 2,4 m trước nhân vật; shot trong `fail` không đạt (luật P1)."""
    beats = {"": stage_solver.objects_from_blocking(bl)}
    for s in specs:
        if s.get("nhip"):
            beats[s["nhip"]] = stage_solver.objects_from_blocking(bl, None, s["nhip"])
    shots = []
    for s in specs:
        o = beats[s.get("nhip") or ""]["kelly"]
        at, aim = [o["xy"][0], o["xy"][1] - 2.4, 1.5], [o["xy"][0], o["xy"][1], 1.2]
        ok = s["shot"] not in fail
        best = {"tag": "giai", "ok": ok, "check": {"ok": ok, "why": {} if ok else {"P1": "ô K8: ngoài phòng"}},
                "m": {"at": at, "aim": aim, "lens": 32, "cell": "K9"}, "clay": f"v2_shot{s['shot']}_clay_raw.png"}
        open(os.path.join(rd, best["clay"]), "wb").close()
        shots.append({"shot": s["shot"], "spec": s, "objs": beats[s.get("nhip") or ""], "best": best})
    solve = {"beats": beats, "shots": [{"shot": s["shot"], "errors": [], "advice": [], "cams": []} for s in specs], "continuity": []}
    return solve, {"shots": shots}


class Base(unittest.TestCase):
    tearDown = _tlp.PackTests.tearDown

    def setUp(self):
        _tlp.PackTests.setUp(self)
        location_pack.set_model3d(self.p.conn, self.place, self.model, SPOTS, "giua_phong", anchor=[3.4, 9.0, 0.0])
        self.data = os.path.join(self.tmp, "projects")
        self.env2 = mock.patch.dict(os.environ, ON)
        self.env2.start()
        self.addCleanup(self.env2.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        tool = stage_auto.tool()
        for name, fn in (("k1_run", fake_k1), ("v2_run", fake_v2)):
            patch = mock.patch.object(tool, name, side_effect=fn)
            patch.start()
            self.addCleanup(patch.stop)
        for target, value in (("core.assets.standard_for", PROFILE), ("core.place_refs.shot_objects", [])):
            patch = mock.patch(target, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)

    def project(self, scenes=((1, "giua_phong"), (1, "giua_phong"), (1, "can_cua")), place=None):
        pid = self.p.create_project(f"sa-{os.urandom(3).hex()}", aspect="9:16")
        for i, (scene, spot) in enumerate(scenes, 1):
            sid = self.p.create_scene(pid, i, f"s{i}")
            d = {"size": "MS", "characters": ["KELLY"], "location_asset": place or self.place, "time": "day", "plate_spot": spot,
                 "story_scene": scene, "action": f"Kelly shot {i}", "image_prompt": f"Kelly shot {i}"}
            self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        self.p.conn.commit()
        return pid

    def shot(self, pid, idx):
        return json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=?", (pid, idx)).fetchone()["data"])


class FlagTests(unittest.TestCase):
    def test_flag_registered_off_unverified_costs(self):
        meta = features.FEATURES["stage_auto"]
        self.assertFalse(meta["verified"])
        self.assertTrue(meta["costs"])
        self.assertIn(31, meta["fixes_projects"])
        with mock.patch.dict(os.environ, OFF):
            self.assertFalse(stage_auto.enabled())
            self.assertIsNone(stage_auto.run(None, 1, "x"))

    def test_phase_order_stage_before_plates(self):
        import inspect
        src = inspect.getsource(autopilot)
        self.assertLess(src.index('("previz", _previz_phase)'), src.index('("stage", _stage_phase)'))
        self.assertLess(src.index('("stage", _stage_phase)'), src.index('("plates", _plates_phase)'))


class InputsTests(Base):
    def test_inputs_from_library_and_script(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        self.assertEqual(seg["main_spot"], "giua_phong")
        self.assertEqual(seg["spots"], {"giua_phong": [1, 2], "can_cua": [3]})
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        inputs, missing = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertEqual(missing, [])
        self.assertEqual(inputs["people"], [{"key": "kelly", "label": "KELLY", "H": 1.7}])
        self.assertEqual([s["shot"] for s in inputs["shots"]], [1, 2, 3])
        self.assertTrue(any("`can_cua` tại (-0.45 Đ, +1.35 B" in n and "shot 3" in n for n in inputs["user_notes"]))

    def test_missing_height_stops_not_default(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        with mock.patch("core.assets.standard_for", return_value={"approved": True}):
            _, missing = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertTrue(any("chiều cao nhân vật KELLY" in m for m in missing))

    def test_prop_without_size_is_missing_with_size_is_fixed(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        with mock.patch("core.place_refs.shot_objects", return_value=[{"id": 9, "name": "Xe nôi", "size": {"height_m": 1.0}}]):
            _, missing = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertTrue(any("Xe nôi" in m for m in missing))
        with mock.patch("core.place_refs.shot_objects",
                        return_value=[{"id": 9, "name": "Xe nôi", "size": {"height_m": 1.0, "width_m": 0.6}}]):
            inputs, missing = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertEqual(missing, [])
        self.assertIn({"key": "xenoi", "kind": "dao_cu", "label": "Xe nôi", "h": 1.0, "d": 0.6, "source": "Kho #9 size"}, inputs["fixed"])

    def test_k1_cached_by_model_and_spot(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        base = stage_auto.base_dir(self.data, pid, seg["stage"])
        stage_auto.ensure_k1(seg["entry"], "giua_phong", base)
        stage_auto.ensure_k1(seg["entry"], "giua_phong", base)
        self.assertEqual(stage_auto.tool().k1_run.call_count, 1)


class FamilyTests(Base):
    def test_same_spots_two_places_warn_unless_family(self):
        other = self.place + 0
        from core import assets
        place2 = assets.create(self.p.conn, "FF", "location", "Phòng mở cửa")
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (64, 36), (90, 90, 90)).save(buf, "PNG")
        assets.add_image(self.p.conn, place2, "b.png", buf.getvalue())
        location_pack.set_model3d(self.p.conn, place2, self.model, SPOTS, "giua_phong", anchor=[3.4, 9.0, 0.0])
        pid = self.project(((1, "giua_phong"),))
        sid = self.p.create_scene(pid, 2, "s2")
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(
            {"size": "MS", "characters": ["KELLY"], "location_asset": place2, "plate_spot": "can_cua", "story_scene": 2,
             "action": "x", "image_prompt": "x"}), sid))
        self.p.conn.commit()
        segs = stage_auto.segments(self.p.conn, pid)
        self.assertEqual(len({g["stage"] for g in segs}), 2)
        self.assertEqual(len(stage_auto.family_hints(segs)), 1)
        for pl in (other, place2):                       # khai cùng họ → một sân khấu, hết VÀNG
            prof = json.loads(self.p.conn.execute("SELECT profile FROM assets WHERE id=?", (pl,)).fetchone()["profile"])
            prof["model3d"]["stage_family"] = "phong_2_cua"
            self.p.conn.execute("UPDATE assets SET profile=? WHERE id=?", (json.dumps(prof), pl))
        self.p.conn.commit()
        segs = stage_auto.segments(self.p.conn, pid)
        self.assertEqual({g["stage"] for g in segs}, {"phong2cua"})
        self.assertEqual(stage_auto.family_hints(segs), [])


class RunTests(Base):
    def test_run_writes_stage_camera_and_skips_g0(self):
        pid = self.project()
        client = FakeClaude(answer([1, 2, 3]))
        r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(r["applied"], [1, 2, 3])
        self.assertEqual(r["held"], [])
        cam = self.shot(pid, 1)["stage_camera"]
        self.assertTrue(cam["auto"])
        self.assertEqual(cam["location"], [3.4, -0.3, 1.5])              # tọa độ model = O (giua_phong) + máy so với O
        self.assertTrue(cam["guide"].endswith("v2_shot1_clay_raw.png"))
        self.assertEqual(cam["guide_people"], {"orange": "KELLY"})
        self.assertEqual(self.shot(pid, 1)["stage_segment"], "1@kho%d" % self.place)
        todo, kept, _ = camera_plan.todo_groups(self.p.conn, pid, self.data)
        self.assertEqual(todo, [])                                         # Q4: G0 không lập cho cảnh đã có máy sân khấu
        self.assertTrue(kept)

    def test_rerun_same_inputs_does_not_call_claude_again(self):
        pid = self.project()
        client = FakeClaude(answer([1, 2, 3]))
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 1)

    def test_failed_shot_held_after_two_rounds_others_applied(self):
        pid = self.project()
        client = FakeClaude(answer([1, 2, 3]))
        with mock.patch.object(stage_auto.tool(), "v2_run", side_effect=lambda *a, **k: fake_v2(*a, **k, fail=(3,))):
            r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), stage_director.MAX_ROUNDS)    # ≤ 2 lượt rồi dừng
        self.assertIn("Lượt sửa", client.prompts[1])
        self.assertEqual(r["applied"], [1, 2])
        self.assertEqual(len(r["held"]), 1)
        self.assertIn("shot 3", r["held"][0][1])
        self.assertNotIn("stage_camera", self.shot(pid, 3))

    def test_bad_answer_twice_saved_not_paid_again(self):
        pid = self.project()
        client = FakeClaude({"blocking": {}, "shot_specs": []})
        r1 = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertTrue(r1["held"])
        n = len(client.prompts)
        r2 = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), n)
        self.assertEqual([h[0] for h in r1["held"]], [h[0] for h in r2["held"]])

    def test_end_state_carried_to_next_scene_on_same_stage(self):
        pid = self.project(((1, "giua_phong"), (1, "giua_phong"), (2, "giua_phong")))
        client = FakeClaude(answer([1, 2], moved=(1.0, 0.5)), answer([3], at=(1.0, 0.5)))
        stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 2)
        self.assertIn("Vị trí CUỐI ở cảnh trước trên cùng sân khấu (cảnh 1): `kelly` tại (+1.00, +0.50)", client.prompts[1])

    def test_drawn_shots_not_moved_unless_force(self):
        pid = self.project()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=1", (pid,)).fetchone()["id"]
        self.p.conn.execute("INSERT INTO jobs (project_id, scene_id, type, state, result_path, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                            (pid, sid, "image_gen", "succeeded", "x.png", "2026-10-15", "2026-10-15"))
        self.p.conn.commit()
        client = FakeClaude(answer([1, 2, 3]))
        r = stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(client.prompts, [])
        self.assertEqual(r["skipped"], ["1@kho%d" % self.place])
        r = stage_auto.run(self.p.conn, pid, self.data, client=client, force=True)
        self.assertEqual(r["applied"], [1, 2, 3])

    def test_user_locked_stage_camera_kept(self):
        pid = self.project()
        sid = self.p.conn.execute("SELECT id FROM scenes WHERE project_id=? AND idx=2", (pid,)).fetchone()["id"]
        d = self.shot(pid, 2)
        d.update(stage_camera={"location": [0, 0, 1], "look_at": [0, 1, 1], "lens": 35}, _user_locked=["stage_camera"])
        self.p.conn.execute("UPDATE scenes SET data=? WHERE id=?", (json.dumps(d), sid))
        self.p.conn.commit()
        r = stage_auto.run(self.p.conn, pid, self.data, client=FakeClaude(answer([1, 2, 3])))
        self.assertEqual(r["applied"], [1, 3])
        self.assertEqual(self.shot(pid, 2)["stage_camera"]["lens"], 35)

    def test_no_claude_is_said_and_held(self):
        pid = self.project()
        r = stage_auto.run(self.p.conn, pid, self.data, client=None)
        self.assertIn("chưa cấu hình Claude", r["held"][0][1])

    def test_stage_report_does_not_hold_a_staged_scene(self):
        pid = self.project()
        items = [{"scene_id": s["id"], "idx": s["idx"], "place": "P", "spot": location_pack.spot_for(s["entry"], s["data"])["name"]}
                 for s in location_pack.shots_at_3d_places(self.p.conn, pid)]
        self.assertEqual(len(location_pack.stage_report(self.p.conn, items)), 1)       # 2 chỗ đứng, chưa có sân khấu → giữ
        stage_auto.run(self.p.conn, pid, self.data, client=FakeClaude(answer([1, 2, 3])))
        self.assertEqual(location_pack.stage_report(self.p.conn, items), [])
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_CAMERA": ""}):              # máy sân khấu không được dùng → vẫn giữ
            self.assertEqual(len(location_pack.stage_report(self.p.conn, items)), 1)


class AutopilotPhaseTests(Base):
    def ctx(self, client):
        return mock.Mock(data_dir=self.data, llm=client)

    def test_off_nothing_runs(self):
        pid = self.project()
        with mock.patch.dict(os.environ, OFF), mock.patch.object(stage_auto, "run") as run:
            self.assertIsNone(autopilot._stage_phase(self.p, pid, self.ctx(None)))
        run.assert_not_called()

    def test_held_shot_waits_at_plates_gate_then_passes_after_continue(self):
        pid = self.project()
        ctx = self.ctx(FakeClaude(answer([1, 2, 3])))
        with mock.patch.object(stage_auto.tool(), "v2_run", side_effect=lambda *a, **k: fake_v2(*a, **k, fail=(3,))):
            with self.assertRaises(autopilot._Wait) as w:
                autopilot._stage_phase(self.p, pid, ctx)
            self.assertEqual(w.exception.gate, "plates")
            self.assertIn("shot 3", str(w.exception))
            gates = autopilot.get_gates(self.p, pid)
            autopilot.set_gates(self.p, pid, {"plate_ack": gates["plate_pending"], "plate_pending": []})
            self.assertIsNone(autopilot._stage_phase(self.p, pid, ctx))
        self.assertEqual(len(ctx.llm.prompts), stage_director.MAX_ROUNDS)    # Tiếp tục không gọi lại Claude


class SolverReachTests(unittest.TestCase):
    def test_cells_outside_the_walls_are_unreachable(self):
        st = sg.make_stage([0, 0, 0])
        cells = {}
        for name, x, y in sg.cells(st):
            cells[name] = {"cell": name, "x": x, "y": y, "status": "same", "obstacle": max(abs(x), abs(y)) == 3.5}
        got = stage_solver.reachable_cells(cells, st)
        self.assertIn(sg.cell_name(st, 2.5, 2.5), got)
        self.assertNotIn(sg.cell_name(st, 5.5, 0.5), got)
        objs = {"kelly": {"key": "kelly", "kind": "nguoi", "xy": [0, 0], "z": 0, "H": 1.7}}
        sol = stage_solver.solve_scene([], {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0, 0], "H": 1.7}]}, 9 / 16,
                                       grid_cells=list(cells.values()), stage=st, reach=True)
        self.assertEqual(sol["shots"], [])
        grid = {n: dict(c) for n, c in cells.items()}
        grid[sg.cell_name(st, 5.5, 0.5)]["unreachable"] = True
        self.assertIn("không đi tới được", stage_solver._p1_grid((5.5, 0.5, 1.5), grid, st))
        self.assertIsNone(stage_solver._p1_grid((0.5, 0.5, 1.5), grid, st))
        self.assertTrue(objs)

    def test_reach_off_keeps_old_behaviour(self):
        st = sg.make_stage([0, 0, 0])
        cells = [{"cell": n, "x": x, "y": y, "status": "same", "obstacle": max(abs(x), abs(y)) == 3.5} for n, x, y in sg.cells(st)]
        spec = {"shot": 1, "co": "MS", "do_cao": "ngang", "thanh_phan": [{"vat": "kelly", "vai": "chinh", "vung": "giua", "thay": "mat"}]}
        bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0, 0], "H": 1.7, "facing": 0}]}
        a = stage_solver.solve_scene([spec], bl, 9 / 16, grid_cells=cells, stage=st)
        b = stage_solver.solve_scene([spec], bl, 9 / 16, grid_cells=cells, stage=st, reach=False)
        self.assertEqual(json.dumps(a["shots"], default=str), json.dumps(b["shots"], default=str))


class BlenderPropsTests(unittest.TestCase):
    def test_any_prop_becomes_a_block(self):
        bl = {"objects": [{"key": "kelly", "kind": "nguoi", "at": [0, 0], "H": 1.7, "facing": 0},
                          {"key": "xenoi", "kind": "dao_cu", "at": [1, 1], "h": 1.0, "d": 0.6}]}
        beats = {"": stage_solver.objects_from_blocking(bl)}
        props = stage_auto.tool().blender_props(beats)
        block = next(p for p in props if p["kind"] == "block")
        self.assertEqual((block["name"], block["radius"], block["height"]), ("PROP_XENOI", 0.3, 1.0))
        self.assertEqual(beats[""]["xenoi"]["own"], "STAGE_PROP_XENOI_")

    def test_two_wells_is_an_error_not_exit(self):
        bl = {"objects": [{"key": "g1", "kind": "gieng", "at": [0, 3], "h": 0.9, "d": 1.5},
                          {"key": "g2", "kind": "gieng", "at": [5, 3], "h": 0.9, "d": 1.5}]}
        with self.assertRaises(ValueError):
            stage_auto.tool().blender_props({"": stage_solver.objects_from_blocking(bl)})

    def test_person_inside_a_prop_block_is_refused(self):
        objs = stage_solver.objects_from_blocking({"objects": [{"key": "kelly", "kind": "nguoi", "at": [1, 1], "H": 1.7},
                                                               {"key": "xenoi", "kind": "dao_cu", "at": [1, 1.1], "h": 1, "d": 0.6}]})
        self.assertTrue(stage_director.overlap_errors(objs))

    def test_k1_cfg_has_no_people_and_says_missing_spot(self):
        entry = {"path": "m.glb", "anchor": [0, 9, 0], "spots": SPOTS}
        cfg = stage_auto.tool().k1_cfg(entry, "giua_phong", "out")
        self.assertEqual((cfg["props"], cfg["cameras"]), ([], []))
        with self.assertRaises(ValueError):
            stage_auto.tool().k1_cfg(entry, "khong_co", "out")


class GuideReferenceTests(unittest.TestCase):
    def test_guide_sent_with_its_role_and_note(self):
        from core import assets, runner
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "g.png")
        open(path, "wb").close()
        data = {"stage_camera": {"guide": path, "guide_people": {"orange": "KELLY"}}}
        with mock.patch.dict(os.environ, ON):
            ref = runner.stage_guide_reference(mock.Mock(), {"id": 1}, data)
        self.assertEqual(ref["role"], "stage_guide")
        self.assertIn("orange = KELLY", ref["label"])
        note = assets.reference_note([ref]) if hasattr(assets, "reference_note") else None
        if note is not None:
            self.assertIn("BLOCKING GUIDE", note)
        with mock.patch.dict(os.environ, OFF):
            self.assertIsNone(runner.stage_guide_reference(mock.Mock(), {"id": 1}, data))

    def test_missing_guide_file_is_said(self):
        from core import runner
        say = mock.Mock()
        r = mock.Mock(_diag_once=say)
        with mock.patch.dict(os.environ, ON):
            self.assertIsNone(runner.stage_guide_reference(r, {"id": 1}, {"stage_camera": {"guide": "/khong/co.png"}}))
        say.assert_called_once()


class EstimateTests(Base):
    def test_estimate_counts_segments_without_calling(self):
        pid = self.project(((1, "giua_phong"), (2, "can_cua")))
        with mock.patch("core.cost.llm_estimate", return_value=0.2):
            est = stage_auto.estimate(self.p.conn, pid, self.data)
        self.assertEqual(len(est["segments"]), 2)
        from core import cost
        self.assertAlmostEqual(est["usd"], round(0.2 * cost.LLM_MARGIN * 2, 3))
        self.assertAlmostEqual(est["usd_max"], round(0.2 * cost.LLM_MARGIN * 2 * 2 * stage_director.MAX_ROUNDS, 3))


if __name__ == "__main__":
    unittest.main()


# ---- rà quy ước 7 (15/10) + lỗi shot 17 ---------------------------------------------------------------------------------------
class ReviewFixTests(Base):
    def test_needs_stage_camera_and_place_refs(self):
        self.assertEqual(features.REQUIRES["stage_auto"], ("stage_camera", "place_render_refs"))
        with mock.patch.dict(os.environ, {"FEATURE_STAGE_CAMERA": ""}):
            self.assertFalse(stage_auto.enabled())

    def test_weapons_are_not_floor_blocks(self):
        pid = self.project()
        seg = stage_auto.segments(self.p.conn, pid)[0]
        k1 = stage_auto.ensure_k1(seg["entry"], seg["main_spot"], stage_auto.base_dir(self.data, pid, seg["stage"]))
        with mock.patch("core.place_refs.shot_objects", return_value=[{"id": 5, "name": "UMP", "kind": "weapon", "size": {}}]):
            inputs, missing = stage_auto.inputs_for(self.p.conn, pid, seg, k1)
        self.assertEqual((missing, [o for o in inputs["fixed"] if o["kind"] == "dao_cu"]), ([], []))

    def test_director_may_not_invent_props(self):
        inputs = {"auto": True, "fixed": [], "shots": [{"shot": 1}]}
        obj = answer([1])
        obj["blocking"]["objects"].append({"key": "ghe", "kind": "dao_cu", "at": [2, 2], "h": 0.5, "d": 0.5})
        from core.llm_io import SchemaError
        with self.assertRaises(SchemaError):
            stage_director.validate_answer(obj, inputs)

    def test_unexpected_error_after_paid_call_is_saved(self):
        pid = self.project()
        client = FakeClaude(answer([1, 2, 3]))
        with mock.patch.object(stage_auto, "cameras_from", side_effect=KeyError("why")):
            r1 = stage_auto.run(self.p.conn, pid, self.data, client=client)
            stage_auto.run(self.p.conn, pid, self.data, client=client)
        self.assertEqual(len(client.prompts), 1)
        self.assertIn("không dựng được máy", r1["held"][0][1])

    def test_old_auto_camera_removed_when_inputs_change_and_missing(self):
        pid = self.project()
        stage_auto.run(self.p.conn, pid, self.data, client=FakeClaude(answer([1, 2, 3])))
        self.assertIn("stage_camera", self.shot(pid, 1))
        with mock.patch("core.assets.standard_for", return_value={"approved": True}):
            stage_auto.run(self.p.conn, pid, self.data, client=FakeClaude(answer([1, 2, 3])))
        self.assertNotIn("stage_camera", self.shot(pid, 1))

    def test_clone_drops_auto_stage_cameras(self):
        from core import compare
        pid = self.project()
        stage_auto.run(self.p.conn, pid, self.data, client=FakeClaude(answer([1, 2, 3])))
        new = compare.clone_project(self.p, pid, "ban sao")
        d = json.loads(self.p.conn.execute("SELECT data FROM scenes WHERE project_id=? AND idx=1", (new,)).fetchone()["data"])
        self.assertNotIn("stage_camera", d)
        self.assertNotIn("stage_segment", d)

    def test_log_said_once_per_message(self):
        pid = self.project()
        said = []
        stage_auto.run(self.p.conn, pid, self.data, client=None, log=said.append)
        n = len(said)
        stage_auto.run(self.p.conn, pid, self.data, client=None, log=said.append)
        self.assertEqual(len(said), n)


class StoryboardGuideTests(unittest.TestCase):
    def test_job_fields_sends_guide_with_note(self):
        from core import scene_storyboard, storyboard_frames
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        guide = os.path.join(tmp, "g.png")
        open(guide, "wb").close()
        g = {"anchor": {"id": 1, "data": {}}, "index": 0, "shots": [{"id": 1}]}
        with mock.patch.object(scene_storyboard, "group_of", return_value=g), \
                mock.patch.object(scene_storyboard, "turned_away", return_value=False), \
                mock.patch.object(scene_storyboard, "own_camera", return_value=True), \
                mock.patch.object(scene_storyboard, "story_text", return_value=""), \
                mock.patch.object(scene_storyboard, "storyboard_id", return_value="x"), \
                mock.patch.object(scene_storyboard, "fresh_session", return_value=False), \
                mock.patch.object(scene_storyboard, "cast_note", return_value=""):
            f = scene_storyboard.job_fields(None, tmp, 1, 1, [{"path": "a.png", "label": "KELLY", "role": "character"}], 1,
                                            guide=guide, guide_label="blocking guide (orange = KELLY)")
        self.assertEqual(f["refs"][-1]["role"], "stage_guide")
        self.assertIn("BLOCKING GUIDE", f["storyboard"]["image_mapping"])
        self.assertIn("blocking guide from this frame's camera", storyboard_frames.mapping_text(f["refs"], 1))


class NearFrameTests(unittest.TestCase):
    def test_rays_cover_the_frame(self):
        from core import plate_camera as pc
        rays = pc.frame_rays([0, 0, 1.5], [0, 5, 1.5], 32, 9 / 16)
        self.assertEqual(len(rays), 9 * 16)
        self.assertTrue(all(d[1] > 0.8 for d in rays))                 # mọi tia nhìn về trước

    def test_balloon_next_to_camera_is_caught_floor_and_far_walls_are_not(self):
        from core import plate_camera as pc
        hits = [(0.25, 0.1, "balloon")] * 60 + [(4.0, 0.0, "wall")] * 84          # #31 shot 17: nửa khung là quả bóng sát máy
        got = pc.near_frame_problem(hits, 1.42)
        self.assertEqual(got["object"], "balloon")
        self.assertGreaterEqual(got["share"], 0.4)
        self.assertIsNone(pc.near_frame_problem([(0.3, 0.95, "floor")] * 144, 1.42))   # sàn dưới máy cúi
        self.assertIsNone(pc.near_frame_problem([(0.3, 0.1, "PLATES_PROP_0")] * 144, 1.42))
        self.assertIsNone(pc.near_frame_problem([(0.25, 0.1, "x")] * 10 + [(5.0, 0, "w")] * 134, 1.42))

    def test_camera_problem_holds_near_block(self):
        rec = {"clearance": {"near_block": True, "near": {"message": "vật 'balloon' sát máy"}}}
        self.assertIn("balloon", location_pack.camera_problem(rec))
        self.assertIsNone(location_pack.camera_problem({"clearance": {"near": {"message": "x"}}}))   # máy khóa: chỉ cảnh báo
