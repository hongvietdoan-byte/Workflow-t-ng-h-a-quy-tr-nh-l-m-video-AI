"""Read-only connectivity check for the real providers (does NOT create tasks, costs nothing).

    py -m core.adapters.check

Reads CLIPAI_TOKEN / DEEPIX_TOKEN from the environment and calls list endpoints only.
The token is never printed.
"""
import sys
from typing import List, Tuple

from ..providers import ProviderError
import os

from .clipai import PATH_LIST, ClipAIVideoProvider
from .http import describe_token
from .deepix import DeepixImageProvider

PATH_DEEPIX_LIST = "/api/image-generator/message-list"


def run(clipai=None, deepix=None) -> List[Tuple[str, bool, str]]:
    results = []
    try:
        provider = clipai or ClipAIVideoProvider.from_env()
        data = provider.client.get(PATH_LIST, {"page": 1, "pageSize": 1, "task_type": 0, "order_by_desc": 1})
        results.append(("Clip AI", True, f"reachable, token accepted ({(data or {}).get('count', '?')} tasks on record)"))
    except ProviderError as e:
        results.append(("Clip AI", False, str(e)))
    try:
        provider = deepix or DeepixImageProvider.from_env()
        provider.client.get(PATH_DEEPIX_LIST, {"page": 1, "page_size": 1, "days": 30})
        results.append(("Deepix", True, "reachable, token accepted"))
    except ProviderError as e:
        results.append(("Deepix", False, str(e)))
    return results


def diagnose() -> None:
    """Print the shape of each token (length and problems only; the token itself is never shown)."""
    for var in ("CLIPAI_TOKEN", "DEEPIX_TOKEN"):
        raw = os.environ.get(var, "")
        stripped = raw.strip()
        problems = describe_token(stripped)
        print(f"{var}: length={len(raw)} (after trim {len(stripped)}), "
              + ("looks fine" if stripped and not problems else ", ".join(problems) or "EMPTY"))


def load_dashboard_env(path: str = "dashboard.env") -> None:
    """The non-secret settings the launcher would load (LLM_PROVIDER, IMAGE_PROVIDER...); values already set in the environment win."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"'))
    except OSError:
        pass


def check_llm(client=None) -> Tuple[str, bool, str]:
    """Ask Claude (API key or Claude Code on this PC) for one word. Spends a few tokens, so it only runs with --llm."""
    from .. import llm_runner
    try:
        client = client or llm_runner.client_from_env()
        if client is None:
            return ("Claude", False, "chưa cấu hình (đặt ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli)")
        reply = client.complete("Trả lời đúng một từ: OK")
        return ("Claude (" + getattr(client, "name", "?") + ")", True, f"trả lời được: {reply.text.strip()[:40]!r}")
    except llm_runner.LlmError as e:
        return ("Claude", False, str(e))


def main() -> int:
    load_dashboard_env()
    diagnose()
    ok_all = True
    results = run()
    if "--llm" in sys.argv:
        results.append(check_llm())
    for name, ok, message in results:
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {message}")
        ok_all = ok_all and ok
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
