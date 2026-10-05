"""Reads the data script of a Nuxt page (`window.__NUXT__=…`) WITHOUT running any code (S14.5 C2b, rà bảo mật 06/10).

The real ff.garena.com pages carry their data as `(function(a,b,…){ z.id=75; B[0]={…}; … return {…}}(arg1,arg2,…))`: a function whose
parameters are filled with literal arguments, a few assignments into those parameters, then one object literal. This module parses
exactly that shape — literals (strings, numbers, true/false/null, `void 0`, objects, arrays, `Array(n)`), parameter names, member
assignments `x.k=…` / `x[0]=…` / `x["k"]=…` — and builds the value in Python, giving the same result as JSON.stringify of the evaluated
script (undefined object fields dropped, undefined array items become null). Anything else (a call, an operator, `new`, a template
string…) is refused with NuxtError: nothing in the page is ever executed, so a page cannot read files, reach the network or stop us.
Checked 06/10/2026 against six real pages (maps, chars, pets, weapons, news, chars/796): identical to what Node.js produced.
"""
import json
import re
from typing import Any, Dict, List, Optional

MAX_CHARS = 5_000_000          # a page's script larger than this is refused (the real ones are 15–45k characters)
MAX_DEPTH = 200


class NuxtError(ValueError):
    """The script is not in the shape this reader understands (or is too large / too deep)."""


class _Undef:
    def __repr__(self):
        return "undefined"


UNDEF = _Undef()
_TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<num>-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)
  | (?P<name>[A-Za-z_$][\w$]*)
  | (?P<punct>[{}\[\]():;,.=!])
""", re.VERBOSE)
_SIMPLE_ESC = {'"': '"', "'": "'", "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v", "0": "\0"}


def _unquote(raw: str) -> str:
    body, out, i = raw[1:-1], [], 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        e = body[i + 1]
        if e == "u":
            if body[i + 2] == "{":
                end = body.index("}", i)
                out.append(chr(int(body[i + 3:end], 16)))
                i = end + 1
            else:
                out.append(chr(int(body[i + 2:i + 6], 16)))
                i += 6
            continue
        if e == "x":
            out.append(chr(int(body[i + 2:i + 4], 16)))
            i += 4
            continue
        out.append(_SIMPLE_ESC.get(e, e))
        i += 2
    s = "".join(out)
    try:                                       # join surrogate pairs written as two \u escapes
        return s.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeError:
        return s


def _tokens(code: str) -> List[tuple]:
    out, pos = [], 0
    while pos < len(code):
        m = _TOKEN.match(code, pos)
        if not m:
            raise NuxtError(f"ký tự không đọc được ở vị trí {pos}: {code[pos:pos + 30]!r}")
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group(kind), pos))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, code: str):
        self.t = _tokens(code)
        self.i = 0
        self.env: Dict[str, Any] = {}

    # -- token helpers
    def peek(self, k: int = 0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else ("eof", "", -1)

    def take(self, value: Optional[str] = None, kind: Optional[str] = None):
        tok = self.peek()
        if (value is not None and tok[1] != value) or (kind is not None and tok[0] != kind) or tok[0] == "eof":
            want = value or kind or "?"
            raise NuxtError(f"cần '{want}' nhưng gặp {tok[1]!r} (vị trí {tok[2]})")
        self.i += 1
        return tok

    def at(self, value: str) -> bool:
        return self.peek()[1] == value and self.peek()[0] == "punct"

    # -- program: (function(p,…){ stmts; return EXPR }(args))  or  (function(…){…})(args)
    def program(self):
        self.take("(")
        self.take("function", "name")
        self.take("(")
        params = []
        while not self.at(")"):
            params.append(self.take(kind="name")[1])
            if not self.at(")"):
                self.take(",")
        self.take(")")
        self.take("{")
        body_start = self.i
        depth = 1                              # skip the body for now: the arguments must be known first
        while depth:
            tok = self.take()
            if tok[0] == "punct" and tok[1] in "{":
                depth += 1
            elif tok[0] == "punct" and tok[1] == "}":
                depth -= 1
        body_end = self.i - 1
        wrapped = self.at(")")
        if wrapped:
            self.take(")")
        self.take("(")
        args = []
        while not self.at(")"):
            args.append(self.expr(0))
            if not self.at(")"):
                self.take(",")
        self.take(")")
        if not wrapped:
            self.take(")")
        if self.peek()[0] != "eof":
            raise NuxtError(f"còn mã sau dữ liệu: {self.peek()[1]!r}")
        self.env = {p: (args[n] if n < len(args) else UNDEF) for n, p in enumerate(params)}
        end, self.i = self.i, body_start
        result = UNDEF
        while self.i < body_end:
            if self.peek()[1] == "return" and self.peek()[0] == "name":
                self.take()
                result = self.expr(0)
                if self.at(";"):
                    self.take(";")
                if self.i != body_end:
                    raise NuxtError("còn mã sau lệnh return")
                break
            self.assignment()
        self.i = end
        return result

    def assignment(self):
        name = self.take(kind="name")[1]
        if name not in self.env:
            raise NuxtError(f"tên lạ '{name}' (chỉ nhận tham số của hàm)")
        target, key = None, None
        obj = self.env[name]
        while not self.at("="):
            if target is not None:
                obj = self._get(target, key)
            if self.at("."):
                self.take(".")
                target, key = obj, self.take(kind="name")[1]
            elif self.at("["):
                self.take("[")
                tok = self.take()
                if tok[0] == "num":
                    key = int(float(tok[1]))
                elif tok[0] == "str":
                    key = _unquote(tok[1])
                else:
                    raise NuxtError(f"chỉ số lạ {tok[1]!r}")
                self.take("]")
                target = obj
            else:
                raise NuxtError(f"lệnh gán lạ ở {self.peek()[1]!r}")
        if target is None:
            raise NuxtError("không nhận gán lại tham số")
        self.take("=")
        value = self.expr(0)
        if self.at(";"):
            self.take(";")
        self._set(target, key, value)

    @staticmethod
    def _get(obj, key):
        if isinstance(obj, dict):
            return obj.get(str(key), UNDEF)
        if isinstance(obj, list) and isinstance(key, int) and 0 <= key < len(obj):
            return obj[key]
        raise NuxtError(f"không đọc được '{key}' của {type(obj).__name__}")

    @staticmethod
    def _set(obj, key, value):
        if isinstance(obj, dict):
            obj[str(key)] = value
        elif isinstance(obj, list) and isinstance(key, int) and 0 <= key < 1_000_000:
            obj.extend([UNDEF] * (key + 1 - len(obj)))
            obj[key] = value
        else:
            raise NuxtError(f"không gán được '{key}' vào {type(obj).__name__}")

    def expr(self, depth: int):
        if depth > MAX_DEPTH:
            raise NuxtError("dữ liệu lồng quá sâu")
        kind, val, pos = self.take()
        if kind == "str":
            return _unquote(val)
        if kind == "num":
            f = float(val)
            return int(f) if f.is_integer() and not re.search(r"[.eE]", val) else f
        if kind == "punct" and val == "-" :
            raise NuxtError("toán tử lạ")
        if kind == "punct" and val == "!" and self.peek()[0] == "num" and self.peek()[1] in ("0", "1"):
            return self.take()[1] == "0"                               # minifiers write !0 / !1 for true / false
        if kind == "punct" and val == "{":
            obj: Dict[str, Any] = {}
            while not self.at("}"):
                k = self.take()
                if k[0] == "str":
                    key = _unquote(k[1])
                elif k[0] in ("name", "num"):
                    key = k[1]
                else:
                    raise NuxtError(f"khóa lạ {k[1]!r} (vị trí {k[2]})")
                self.take(":")
                obj[key] = self.expr(depth + 1)
                if not self.at("}"):
                    self.take(",")
            self.take("}")
            return obj
        if kind == "punct" and val == "[":
            arr: List[Any] = []
            while not self.at("]"):
                arr.append(self.expr(depth + 1))
                if not self.at("]"):
                    self.take(",")
            self.take("]")
            return arr
        if kind == "name":
            if val == "true":
                return True
            if val == "false":
                return False
            if val == "null":
                return None
            if val == "undefined":
                return UNDEF
            if val == "void":
                self.take("0", "num")
                return UNDEF
            if val == "Array" and self.at("("):
                self.take("(")
                n = int(self.take(kind="num")[1])
                self.take(")")
                if not 0 <= n <= 100_000:
                    raise NuxtError("Array quá lớn")
                return [UNDEF] * n
            if val in self.env:
                return self.env[val]
            raise NuxtError(f"tên lạ '{val}' (vị trí {pos}) — chỉ đọc dữ liệu, không chạy mã")
        raise NuxtError(f"không đọc được {val!r} (vị trí {pos}) — chỉ đọc dữ liệu, không chạy mã")


def _plain(value, seen=None):
    """Like JSON.stringify: drop undefined object fields, undefined array items → None; a cycle is refused."""
    seen = seen if seen is not None else set()
    if isinstance(value, (dict, list)):
        if id(value) in seen:
            raise NuxtError("dữ liệu tự tham chiếu vòng")
        seen.add(id(value))
        if isinstance(value, dict):
            out = {k: _plain(v, seen) for k, v in value.items() if v is not UNDEF}
        else:
            out = [None if v is UNDEF else _plain(v, seen) for v in value]
        seen.discard(id(value))
        return out
    return None if value is UNDEF else value


def read(code: str) -> Any:
    """The value of a Nuxt data script (the text after `window.__NUXT__=`), as plain Python. NuxtError when it is not data."""
    code = (code or "").strip().rstrip(";").strip()
    if len(code) > MAX_CHARS:
        raise NuxtError(f"dữ liệu trang quá lớn ({len(code):,} ký tự)")
    if not code.startswith("("):
        p = _Parser(code)
        p.env = {}
        value = p.expr(0)
        if p.peek()[0] != "eof":
            raise NuxtError(f"còn mã sau dữ liệu: {p.peek()[1]!r}")
        return _plain(value)
    return _plain(_Parser(code).program())


def to_json(code: str) -> str:
    return json.dumps(read(code), ensure_ascii=False)
