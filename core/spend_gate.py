"""One money gate for a paid send outside the runners (S14.1 A1a, docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 3.1), with the
money policy of 04/10 (S14.16, mục 6c — core.money_policy): prices are for reference, the caps WARN, only a real stop refuses.

Before: every place that paid for a picture / clip outside ImageRunner / VideoRunner wrote its own checks, and some forgot one —
the character set (core.costume) checked nothing, the end frame / establishing picture / Kling multi-shot try skipped the project's
budget. The gate puts the existing checks (it re-uses them, no new money logic) in one place:

  REFUSED (slot.over = the reason, Vietnamese, with how to reopen):
  * the project is paused → nothing is sent (the same rule as Pipeline.start; slot.paused);
  * the service said it is out of credit (budget.check_* → budget.halted).
  WARNED, the send goes (slot.warning = one sentence with numbers, also written to diag as money_policy.WARN_CODE):
  * budget.warn_image / warn_video / warn_audio: the trial round's planned amount / count, a broken price table;
  * project_budget.warning: the project's approved amount for `budget_stage` (images / videos / claude_*) and its total;
  * a model / tier the price table does not know: estimated HIGH (money_policy.estimate: the highest known price × 1,5).
  * all of it under budget.SPEND_LOCK, from the check to the ledger row;
  * slot.send(fn, …): a provider error 'out_of_credit' halts that service (budget.halt), the error goes on to the caller;
  * slot.record(): one usage_events row right after each send, labelled `ledger_stage` (character_set, end_frame, establishing…);
    a send that failed is not recorded; a send the caller forgot to record is recorded when the block ends (never left out).

Usage:
    with spend_gate.spend(conn, "image", provider.name, project_id=pid, model=m, tier=t, units=2, ledger_stage="character_set") as slot:
        if slot.over: ...                     # a real stop: the caller decides (note + break, "skipped", or slot.raise_if_over("…"))
        task = slot.send(provider.submit, prompt, refs)
        slot.record()

`slot.over` is a reason or None; `slot.warning` a warning or None. The gate itself never raises on a refusal — each caller keeps its
own behaviour; slot.raise_if_over raises SpendRefused (a ValueError, caught by the dashboard's act()) or PipelinePaused.
"""
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from . import budget, cost, money_policy, project_budget
from .pipeline import PipelinePaused
from .providers import ProviderError

_DEFAULT = object()
BUDGET_STAGE = {"image": "images", "video": "videos", "audio": None}       # audio has no USD price: capped by count only
UNIT = {"image": "image", "video": "second", "audio": "item"}
PAUSED = "dự án đang TẠM DỪNG — không gửi việc tốn tiền; bỏ tạm dừng dự án rồi chạy lại"


class SpendRefused(ValueError):
    """A paid send refused by the money gate (a ValueError so dashboard/common.ERRORS and act() show it)."""


class Slot:
    def __init__(self, conn, kind: str, provider_name: str, project_id: Optional[int], model: Optional[str], tier: Optional[str],
                 units: float, ledger_stage: Optional[str]):
        self.conn, self.kind, self.provider_name, self.project_id = conn, kind, provider_name, project_id
        self.model, self.tier, self.units, self.ledger_stage = model, tier, units, ledger_stage
        self.over: Optional[str] = None
        self.warning: Optional[str] = None             # S14.16: the caps warn — the send goes (money_policy)
        self.warnings: List[str] = []
        self.estimate: Optional[Dict] = None           # money_policy.estimate of this send (usd, how, missing)
        self.paused = False
        self.sent = 0
        self.recorded = 0

    def raise_if_over(self, what: str = "") -> None:
        if not self.over:
            return
        if self.paused:
            raise PipelinePaused(f"{what}: {self.over}" if what else self.over)
        raise SpendRefused(f"{what}: {self.over}" if what else self.over)

    def send(self, fn: Callable[..., Any], *args, **kwargs) -> Any:
        """Call the provider's submit. Refused slot → SpendRefused (nothing sent). 'out_of_credit' → the service is halted."""
        if self.over:
            self.raise_if_over()
        try:
            out = fn(*args, **kwargs)
        except ProviderError as e:
            if e.code == "out_of_credit":
                budget.halt(self.conn, self.provider_name, str(e))
            raise
        self.sent += 1
        return out

    def record(self, quantity: Optional[float] = None, *, model: Optional[str] = None, tier: Optional[str] = None,
               job_id: Optional[int] = None) -> None:
        """The ledger row of one send (quantity: 1 picture / 1 audio, or the clip's seconds = units)."""
        if quantity is None:
            quantity = self.units if self.kind == "video" else 1
        cost.record_usage(self.conn, job_id, self.kind, self.provider_name, model or self.model or "unknown",
                          tier or self.tier or "default", quantity, UNIT[self.kind], project_id=self.project_id,
                          stage=self.ledger_stage)
        self.recorded += 1


def _paused(conn, project_id: Optional[int]) -> bool:
    if project_id is None:
        return False
    row = conn.execute("SELECT paused FROM projects WHERE id=?", (project_id,)).fetchone()
    return bool(row and row["paused"])


def _paused_text(conn, kind: str, project_id: int, model: Optional[str], tier: Optional[str], units: float) -> str:
    """A real stop says its numbers (S14.16): the project's money spent, its planned amount, the send stopped, how to open."""
    try:
        spent = sum(project_budget.spent_by_stage(conn, project_id).values())
        plan = project_budget.planned(conn, project_id)
        est = money_policy.estimate(kind, model, tier, units)["usd"]
        what = {"image": "ảnh", "video": "clip", "audio": "âm thanh"}.get(kind, kind)
        return (f"⛔ CHẶN: {PAUSED} (đã chi ≈ ${spent:.2f}" + (f", mức dự tính ${plan:.2f}" if plan is not None else "")
                + f"; lượt bị chặn: {what} {model or ''}" + (f" ≈ ${est:.2f} (ước tính)" if est is not None else "") + ")")
    except Exception:  # noqa: BLE001 - the stop itself must still be said
        return PAUSED


def _price(kind: str, model: Optional[str], tier: Optional[str], units: float) -> Optional[float]:
    """This send's price, estimated HIGH when the table does not know the model / tier (money_policy.estimate)."""
    return money_policy.estimate(kind, model, tier, units)["usd"]


def assess(conn, kind: str, provider_name: str, project_id: Optional[int] = None, model: Optional[str] = None,
           tier: Optional[str] = None, units: float = 1, budget_stage: Optional[str] = None) -> Tuple[Optional[str], List[str], Dict]:
    """(stop reason or None, warnings, estimate) of one send — without the lock. Stop = only a service out of credit (the paused
    project is checked by `spend`). Simulated providers (mock*) cost nothing: no stop, no warning."""
    name = str(provider_name or "")
    est = money_policy.estimate(kind, model, tier, units)
    if name.startswith("mock"):
        return None, [], est
    if kind == "image":
        stop = budget.check_image(conn, name, model, count=max(1, int(round(units))))
        warn = budget.warn_image(conn, name, model, count=max(1, int(round(units))))
    elif kind == "video":
        stop = budget.check_video(conn, name, model or "", tier or "", units)
        warn = budget.warn_video(conn, name, model or "", tier or "", units)
    else:
        stop = budget.check_audio(conn, name)
        warn = budget.warn_audio(conn, name)
    if stop:
        return stop, [], est
    warns = [warn] if warn else []
    if project_id is not None and budget_stage:
        pw = project_budget.warning(conn, project_id, budget_stage, est["usd"])
        if pw:
            warns.append(pw)
    if project_id is not None:                    # 08/10 phương án 1: phần trích riêng của dự án (chỉ cảnh báo)
        from . import project_reserve
        rw = project_reserve.warning(conn, project_id, est["usd"])
        if rw:
            warns.append(rw)
    if est.get("missing") and kind != "audio" and not any(est["missing"] in w for w in warns):
        warns.append(f"⚠ thiếu giá: {est['missing']} — {est['note']} — VẪN GỬI (thêm giá ở ⚙ → 💵 Tiền → 💲 Bảng giá)")
    return None, warns, est


def reason(conn, kind: str, provider_name: str, project_id: Optional[int] = None, model: Optional[str] = None,
           tier: Optional[str] = None, units: float = 1, budget_stage: Optional[str] = None) -> Optional[str]:
    """Why this send must not go (a real stop: the service is out of credit), else None. Warnings: see `assess`."""
    return assess(conn, kind, provider_name, project_id, model, tier, units, budget_stage)[0]


def warn(conn, warnings: List[str], *, stage: str, project_id: Optional[int] = None, job_id: Optional[int] = None,
         scene_id: Optional[int] = None) -> Optional[str]:
    """Write the warnings of one send to diag (money_policy.note, at most once every few minutes per kind) → the joined text or None."""
    if not warnings:
        return None
    text = " | ".join(warnings)
    money_policy.note(conn, text, stage=stage, project_id=project_id, job_id=job_id, scene_id=scene_id,
                      key=f"{stage}:{project_id or '-'}")
    return text


@contextmanager
def spend(conn, kind: str, provider_name: str, *, project_id: Optional[int] = None, model: Optional[str] = None,
          tier: Optional[str] = None, units: float = 1, budget_stage: Any = _DEFAULT,
          ledger_stage: Optional[str] = None) -> Iterator[Slot]:
    """Hold budget.SPEND_LOCK, check, yield a Slot (slot.over = a real stop or None, slot.warning = a money warning or None)."""
    if kind not in UNIT:
        raise ValueError(f"spend_gate: loại '{kind}' không hỗ trợ (Claude đi qua llm_runner)")
    stage = BUDGET_STAGE[kind] if budget_stage is _DEFAULT else budget_stage
    if stage is not None and stage not in project_budget.STAGES:
        # a ledger label passed as a budget stage would read cap 0 and refuse every call of a locked project
        raise ValueError(f"spend_gate: budget_stage '{stage}' không phải khâu ngân sách ({', '.join(project_budget.STAGES)})")
    with budget.SPEND_LOCK:
        slot = Slot(conn, kind, provider_name, project_id, model, tier, units, ledger_stage)
        if _paused(conn, project_id):
            slot.over, slot.paused = _paused_text(conn, kind, project_id, model, tier, units), True
        else:
            slot.over, slot.warnings, slot.estimate = assess(conn, kind, provider_name, project_id, model, tier, units, stage)
            slot.warning = warn(conn, slot.warnings, stage={"image": "image", "video": "video"}.get(kind, "music"),
                                project_id=project_id)
        try:
            yield slot
        finally:
            for _ in range(slot.sent - slot.recorded):           # a paid send is never left out of the ledger
                slot.record()
