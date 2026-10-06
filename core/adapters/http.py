"""Minimal HTTP client for the Deepix / Clip AI gateways (stdlib only, injectable transport).

Envelope rule (from the vendor docs): a response is successful when `code` is absent/0/200 AND
`status` is absent/'success'/'ok'. The bearer token is only ever sent to the configured API host,
never to result-download URLs, and is never included in error messages.
"""
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from ..providers import ProviderError


# Data Pack P5: how the services say "no money left" (HTTP 402 aside). Kept narrow — a false stop halts every paid send.
_OUT_OF_CREDIT = ("insufficient balance", "insufficient credit", "insufficient funds", "credit balance is too low", "not enough credit",
                  "not enough balance", "balance is not enough", "out of credit", "余额不足", "积分不足",
                  "额度不足", "欠费")


def out_of_credit(message: str) -> bool:
    m = (message or "").lower()
    return any(h in m for h in _OUT_OF_CREDIT)


@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: Dict[str, str] = field(default_factory=dict)   # Data Pack P1: lower-case names (Anthropic 'request-id')


Transport = Callable[[str, str, Dict[str, str], Optional[bytes], float], HttpResponse]


def urllib_transport(method: str, url: str, headers: Dict[str, str], body: Optional[bytes],
                     timeout: float) -> HttpResponse:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()})
    except urllib.error.HTTPError as e:
        return HttpResponse(e.code, e.read(), {k.lower(): v for k, v in (e.headers or {}).items()})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ProviderError(f"network error: {e}", code="network", transient=True) from None


def encode_multipart(fields: Dict[str, str], files: List[Tuple[str, str, bytes]]) -> Tuple[bytes, str]:
    """files: (field_name, filename, content). Returns (body, content_type)."""
    boundary = uuid.uuid4().hex
    parts: List[bytes] = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, filename, content in files:
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                      f"Content-Type: {ctype}\r\n\r\n").encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def clean_token(raw: str) -> str:
    """Normalise a pasted token; raise a clear (token-free) error when it cannot be a valid header value."""
    token = (raw or "").strip().strip("\"'`<>").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    problems = describe_token(token)
    if token and problems:
        raise ProviderError("token looks corrupted (" + ", ".join(problems) + "); copy it again from the website "
                            "and re-enter it with a single paste", code="config")
    return token


def describe_token(token: str) -> List[str]:
    """Return problems found in a token without revealing its content."""
    problems = []
    if any(ch.isspace() for ch in token):
        problems.append("contains whitespace or a line break")
    if any(ord(ch) > 126 or ord(ch) < 33 for ch in token if not ch.isspace()):
        problems.append("contains non-ASCII or control characters")
    if any(ch in token for ch in "\"'"):
        problems.append("contains quote characters")
    return problems


_RATE_LIMIT_HINTS = ("too many request", "rate limit", "retry after")


def parse_envelope(payload) -> object:
    """Return `data` of a successful envelope, or raise ProviderError.

    A "too many requests" style error (the vendor is asking us to slow down, not reporting that the
    underlying job failed) is marked transient: the caller keeps polling instead of marking a running
    job "failed" just because the *status check itself* got rate-limited (a real job kept generating
    successfully server-side while its poll calls kept hitting this and being wrongly declared failed)."""
    if not isinstance(payload, dict):
        raise ProviderError(f"invalid API response: {str(payload)[:200]}", code="bad_response")
    code_ok = "code" not in payload or payload["code"] in (0, 200)
    status_ok = "status" not in payload or payload["status"] in ("success", "ok")
    if not (code_ok and status_ok):
        message = payload.get("msg") or payload.get("message") or "unknown error"
        if out_of_credit(message):
            raise ProviderError(f"hết tiền / hết credit ở nhà cung cấp: {message}", code="out_of_credit")
        signal = f"code={payload['code']}" if "code" in payload else f"status={payload.get('status')}"
        transient = any(h in message.lower() for h in _RATE_LIMIT_HINTS)
        raise ProviderError(f"API error ({signal}): {message}", code="api_error", transient=transient)
    return payload.get("data")


class ApiClient:
    def __init__(self, base_url: str, token: str, user_agent: str, transport: Transport = urllib_transport,
                 timeout: float = 60, auth_header: str = "Authorization", auth_prefix: str = "Bearer "):
        self.base = base_url.rstrip("/")
        self._token = token
        self.auth_header, self.auth_prefix = auth_header, auth_prefix     # sync.so: x-api-key, no prefix
        self.user_agent = user_agent
        self.transport = transport
        self.timeout = timeout

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {self.auth_header: f"{self.auth_prefix}{self._token}", "User-Agent": self.user_agent}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _send(self, method: str, path: str, body: Optional[bytes] = None, content_type: Optional[str] = None,
              query: Optional[Dict] = None, raw: bool = False):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        resp = self.transport(method, url, self._headers(content_type), body, self.timeout)
        if resp.status == 401:
            raise ProviderError("invalid or missing token (HTTP 401)", code="auth")
        if resp.status == 402:   # Data Pack P5: payment required = the account is out of money — stop every send, say it
            raise ProviderError("hết tiền / hết credit (HTTP 402): " + resp.body[:200].decode("utf-8", "replace"), code="out_of_credit")
        if resp.status == 413:
            raise ProviderError("payload too large (HTTP 413): reference image over the size limit", code="too_large")
        if resp.status == 429:   # rate limited: rejected before generating (no cost) - wait and try again, never a failure
            raise ProviderError("rate limited (HTTP 429)", code="rate_limited", transient=True)
        if resp.status >= 500:
            raise ProviderError(f"server error (HTTP {resp.status})", code="server_error", transient=True)
        if resp.status >= 400:
            text = resp.body[:300].decode("utf-8", "replace")
            hint = (" (a header was rejected: the token probably contains a hidden character; the checker above "
                    "reports token problems, then copy the token again and paste it once)"
                    if "invalid header" in text.lower() else "")
            if out_of_credit(text):
                raise ProviderError(f"hết tiền / hết credit (HTTP {resp.status}): {text}", code="out_of_credit")
            raise ProviderError(f"HTTP {resp.status}: {text}{hint}", code="http_error")
        try:
            payload = json.loads(resp.body.decode("utf-8"))
        except ValueError:
            raise ProviderError(f"invalid JSON response: {resp.body[:200]!r}", code="bad_response") from None
        return payload if raw else parse_envelope(payload)

    def get(self, path: str, query: Optional[Dict] = None, raw: bool = False):
        return self._send("GET", path, query=query, raw=raw)

    def post_json(self, path: str, body: Dict):
        return self._send("POST", path, json.dumps(body).encode("utf-8"), "application/json")

    def post_multipart(self, path: str, fields: Dict[str, str], files: List[Tuple[str, str, bytes]], raw: bool = False):
        """raw=True: the reply is not the usual {code, data} envelope (e.g. Deepix cutout) and is returned as parsed JSON."""
        data, content_type = encode_multipart(fields, files)
        return self._send("POST", path, data, content_type, raw=raw)

    def download(self, url: str, dest_path: str) -> str:
        """Download a result file. Deliberately sends NO Authorization header (URL is a third-party host)."""
        resp = self.transport("GET", url, {"User-Agent": self.user_agent}, None, max(self.timeout, 120))
        if resp.status != 200:
            raise ProviderError(f"download failed (HTTP {resp.status})", code="download", transient=resp.status >= 500)
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(resp.body)
        return dest_path
