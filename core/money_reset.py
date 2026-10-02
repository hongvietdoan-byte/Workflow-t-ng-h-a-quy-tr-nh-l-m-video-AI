"""Owner-only reset of the starting point ("mốc") of the money bars. Nothing is deleted: usage_events / llm_calls keep every row, a bar
just counts from a new point.

  trial    budget.restart: the test round counts from now (cap kept)
  claude   budget.restart_llm: the Claude API cap counts from now
  user     a baseline time for one person (team.user_baseline) → their monthly bar counts from it
  project  a per-stage baseline in the project's budget (project_budget.spent_by_stage subtracts it) — the only bar that loosens a
           hard lock, so it is also kept in the budget's `resets` history

Every reset is written to the audit log and to `money_reset_last:<bar>[:<key>]` (shown as "Đặt lại lần cuối")."""
import json
from datetime import datetime, timezone
from typing import Dict, Optional

from . import auth, budget, project_budget, team

BARS = {"trial": "Thanh thử nghiệm (tổng tiền cả đợt)", "claude": "Thanh Claude API", "user": "Thanh tiền theo người",
        "project": "Thanh ngân sách dự án"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get(actor, name: str):
    return actor.get(name) if isinstance(actor, dict) else getattr(actor, name, None)


def _last_key(bar: str, key=None) -> str:
    return f"money_reset_last:{bar}" + (f":{str(key).strip().lower()}" if key not in (None, "") else "")


def last(conn, bar: str, key=None) -> Optional[Dict]:
    """{at, who, why} of the last reset of this bar (key = e-mail or project id), or None."""
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (_last_key(bar, key),)).fetchone()
    try:
        return json.loads(row[0]) if row else None
    except ValueError:
        return None


def _put(conn, key: str, value: str) -> None:
    conn.execute("INSERT INTO app_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()


def _put_last(conn, bar: str, key, who: str, why: str, at: str) -> None:
    _put(conn, _last_key(bar, key), json.dumps({"at": at, "who": who, "why": why}, ensure_ascii=False))


def user_bar(conn, email: str) -> Dict:
    """The monthly bar of one person as the Team screen shows it: {email, month_usd (30 days, from their reset point), limit (soft, warning
    only), since (their reset point or None)}."""
    mail = str(email or "").strip().lower()
    return {"email": mail, "month_usd": round(team.month_spend(conn, mail), 4), "limit": team.get_limit(conn, mail),
            "since": team.user_baseline(conn, mail)}


def reset(conn, actor, bars, reason: str, *, usd: Optional[float] = None, llm_usd: Optional[float] = None,
          email: Optional[str] = None, project_id: Optional[int] = None) -> Dict:
    """Move the starting point of the chosen bars to now. Only the Owner; a reason is required. Returns {bar: what was set}."""
    if _get(actor, "role") != "owner":
        raise auth.AuthError("Chỉ Owner được đặt lại thanh tiền")
    why = str(reason or "").strip()
    if not why:
        raise ValueError("đặt lại thanh tiền phải có lý do")
    if not isinstance(bars, (list, tuple)):
        raise ValueError("bars phải là danh sách thanh")
    bars = list(dict.fromkeys(bars))
    if not bars:
        raise ValueError("chưa chọn thanh nào")
    for b in bars:
        if b not in BARS:
            raise ValueError(f"không có thanh '{b}'")
    mail = str(email or "").strip().lower()
    if "user" in bars and not mail:
        raise ValueError("đặt lại thanh theo người cần e-mail")
    pdata = None
    if "project" in bars:
        if project_id is None:
            raise ValueError("đặt lại thanh dự án cần project_id")
        pdata = project_budget.get(conn, int(project_id))
        if not pdata:
            raise ValueError("dự án chưa có ngân sách")
    who = str(_get(actor, "email") or "?")
    at = _now()
    done: Dict = {}
    if "trial" in bars:
        b = budget.restart(conn, usd)
        done["trial"] = {"since": b.get("since"), "usd": b.get("usd")}
        _put_last(conn, "trial", None, who, why, at)
    if "claude" in bars:
        b = budget.restart_llm(conn, llm_usd if llm_usd is not None else budget.get(conn).get("llm_usd"))
        done["claude"] = {"llm_since": b.get("llm_since"), "llm_usd": b.get("llm_usd")}
        _put_last(conn, "claude", None, who, why, at)
    if "user" in bars:
        before = team.month_spend(conn, mail)
        _put(conn, team._baseline_key(mail), at)
        done["user"] = {"email": mail, "since": at, "before_usd": round(before, 4), "after_usd": round(team.month_spend(conn, mail), 4)}
        _put_last(conn, "user", mail, who, why, at)
    if "project" in bars:
        pid = int(project_id)
        pdata["baseline"] = project_budget.ledger_by_stage(conn, pid)
        pdata["baseline_at"] = at
        pdata.setdefault("resets", []).append({"at": at, "who": who, "why": why})
        project_budget._save(conn, pid, pdata)
        done["project"] = {"project_id": pid, "baseline": pdata["baseline"], "since": at}
        _put_last(conn, "project", pid, who, why, at)
    auth.audit(conn, who, "reset_money", f"{bars} {why}")
    return done
