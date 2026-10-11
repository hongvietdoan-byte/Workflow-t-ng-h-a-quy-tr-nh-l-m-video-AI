"""Broker chỉ đọc; phiên admin do server xác minh, không nhận role từ client."""
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from core import auth, features, tickets

class SnapshotBroker:
    def __init__(self, path, *, data_dir=None, clock=time.monotonic):
        configured = Path(path)
        if not configured.is_absolute():
            raise ValueError('CSDL broker cần đường dẫn tuyệt đối đã cấu hình')
        self.path = configured.resolve()
        self.data_dir = Path(data_dir).resolve() if data_dir is not None else self.path.parent
        if data_dir is not None and not Path(data_dir).is_absolute():
            raise ValueError('Thư mục dữ liệu cần đường dẫn tuyệt đối đã cấu hình')
        self.clock = clock
        self._tokens = {}

    def _connection(self):
        c = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=3)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA query_only=ON')
        c.execute('BEGIN')
        return c

    def _owner(self, c, session):
        who = auth.identity(c, session)
        if who is None or who.role != 'owner':
            raise PermissionError('Phiên admin không còn hợp lệ')

    def _enabled(self):
        if not features.on('lao_dai_pet') or not features.on('support_tickets'):
            raise PermissionError('Pet đang tắt')

    def issue(self, session, *, ttl=300):
        self._enabled()
        if not isinstance(ttl, (int, float)) or not 0 < ttl <= 300:
            raise ValueError('TTL phải trong 1–300 giây')
        c = self._connection()
        try: self._owner(c, session)
        finally: c.close()
        token = secrets.token_urlsafe(32)
        now = self.clock()
        self._tokens = {k:v for k,v in self._tokens.items() if v[1] > now}
        self._tokens[hashlib.sha256(token.encode()).digest()] = (session, now + ttl)
        return token

    def snapshot(self, token):
        self._enabled()
        key = hashlib.sha256((token or '').encode()).digest()
        grant = self._tokens.get(key)
        if grant is None or grant[1] <= self.clock():
            self._tokens.pop(key, None)
            raise PermissionError('Token chỉ đọc thiếu hoặc hết hạn')
        c = self._connection()
        try:
            self._owner(c, grant[0])
            return tickets.admin_snapshot(c, data_dir=str(self.data_dir))
        except PermissionError:
            self._tokens.pop(key, None)
            raise
        finally: c.close()


def make_server(broker, *, host='127.0.0.1', port=0):
    if host != '127.0.0.1':
        raise ValueError('Broker chỉ bind 127.0.0.1')
    broker._enabled()
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self, *args):
            pass  # Không ghi header/token/path vào log.
        def reply(self, status, body):
            payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def do_GET(self):
            if self.path != '/snapshot':
                self.reply(404, {'error':'Đường đọc không hợp lệ'}); return
            header = self.headers.get('Authorization', '')
            if not header.startswith('Bearer '):
                self.reply(401, {'error':'Cần token chỉ đọc'}); return
            try:
                result = broker.snapshot(header[7:])
            except PermissionError:
                self.reply(401, {'error':'Phiên admin/token thiếu, hết hạn hoặc đã thu hồi'})
            except Exception:
                self.reply(503, {'error':'Không đọc được snapshot; kiểm cấu hình broker'})
            else: self.reply(200, result)
        def reject(self):
            self.close_connection = True
            self.reply(405, {'error':'Chỉ hỗ trợ GET'})
        do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_TRACE = do_CONNECT = reject
    server = ThreadingHTTPServer((host, port), Handler)
    server.timeout = 5
    server.daemon_threads = True
    return server
