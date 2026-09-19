"""Read-only connectivity check for the real providers (does NOT create tasks, costs nothing).

    py -m core.adapters.check

Reads CLIPAI_TOKEN / DEEPIX_TOKEN from the environment and calls list endpoints only.
The token is never printed.
"""
import sys
from typing import List, Tuple

from ..providers import ProviderError
from .clipai import PATH_LIST, ClipAIVideoProvider
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


def main() -> int:
    ok_all = True
    for name, ok, message in run():
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {message}")
        ok_all = ok_all and ok
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
