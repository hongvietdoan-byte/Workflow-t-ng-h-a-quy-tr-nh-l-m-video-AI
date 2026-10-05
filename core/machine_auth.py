"""Đăng nhập LAN theo "máy được duyệt" (S14.7, Gói D1 — người dùng chốt 04/10, kế hoạch nâng cấp dashboard mục 6b ý 2).

Vì sao: đăng nhập chỉ bằng e-mail là LỜI KHAI (core/auth.py). Khi mở Dashboard cho mạng LAN (DASHBOARD_LAN=1) ai trong LAN gõ e-mail
đồng nghiệp đều thành người đó. Lớp này gắn mỗi e-mail với MÁY PC đã được Owner duyệt:

- Nhận máy: IP người xem (`st.context.ip_address`) → tên máy qua DNS ngược, rồi XÁC NHẬN CHIỀU THUẬN (tên → `getaddrinfo` phải chứa lại
  đúng IP đó). Thử thật trên mạng công ty 05/10: DNS ngược trả `GKP8Q03.vn.corp.seagroup.com`, nhưng 2 IP khác nhau (.31, .36) cùng trả
  một tên → bản ghi DNS có thể cũ, nên chiều thuận là bắt buộc. NetBIOS (`nbtstat -A`) bị chặn → chỉ dùng DNS. Tên lưu = phần trước dấu
  chấm, viết hoa. Hạn giờ ≤ 2 s (luồng riêng), nhớ theo IP vài phút. localhost (127.0.0.1 / ::1) = máy chủ, tên = `socket.gethostname()`.
- Lần đầu một e-mail vào từ máy chưa duyệt → ghi yêu cầu CHỜ (bảng machine_approvals) và báo rõ "chờ Owner duyệt máy <TÊN>"; Owner duyệt /
  từ chối / thu hồi ở 👥 Nhóm. Sau khi duyệt, e-mail chỉ vào được từ máy đã duyệt (một e-mail có thể có nhiều máy). Phiên đang mở cũng
  được kiểm lại mỗi lần tải trang (`session_refusal`): mang đường dẫn ?s=… sang máy khác không dùng được.
- Không xác định được tên máy → từ chối kèm lý do + cách xử lý (Owner vẫn vào được bằng mã DASHBOARD_OWNER_PASSCODE như trước).
- Owner: trên chính máy chạy Dashboard như cũ; từ máy khác cần mã Owner (auth.owner_remote_check) — không cần duyệt máy.
- Giới hạn số lần thử sai theo IP (MAX_FAILS trong FAIL_WINDOW giây) + mọi lần thành công / từ chối / yêu cầu duyệt ghi audit kèm tên máy.
- Chỉ áp khi DASHBOARD_LAN=1; chế độ chỉ localhost giữ hành vi cũ. Không làm NTLM/Kerberos (không lấy được tài khoản Windows).

GIỚI HẠN CẦN BIẾT: reverse proxy / tunnel (ngrok, cloudflared, IIS/nginx…) chạy TRÊN CÙNG MÁY làm mọi người xem trông như đến từ
127.0.0.1 → ai cũng thành "máy chủ" (Owner vào không cần mã, thành viên dùng chung tên máy chủ). Đừng đặt Dashboard sau proxy/tunnel khi
dựa vào lớp này. Tên máy cũng chỉ đáng tin bằng DNS nội bộ: ai sửa được DNS / mạo IP của máy đã duyệt thì qua được.
"""
import concurrent.futures
import ipaddress
import os
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

from . import auth

TIMEOUT = 2.0                 # seconds for one name lookup (reverse + forward), in a worker thread
CACHE_SECONDS = 300           # a found name is kept this long per IP
CACHE_MISS_SECONDS = 30       # "no name" is kept shorter: the person may fix the network and try again
MAX_FAILS = 5                 # refused sign-ins from one IP …
FAIL_WINDOW = 600             # … within this many seconds → wait
LOCAL_IPS = ("127.0.0.1", "::1")

_cache: Dict[str, Tuple[float, Optional[str], str]] = {}
_cache_lock = threading.Lock()
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="machine-dns")


class MachinePending(auth.AuthError):
    """The machine is waiting for the Owner's approval (not a wrong attempt: not counted towards the try limit)."""


def lan_on() -> bool:
    return os.environ.get("DASHBOARD_LAN", "").strip().lower() in ("1", "true", "on")


def _stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---- tên máy ------------------------------------------------------------------------------------------------------------------------
def normalize_ip(ip: Optional[str]) -> str:
    ip = (ip or "").strip().strip("[]")
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if a.version == 6 and a.ipv4_mapped is not None:
        return str(a.ipv4_mapped)
    return str(a)


def is_local_ip(ip: Optional[str]) -> bool:
    ip = normalize_ip(ip)
    return ip in LOCAL_IPS or ip.startswith("127.")


def short_name(host: str) -> str:
    return (host or "").strip().split(".")[0].upper()


def _dns_name(ip: str) -> Optional[str]:
    """Reverse DNS, then forward: the name must resolve back to this very IP (a stale record maps other IPs to the name). Raises
    LookupError with the reason when there is no trustworthy name. Replaced in tests (no real DNS there)."""
    try:
        host, _aliases, _addrs = socket.gethostbyaddr(ip)
    except (socket.herror, socket.gaierror, OSError) as e:
        raise LookupError(f"DNS nội bộ không có tên cho IP {ip} ({e.__class__.__name__})") from e
    try:
        forward = {normalize_ip(info[4][0]) for info in socket.getaddrinfo(host, None)}
    except (socket.gaierror, OSError) as e:
        raise LookupError(f"tên {host} không tra ngược lại được ({e.__class__.__name__})") from e
    if ip not in forward:
        raise LookupError(f"tên {host} trỏ tới {', '.join(sorted(forward)) or 'không IP nào'}, không khớp IP {ip} (bản ghi DNS cũ?)")
    return host


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def machine_of(ip: Optional[str], local: Optional[bool] = None) -> Tuple[Optional[str], str]:
    """(PC NAME, "") or (None, why). `local` = the request is from the dashboard machine itself (common.request_source)."""
    ip = normalize_ip(ip)
    if local or is_local_ip(ip):
        return short_name(socket.gethostname()) or None, ""
    if not ip:
        return None, "không có địa chỉ IP của trình duyệt"
    now = time.time()
    with _cache_lock:
        hit = _cache.get(ip)
    if hit and hit[0] > now:
        return hit[1], hit[2]
    fut = _pool.submit(_dns_name, ip)
    try:
        host = fut.result(timeout=TIMEOUT)
        name, why = (short_name(host) or None), ("" if host else f"DNS nội bộ không có tên cho IP {ip}")
    except concurrent.futures.TimeoutError:
        name, why = None, f"tra tên máy quá {TIMEOUT:g} s"
    except LookupError as e:
        name, why = None, str(e)
    except Exception as e:  # noqa: BLE001 - any resolver failure = no trustworthy name (said, never silent)
        name, why = None, f"lỗi tra tên máy: {type(e).__name__}"
    if name is None and not why:
        why = f"DNS nội bộ không có tên cho IP {ip}"
    with _cache_lock:
        _cache[ip] = (now + (CACHE_SECONDS if name else CACHE_MISS_SECONDS), name, why)
    return name, why


# ---- bảng máy được duyệt ------------------------------------------------------------------------------------------------------------
def status(conn, email: str, machine: str) -> Optional[str]:
    r = conn.execute("SELECT status FROM machine_approvals WHERE email=? AND machine=?",
                     ((email or "").strip().lower(), machine)).fetchone()
    return r["status"] if r else None


def request(conn, email: str, machine: str, ip: str) -> None:
    """Ask the Owner to approve `machine` for `email` (idempotent: a second ask only refreshes the address / time seen)."""
    conn.execute("INSERT INTO machine_approvals (email, machine, status, requested_at, last_ip, last_seen) VALUES (?,?,?,?,?,?)"
                 " ON CONFLICT(email, machine) DO UPDATE SET last_ip=excluded.last_ip, last_seen=excluded.last_seen",
                 (email, machine, "pending", _stamp(), ip, _stamp()))
    conn.commit()


def touch(conn, email: str, machine: str, ip: str) -> None:
    conn.execute("UPDATE machine_approvals SET last_ip=?, last_seen=? WHERE email=? AND machine=?", (ip, _stamp(), email, machine))
    conn.commit()


def requests(conn) -> List[Dict]:
    """Every row, waiting ones first (the 👥 Nhóm block)."""
    return [dict(r) for r in conn.execute(
        "SELECT * FROM machine_approvals ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,"
        " requested_at DESC, email, machine")]


def _actor_email(actor) -> str:
    if isinstance(actor, str):
        return actor.strip().lower()
    get = actor.get if isinstance(actor, dict) else (lambda k, d=None: getattr(actor, k, d))
    return (get("email") or "").strip().lower()


def _decide(conn, actor, email: str, machine: str, new: str, action: str) -> None:
    who = _actor_email(actor)
    if who != auth.OWNER_EMAIL:
        raise auth.AuthError("Chỉ Owner được duyệt / từ chối / thu hồi máy đăng nhập.")
    email = (email or "").strip().lower()
    if conn.execute("SELECT 1 FROM machine_approvals WHERE email=? AND machine=?", (email, machine)).fetchone() is None:
        conn.execute("INSERT INTO machine_approvals (email, machine, status, requested_at) VALUES (?,?,?,?)",
                     (email, machine, new, _stamp()))
    conn.execute("UPDATE machine_approvals SET status=?, decided_at=?, decided_by=? WHERE email=? AND machine=?",
                 (new, _stamp(), who, email, machine))
    conn.commit()
    if new != "approved":
        auth.revoke_sessions(conn, email)       # an open session ends at once (the other machines' sessions too: they sign in again)
    auth.audit(conn, who, action, f"{email} @ {machine}")


def approve(conn, actor, email: str, machine: str) -> None:
    _decide(conn, actor, email, machine, "approved", "machine_approve")


def reject(conn, actor, email: str, machine: str) -> None:
    _decide(conn, actor, email, machine, "rejected", "machine_reject")


def revoke(conn, actor, email: str, machine: str) -> None:
    """Take back an approval (the row stays, as 'rejected', so the history and a later re-approval are one click)."""
    _decide(conn, actor, email, machine, "rejected", "machine_revoke")


# ---- giới hạn số lần thử ------------------------------------------------------------------------------------------------------------
def record_attempt(conn, ip: str, email: str, ok: bool) -> None:
    conn.execute("INSERT INTO login_attempts (at, ip, email, ok) VALUES (?,?,?,?)", (time.time(), ip, (email or "")[:120], 1 if ok else 0))
    conn.execute("DELETE FROM login_attempts WHERE at < ?", (time.time() - 7 * 86400,))
    conn.commit()


def blocked(conn, ip: str, now: Optional[float] = None) -> Optional[str]:
    """The refusal when this address failed MAX_FAILS times within FAIL_WINDOW seconds, else None."""
    now = time.time() if now is None else now
    rows = conn.execute("SELECT at FROM login_attempts WHERE ip=? AND ok=0 AND at>=? ORDER BY at", (ip, now - FAIL_WINDOW)).fetchall()
    if len(rows) < MAX_FAILS:
        return None
    wait = max(int((rows[-MAX_FAILS]["at"] + FAIL_WINDOW - now) // 60) + 1, 1)
    return (f"Đăng nhập sai quá nhiều lần từ địa chỉ này ({len(rows)} lần trong {FAIL_WINDOW // 60} phút). Chờ khoảng {wait} phút rồi thử "
            "lại; nếu bạn không thử sai, báo Owner (nhật ký ở 👥 Nhóm).")


# ---- đăng nhập ----------------------------------------------------------------------------------------------------------------------
HOW_TO = ("Cách xử lý: dùng máy PC công ty nối thẳng mạng nội bộ (không qua VPN / Wi-Fi khách / proxy), tải lại trang; vẫn lỗi thì gửi "
          "Owner địa chỉ IP trên để kiểm tra DNS nội bộ.")


def _gate(conn, ip: str, local: bool):
    def gate(email: str, role: str) -> str:
        name, why = machine_of(ip, local)
        if role == "owner":                     # the Owner: passcode / local rule already passed (auth.owner_remote_check)
            return f"machine={name or '?'}"
        if name is None:
            auth.audit(conn, email, "login_refused_machine", f"? ip={ip} ({why})")
            raise auth.AuthError(f"Không xác định được tên máy của bạn (IP {ip or '?'}): {why}. Dashboard mở cho mạng LAN chỉ cho "
                                 f"đăng nhập từ máy PC đã được Owner duyệt. {HOW_TO}")
        st = status(conn, email, name)
        if st == "approved":
            touch(conn, email, name, ip)
            return f"machine={name}"
        if st == "rejected":
            auth.audit(conn, email, "login_refused_machine", f"{name} ip={ip} (đã bị từ chối / thu hồi)")
            raise auth.AuthError(f"Máy {name} chưa được phép đăng nhập bằng {email} (Owner đã từ chối hoặc thu hồi). Nhờ Owner duyệt "
                                 "lại ở 👥 Nhóm → Máy được duyệt, hoặc dùng máy đã được duyệt.")
        first = st is None
        request(conn, email, name, ip)
        if first:
            auth.audit(conn, email, "machine_request", f"{name} ip={ip}")
        raise MachinePending(f"{'Đã gửi yêu cầu' if first else 'Vẫn đang'} chờ Owner duyệt máy {name} cho {email}. Owner duyệt ở "
                             "👥 Nhóm → Máy được duyệt; sau đó bấm “Vào Dashboard” lại.")
    return gate


def sign_in(conn, email: str, ip: str, local: bool, source: str = "", passcode: Optional[str] = None) -> str:
    """The dashboard's one way in. LAN off → auth.login exactly as before. LAN on → try limit, machine check (members), audit with the
    machine. Returns the session token; raises auth.AuthError (MachinePending while the Owner has not decided)."""
    if not lan_on():
        return auth.login(conn, email, source, local, passcode)
    ip = normalize_ip(ip)
    key = ip or ("local" if local else "?")
    refused = blocked(conn, key)
    if refused:
        auth.audit(conn, (email or "")[:120], "login_rate_limited", f"ip={key}")
        raise auth.AuthError(refused)
    try:
        token = auth.login(conn, email, source, local, passcode, gate=_gate(conn, ip, local))
    except MachinePending:
        raise
    except auth.AuthError:
        record_attempt(conn, key, email, False)
        raise
    record_attempt(conn, key, email, True)
    return token


def session_refusal(conn, email: str, role: str, ip: str, local: bool) -> Optional[str]:
    """Checked on every page load of a signed-in member (LAN on): None = fine, else why the session may not be used from here."""
    if not lan_on() or role == "owner":
        return None
    name, why = machine_of(ip, local)
    if name is None:
        return f"Không xác định được tên máy của bạn: {why}. {HOW_TO}"
    if status(conn, email, name) != "approved":
        return f"Máy {name} chưa được Owner duyệt cho {email} — đăng nhập lại từ máy này để gửi yêu cầu duyệt."
    return None
