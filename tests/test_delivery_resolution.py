import unittest
from unittest.mock import patch
from core import final_cut

class DeliveryResolutionTests(unittest.TestCase):
    def test_480_blocks_named_shot_even_manual(self):
        rows = [{'title': 'Shot 02 - Kelly', 'idx': 2, 'path': '02.mp4'}]
        with patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)):
            with self.assertRaisesRegex(ValueError, 'Kelly.*1080p.*720p'):
                final_cut.require_delivery_resolution(rows, (1080, 1920))

    def test_720_can_upscale_and_small_test_frame_is_valid(self):
        rows = [{'title': 'Shot 03', 'path': '03.mp4'}]
        with patch('core.ffmpeg_studio.probe_size', return_value=(720, 1280)):
            self.assertIsNone(final_cut.require_delivery_resolution(rows, (1080, 1920)))
        with patch('core.ffmpeg_studio.probe_size', return_value=(64, 64)):
            self.assertIsNone(final_cut.require_delivery_resolution(rows, (64, 64)))

    def test_unknown_size_cannot_be_delivered(self):
        with patch('core.ffmpeg_studio.probe_size', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Shot 09.*không đo được'):
                final_cut.require_delivery_resolution([{'title': 'Shot 09', 'path': '09.mp4'}], (1080, 1920))

class DeliveryEntryTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from core.db import connect
        from core.pipeline import Pipeline
        self.data = tempfile.mkdtemp()
        self.p = Pipeline(connect(':memory:'))
        self.pid = self.p.create_project('Ca nhóm #24 mô phỏng', aspect='9:16')
        self.paths = []
        import os
        for idx in (2, 3, 9):
            sid = self.p.create_scene(self.pid, idx, f'Kelly {idx:02d}')
            path = final_cut.clip_path(self.data, self.pid, idx)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(b'unit clip - measured by probe mock')
            jid = self.p.create_job(sid, 'video_gen')
            self.p.conn.execute("UPDATE jobs SET state='approved', quality_tier='direct', result_path=?, model='seedance-2.5' WHERE id=?", (path, jid))
            self.paths.append(path)
        self.p.conn.commit()
        self.addCleanup(self.p.conn.close)
        import shutil
        self.addCleanup(shutil.rmtree, self.data, True)

    def test_final_blocks_before_render_even_explicit_clips_and_edits(self):
        from core import delivery
        with patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)), patch('core.ffmpeg_studio.render_final') as render:
            with self.assertRaisesRegex(ValueError, 'Kelly 02.*Kelly 03.*Kelly 09'):
                delivery.render(self.p, self.pid, self.data, None, clips=self.paths, edits={'fit': [2, 3, 9]})
            render.assert_not_called()
        self.assertEqual(self.p.conn.execute('SELECT COUNT(*) FROM outputs').fetchone()[0], 0)

    def test_resolution_follows_original_clip_not_group_label(self):
        from core import delivery
        jobs = self.p.conn.execute("SELECT id FROM jobs WHERE type='video_gen' ORDER BY id").fetchall()
        self.p.conn.execute("UPDATE jobs SET sent_group='[{\"id\":2},{\"id\":3},{\"id\":9}]', quality_tier='final' WHERE id=?", (jobs[0]['id'],))
        self.p.conn.execute("UPDATE jobs SET group_leader=?, quality_tier='direct' WHERE id!=? AND type='video_gen'", (jobs[0]['id'], jobs[0]['id']))
        with patch('core.ffmpeg_studio.probe_size', return_value=(640, 1136)):
            with self.assertRaisesRegex(ValueError, 'Kelly 09'):
                delivery.render(self.p, self.pid, self.data, None)

    def test_draft_writes_label_without_overwriting_final(self):
        import json, os
        from core import delivery
        final = os.path.join(self.data, str(self.pid), 'output', 'FINAL_VIDEO.mp4')
        os.makedirs(os.path.dirname(final), exist_ok=True)
        with open(final, 'wb') as f:
            f.write(b'approved final')
        oid = delivery.record(self.p, self.pid, 'final', final)
        with patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)), patch('core.ffmpeg_studio.probe_duration', return_value=1), patch('core.ffmpeg_studio.render_final'):
            preview = final_cut.draft_preview(self.p, self.data, self.pid)
        self.assertEqual(preview['manifest']['label'], 'NHÁP — có clip 480p')
        with open(preview['path'] + '.manifest.json', encoding='utf-8') as f:
            self.assertEqual(json.load(f)['kind'], 'draft')
        self.assertEqual(self.p.conn.execute('SELECT id FROM outputs').fetchone()[0], oid)
        with open(final, 'rb') as f:
            self.assertEqual(f.read(), b'approved final')

    def test_quality_state_never_calls_known_480_final_ok_with_flag_off(self):
        from core import quality_tier
        sid = self.p.conn.execute('SELECT id FROM scenes WHERE idx=2').fetchone()[0]
        with patch('core.quality_tier.enabled', return_value=False), patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)):
            self.assertNotIn(quality_tier.state(self.p.conn, sid), ('final_ok', 'direct_ok'))

    def test_quote_off_prices_720_instead_of_480(self):
        from core import quality_tier, cost
        sid = self.p.conn.execute('SELECT id FROM scenes WHERE idx=2').fetchone()[0]
        row = {'scene_id': sid, 'model': 'seedance-2.5', 'resolution': '480p', 'billed_seconds': 4, 'cost': 0.01}
        with patch('core.quality_tier.enabled', return_value=False):
            result = quality_tier.delivery_quote(self.p.conn, self.pid, [row], cost.load_pricing())[0]
        self.assertEqual(result['resolution'], '720p')
        self.assertGreater(result['cost'], row['cost'])
        self.assertTrue(result['warnings'])

    def test_relative_path_uses_repo_root_and_remote_never_probed(self):
        import os
        with patch('core.ffmpeg_studio.probe_size', return_value=(720, 1280)) as probe:
            final_cut.measured_size('fixtures/local.mp4')
            self.assertTrue(os.path.isabs(probe.call_args.args[0]))
            probe.reset_mock()
            self.assertIsNone(final_cut.measured_size('https://invalid/clip.mp4'))
            self.assertIsNone(final_cut.measured_size('\\\\server\\clip.mp4'))
            probe.assert_not_called()

from tests.test_cost_route_e1 import Base as QuoteBase

class DeliveryQuoteCurrentTests(QuoteBase):
    def test_matching_paid_480_still_needs_final_and_is_in_estimate(self):
        from tests.test_video_quote_current import CurrentQuoteTests
        from core import cost, quality_tier
        jid, _ = CurrentQuoteTests.proven_clip(self, self.s1)
        self.p.conn.execute("UPDATE jobs SET result_path='fixture-480.mp4', quality_tier='draft' WHERE id=?", (jid,))
        self.p.conn.commit()
        with patch('core.quality_tier.enabled', return_value=False), patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)):
            needed = cost.video_need(self.p.conn, self.s1)
            estimate = cost.estimate_run(self.p, self.pid)
        self.assertTrue(needed['needed'])
        self.assertIn('nâng 1080p', needed['reason'])
        self.assertEqual(estimate['counts']['clips'], 1)
        self.assertGreater(estimate['videos'], 0)

class ActualClipResolutionTests(unittest.TestCase):
    def test_actual_480_blocks_full_hd_but_can_render_small(self):
        import tempfile, os, subprocess, shutil
        from core import ffmpeg_studio, delivery
        from core.db import connect
        from core.pipeline import Pipeline
        try:
            ff = ffmpeg_studio.find_ffmpeg()
        except ffmpeg_studio.FFmpegNotFound:
            self.skipTest('Thiếu ffmpeg')
        data = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, data, True)
        p = Pipeline(connect(':memory:'))
        self.addCleanup(p.conn.close)
        pid = p.create_project('480p thật', aspect='9:16')
        p.create_scene(pid, 2, 'Kelly 02')
        path = final_cut.clip_path(data, pid, 2)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run([ff, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=s=480x854:d=0.5', '-pix_fmt', 'yuv420p', path], check=True)
        with self.assertRaisesRegex(ValueError, 'Kelly 02.*1080p.*720p'):
            delivery.render(p, pid, data, None)
        res = delivery.render(p, pid, data, None, render_size=(240, 426))
        self.assertEqual(ffmpeg_studio.probe_size(res['path']), (240, 426))

class DeliveryFlowGuardTests(unittest.TestCase):
    setUp = DeliveryEntryTests.setUp
    def test_export_hd_checks_source_under_layer(self):
        import json, os
        from core import delivery
        out = os.path.join(self.data, 'small-final.mp4')
        with open(out, 'wb') as f:
            f.write(b'unit render')
        oid = delivery.record(self.p, self.pid, 'final', out, manifest={'clips': [{'path': self.paths[0], 'title': 'Kelly 02'}], 'render_size': [240, 426]})
        layer = delivery.record(self.p, self.pid, 'subtitle', out, oid)
        with patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)), patch('core.ffmpeg_studio.resize_to_size') as resize:
            with self.assertRaisesRegex(ValueError, 'Kelly 02.*1080p'):
                delivery.export_layer(self.p, self.pid, self.data, {'w': 1080, 'h': 1920}, parent_id=layer)
            resize.assert_not_called()

    def test_legacy_export_hd_requires_source_provenance(self):
        import os
        from core import delivery
        out = os.path.join(self.data, 'legacy.mp4')
        with open(out, 'wb') as f:
            f.write(b'legacy already upscaled')
        oid = delivery.record(self.p, self.pid, 'final', out)
        with patch('core.ffmpeg_studio.probe_size', return_value=(1080, 1920)), patch('core.ffmpeg_studio.resize_to_size') as resize:
            with self.assertRaisesRegex(ValueError, 'thiếu thông tin clip gốc'):
                delivery.export_layer(self.p, self.pid, self.data, {'w': 1080, 'h': 1920}, parent_id=oid)
            resize.assert_not_called()

    def test_legacy_first_hd_does_not_allow_next_480(self):
        rows = [{'title': 'HD first', 'path': self.paths[0]}, {'title': 'Kelly 03', 'path': self.paths[1]}]
        def probe(path):
            return (1080, 1920) if path == self.paths[0] else (480, 854)
        with patch('core.ffmpeg_studio.probe_size', side_effect=probe):
            with self.assertRaisesRegex(ValueError, 'Kelly 03'):
                final_cut.require_delivery_resolution(rows, None)

    def test_editor_apply_blocks_before_stash_qc_and_render(self):
        from core import editor_apply
        from unittest.mock import Mock
        qc, render = Mock(), Mock()
        with patch('core.editor_review.load', return_value={'proposals': [{}], 'rough_cut': 'same', 'fingerprint': 'rv'}), patch('core.rough_cut.build', return_value={'fingerprint': 'same'}), patch('core.editor_apply.plan', return_value={'clips': self.paths}), patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)), patch('core.editor_apply._stash') as stash:
            with self.assertRaisesRegex(ValueError, 'Kelly 02'):
                editor_apply.apply(self.p, self.pid, self.data, ['F1'], render_fn=render, qc_fn=qc)
            stash.assert_not_called()
            render.assert_not_called()
            qc.assert_not_called()

    def test_autopilot_blocks_before_music_sfx_and_custom_render(self):
        from core import autopilot
        from contextlib import ExitStack
        from unittest.mock import Mock
        autopilot._set(self.p, self.pid, autopilot.RUNNING)
        ctx = autopilot.Context(self.data, None, None, None, render=Mock())
        names = ['_director_phase', '_story_check_phase', '_voice_first_phase', '_previz_phase', '_plates_phase', '_images_phase', '_setcheck_phase', '_end_frame_phase', '_storyboard_phase', '_motion_phase', '_voice_phase', '_videos_phase']
        with ExitStack() as stack:
            for name in names:
                stack.enter_context(patch.object(autopilot, name, return_value=None))
            music = stack.enter_context(patch.object(autopilot, '_music_phase', return_value=None))
            sfx = stack.enter_context(patch.object(autopilot, '_sfx_phase', return_value=None))
            stack.enter_context(patch('core.ffmpeg_studio.probe_size', return_value=(480, 854)))
            result = autopilot.tick(self.p, self.pid, ctx)
        self.assertEqual(result, autopilot.ERROR)
        self.assertIn('nâng 1080p', autopilot.status(self.p, self.pid)['note'])
        music.assert_not_called()
        sfx.assert_not_called()
        ctx.render.assert_not_called()

    def test_draft_cannot_overwrite_registered_final(self):
        import os
        from core import delivery
        out = os.path.join(self.data, 'custom-final.mp4')
        oid = delivery.record(self.p, self.pid, 'final', out)
        with patch('core.ffmpeg_studio.probe_duration', return_value=1), patch('core.ffmpeg_studio.render_final') as render:
            with self.assertRaisesRegex(ValueError, 'không ghi đè bản giao'):
                final_cut.draft_preview(self.p, self.data, self.pid, out)
            render.assert_not_called()

class DeliveryRemainingQuoteTests(QuoteBase):
    N = 2

    def test_paid_running_draft_quotes_only_upgrade_on_and_off(self):
        from core import cost, quality_tier
        j = self.p.create_job(self.s1, 'video_gen')
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.p.conn.execute("UPDATE jobs SET state='running',external_id='paid',model='seedance-2.5',quality_tier='draft' WHERE id=?", (j,))
                self.p.conn.commit()
                with patch('core.quality_tier.enabled', return_value=enabled), patch('core.model_router.plan', return_value=[{'scene_id': self.s1, 'model': 'seedance-2.5', 'resolution': '480p', 'billed_seconds': 4, 'seconds': 4, 'cost': 0.13}]):
                    e = cost.estimate_run(self.p, self.pid)
                self.assertAlmostEqual(e['videos'], round(quality_tier.upgrade_price('9:16', 4), 2))
                self.assertEqual(e['counts']['drafts'], 0)

    def test_paid_running_draft_group_quotes_upgrade_once(self):
        import json
        from core import cost, quality_tier
        j = self.p.create_job(self.s1, 'video_gen')
        self.p.conn.execute("UPDATE jobs SET state='running',external_id='paid-group',model='seedance-2.5',quality_tier='draft',sent_group=? WHERE id=?", (json.dumps([{'id': self.s1}, {'id': self.sids[1]}]), j))
        follower = self.p.create_job(self.sids[1], 'video_gen')
        self.p.conn.execute("UPDATE jobs SET state='running',external_id='paid-group',model='seedance-2.5',quality_tier='draft',group_leader=? WHERE id=?", (j, follower))
        self.p.conn.commit()
        rows = [{'scene_id': sid, 'model': 'seedance-2.5', 'resolution': '480p', 'billed_seconds': 4, 'seconds': 4, 'cost': 0.13} for sid in self.sids]
        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch('core.quality_tier.enabled', return_value=enabled), patch('core.model_router.plan', return_value=rows):
                e = cost.estimate_run(self.p, self.pid)
                self.assertAlmostEqual(e['videos'], round(quality_tier.upgrade_price('9:16', 8), 2))
                self.assertEqual(e['counts']['drafts'], 0)
        self.p.conn.execute("UPDATE jobs SET quality_tier='final' WHERE id IN (?,?)", (j, follower))
        with patch('core.quality_tier.enabled', return_value=True), patch('core.model_router.plan', return_value=rows):
            self.assertEqual(cost.estimate_run(self.p, self.pid)['videos'], 0)

class DeliveryUnknownFinalTests(QuoteBase):
    def test_unknown_final_requires_restore_without_new_paid_job(self):
        from core import quality_tier, cost
        j = self.p.create_job(self.s1, 'video_gen')
        for path in (None, 'missing.mp4', 'https://invalid/clip.mp4'):
            for tier in ('final', 'direct'):
                with self.subTest(path=path, tier=tier):
                    self.p.conn.execute("UPDATE jobs SET state='approved',quality_tier=?,result_path=?,external_id='paid-final' WHERE id=?", (tier, path, j))
                    self.p.conn.commit()
                    with patch('core.quality_tier.enabled', return_value=True), patch('core.ffmpeg_studio.probe_size', return_value=None):
                        self.assertNotIn(quality_tier.state(self.p.conn, self.s1), ('final_ok', 'direct_ok'))
                        self.assertIn('kiểm tra/tải lại', quality_tier.final_offer(self.p.conn, self.s1)['why'])
                        self.assertIsNone(quality_tier.final_offer(self.p.conn, self.s1)['usd'])
                        self.assertIn(self.s1, quality_tier.final_estimate(self.p.conn, self.pid)['unknown'])
                        self.assertTrue(cost.estimate_run(self.p, self.pid)['unknown'])
                        with self.assertRaisesRegex(ValueError, 'kiểm tra/tải lại'):
                            quality_tier.request_final(self.p, self.s1, confirm_new=True)
                    self.assertEqual(self.p.conn.execute("SELECT COUNT(*) FROM jobs WHERE type='video_gen'").fetchone()[0], 1)


    def test_known_720_still_final_ok(self):
        from core import quality_tier
        j = self.p.create_job(self.s1, 'video_gen')
        self.p.conn.execute("UPDATE jobs SET state='approved',quality_tier='final',result_path='fixture720.mp4' WHERE id=?", (j,))
        with patch('core.ffmpeg_studio.probe_size', return_value=(720, 1280)):
            self.assertEqual(quality_tier.state(self.p.conn, self.s1), 'final_ok')
