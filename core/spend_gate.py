"""One money gate for a paid send outside the runners (S14.1 A1a, docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md mục 3.1).

Before: every place that paid for a picture / clip outside ImageRunner / VideoRunner wrote its own checks, and some forgot one —
the character set (core.costume) checked nothing, the end frame / establishing picture / Kling multi-shot try skipped the project's
locked budget. The gate puts the existing checks (it re-uses them, no new money logic) in one place:

  * the project is paused → nothing is sent (the same rule as Pipeline.start);
  * budget.check_image / check_video / check_audio: the trial round's caps, a service out of credit (budget.halted), a broken price
    table (budget.pricing_problem), a model without a price while the trial is on;
  * project_budget.check: the project's locked budget for `budget_stage` (images / videos / claude_*) — a price the table does not
    know is passed as None and refused when the project is locked (T6);
  * all of it under budget.SPEND_LOCK, from the check to the ledger row (two threads must not both pass the cap);
  * slot.send(fn, …): a provider error 'out_of_credit' halts that service (budget.halt), the error goes on to the caller;
  * slot.record(): one usage_events row right after each send, labelled `ledger_stage` (character_set, end_frame, establishing…);
    a send that failed is not recorded; a send the caller forgot to record is recorded when the block ends (never left out).

Usage:
    with spend_gate.spend(conn, "image", provider.name, project_id=pid, model=m, tier=t, units=2, ledger_stage="character_set") as slot:
        if slot.over: ...                     # the caller decides: note + break, return "skipped", or slot.raise_if_over("…")
        task = slot.send(provider.submit, prompt, refs)
        slot.record()

`slot.over` is a reason (Vietnamese, says where to fix it) or None. The gate itself never raises on a refusal — each caller keeps its
own behaviour; slot.raise_if_over raises SpendRefused (a ValueError, caught by the dashboard's act()) or PipelinePaused.
"""
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from . import budget, cost, project_budget
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


def _price(kind: str, model: Optional[str], tier: Optional[str], units: float) -> Optional[float]:
    pricing = cost.load_pricing()
    if kind == "image":
        one = cost._number(pricing.get("per_image", {}).get(model)) if model else None
        return None if one is None else one * units
    if kind == "video":
        return cost.clip_price(pricing, model, tier, units) if model else None
    return None


def reason(conn, kind: str, provider_name: str, project_id: Optional[int] = None, model: Optional[str] = None,
           tier: Optional[str] = None, units: float = 1, budget_stage: Optional[str] = None) -> Optional[str]:
    """Why this send must not go (the gate's checks, without the lock), else None. Simulated providers (mock*) cost nothing."""
    name = str(provider_name or "")
    if name.startswith("mock"):
        return None
    if kind == "image":
        why = budget.check_image(conn, name, model, count=max(1, int(round(units))))
    elif kind == "video":
        why = budget.check_video(conn, name, model or "", tier or "", units)     # no model → no price → refused while the trial is on
    else:
        why = budget.check_audio(conn, name)
    if why:
        return why
    if project_id is not None and budget_stage:
        return project_budget.check(conn, project_id, budget_stage, _price(kind, model, tier, units))
    return None


@contextmanager
def spend(conn, kind: str, provider_name: str, *, project_id: Optional[int] = None, model: Optional[str] = None,
          tier: Optional[str] = None, units: float = 1, budget_stage: Any = _DEFAULT,
          ledger_stage: Optional[str] = None) -> Iterator[Slot]:
    """Hold budget.SPEND_LOCK, check, yield a Slot (slot.over = the reason or None). See the module text."""
    if kind not in UNIT:
        raise ValueError(f"spend_gate: loại '{kind}' không hỗ trợ (Claude đi qua llm_runner)")
    stage = BUDGET_STAGE[kind] if budget_stage is _DEFAULT else budget_stage
    if stage is not None and stage not in project_budget.STAGES:
        # a ledger label passed as a budget stage would read cap 0 and refuse every call of a locked project
        raise ValueError(f"spend_gate: budget_stage '{stage}' không phải khâu ngân sách ({', '.join(project_budget.STAGES)})")
    with budget.SPEND_LOCK:
        slot = Slot(conn, kind, provider_name, project_id, model, tier, units, ledger_stage)
        if _paused(conn, project_id):
            slot.over, slot.paused = PAUSED, True
        else:
            slot.over = reason(conn, kind, provider_name, project_id, model, tier, units, stage)
        try:
            yield slot
        finally:
            for _ in range(slot.sent - slot.recorded):           # a paid send is never left out of the ledger
                slot.record()
