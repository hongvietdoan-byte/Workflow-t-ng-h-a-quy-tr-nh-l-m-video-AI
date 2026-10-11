"""Đăng nhập admin phía server cho 8502 (devsys/admin_auth) + trang Phiếu ghi thật khi Owner đăng nhập.

Danh tính đọc lại từ CSDL mỗi lần chạy trang; người không phải Owner chỉ xem; link Owner `?s=` từ máy khác bị từ chối."""
import pytest
from streamlit.testing.v1 import AppTest

from core import auth, db, tickets

APP = 'from devsys.tickets_page import render\nrender()'


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr('core.features.on', lambda n: True)
    path = tmp_path / 'manifest.sqlite'
    conn = db.connect(str(path))
    monkeypatch.setenv('PIPELINE_DB', str(path))
    monkeypatch.delenv('DASHBOARD_LAN', raising=False)
    yield conn
    conn.close()


def make(conn, root='lỗi a', **kw):
    return tickets.open_or_merge(conn, title=root, kind='code', source_actor='tieu_nhi', root_cause=root, **kw)


def run(token=None):
    at = AppTest.from_string(APP)
    if token:
        at.query_params['s'] = token
    return at.run()


def test_no_login_is_read_only_with_login_form(store):
    make(store)
    at = run()
    assert not at.exception
    assert 'CHỈ ĐỌC' in at.warning[0].value
    assert all(b.disabled for b in at.button if b.label in ('Duyệt', 'Từ chối', 'Cần thêm thông tin', 'Gia hạn'))
    assert any(b.label == 'Đăng nhập để duyệt' for b in at.button)


def test_owner_link_enables_decisions_and_writes_with_server_identity(store):
    t = make(store)
    token = auth.login(store, auth.OWNER_EMAIL, 'test', local=True)
    at = run(token)
    assert not at.exception
    assert 'Đã đăng nhập Owner' in at.success[0].value
    ask = next(b for b in at.button if b.key == f'ticket_{t["id"]}_{t["revision"]}_Cần thêm thông tin')
    assert not ask.disabled
    ask.click().run()
    assert not at.exception
    store.commit()
    after = tickets.get(store, t['id'])
    assert after['state'] == 'waiting_info' and after['revision'] == t['revision'] + 1
    last = store.execute('SELECT actor FROM ticket_events WHERE ticket_id=? ORDER BY rowid DESC LIMIT 1', (t['id'],)).fetchone()[0]
    assert last == auth.OWNER_EMAIL          # người ghi = danh tính trong CSDL, không phải chữ từ trình duyệt


def test_member_session_stays_read_only(store):
    make(store)
    token = auth.login(store, 'ban@garena.vn', 'test', local=True)          # tự thành member theo miền công ty
    at = run(token)
    assert not at.exception
    assert 'không phải Owner' in at.warning[0].value
    assert all(b.disabled for b in at.button if b.label in ('Duyệt', 'Từ chối', 'Cần thêm thông tin', 'Gia hạn'))


def test_expired_or_fake_token_is_ignored(store):
    make(store)
    at = run('khong-phai-token-that')
    assert not at.exception and 'CHỈ ĐỌC' in at.warning[0].value


def test_owner_link_from_another_machine_is_refused(store, monkeypatch):
    from devsys import admin_auth
    token = auth.login(store, auth.OWNER_EMAIL, 'test', local=True)
    monkeypatch.setattr(admin_auth, 'request_source', lambda: ('ip=10.0.0.9', False))
    at = run(token)
    assert not at.exception and 'CHỈ ĐỌC' in at.warning[0].value


def test_sign_out_removes_session(store):
    from devsys import admin_auth
    token = auth.login(store, auth.OWNER_EMAIL, 'test', local=True)
    at = run(token)
    next(b for b in at.button if b.key == 'ticket_logout').click().run()
    assert not at.exception
    store.commit()
    assert auth.identity(store, token) is None
    assert admin_auth.TOKEN_KEY not in at.session_state


def _owner(store):
    return auth.login(store, auth.OWNER_EMAIL, 'test', local=True)


def test_double_click_or_stale_view_does_not_skip_a_step(store):
    t = make(store)
    at = run(_owner(store))
    key = f'ticket_{t["id"]}_{t["revision"]}_Duyệt'
    stale = next(b for b in at.button if b.key == key)
    # trong lúc Owner đang xem, phiếu đổi bước ở nơi khác
    owner = auth.identity(store, _owner(store))
    tickets.transition(store, t['id'], 'triaged', owner, 'nơi khác', 'new', expected_revision=t['revision'])
    store.commit()
    stale.click().run()
    assert not at.exception
    assert tickets.get(store, t['id'])['state'] == 'triaged'           # cú bấm trên bản cũ không đẩy thêm bước nào


def test_extend_long_overdue_ticket_counts_from_now(store):
    from datetime import timedelta
    t = make(store, now=tickets._time() - timedelta(days=10))
    at = run(_owner(store))
    next(b for b in at.button if b.key == f'ticket_{t["id"]}_{t["revision"]}_Gia hạn').click().run()
    assert not at.exception
    store.commit()
    after = tickets.get(store, t['id'])
    assert tickets._time(after['due_at']) > tickets._time() + timedelta(hours=23)
    assert after['original_due_at'] == t['original_due_at']


def test_decision_error_is_shown_in_the_same_click(store, monkeypatch):
    from devsys import tickets_page as ui
    t = make(store)
    at = run(_owner(store))
    monkeypatch.setattr(ui, 'decide', lambda *a, **k: (_ for _ in ()).throw(tickets.TicketError('Phiếu đã thay đổi')))
    next(b for b in at.button if b.key == f'ticket_{t["id"]}_{t["revision"]}_Duyệt').click().run()
    assert not at.exception
    assert any('Phiếu đã thay đổi' in e.value for e in at.error)


def test_sign_in_is_owner_only_and_needs_passcode_from_another_machine(store, monkeypatch):
    from devsys import admin_auth
    assert 'chỉ cho Owner' in admin_auth.sign_in('ban@garena.vn')
    assert store.execute("SELECT count(*) FROM users WHERE email='ban@garena.vn'").fetchone()[0] == 0   # không tự tạo thành viên
    monkeypatch.setattr(admin_auth, 'request_source', lambda: ('ip=10.0.0.9', False))
    monkeypatch.delenv('DASHBOARD_OWNER_PASSCODE', raising=False)
    assert 'cần mã Owner' in admin_auth.sign_in(auth.OWNER_EMAIL)


def test_decide_refuses_anyone_but_a_server_owner_identity(store):
    from devsys import tickets_page as ui
    t = make(store)
    member = auth.identity(store, auth.login(store, 'ban@garena.vn', 'test', local=True))
    for who in (None, member, auth.OWNER_EMAIL, {'role': 'owner', 'email': auth.OWNER_EMAIL}):
        with pytest.raises(tickets.TicketError):
            ui.decide(store, t['id'], 'Duyệt', who, 'thử', t['revision'])
    assert tickets.get(store, t['id'])['state'] == 'new'


def test_link_token_never_stays_in_the_address(store, monkeypatch):
    from devsys import admin_auth
    monkeypatch.setenv('PIPELINE_DB', str(store.execute('PRAGMA database_list').fetchone()[2]) + '.missing')
    at = run(_owner(store))
    assert not at.exception
    assert 's' not in at.query_params
