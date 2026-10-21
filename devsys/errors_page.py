"""Trang Sổ lỗi: chỉ đọc file trong git, không kết nối dữ liệu sản xuất."""
from . import errors


def render(st=None, path=None):
    if st is None:
        import streamlit as st
    st.title('📕 Sổ lỗi')
    st.caption('Đọc devsys/errors.json · FIXED_UNVERIFIED chưa phải xác minh chạy thật. Bộ lọc chỉ đổi phần hiển thị.')
    try:
        doc = errors.load(path)
        issues = errors.register_problems(doc)
    except FileNotFoundError:
        st.warning('Chưa có sổ lỗi devsys/errors.json.')
        return
    except (OSError, ValueError) as exc:
        st.error(f'Không đọc được sổ lỗi: {exc}')
        return
    for problem in issues:
        st.error(problem)
    if any(problem.startswith('errors.json:') for problem in issues):
        return
    rows = doc['items']
    if not all(isinstance(row, dict) for row in rows):
        return
    status = st.selectbox('Trạng thái', ['Tất cả', *errors.STATUSES], key='errors_status')
    ws = st.selectbox('Workstream', ['Tất cả', *errors.WORKSTREAMS], key='errors_ws')
    projects = sorted({str(p) for row in rows for p in (row.get('project_ids') or [])})
    project = st.selectbox('Dự án', ['Tất cả', *projects], key='errors_project')
    selected = [row for row in rows
                if (status == 'Tất cả' or row.get('status') == status)
                and (ws == 'Tất cả' or row.get('plan_workstream') == ws)
                and (project == 'Tất cả' or project in [str(p) for p in row.get('project_ids') or []])]
    n = len(selected)
    st.metric('Hiển thị / tổng', f'{n} / {len(rows)}')
    st.metric('Có khâu', f'{sum(bool(r.get("stage")) for r in selected)} / {n}')
    st.metric('Có workstream', f'{sum(r.get("plan_workstream") in errors.WORKSTREAMS for r in selected)} / {n}')
    st.metric('Có dự án', f'{sum(bool(r.get("project_ids")) for r in selected)} / {n}')
    st.caption('Coverage tính trên các mục đang hiển thị; cảnh báo hợp đồng tính trên toàn sổ.')
    if not selected:
        st.info('Không có lỗi khớp bộ lọc.')
        return
    st.dataframe([{'Mã': r.get('id'), 'Alias': ', '.join(r.get('alias') or []),
                   'Nội dung': r.get('title'), 'Trạng thái': r.get('status'),
                   'Workstream': r.get('plan_workstream'), 'Khâu': r.get('stage'),
                   'Dự án': ', '.join(map(str, r.get('project_ids') or [])),
                   'Mức độ': r.get('severity'), 'Commit sửa': r.get('fix_commit'),
                   'Bằng chứng chạy thật': str(r.get('real_run_evidence') or ''),
                   'Nguồn': r.get('source_document')} for r in selected],
                 hide_index=True, width="stretch")
