"""Khóa cứng `--max-usd` cho script dòng lệnh (S14.2; người dùng duyệt 04/10 — docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 6d ý 6).

Ở dashboard mọi trần tiền chỉ CẢNH BÁO (mục 6c) vì có người nhìn thanh 💵. Ở dòng lệnh không ai thấy cảnh báo, nên script gọi API trả
tiền giữ một trần CỨNG do chính lệnh khai báo:

    ap = argparse.ArgumentParser(); ap.add_argument("--yes", action="store_true"); script_cap.add_argument(ap)
    a = ap.parse_args()
    cap = script_cap.from_args(a, "tên việc")       # có --yes mà thiếu --max-usd → SystemExit (từ chối chạy)
    with cap:                                       # cap là ScriptCap (đã có --max-usd) hoặc NO_CAP (chạy khô, không gọi gì)
        for item in items:
            if not cap.allow(cap.estimate_llm("director")):   # đã chi + ước tính lượt kế > trần → dừng, giữ kết quả đã có
                break
            ...
    # khối `with` đóng: in "đã chi ≈ $x / trần $y"; CapReached (lượt bị chặn ở tầng dưới) được nuốt ở đây → code sau `with` vẫn
    # chạy (ghi kết quả đã có).

Đếm tiền (một tiến trình, không lẫn với dashboard đang chạy cùng sổ chi): mỗi dòng sổ chi chính tiến trình này ghi
(`cost.record_usage`, trừ dòng Claude) được định giá bằng `money_policy.estimate` (tính dư); mỗi lời gọi Claude bằng
`llm_runner.reply_usd` (giá cao nhất đã biết × 1,5 khi model chưa có giá). Chặn trước khi trả tiền: `budget.check_image /
check_video / check_audio` (mọi lượt gửi ảnh / video / âm thanh — cả spend_gate lẫn script thử nghiệm gọi thẳng) và
`llm_runner` trước mỗi lời gọi Claude hỏi `refusal(...)` của trần đang bật. Âm thanh chưa có giá USD: không tính vào trần (giới hạn
theo lượt ở core.budget), nói một lần. Nhà cung cấp giả (mock*) = 0 USD."""
import threading
from typing import Optional

_LOCK = threading.Lock()
_ACTIVE: Optional["ScriptCap"] = None
LLM_GUESS_OUTPUT = 4000          # lời gọi Claude chưa biết dài bao nhiêu: tính trước token ra ≤ số này (≤ max_tokens của lời gọi)


class CapReached(RuntimeError):
    """Lượt kế làm vượt trần `--max-usd` của lần chạy này — không gửi."""


class ScriptCap:
    def __init__(self, max_usd: float, what: str = "script", log=print):
        if max_usd is None or float(max_usd) <= 0:
            raise ValueError("--max-usd phải > 0")
        self.max_usd = float(max_usd)
        self.what = what
        self.log = log
        self.spent = 0.0
        self.calls = 0
        self.stopped: Optional[str] = None
        self._audio_said = False

    # ---- trước khi trả tiền ------------------------------------------------------------------------------------------------
    def refusal(self, next_usd: Optional[float], label: str = "lượt kế") -> Optional[str]:
        """Câu từ chối (đã chi + ước tính lượt kế > trần), hoặc None. Đã dừng một lần thì mọi lượt sau đều bị từ chối."""
        with _LOCK:
            if self.stopped:
                return self.stopped
            nxt = float(next_usd or 0.0)
            if self.spent + nxt > self.max_usd + 1e-9:
                self.stopped = (f"DỪNG ({self.what}): đã chi ≈ ${self.spent:.2f} + {label} ≈ ${nxt:.2f} (ước tính) > trần --max-usd "
                                f"${self.max_usd:.2f} — không gửi, kết quả đã có được giữ")
                self.log(self.stopped)
                return self.stopped
            return None

    def allow(self, next_usd: Optional[float], label: str = "lượt kế") -> bool:
        return self.refusal(next_usd, label) is None

    def guard(self, next_usd: Optional[float], label: str = "lượt kế") -> None:
        why = self.refusal(next_usd, label)
        if why:
            raise CapReached(why)

    # ---- sau khi trả tiền ------------------------------------------------------------------------------------------------
    def add(self, usd: Optional[float]) -> None:
        with _LOCK:
            self.spent += float(usd or 0.0)
            self.calls += 1

    # ---- ước tính (tính dư) ----------------------------------------------------------------------------------------------
    def estimate(self, kind: str, model: Optional[str], tier: Optional[str] = None, units: float = 1) -> Optional[float]:
        from . import money_policy
        return money_policy.estimate(kind, model, tier, units)["usd"]

    def estimate_llm(self, stage: str, images: int = 0, conn=None, calls: int = 1) -> float:
        """Một (hoặc `calls`) lời gọi Claude của khâu này, tính dư (× cost.LLM_MARGIN; model chưa có giá: giá cao nhất × 1,5)."""
        from . import cost, money_policy
        usd = cost.llm_estimate(conn, stage, calls, images=images)
        if usd is None:
            pricing = cost.load_pricing()
            base_in, base_out = cost.LLM_STAGE_TOKENS.get(stage, (6000, 1500))
            a, _ = money_policy.token_price(pricing, cost.llm_model(), "input", (base_in + images * cost.IMAGE_TOKENS) * calls)
            b, _ = money_policy.token_price(pricing, cost.llm_model(), "output", base_out * calls)
            usd = (a or 0.0) + (b or 0.0)
        return usd * cost.LLM_MARGIN

    def summary(self) -> str:
        return (f"{self.what}: đã chi ≈ ${self.spent:.2f} / trần --max-usd ${self.max_usd:.2f} ({self.calls} lượt trả tiền)"
                + (" — ĐÃ DỪNG vì chạm trần" if self.stopped else ""))

    # ---- bật / tắt cho cả tiến trình ------------------------------------------------------------------------------------
    def start(self) -> "ScriptCap":
        """Bật cho tới hết tiến trình (script cũ không muốn thụt lề cả thân vào `with`): in tóm tắt lúc thoát."""
        import atexit
        import sys
        self.__enter__()
        atexit.register(self.finish)
        previous = sys.excepthook

        def hook(kind, value, tb):          # rà soát A2 (b): chạm trần = một câu tiếng Việt (đã in lúc chặn), không traceback
            if isinstance(value, CapReached):
                self.log("Đã dừng lệnh vì chạm trần --max-usd; kết quả đã có được giữ.")
                return
            previous(kind, value, tb)
        sys.excepthook = hook
        return self

    def finish(self) -> None:
        if _ACTIVE is self:
            self.__exit__(None, None, None)

    def __enter__(self) -> "ScriptCap":
        global _ACTIVE
        with _LOCK:
            if _ACTIVE is not None and _ACTIVE is not self:
                raise RuntimeError("đã có một trần --max-usd đang bật trong tiến trình này")
            _ACTIVE = self
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        global _ACTIVE
        with _LOCK:
            if _ACTIVE is self:
                _ACTIVE = None
        self.log(self.summary())
        return exc_type is not None and issubclass(exc_type, CapReached)    # chạm trần: nuốt, code sau `with` ghi kết quả đã có


class _NoCap:
    """Chạy khô (không --yes, không --max-usd): không bật trần nào — script không được gọi gì trả tiền."""
    max_usd = None
    spent = 0.0
    stopped = None

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def start(self):
        return self

    def finish(self) -> None:
        return None

    def allow(self, next_usd=None, label: str = "") -> bool:
        return True

    def refusal(self, next_usd=None, label: str = ""):
        return None

    def guard(self, next_usd=None, label: str = "") -> None:
        return None

    def add(self, usd=None) -> None:
        return None

    def estimate(self, *a, **k):
        return None

    def estimate_llm(self, *a, **k) -> float:
        return 0.0

    def summary(self) -> str:
        return "chưa gọi gì trả tiền"


NO_CAP = _NoCap()


def add_argument(parser) -> None:
    parser.add_argument("--max-usd", type=float, default=None, dest="max_usd",
                        help="BẮT BUỘC khi gọi thật (--yes): trần CỨNG USD của lần chạy này — chi + ước tính lượt kế vượt thì dừng, giữ kết "
                             "quả đã có, in đã chi bao nhiêu (core/script_cap.py)")


def from_args(args, what: str, log=print):
    """ScriptCap từ `--max-usd`. Có `--yes` (hoặc `paid=True` qua thuộc tính args.paid) mà thiếu `--max-usd` → SystemExit: từ chối chạy."""
    max_usd = getattr(args, "max_usd", None)
    paid = bool(getattr(args, "yes", False) or getattr(args, "paid", False))
    if max_usd is None:
        if paid:
            raise SystemExit(f"Từ chối chạy ({what}): lệnh gọi API trả tiền phải khai trần cứng --max-usd <USD> "
                             "(ví dụ --max-usd 0.5). Không ai thấy cảnh báo ở dòng lệnh nên trần này CHẶN thật.")
        return NO_CAP
    if float(max_usd) <= 0:
        raise SystemExit(f"Từ chối chạy ({what}): --max-usd phải > 0")
    return ScriptCap(float(max_usd), what, log)


def require(args, what: str, log=print) -> ScriptCap:
    """Cho script KHÔNG có bước chạy khô (mọi lần chạy đều trả tiền): thiếu --max-usd → SystemExit."""
    cap = from_args(args, what, log)
    if cap is NO_CAP:
        raise SystemExit(f"Từ chối chạy ({what}): lệnh gọi API trả tiền phải khai trần cứng --max-usd <USD> (ví dụ --max-usd 0.5).")
    return cap


def active() -> Optional[ScriptCap]:
    return _ACTIVE


# ---- móc cho các cổng sẵn có (core.budget / core.cost / core.llm_runner) ----------------------------------------------------------
def send_refusal(kind: str, provider_name: str, model: Optional[str] = None, tier: Optional[str] = None,
                 units: float = 1) -> Optional[str]:
    """budget.check_*: trần đang bật từ chối lượt gửi này? Mock = 0 USD; âm thanh chưa có giá = 0 USD (nói một lần)."""
    cap = _ACTIVE
    if cap is None or str(provider_name or "").startswith("mock"):
        return None
    usd = cap.estimate(kind, model, tier, units)
    if usd is None:
        if kind == "audio":
            if not cap._audio_said:
                cap._audio_said = True
                cap.log(f"⚠ ({cap.what}) âm thanh chưa có giá USD — không tính vào --max-usd; giới hạn theo lượt (⚙ → 💵 đợt thử)")
            return cap.refusal(0.0)
        return cap.refusal(float("inf"), f"{kind} {model or ''} (chưa có giá, không ước tính được)")
    return cap.refusal(usd, f"{kind} {model or ''}".strip())


def record_row(kind: str, provider: str, model: Optional[str], tier: Optional[str], quantity: float) -> None:
    """cost.record_usage (dòng không phải Claude): cộng giá tính dư của dòng sổ chi này vào trần đang bật."""
    cap = _ACTIVE
    if cap is None or kind == "llm" or str(provider or "").startswith("mock"):
        return
    usd = cap.estimate(kind, model, None if tier in (None, "default", "image") else tier, quantity) if kind in ("image", "video") else None
    cap.add(usd)


def llm_refusal(next_usd: float) -> Optional[str]:
    cap = _ACTIVE
    return None if cap is None else cap.refusal(next_usd, "lời gọi Claude kế")


def llm_spent(usd: float) -> None:
    cap = _ACTIVE
    if cap is not None:
        cap.add(usd)
