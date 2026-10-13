"""Cấp quyền explicit từ Owner LOCAL đã đăng nhập 8502; không gửi bí mật về UI."""
import threading
from core import features
from tools.lao_dai.broker import SnapshotBroker
from tools.lao_dai.channel import ChannelService, CredentialStore

_lock=threading.RLock()
_service=None

def sync_service():
    global _service
    with _lock:
        if not features.on('lao_dai_pet') or not features.on('support_tickets'):
            if _service:_service.stop();_service=None
            return None
        return _service

def render(st,admin_auth):
    """Gọi mọi rerun, OFF không tạo credential/broker hoặc đổi trải nghiệm cũ."""
    global _service
    sync_service()
    if not features.on('lao_dai_pet') or not features.on('support_tickets'):return
    who=admin_auth.current()
    if not admin_auth.is_owner(who) or not admin_auth.request_source()[1]:
        st.sidebar.caption('Pet: chỉ Owner đăng nhập trên máy chạy 8502 được cấp quyền.')
        return
    with st.expander('Lão Đại · quyền đọc trên máy này'):
        st.caption('Bấm cấp token chỉ đọc trong kho Windows, hạn 5 phút. Hết hạn cần bấm cấp lại; pet không duyệt phiếu.')
        if st.button('Cấp quyền đọc 5 phút',key='lao_dai_authorize'):
            # Kiểm lại ngay sau click, không tin danh tính cũ trên lần vẽ UI.
            ident=admin_auth.current()
            if not admin_auth.is_owner(ident) or not admin_auth.request_source()[1]:
                st.error('Phiên Owner local không còn hợp lệ.');return
            try:
                with _lock:
                    if _service is None:
                        path=admin_auth.db_path()
                        _service=ChannelService(SnapshotBroker(path,data_dir=path.parent),CredentialStore())
                    _service.authorize(st.session_state.get(admin_auth.TOKEN_KEY),local=True,owner=True)
            except Exception:st.error('Không cấp được quyền đọc: kiểm cờ, phiên Owner và kho credential Windows.')
            else:st.success('Đã cấp quyền đọc 5 phút. Chạy tools/launch_lao_dai.ps1 trên máy này.')
        if st.button('Thu hồi quyền pet',key='lao_dai_revoke'):
            with _lock:
                if _service:_service.stop();_service=None
            st.success('Đã thu hồi quyền pet.')
