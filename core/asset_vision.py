"""Reading the informational detail in a resource's picture into text.

A character's design sheet (turn-around, expressions, color palette, close-ups of accessories, all on one canvas) carries a lot of useful
detail — exactly the kind of thing core/assets.py explains it must NOT hand to an image-to-image generator: the generator does not
"read" the sheet as a reference document, it copies pixels, and with several characters in one scene it copies the wrong pixels onto the
wrong person (see `assets.is_composite_sheet`, `assets.best_references`).

Text does not get blended that way. So instead of throwing the sheet's detail away, Claude looks at it once per resource and writes what
it sees (hair, outfit colors, accessories, build) as a short paragraph. That text is stored in the resource's own description, which the
Director prompt already includes for every resource attached to a project (`assets.context_text`) — so the detail still reaches the
image prompt, just through words instead of pixels, where it can't be mis-copied onto the wrong person.

Runs in the background, one game's library at a time, and only for resources that do not have this text yet (a person's own edits to the
description are kept; this appends a marked, replaceable block, like core/ff_site.py does for the website text).
"""
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from . import assets, diag, llm_runner
from .db import connect

MARK = "[AI đọc ảnh]"
MAX_IMAGES = 4
PAUSE = 0.3                            # seconds between assets: gentle on rate limits, and lets the page stay responsive

_lock = threading.Lock()
_active: set = set()
_errors: Dict[str, Tuple[str, float]] = {}
_progress: Dict[str, Dict] = {}
RETRY_AFTER = 300


def active(game: str) -> bool:
    return game in _active


def last_error(game: str) -> Optional[str]:
    entry = _errors.get(game)
    if entry and time.time() - entry[1] < RETRY_AFTER:
        return entry[0]
    return None


def clear_error(game: str) -> None:
    _errors.pop(game, None)


def progress(game: str) -> Dict:
    return _progress.get(game, {"done": 0, "total": 0})


def _eligible(a: Dict) -> bool:
    return a["kind"] in ("character", "pet") and a["images"] and MARK not in (a["description"] or "")


def pending(conn, game: str) -> int:
    """Library resources (character/pet, with pictures) that have not been read by Claude yet."""
    # one query, no pictures read from disk (02/10: the full list of entries was built just to count them; at 10× the library that took 0.5 s)
    row = conn.execute("SELECT COUNT(*) FROM assets a WHERE a.project_id IS NULL AND a.game=? AND a.kind IN ('character', 'pet')"
                       " AND instr(COALESCE(a.description, ''), ?) = 0"
                       " AND EXISTS (SELECT 1 FROM asset_images i WHERE i.asset_id=a.id AND i.status='approved')", (game, MARK)).fetchone()
    return int(row[0])


def can_run(conn, game: str, client_factory: Optional[Callable] = None) -> bool:
    if active(game) or last_error(game) or not pending(conn, game):
        return False
    try:
        return (client_factory or llm_runner.ledger_factory(llm_runner.db_file(conn)))() is not None
    except llm_runner.LlmError:
        return False


def _pick_images(asset: Dict) -> List[Dict]:
    """The composite sheet if there is one (it holds the palette/accessory detail worth reading), plus a couple of single-figure
    shots (a different angle helps describe the back/side of an outfit)."""
    images = asset["images"]
    sheets = [i for i in images if assets.is_composite_sheet(i["path"])]
    singles = [i for i in images if i not in sheets]
    picked = (sheets[:1] + singles[:MAX_IMAGES - 1]) if sheets else singles[:MAX_IMAGES]
    return picked or images[:MAX_IMAGES]


def build_prompt(asset: Dict) -> str:
    kind_word = {"character": "nhân vật", "pet": "thú cưng"}.get(asset["kind"], "đối tượng")
    return (f"Đây là ảnh tham khảo (có thể là một bảng thiết kế nhiều góc/tư thế) của {kind_word} \"{asset['name']}\" trong game. Nhìn kỹ và viết "
            "một đoạn MÔ TẢ NGOẠI HÌNH ngắn gọn, cụ thể, để một AI vẽ ảnh khác có thể vẽ lại đúng người này chỉ bằng chữ, không cần nhìn ảnh: "
            "màu và kiểu tóc, màu và kiểu trang phục (áo, quần/váy, giày), phụ kiện đặc trưng (vũ khí, mũ, kính, hình xăm, dấu hiệu riêng), "
            "vóc dáng, màu da/màu lông. Viết bằng tiếng Việt, súc tích (3-5 câu), chỉ tả những gì nhìn thấy, không suy đoán tính cách hay cốt truyện.")


def describe(client, asset: Dict) -> str:
    images = [(f"Ảnh {i}:", img["path"]) for i, img in enumerate(_pick_images(asset), 1)]
    if not images:
        raise llm_runner.LlmError("mục này chưa có ảnh", code="no_image")
    with llm_runner.tagged("asset_vision"):
        reply = client.complete(build_prompt(asset), images)
    text = reply.text.strip()
    if not text:
        raise llm_runner.LlmError("Claude không trả lời gì", code="empty")
    return text


def _with_block(description: str, text: str) -> str:
    return assets.replace_block(description, MARK, text)


def sync_one(conn, client, asset_id: int) -> bool:
    """Read one resource's pictures and store the description. False when it had nothing to read."""
    asset = assets.get(conn, asset_id)
    if asset is None or not asset["images"]:
        return False
    text = describe(client, asset)
    assets.update(conn, asset_id, asset["name"], asset["aliases"], _with_block(asset["description"], text))
    return True


def start(db_path: str, game: str, client_factory: Optional[Callable] = None) -> bool:
    """Start reading this game's unread resources in the background. True if a run was started."""
    conn = connect(db_path)
    client_factory = client_factory or llm_runner.ledger_factory(db_path)      # every Claude call -> cost ledger + Claude cap
    with _lock:
        if not can_run(conn, game, client_factory):
            return False
        _active.add(game)
    threading.Thread(target=_work, args=(db_path, game, client_factory), daemon=True, name=f"asset-vision-{game}").start()
    return True


def _work(db_path: str, game: str, client_factory: Callable) -> None:
    conn = None
    try:
        conn = connect(db_path)
        client = client_factory()
        if client is None:
            _errors[game] = ("chưa có Claude (ANTHROPIC_API_KEY hoặc LLM_PROVIDER=claude_cli)", time.time())
            return
        todo = [a["id"] for a in assets.list_assets(conn, game, None, None, shared_only=True) if _eligible(a)]
        _progress[game] = {"done": 0, "total": len(todo)}
        for asset_id in todo:
            try:
                sync_one(conn, client, asset_id)
                _progress[game]["done"] += 1
            except llm_runner.LlmError as e:
                if e.code in ("auth", "config", "timeout", "cli_error", "rate_limit", "server_error"):
                    _errors[game] = (str(e), time.time())
                    return
                diag.record(conn, "system", "warn", f"đọc ảnh tài nguyên lỗi (mục #{asset_id}): {e}", "asset_vision")
            time.sleep(PAUSE)
    except Exception as e:  # noqa: BLE001 - a background read must never die silently
        _errors[game] = (f"{type(e).__name__}: {e}", time.time())
    finally:
        with _lock:
            _active.discard(game)
