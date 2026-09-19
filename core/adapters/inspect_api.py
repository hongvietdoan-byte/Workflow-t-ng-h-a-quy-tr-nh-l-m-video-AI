"""Read-only inspection of the real APIs: what fields do they return, is any cost/credit info exposed,
and how much has been used? Creates nothing, costs nothing, prints no tokens/prompts/URLs.

    py -m core.adapters.inspect_api            # field names + any cost-like fields
    py -m core.adapters.inspect_api --usage    # usage summary of your Clip AI task history
"""
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from ..providers import ProviderError
from .clipai import PATH_LIST, ClipAIVideoProvider
from .deepix import DeepixImageProvider

PATH_DEEPIX_LIST = "/api/image-generator/message-list"
COST_KEY = re.compile(r"cost|credit|price|fee|balance|point|consum|charge|spend|quota", re.I)
_TASK_STATUS = {0: "submitted", 1: "processing", 2: "succeed", 3: "failed", 4: "pending"}


def _deepix_items(data) -> List[dict]:
    node = data or {}
    for key in ("data", "items", "list"):
        if isinstance(node, dict) and key in node:
            node = node[key]
    if isinstance(node, dict):
        node = node.get("items") or []
    return node if isinstance(node, list) else []


def describe_item(item: dict) -> Dict[str, object]:
    """Field names with their value type; values are shown only for cost-like keys."""
    out = {}
    for key, value in item.items():
        if COST_KEY.search(key):
            out[key] = f"{type(value).__name__} = {value!r}"
        else:
            out[key] = type(value).__name__
    return out


def cost_fields(item: dict) -> List[str]:
    return [k for k in item if COST_KEY.search(k)]


def usage_summary(rows: List[dict]) -> Dict[str, object]:
    by_model: Dict[str, dict] = defaultdict(lambda: {"tasks": 0, "seconds": 0})
    status = Counter()
    for row in rows:
        model = str(row.get("model_name") or "unknown")
        by_model[model]["tasks"] += 1
        try:
            by_model[model]["seconds"] += float(row.get("duration") or 0)
        except (TypeError, ValueError):
            pass
        status[_TASK_STATUS.get(row.get("task_status"), str(row.get("task_status")))] += 1
    return {"tasks": len(rows), "by_model": dict(by_model), "status": dict(status)}


def fetch_video_rows(provider: ClipAIVideoProvider, pages: int = 12, page_size: int = 50) -> List[dict]:
    rows: List[dict] = []
    for page in range(1, pages + 1):
        data = provider.client.get(PATH_LIST, {"page": page, "pageSize": page_size, "task_type": 0, "order_by_desc": 1})
        batch = (data or {}).get("data") or []
        rows += batch
        if len(batch) < page_size:
            break
    return rows


def main(argv: Optional[list] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        clip = ClipAIVideoProvider.from_env()
        deepix = DeepixImageProvider.from_env()
        first = (clip.client.get(PATH_LIST, {"page": 1, "pageSize": 3, "task_type": 0, "order_by_desc": 1}) or {})
        rows = first.get("data") or []
        print("Clip AI video-list fields:")
        if rows:
            for key, kind in describe_item(rows[0]).items():
                print(f"  - {key}: {kind}")
        flagged = sorted({k for r in rows for k in cost_fields(r)})
        print("Clip AI cost-like fields:", flagged or "none exposed")
        items = _deepix_items(deepix.client.get(PATH_DEEPIX_LIST, {"page": 1, "page_size": 3, "days": 30}))
        print("Deepix message-list fields:")
        if items:
            for key, kind in describe_item(items[0]).items():
                print(f"  - {key}: {kind}")
        print("Deepix cost-like fields:", sorted({k for r in items for k in cost_fields(r)}) or "none exposed")
        if "--usage" in argv:
            summary = usage_summary(fetch_video_rows(clip))
            print(f"\nClip AI usage across {summary['tasks']} recent tasks:")
            for model, stats in sorted(summary["by_model"].items()):
                print(f"  {model}: {stats['tasks']} tasks, {stats['seconds']:.0f} seconds of video")
            print("  status:", summary["status"])
    except ProviderError as e:
        print(f"FAILED ({e.code}): {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
