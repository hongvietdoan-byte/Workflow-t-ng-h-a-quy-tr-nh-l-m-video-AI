"""Trạng thái đăng nhập CLI của pipeline: không đọc credential, không gọi model.

Chỉ được UI có quyền cài đặt gọi khi người dùng mở ô kiểm. Không trả lại
stdout/stderr/ngoại lệ của tiến trình; bộ nhớ đệm chỉ chứa metadata allowlist.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time

TTL_SECONDS = 30
TIMEOUT_SECONDS = 8
_CACHE = {}
_LOCK = threading.Lock()
_EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}\Z")


def clear_cache():
    with _LOCK:
        _CACHE.clear()


def _parse(proc):
    try:
        def invalid_constant(_):
            raise ValueError("invalid_json")
        payload = json.loads(proc.stdout, parse_constant=invalid_constant)
        if not isinstance(payload, dict) or type(payload.get("loggedIn")) is not bool:
            return "invalid_response", None
        if not payload["loggedIn"]:
            return ("logged_out", None) if proc.returncode in (0, 1) else ("command_failed", None)
        if proc.returncode != 0:
            return "command_failed", None
        email = payload.get("email")
        email = email if isinstance(email, str) and len(email) <= 254 and _EMAIL.fullmatch(email) else None
        return "logged_in", email
    except (TypeError, ValueError, AttributeError):
        return "invalid_response", None


def _windows():
    return os.name == "nt"


def _stop_owned(process, env, cwd):
    """Chỉ dừng cây PID/session do lần kiểm này tạo, rồi thu hồi tiến trình cha."""
    if _windows():
        taskkill = str(Path(env.get("SYSTEMROOT", "C:/Windows")) / "System32" / "taskkill.exe")
        try:
            subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"], env=env, cwd=cwd,
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5, shell=False, creationflags=subprocess.CREATE_NO_WINDOW, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(process.pid, getattr(signal, "SIGKILL", 9))
        except (OSError, ProcessLookupError):
            pass
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def _owned_command(args, *, timeout, **options):
    """Sở hữu cả shim .cmd và node con; timeout không chỉ kill shim như run()."""
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if _windows() else {"start_new_session": True}
    process = subprocess.Popen(args, **options, **flags)
    try:
        output, _ = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(args, process.returncode, stdout=output)
    except subprocess.TimeoutExpired:
        _stop_owned(process, options["env"], options["cwd"])
        # Không đưa stdout/stderr từng phần của TimeoutExpired vào báo cáo.
        raise subprocess.TimeoutExpired("claude auth status", timeout) from None
    except (OSError, subprocess.SubprocessError):
        _stop_owned(process, options["env"], options["cwd"])
        raise
    finally:
        stream = getattr(process, "stdout", None)
        if stream is not None:
            try:
                stream.close()
            except (OSError, ValueError):
                pass


def get_status(provider, *, force=False):
    """Return {status,email,command,config_dir}; provider đã resolve bởi pipeline.

    Auth dùng cùng clean_env public và cwd tạm của ClaudeCliClient, không khởi
    tạo client/provider hay nạp cấu hình dự án làm tài khoản của máy khác.
    """
    result = {"status": "not_selected", "email": None, "command": None, "config_dir": None}
    if provider != "claude_cli":
        return result
    from .llm_runner import ClaudeCliClient
    env = ClaudeCliClient.clean_env()
    home = env.get("USERPROFILE") if os.name == "nt" else env.get("HOME")
    home = home or env.get("HOME") or env.get("USERPROFILE")
    configured = env.get("CLAUDE_CONFIG_DIR")
    config = configured or (str(Path(home) / ".claude") if home else None)
    if config and not Path(config).is_absolute():
        result["status"] = "invalid_config"
        return result
    result["config_dir"] = config
    try:
        command = shutil.which("claude", path=env.get("PATH"))
    except OSError:
        command = None
    result["command"] = command
    if not command:
        result["status"] = "not_installed"
        return result
    # Hash kín toàn môi trường đã lọc: thay runtime/HOME/config/PATH thì không
    # mượn kết quả cũ. Không lưu môi trường hoặc đưa hash/nội dung vào report.
    signature = hashlib.sha256(json.dumps(env, sort_keys=True).encode("utf-8")).digest()
    key = (command, config, signature, os.getpid(), os.getcwd())
    with _LOCK:
        now = time.monotonic()
        cached = _CACHE.get(key)
        if not force and cached and 0 <= now - cached[0] < TTL_SECONDS:
            return dict(cached[1])
        try:
            with tempfile.TemporaryDirectory(prefix="claude_auth_") as work:
                proc = _owned_command([command, "auth", "status"], stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                      text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
                                      shell=False, cwd=work, env=env)
            result["status"], result["email"] = _parse(proc)
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        except (OSError, subprocess.SubprocessError):
            result["status"] = "command_failed"
        # Giới hạn bộ nhớ khi môi trường/tài khoản được thay nhiều lần.
        _CACHE.clear()
        _CACHE[key] = (time.monotonic(), dict(result))
        return result
