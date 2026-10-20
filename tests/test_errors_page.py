"""Sổ lỗi chỉ đọc: dữ liệu hợp đồng, bộ lọc và cảnh báo hiển thị."""
import json

import pytest


def item(i=1, **kw):
    from devsys import errors
    row = {k: None for k in errors.FIELDS}
    row.update(id=f'P31-G{i}', alias=[], title='<script>& lỗi', source_document='fixture',
               project_ids=[31], stage='L8', severity='cao', status='OPEN', plan_workstream='WS1',
               first_seen='2026-10-20', last_seen='2026-10-20')
    row.update(kw)
    return row


def document(*rows):
    return {'schema_version': 1, 'items': list(rows)}


def test_canonical_open_counts(tmp_path):
    from devsys import plan_map
    rows = [item(i, status=s, fix_commit='abc', tests=['test'], real_run_evidence=['run'],
                 status_reason='cho phép', reopen_history=['again'])
            for i, s in enumerate(('OPEN', 'IN_PROGRESS', 'FIXED_UNVERIFIED', 'REOPENED', 'VERIFIED', 'WONT_FIX'), 1)]
    rows.append(item(7, stage=None))
    path = tmp_path / 'errors.json'
    path.write_text(json.dumps(document(*rows)), encoding='utf-8')
    assert plan_map.open_errors_by_stage(str(path)) == {'L8': 4, 'NEN': 1}
    assert plan_map.open_errors_by_stage(str(tmp_path / 'missing')) is None


def test_stage_border_red_when_open_error():
    from xml.etree import ElementTree as ET
    from devsys import plan_map
    model = plan_map.model({'waves': [], 'bad': [], 'cap': None, 'focus': None},
                           [{'id': 'L8', 'ten': 'khâu', 'thieu': False, 'tu_do': False}], {}, {'L8': 1})
    svg = ET.fromstring(plan_map.stages_svg(model, 't'))
    borders = [r.attrib['stroke'] for r in svg if r.tag.endswith('rect') and r.get('width') == '410']
    assert borders == [plan_map.STAGE_COLOR['ok'], plan_map.STAGE_COLOR['thieu']]


@pytest.mark.parametrize('doc', [{'errors': []}, {'schema_version': 2, 'items': []},
                                     document('bad'), document(item(status='VERIFIED'))])
def test_map_rejects_bad_register(tmp_path, doc):
    from devsys import plan_map
    path = tmp_path / 'errors.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(ValueError):
        plan_map.open_errors_by_stage(str(path))


class Screen:
    def __init__(self, choices=None):
        self.choices = choices or {}
        self.calls = []

    def selectbox(self, label, options, **kw):
        return self.choices.get(label, options[0])

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return record


def test_render_filters_coverage_and_no_write(tmp_path):
    from devsys import errors_page
    path = tmp_path / 'errors.json'
    path.write_text(json.dumps(document(item(), item(2, project_ids=[33], plan_workstream='WS2'),
                                        item(3, stage=None))), encoding='utf-8')
    before = path.read_bytes()
    screen = Screen({'Dự án': '31', 'Workstream': 'WS1', 'Trạng thái': 'OPEN'})
    errors_page.render(screen, str(path))
    metrics = {args[0]: args[1] for name, args, _ in screen.calls if name == 'metric'}
    assert metrics['Hiển thị / tổng'] == '2 / 3'
    assert metrics['Có khâu'] == '1 / 2'
    table = next(args[0] for name, args, _ in screen.calls if name == 'dataframe')
    assert [r['Mã'] for r in table] == ['P31-G1', 'P31-G3']
    assert table[0]['Nội dung'] == '<script>& lỗi'
    assert not any(kw.get('unsafe_allow_html') for _, _, kw in screen.calls)
    assert path.read_bytes() == before


def test_problems_visible_even_if_filtered_out(tmp_path):
    from devsys import errors_page
    path = tmp_path / 'errors.json'
    path.write_text(json.dumps(document(item(status='VERIFIED', fix_commit='a', tests=['t']))), encoding='utf-8')
    screen = Screen({'Trạng thái': 'OPEN'})
    errors_page.render(screen, str(path))
    assert any('real_run_evidence' in str(args) for name, args, _ in screen.calls if name == 'error')


@pytest.mark.parametrize('contents', ['{', '{"items": [7]}', json.dumps(document(item(alias=[7])))])
def test_ui_reports_broken_register(tmp_path, contents):
    from devsys import errors_page
    path = tmp_path / 'errors.json'
    path.write_text(contents, encoding='utf-8')
    screen = Screen()
    errors_page.render(screen, str(path))
    assert any(name == 'error' for name, _, _ in screen.calls)


def test_streamlit_page_filters_and_shows_global_problem(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from devsys import errors
    path = tmp_path / 'errors.json'
    path.write_text(json.dumps(document(item(), item(2, status='VERIFIED', project_ids=[33],
                                                    fix_commit='a', tests=['t']))), encoding='utf-8')
    monkeypatch.setattr(errors, 'PATH', str(path))
    at = AppTest.from_string('from devsys.errors_page import render\nrender()').run()
    assert not at.exception
    assert any('real_run_evidence' in e.value for e in at.error)
    at.selectbox(key='errors_project').select('31').run()
    assert not at.exception
    assert at.metric[0].value == '1 / 2'
    assert at.dataframe[0].value.iloc[0]['Nội dung'] == '<script>& lỗi'
    assert any('real_run_evidence' in e.value for e in at.error)
