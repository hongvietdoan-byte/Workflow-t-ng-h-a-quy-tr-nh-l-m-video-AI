"""DP12 — lớp chặn của pilot vòng A (plugin pytest: `-p pilot_a_guard`, cần tools/ trong PYTHONPATH).

- Mạng ra NGOÀI máy (không phải 127.*, ::1, localhost, socket unix): chặn bằng `Blocked` + đếm — vòng A phải 0 lời gọi ra ngoài (tiêu chí 3: không
  lời gọi trả tiền nào đi được, kể cả khi một test quên mock).
- Mở GHI tệp dưới `<repo>/data`: không chặn (để không đổi kết quả test), chỉ GHI LẠI đường — tiêu chí 4 (0 ghi vào dữ liệu thật).
Mỗi tiến trình (xdist: mỗi worker) ghi `$PILOT_A_GUARD_OUT.<pid>.json` lúc kết thúc: {"network": n, "network_hosts": [...], "data_writes": [...]}."""
import builtins
import io
import json
import os
import socket

_WRITE = ("w", "a", "x", "+")
_LOCAL = ("127.", "::1", "localhost", "0.0.0.0")


class Blocked(OSError):
    """Pilot vòng A: kết nối ra ngoài máy bị chặn."""


class Guard:
    def __init__(self, data_root: str):
        self.data_root = os.path.normcase(os.path.realpath(data_root))
        self.network = 0
        self.network_hosts = []
        self.data_writes = []
        self._saved = {}

    def _under_data(self, path) -> bool:
        try:
            p = os.path.normcase(os.path.realpath(os.fspath(path)))
        except (TypeError, ValueError):
            return False
        return p == self.data_root or p.startswith(self.data_root + os.sep)

    def _outbound(self, address) -> bool:
        if isinstance(address, (str, bytes)):          # AF_UNIX
            return False
        host = str(address[0]) if isinstance(address, tuple) and address else ""
        return not host.startswith(_LOCAL)

    def __enter__(self):
        guard = self
        orig_connect, orig_connect_ex = socket.socket.connect, socket.socket.connect_ex
        orig_open, orig_io_open = builtins.open, io.open

        def connect(sock, address):
            if guard._outbound(address):
                guard.network += 1
                guard.network_hosts.append(str(address[0]))
                raise Blocked(f"pilot vòng A: chặn kết nối ra ngoài {address}")
            return orig_connect(sock, address)

        def connect_ex(sock, address):
            if guard._outbound(address):
                guard.network += 1
                guard.network_hosts.append(str(address[0]))
                return 111                              # ECONNREFUSED
            return orig_connect_ex(sock, address)

        def note(file, mode):
            if isinstance(file, (str, bytes, os.PathLike)) and any(c in str(mode) for c in _WRITE) and guard._under_data(file):
                guard.data_writes.append(os.fspath(file) if not isinstance(file, bytes) else file.decode(errors="replace"))

        def g_open(file, mode="r", *a, **kw):
            note(file, mode)
            return orig_open(file, mode, *a, **kw)

        def g_io_open(file, mode="r", *a, **kw):
            note(file, mode)
            return orig_io_open(file, mode, *a, **kw)

        self._saved = {"connect": orig_connect, "connect_ex": orig_connect_ex, "open": orig_open, "io_open": orig_io_open}
        socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
        builtins.open, io.open = g_open, g_io_open
        return self

    def __exit__(self, *exc):
        socket.socket.connect, socket.socket.connect_ex = self._saved["connect"], self._saved["connect_ex"]
        builtins.open, io.open = self._saved["open"], self._saved["io_open"]
        return False

    def result(self):
        return {"network": self.network, "network_hosts": sorted(set(self.network_hosts)), "data_writes": sorted(set(self.data_writes))}


_ACTIVE = None


def pytest_configure(config):  # noqa: ARG001 - pytest hook
    global _ACTIVE
    root = os.environ.get("PILOT_A_DATA_ROOT") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    _ACTIVE = Guard(root).__enter__()


def pytest_unconfigure(config):  # noqa: ARG001 - pytest hook
    global _ACTIVE
    if _ACTIVE is None:
        return
    _ACTIVE.__exit__(None, None, None)
    out = os.environ.get("PILOT_A_GUARD_OUT")
    if out:
        with open(f"{out}.{os.getpid()}.json", "w", encoding="utf-8") as f:
            json.dump(_ACTIVE.result(), f, ensure_ascii=False)
    _ACTIVE = None
