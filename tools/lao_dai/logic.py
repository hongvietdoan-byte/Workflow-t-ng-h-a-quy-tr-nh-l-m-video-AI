"""Logic pet thuần: không SQLite, không duyệt, chỉ mở URL cho phép."""
from dataclasses import dataclass, field
import re
from urllib.parse import urlsplit, parse_qs

_ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

def allowed_url(url):
    try:
        u = urlsplit(url)
        if u.scheme != 'http' or u.hostname not in ('127.0.0.1','localhost') or u.port not in (8501,8502) or u.username or u.password or u.path not in ('','/') or u.fragment:
            return False
        q = parse_qs(u.query, strict_parsing=True, keep_blank_values=True)
        allowed = {'ticket'} if u.port == 8502 else {'pid', 'step'}
        return all(k in allowed and len(v)==1 and _ID.fullmatch(v[0]) for k,v in q.items())
    except (ValueError, TypeError): return False

@dataclass
class PetView:
    state: str
    bubble: str
    reason: str = ''
    toasts: list = field(default_factory=list)

class PetLogic:
    def __init__(self):
        self._seen = set()
        self.failures = 0

    @property
    def poll_seconds(self):
        return 15 if not self.failures else (30 if self.failures == 1 else 60)

    def failure(self, reason='Không kết nối được broker'):
        self.failures += 1
        return PetView('disconnected', 'Mất kết nối', reason)

    def update(self, snapshot):
        try:
            if not isinstance(snapshot,dict) or snapshot.get('schema_version') != 1:
                raise ValueError()
            if snapshot.get('enabled') is not True:
                return PetView('disabled','Pet đang tắt')
            if snapshot.get('available') is not True:
                raise ValueError()
            counts = snapshot['ticket_counts']
            rows = snapshot['ticket_summaries']
            if not isinstance(counts,dict) or not isinstance(rows,list) or any(not isinstance(k,str) or type(v) is not int or v<0 for k,v in counts.items()):
                raise ValueError()
            toasts = []
            for r in rows:
                if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not _ID.fullmatch(r['id']) or not isinstance(r.get('state'),str) or not _ID.fullmatch(r['state']) or r.get('due_status') not in ('green','yellow','red','closed'):
                    raise ValueError()
                key = (r['id'],r['state'],r['due_status'])
                if r['state'] != 'closed' and key not in self._seen:
                    toasts.append(' · '.join(key))
            # Chỉ ghi dedupe sau khi toàn snapshot hợp lệ.
            self._seen.update((r['id'],r['state'],r['due_status']) for r in rows)
            self.failures = 0
            n = sum(v for k,v in counts.items() if k != 'closed')
            return PetView('tickets' if n else 'idle', f'📨 {n} phiếu chờ duyệt' if n else '', toasts=toasts)
        except (ValueError, KeyError, TypeError):
            return self.failure('Snapshot broker thiếu hoặc sai định dạng')


