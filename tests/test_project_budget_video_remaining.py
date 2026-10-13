from unittest import mock
from core import cost, project_budget, quality_tier
from tests.test_cost_route_e1 import Base, ON, OFF


class BudgetVideoRemainderTests(Base):
    def test_remaining_uses_delivery_quote_not_any_existing_job(self):
        shares = {'images': 0, 'videos': 0}
        jid = self.p.create_job(self.s1, 'video_gen')
        self.enterContext(mock.patch('core.final_cut.measured_size', return_value=(720, 1280)))
        for state in ('approved', 'succeeded', 'queued', 'retryable', 'failed', 'cancelled'):
            with self.subTest(state=state):
                self.p.conn.execute('UPDATE jobs SET state=? WHERE id=?', (state, jid))
                with OFF:
                    estimate = cost.estimate_run(self.p, self.pid)
                    left = project_budget.remaining(self.p, self.pid, shares)
                self.assertGreater(estimate['videos'], 0)
                self.assertEqual(left['videos'], estimate['videos'])

    def test_enum_qc_does_not_add_agent_or_team_price(self):
        shares = {'images': 0, 'videos': 0}
        est = {'videos': 2., 'images': 1., 'counts': {'images': 3, 'clips': 1}}
        with mock.patch.object(cost, 'estimate_run', return_value=est), mock.patch.object(cost, '_picture_qc_calls', return_value=3), mock.patch.object(cost, 'llm_estimate', side_effect=lambda c, stage, calls, *a, **k: calls), mock.patch('core.features.on', side_effect=lambda flag: flag == 'qc_observe_enum'), mock.patch('core.qc_scene.active', return_value=True), mock.patch('core.qc_scene.claude_on', return_value=True), mock.patch('core.qc_agent.enabled', return_value=True), mock.patch('core.qc_team.active', return_value=True), mock.patch('core.qc_agent.scene_cap', return_value=100):
            left = project_budget.remaining(self.p, self.pid, shares)
        self.assertEqual(left['claude_qc'], round(4 * project_budget.LLM_MARGIN, 2))

    def test_approved_current_draft_prices_only_final_and_off_still_needs_hd(self):
        with ON:
            jid = self.approved_draft()
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (jid,))
            estimate = cost.estimate_run(self.p, self.pid)
            need = cost.video_need(self.p.conn, self.s1)
        self.assertFalse(need['needed'])
        self.assertTrue(need['final_only'])
        self.assertEqual(estimate['counts']['drafts'], 0)
        self.assertEqual(estimate['counts']['finals_1080'], 1)
        self.assertEqual(estimate['videos'], round(quality_tier.upgrade_price('9:16', 4), 2))
        with OFF:
            self.assertTrue(cost._video_need(self.p.conn, self.s1)['needed'])

    def test_missing_video_price_uses_high_known_rate_and_warns(self):
        pricing = {'currency': 'USD', 'per_video_clip': {}, 'per_image': {'mock-image': 1}, 'per_video_second': {'known:720p': 2}}
        row = {'scene_id': self.s1, 'model': 'unknown-model', 'resolution': '720p',
               'billed_seconds': 4, 'cost': None}
        with OFF, mock.patch('core.model_router.plan', return_value=[row]), mock.patch.object(cost, 'load_pricing', return_value=pricing):
            est = cost.estimate_run(self.p, self.pid, pricing)
            left = project_budget.remaining(self.p, self.pid, {'images': 0, 'videos': 0})
        self.assertEqual(est['videos'], 12)
        self.assertEqual(left['videos'], 12)
        self.assertIn('clip unknown-model', est['unknown'])

    def test_paid_running_draft_has_only_final_remainder(self):
        with ON:
            jid = self.p.create_job(self.s1, 'video_gen')
        self.p.conn.execute("UPDATE jobs SET quality_tier='draft', state='running', external_id='paid-task', model='seedance-2.5' WHERE id=?", (jid,))
        with OFF:
            est = cost.estimate_run(self.p, self.pid)
            left = project_budget.remaining(self.p, self.pid, {'images': 0, 'videos': 0})
        self.assertEqual(est['counts']['drafts'], 0)
        self.assertEqual(est['videos'], round(quality_tier.upgrade_price('9:16', 4), 2))
        self.assertEqual(left['videos'], est['videos'])

    def test_stale_approved_draft_needs_new_gen(self):
        with ON:
            jid = self.approved_draft()
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft', input_hash='stale' WHERE id=?", (jid,))
            self.assertTrue(cost.video_need(self.p.conn, self.s1)['needed'])

    def test_enum_off_keeps_agent_and_team_quote(self):
        est = {'videos': 2., 'images': 1., 'counts': {'images': 3, 'clips': 1}}
        with mock.patch.object(cost, 'estimate_run', return_value=est), mock.patch.object(cost, '_picture_qc_calls', return_value=0), mock.patch.object(cost, 'llm_estimate', return_value=0), mock.patch('core.features.on', return_value=False), mock.patch('core.qc_scene.active', return_value=True), mock.patch('core.qc_agent.enabled', return_value=True), mock.patch('core.qc_team.active', return_value=True), mock.patch('core.qc_agent.scene_cap', return_value=1), mock.patch.object(project_budget, '_frames_per_scene', return_value=[3]):
            left = project_budget.remaining(self.p, self.pid, {'images': 0, 'videos': 0})
        from core import qc_team
        self.assertEqual(left['claude_qc'], round((1 + 3 * qc_team.FRAME_USD) * project_budget.LLM_MARGIN, 2))

    def test_unverified_known_video_price_keeps_margin_without_double_fallback(self):
        row = {'scene_id': self.s1, 'model': 'unverified-video', 'resolution': '720p',
               'billed_seconds': 4, 'cost': 8.0}
        pricing = {'currency': 'USD', 'per_video_clip': {}, 'per_image': {'mock-image': 1},
                   'per_video_second': {'unverified-video:720p': 2},
                   '_unverified_models': ['unverified-video']}
        with OFF, mock.patch('core.model_router.plan', return_value=[row]), mock.patch.object(cost, 'load_pricing', return_value=pricing):
            est = cost.estimate_run(self.p, self.pid, pricing)
            self.assertEqual(est['videos'], 10)
            self.assertEqual(project_budget.remaining(self.p, self.pid, {'images': 0, 'videos': 0})['videos'], 10)
        row['cost'] = None
        row['resolution'] = '1080p'
        with OFF, mock.patch('core.model_router.plan', return_value=[row]):
            self.assertEqual(cost.estimate_run(self.p, self.pid, pricing)['videos'], 15)

    def test_final_remainder_has_one_video_qc_call(self):
        calls = []
        def llm(conn, stage, count, *args, **kwargs):
            calls.append((stage, count))
            return 0
        with ON, mock.patch.object(cost, '_picture_qc_calls', return_value=0), mock.patch.object(cost, 'llm_estimate', side_effect=llm):
            jid = self.approved_draft()
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft' WHERE id=?", (jid,))
            cost.estimate_run(self.p, self.pid)
        self.assertIn(('qc', 1), calls)
        self.assertNotIn(('qc', 0), calls)

    def test_no_video_prices_is_explicit_incomplete_known_subtotal(self):
        row = {'scene_id': self.s1, 'model': 'unknown-model', 'resolution': '720p',
               'billed_seconds': 4, 'cost': None}
        pricing = {'currency': 'USD', 'per_video_clip': {}, 'per_image': {'mock-image': 1}, 'per_video_second': {}}
        with OFF, mock.patch('core.model_router.plan', return_value=[row]), mock.patch.object(cost, 'load_pricing', return_value=pricing):
            run = cost.estimate_run(self.p, self.pid, pricing)
            view = project_budget.estimate_view(self.p, self.pid)
            summary = project_budget.cost_summary(self.p, self.pid)
        self.assertTrue(run['incomplete'])
        self.assertIn('clip unknown-model', run['unpriced'])
        self.assertTrue(view['incomplete'])
        self.assertIn('phần đã biết', view['line'])
        self.assertIn('chưa tính được video', view['text'])
        self.assertIn('phần đã biết', summary['line'])
        self.assertIn('chưa tính được video', summary['text'])
        self.assertNotIn('mọi mục đều có giá', summary['text'])

    def test_missing_video_price_blocks_the_budget_lock(self):
        # Rà gộp 13/10: khóa trần khi thiếu giá video → trần khâu Video = đã chi → chạy tự động dừng trước clip đầu. Không khóa, nói rõ.
        row = {'scene_id': self.s1, 'model': 'unknown-model', 'resolution': '720p', 'billed_seconds': 4, 'cost': None}
        pricing = {'currency': 'USD', 'per_video_clip': {}, 'per_image': {'mock-image': 1}, 'per_video_second': {}}
        with OFF, mock.patch('core.model_router.plan', return_value=[row]), mock.patch.object(cost, 'load_pricing', return_value=pricing):
            prop = project_budget.propose(self.p, self.pid)
            self.assertIn('clip unknown-model', project_budget.lock_blocked(prop))
            with mock.patch('core.access.need_edit'), self.assertRaises(ValueError):
                project_budget.approve(self.p, self.pid, 'user', prop)
        self.assertFalse((project_budget.get(self.p.conn, self.pid) or {}).get('locked'))
        self.assertIsNone(project_budget.lock_blocked({'incomplete': False, 'total': 1.0}))

    def test_summary_component_does_not_claim_unknown_video_is_free(self):
        from dashboard.design.screens import shell_parts
        summary = {'audio': None, 'audio_items': 1, 'images': 1, 'videos': 0,
                   'claude': .2, 'unpriced': 1, 'incomplete': True, 'missing_prices': ['clip unknown-model']}
        text = shell_parts.summary_detail_md(summary)
        self.assertIn('chưa tính được video', text)
        self.assertNotIn('Video ≈', text)
        self.assertNotIn('được ước bằng giá cao nhất', text)


class GroupDraftRemainderTests(Base):
    N = 3

    def test_group_draft_member_not_yet_approved_is_not_priced_twice(self):
        # Rà gộp 13/10: nháp nhóm A(leader)+B+C, người duyệt A và B, C còn pending_review → chỉ MỘT lượt bản cao cho cả nhóm,
        # không cộng thêm nháp + bản cao cho C.
        import json
        a, b, c = self.sids
        with ON:
            leader = self.approved_draft(a)
            group = json.dumps([{"id": a}, {"id": b}, {"id": c}])
            self.p.conn.execute("UPDATE jobs SET quality_tier='draft', sent_group=? WHERE id=?", (group, leader))
            ext = self.p.conn.execute("SELECT external_id FROM jobs WHERE id=?", (leader,)).fetchone()[0]
            for sid, approve in ((b, True), (c, False)):
                jid = self.p.create_job(sid, "video_gen")
                self.p.conn.execute("UPDATE jobs SET model='seedance-2.5', external_id=?, quality_tier='draft', group_leader=? WHERE id=?",
                                    (ext, leader, jid))
                self.p.conn.commit()
                self.p.start(jid)
                self.p.succeed(jid)
                if approve:
                    self.p.approve(jid, "user")
            est = cost.estimate_run(self.p, self.pid)
        self.assertEqual(est['counts']['drafts'], 0)
        self.assertEqual(est['counts']['finals_1080'], 1)
