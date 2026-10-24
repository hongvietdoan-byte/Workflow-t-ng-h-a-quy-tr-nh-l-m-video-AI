"""V3.1 M4.7 / C3-4 — nhật ký ngoại lệ QC do người dùng ghi.

Migration chỉ chạy khi được gọi tường minh; không gắn vào khởi tạo/mở DB. Mỗi lần ghi tạo revision mới. API chỉ nhận token phiên đăng nhập
được `core.auth` xác minh, không nhận email/role do caller khai báo; không có đường CLI/Claude/tool để tự tạo phiên hoặc ghi ngoại lệ.
"""
import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from . import access, auth, features

FLAG = "qc_overrides"
TABLE = "overrides"
Q6C_ANCHOR_ERROR = "Q6C_MAIN_CHARACTER_ANCHOR"
# EP may tune Q6(c) role policy here without changing BYĐ v2 or its schema.
Q6C_MAIN_ROLE = "chinh"
Q6C_SECONDARY_ROLE = "phu"
Q6C_EXCLUDED_ROLE = "khong_duoc_co"
_TARGET_KIND = re.compile(r"^[a-z][a-z0-9_.-]{0,31}$")
_EXPECTED_COLUMNS = {
    "id", "project_id", "target_kind", "target_ref", "error_code", "actor_email", "revision", "reason", "evidence_json", "created_at",
}

DDL = """CREATE TABLE IF NOT EXISTS overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    target_kind TEXT NOT NULL CHECK (length(trim(target_kind)) > 0),
    target_ref TEXT NOT NULL CHECK (length(trim(target_ref)) > 0),
    error_code TEXT NOT NULL CHECK (length(trim(error_code)) > 0),
    actor_email TEXT NOT NULL CHECK (length(trim(actor_email)) > 0),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    reason TEXT NOT NULL CHECK (length(trim(reason)) >= 15),
    evidence_json TEXT NOT NULL CHECK (length(trim(evidence_json)) > 1),
    created_at TEXT NOT NULL,
    UNIQUE (project_id, target_kind, target_ref, revision)
)"""


class OverrideDisabled(RuntimeError):
    """Cờ ghi ngoại lệ đang tắt."""


class OverrideConflict(RuntimeError):
    """Ghi đồng thời bị SQLite từ chối; không tự ghi đè lịch sử."""


def enabled() -> bool:
    """Cờ mặc định TẮT; cờ thiếu cũng được coi là tắt."""
    try:
        return features.on(FLAG)
    except KeyError:
        return False


def has_table(conn) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    return row is not None


def _validate_schema(conn) -> None:
    """Từ chối bảng trùng tên nhưng thiếu các bất biến an toàn của C3-4."""
    info = {row[1]: row for row in conn.execute(f"PRAGMA table_info({TABLE})")}
    missing = _EXPECTED_COLUMNS - set(info)
    if missing:
        raise ValueError("bảng overrides tồn tại nhưng thiếu cột C3-4: " + ", ".join(sorted(missing)))
    expected_types = {
        "id": "INTEGER", "project_id": "INTEGER", "target_kind": "TEXT", "target_ref": "TEXT",
        "error_code": "TEXT", "actor_email": "TEXT", "revision": "INTEGER", "reason": "TEXT",
        "evidence_json": "TEXT", "created_at": "TEXT",
    }
    if any((info[name][2] or "").upper() != kind for name, kind in expected_types.items()):
        raise ValueError("schema overrides có kiểu cột không tương thích C3-4")
    if info["id"][5] != 1 or any(info[name][3] != 1 for name in _EXPECTED_COLUMNS - {"id"}):
        raise ValueError("schema overrides thiếu khóa chính hoặc NOT NULL bắt buộc")

    foreign_keys = conn.execute(f"PRAGMA foreign_key_list({TABLE})").fetchall()
    if not any(row["table"] == "projects" and row["from"] == "project_id"
               and row["to"] == "id" and row["on_delete"].upper() == "RESTRICT" for row in foreign_keys):
        raise ValueError("schema overrides thiếu khóa ngoại projects(id) ON DELETE RESTRICT")

    has_revision_unique = False
    for index in conn.execute(f"PRAGMA index_list({TABLE})").fetchall():
        if not index["unique"] or index["partial"]:
            continue
        columns = [row[2] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()]
        if columns == ["project_id", "target_kind", "target_ref", "revision"]:
            has_revision_unique = True
            break
    if not has_revision_unique:
        raise ValueError("schema overrides thiếu UNIQUE chống trùng revision")

    sql_row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
    sql = sql_row[0] if sql_row else ""
    sql = re.sub(r"/\*.*?\*/|--[^\r\n]*", "", sql, flags=re.DOTALL)
    sql = re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|\[[^\]]*\]", "", sql)
    normalized = re.sub(r"\s+", "", sql.upper())
    required_checks = (
        "CHECK(LENGTH(TRIM(TARGET_KIND))>0)", "CHECK(LENGTH(TRIM(TARGET_REF))>0)",
        "CHECK(LENGTH(TRIM(ERROR_CODE))>0)", "CHECK(LENGTH(TRIM(ACTOR_EMAIL))>0)",
        "CHECK(REVISION>=1)", "CHECK(LENGTH(TRIM(REASON))>=15)", "CHECK(LENGTH(TRIM(EVIDENCE_JSON))>1)",
    )
    if any(fragment not in normalized for fragment in required_checks):
        raise ValueError("schema overrides thiếu CHECK bảo vệ dữ liệu C3-4")


def _savepoint(conn, name: str) -> None:
    conn.execute(f"SAVEPOINT {name}")


def _rollback_savepoint(conn, name: str) -> None:
    try:
        conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
    finally:
        conn.execute(f"RELEASE SAVEPOINT {name}")


def migrate_up(conn) -> bool:
    """Tạo bảng + chỉ mục, có thể chạy lại an toàn; trả True nếu bảng mới được tạo.

    Không được gọi tự động khi mở Dashboard. Trên DB thật, C3-4 yêu cầu sao lưu trước và do phiên chính thực hiện.
    """
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'").fetchone():
        raise ValueError("C3-4 cần bảng projects của schema nền; không tự tạo schema nền")
    was_present = has_table(conn)
    savepoint = "m47b_overrides_up"
    _savepoint(conn, savepoint)
    try:
        conn.execute(DDL)
        _validate_schema(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_overrides_project_target ON overrides(project_id, target_kind, target_ref, revision)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_overrides_actor_time ON overrides(actor_email, created_at)")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception:
        _rollback_savepoint(conn, savepoint)
        raise
    return not was_present


def migrate_down(conn, force: bool = False) -> None:
    """Gỡ bảng bằng thao tác tường minh; từ chối làm mất lịch sử nếu chưa force sau sao lưu."""
    if not has_table(conn):
        return
    _validate_schema(conn)
    savepoint = "m47b_overrides_down"
    _savepoint(conn, savepoint)
    try:
        count = conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]
        if count and not force:
            raise ValueError(f"còn {count} dòng override — gỡ sẽ mất lịch sử; chỉ dùng force=True sau khi sao lưu")
        conn.execute("DROP TABLE overrides")
        conn.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception:
        _rollback_savepoint(conn, savepoint)
        raise


def _reason(value: str) -> str:
    text = " ".join((value or "").split())
    words = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
    if len(text) < 15 or len(words) < 3 or len({w.casefold() for w in words}) < 2:
        raise ValueError("Lý do ngoại lệ phải là câu có nghĩa, tối thiểu 15 ký tự")
    return text


def _evidence(value: Dict) -> str:
    if not isinstance(value, dict) or not value:
        raise ValueError("Cần đính kèm bằng chứng có cấu trúc, không chấp nhận mục trống")
    try:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Bằng chứng phải là dữ liệu JSON hợp lệ") from exc
    if len(serialized.encode("utf-8")) > 16_384:
        raise ValueError("Bằng chứng vượt giới hạn 16 KiB; hãy lưu tệp và ghi mã tham chiếu/hash")
    return serialized


def _human_editor(conn, project_id: int, session_token: Optional[str]) -> str:
    """Chỉ chấp nhận token phiên hợp lệ; không tin email/role do caller tự khai."""
    if not isinstance(session_token, str) or not session_token or len(session_token) > 256:
        raise access.AccessDenied("Cần phiên đăng nhập còn hiệu lực để ghi ngoại lệ QC; công cụ/hệ thống không được ghi.")
    identity = auth.identity(conn, session_token)
    if identity is None:
        raise access.AccessDenied("Cần phiên đăng nhập còn hiệu lực để ghi ngoại lệ QC; công cụ/hệ thống không được ghi.")
    access.require(conn, project_id, identity, "edit", "ghi ngoại lệ QC")
    return identity.email


def record(conn, *, project_id: int, target_kind: str, target_ref: str, error_code: str,
           session_token: Optional[str], reason: str, evidence: Dict) -> Dict:
    """Thêm một revision ngoại lệ."""
    return _record(conn, project_id=project_id, target_kind=target_kind, target_ref=target_ref,
                   error_code=error_code, session_token=session_token, reason=reason, evidence=evidence)


def record_with_effect(conn, *, effect: Callable[[object, Dict], None], project_id: int, target_kind: str,
                       target_ref: str, error_code: str, session_token: Optional[str], reason: str,
                       evidence: Dict) -> Dict:
    """Ghi audit và tác động CSDL liên quan trong cùng transaction.

    `effect` chỉ được ghi trên chính kết nối này; không được tự commit hoặc gọi dịch vụ ngoài. Nếu lỗi, cả hai ghi cùng rollback.
    """
    if not callable(effect):
        raise TypeError("effect phải là hàm ghi CSDL trong cùng transaction")
    return _record(conn, project_id=project_id, target_kind=target_kind, target_ref=target_ref,
                   error_code=error_code, session_token=session_token, reason=reason, evidence=evidence,
                   effect=effect)


def _record(conn, *, project_id: int, target_kind: str, target_ref: str, error_code: str,
            session_token: Optional[str], reason: str, evidence: Dict,
            effect: Optional[Callable[[object, Dict], None]] = None) -> Dict:
    """Thêm revision ngoại lệ sau khi kiểm cờ, danh tính đang hoạt động và quyền edit trên dự án.

    Mỗi lần gọi giữ nguyên dòng cũ. Hàm không tạo bảng/migration; thiếu migration là lỗi rõ ràng. Hàm cần kết nối không có giao dịch
    ngoài: tự lấy BEGIN IMMEDIATE để tuần tự hóa revision rồi tự commit; nếu caller đang giữ snapshot cũ thì từ chối để caller rollback/tải lại.
    """
    if not enabled():
        raise OverrideDisabled("Cờ ghi ngoại lệ QC đang tắt.")
    if not has_table(conn):
        raise RuntimeError("Chưa có bảng overrides; cần áp migration C3-4 sau khi sao lưu DB.")
    if type(project_id) is not int or project_id < 1:
        raise ValueError("project_id phải là số nguyên dương")
    kind = (target_kind or "").strip().lower()
    ref = (target_ref or "").strip()
    code = (error_code or "").strip()
    if not _TARGET_KIND.fullmatch(kind) or not ref or len(ref) > 200 or not code or len(code) > 100:
        raise ValueError("Cần mã loại mục tiêu, tham chiếu mục tiêu và mã lỗi hợp lệ")
    reason_text = _reason(reason)
    evidence_json = _evidence(evidence)

    if conn.in_transaction:
        raise OverrideConflict("Kết thúc hoặc rollback giao dịch hiện tại trước khi ghi ngoại lệ QC.")
    # Khóa ghi trước khi lấy MAX(revision), để hai kết nối cùng mục tiêu xếp hàng tuần tự.
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise OverrideConflict("CSDL đang có giao dịch ghi khác; hãy tải lại và thử lại.") from exc
        raise

    try:
        actor_email = _human_editor(conn, project_id, session_token)
        revision = conn.execute(
            "SELECT COALESCE(MAX(revision), 0) + 1 FROM overrides WHERE project_id=? AND target_kind=? AND target_ref=?",
            (project_id, kind, ref),
        ).fetchone()[0]
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO overrides(project_id,target_kind,target_ref,error_code,actor_email,revision,reason,evidence_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (project_id, kind, ref, code, actor_email, revision, reason_text, evidence_json, created_at),
        )
        row = conn.execute("SELECT * FROM overrides WHERE id=?", (cur.lastrowid,)).fetchone()
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        if effect is not None:
            effect(conn, result)
        try:
            conn.commit()
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        return result
    except sqlite3.IntegrityError as exc:
        if conn.in_transaction:
            conn.rollback()
        if getattr(exc, "sqlite_errorname", "") in {"SQLITE_CONSTRAINT_UNIQUE", "SQLITE_CONSTRAINT_PRIMARYKEY"}:
            raise OverrideConflict("Lịch sử ngoại lệ vừa được cập nhật đồng thời; hãy tải lại và thử lại.") from exc
        raise
    except sqlite3.OperationalError as exc:
        if conn.in_transaction:
            conn.rollback()
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            raise OverrideConflict("CSDL đang có giao dịch ghi khác; hãy tải lại và thử lại.") from exc
        raise
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def latest(conn, project_id: int, target_kind: str, target_ref: str) -> Optional[Dict]:
    """Trả revision gần nhất cho đúng mục tiêu; None nếu chưa ghi."""
    if not has_table(conn):
        return None
    row = conn.execute(
        "SELECT * FROM overrides WHERE project_id=? AND target_kind=? AND target_ref=? ORDER BY revision DESC LIMIT 1",
        (project_id, target_kind, target_ref),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["evidence"] = json.loads(result.pop("evidence_json"))
    return result


def _character_key(value) -> str:
    if not isinstance(value, str):
        return ""
    # Character identity must keep Vietnamese accents. ``fold`` is useful for search, but would make
    # names such as Cúi and Cũi collide in a safety gate.
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _q6c_same_name(left, right, asset_module):
    """Compare complete names, allowing unaccented input but never partial-name matches."""
    left_words = asset_module._said_words(left)
    right_words = asset_module._said_words(right)
    if left_words == right_words and left_words:
        return True
    left_folded = [asset_module.fold(word) for word in left_words]
    right_folded = [asset_module.fold(word) for word in right_words]
    return bool(
        left_words
        and len(left_words) == len(right_words)
        and (all(word == folded for word, folded in zip(left_words, left_folded))
             or all(word == folded for word, folded in zip(right_words, right_folded)))
        and left_folded == right_folded
    )


_Q6C_COMMON_SENTENCE_STARTS = {
    "ánh", "anh", "bà", "bên", "bỗng", "bởi", "bóng", "bước", "các", "cả", "cảnh", "cánh", "chạy",
    "chị", "chú", "cô", "cùng", "cúi", "cuối", "cửa", "dần", "dưới", "đám", "đầu", "đêm", "đi",
    "đến", "đứng", "đưa", "đúng", "em", "gã", "giữa", "hàng", "hắn", "hai", "họ", "hôm", "kẻ", "khi", "khẽ",
    "không", "kết", "khu", "làn", "lão", "lặng", "lúc", "màn", "mặt", "máy", "mỗi", "một", "ngay",
    "người", "ngoài", "những", "nhìn", "nếu", "nền", "nó", "ông", "phía", "rồi", "sau", "sáng",
    "sàn", "scene", "shot", "ta", "tất", "thế", "thấy", "thì", "tiếng", "tối", "trên", "trong", "trước",
    "từ", "từng", "tuy", "vài", "và", "vách", "vì", "với",
}
_Q6C_ACTION_VERBS = {
    "bắn", "bật", "bước", "bò", "biến", "cầm", "chạy", "chạm", "chặn", "chui", "cười", "cúi", "cứu",
    "đánh", "đập", "đặt", "đẩy", "đứng", "đi", "đưa", "gặp", "gọi", "giơ", "giúp", "gật", "hạ", "hét",
    "kéo", "khóc", "khựng", "lắc", "lao", "lấy", "lùi", "mang", "mở", "ngã", "ngồi", "nắm", "ném", "né",
    "nhảy", "nhìn", "nói", "ôm", "phá", "quay", "quỳ", "rẽ", "rơi", "rút", "thở", "tiến", "tìm", "tung",
    "trượt", "vẫy", "xoay", "ở",
}
_Q6C_ACTION_MODIFIERS = {
    "bắt đầu", "bất ngờ", "chậm", "chợt", "đang", "đã", "đột nhiên", "khẽ", "lặng lẽ", "liền", "lập tức",
    "ngay", "nhanh", "sắp", "tiếp tục", "vừa",
}


def _q6c_followed_by_action(tokens, index):
    cursor = index
    for _ in range(4):
        if cursor >= len(tokens):
            return False
        single = tokens[cursor].group(0).casefold()
        if single in _Q6C_ACTION_VERBS:
            return True
        if single in _Q6C_ACTION_MODIFIERS:
            cursor += 1
            continue
        if cursor + 1 < len(tokens):
            pair = " ".join(token.group(0).casefold() for token in tokens[cursor:cursor + 2])
            if pair in _Q6C_ACTION_VERBS:
                return True
            if pair in _Q6C_ACTION_MODIFIERS:
                cursor += 2
                continue
        return False
    return False


def _q6c_prose_names(text, script_parser, dialogue):
    """Find likely named subjects before action verbs; explicit cast/dialogue fields handle other names."""
    found = []
    token_pattern = re.compile(r"[^\W\d_][^\W\d_’'-]*", re.UNICODE)
    for row in (text or "").splitlines():
        if script_parser.is_heading(row):
            continue
        label, separator, _body = row.partition(":")
        if separator and dialogue.is_non_speaker(label.strip()):
            continue
        row = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", row).strip()
        tokens = list(token_pattern.finditer(row))
        index = 0
        while index < len(tokens):
            token = tokens[index].group(0)
            if token.casefold() in _Q6C_COMMON_SENTENCE_STARTS:
                index += 1
                continue
            if not token[0].isupper():
                index += 1
                continue
            end = index + 1
            while (end < len(tokens) and tokens[end].group(0)[0].isupper()
                   and row[tokens[end - 1].end():tokens[end].start()].isspace()):
                end += 1
            candidate = " ".join(match.group(0) for match in tokens[index:end])
            if _q6c_followed_by_action(tokens, end):
                found.append(candidate)
            index = end
    return found


def _q6c_add_names(value, output):
    """Append explicit character-name values from script/shot structures."""
    if isinstance(value, str):
        name = value.strip()
        if name:
            output.append(name)
    elif isinstance(value, dict):
        for key in ("name", "vat", "character", "speaker", "ai", "nguoi", "nhan_vat"):
            if key in value:
                _q6c_add_names(value[key], output)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _q6c_add_names(item, output)


def _q6c_add_text(value, output):
    """Append narrative text without treating arbitrary text as an explicit character name."""
    if isinstance(value, str):
        if value.strip():
            output.append(value)
    elif isinstance(value, dict):
        for key in ("text", "action", "hanh_dong", "description", "line", "content", "mo_ta", "noi_dung"):
            if key in value:
                _q6c_add_text(value[key], output)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _q6c_add_text(item, output)


def _q6c_script_inputs(payload):
    """Return explicit character names and narrative text from supported script/shot fields."""
    names, texts = [], []
    if not isinstance(payload, dict):
        return names, texts
    for key in ("characters", "character_names", "nhan_vat"):
        if key in payload:
            _q6c_add_names(payload[key], names)
    for key in ("text", "action", "description"):
        if key in payload:
            _q6c_add_text(payload[key], texts)
    for key in ("hanh_dong", "actions"):
        value = payload.get(key)
        if isinstance(value, (dict, list, tuple)):
            _q6c_add_names(value, names)
            _q6c_add_text(value, texts)
        elif isinstance(value, str):
            _q6c_add_text(value, texts)
    dialogue = payload.get("dialogue")
    if isinstance(dialogue, (dict, list, tuple)):
        rows = dialogue if isinstance(dialogue, (list, tuple)) else [dialogue]
        for row in rows:
            if isinstance(row, dict):
                for key in ("speaker", "character", "name"):
                    if key in row:
                        _q6c_add_names(row[key], names)
                for key in ("text", "line", "content"):
                    if key in row:
                        _q6c_add_text(row[key], texts)
            else:
                _q6c_add_text(row, texts)
    elif isinstance(dialogue, str):
        _q6c_add_text(dialogue, texts)
    return names, texts


def _q6c_has_kho_image(conn, character_name, character, project_assets, asset_module):
    """Check an explicit character reference first, then a matching attached Kho asset."""
    ref_asset_id = character.get("ref_asset_id")
    if ref_asset_id is not None:
        if ref_asset_id == 0:
            return False
        if type(ref_asset_id) is not int or ref_asset_id < 1:
            return False
        asset = asset_module.get(conn, ref_asset_id)
        return bool(asset and asset.get("kind") in ("character", "pet") and asset.get("images"))

    eligible = [asset for asset in project_assets
                if asset.get("kind") in ("character", "pet") and asset.get("images")]
    for asset in eligible:
        if any(_q6c_same_name(character_name, alias, asset_module) for alias in asset_module.names_of(asset)):
            return True
    # The reference-linking path also accepts a unique character asset whose first word is the
    # Bible name (e.g. "Kelly" -> "Kelly thức tỉnh"). Keep that behavior, but reject ambiguous
    # prefixes and keep the comparison accent-safe.
    if character.get("id") is None:
        return False
    character_words = asset_module._said_words(character_name)
    if not character_words:
        return False
    prefix_matches = [asset for asset in eligible
                      if (asset_words := asset_module._said_words(asset.get("name")))
                      and _q6c_same_name(character_words[0], asset_words[0], asset_module)]
    return len(prefix_matches) == 1


def character_anchor_gate(conn, project_id: int) -> Dict:
    """M4.7 Q6(c): require an approved anchor for project characters marked `chinh` in any BYĐ v2 shot.

    The result is read-only and caller-ready: `block` contains override target metadata, `warn` covers characters known only as
    secondary or without a declared main role, and `review` reports missing/unreadable BYĐ v2 or unmatched main cast names.
    Unmatched secondary cast names still warn. Overrides are bound to the current main-cast occurrences, so changed BYĐ findings
    need a new review. This gate is inert while M4.7 is off.
    """
    result = {"block": [], "review": [], "warn": [], "overridden": []}
    if not enabled():
        return result
    if type(project_id) is not int or project_id < 1:
        raise ValueError("project_id phải là số nguyên dương")

    from . import assets, dialogue, script_parser, shot_intent

    try:
        scenes = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx,id", (project_id,)).fetchall()
        characters = conn.execute(
            "SELECT id, name, anchor_approved, ref_asset_id "
            "FROM characters WHERE project_id=? ORDER BY id", (project_id,)
        ).fetchall()
    except sqlite3.Error as exc:
        result["review"].append(f"REVIEW Q6(c): không đọc được dữ liệu shot/nhân vật ({type(exc).__name__}); chưa chặn vì thiếu BYĐ v2.")
        return result

    by_key = {}
    ambiguous = set()
    for character in characters:
        key = _character_key(character["name"])
        if not key:
            result["review"].append(f"REVIEW Q6(c): nhân vật id={character['id']} không có tên để đối chiếu BYĐ v2.")
            continue
        if key in by_key and by_key[key]["id"] != character["id"]:
            ambiguous.add(key)
        else:
            by_key[key] = {"id": character["id"], "name": character["name"],
                           "anchor_approved": bool(character["anchor_approved"]),
                           "ref_asset_id": character["ref_asset_id"]}
    if ambiguous:
        names = sorted({by_key[key]["name"] for key in ambiguous})
        result["review"].append("REVIEW Q6(c): tên nhân vật trùng khi đối chiếu BYĐ v2: " + ", ".join(names))

    def character_match(candidate):
        matches = [key for key, character in by_key.items()
                   if key not in ambiguous and _q6c_same_name(candidate, character["name"], assets)]
        if len(matches) > 1:
            result["review"].append(
                f"REVIEW Q6(c): tên '{candidate}' khớp nhiều nhân vật trong dự án; không tự chọn."
            )
            return None
        return matches[0] if matches else None

    named_candidates = []
    narrative_texts = []
    prose_texts = []
    for scene in scenes:
        try:
            payload = json.loads(scene["data"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        names, texts = _q6c_script_inputs(payload)
        named_candidates.extend(names)
        narrative_texts.extend(texts)
        prose_texts.extend(texts)

    try:
        story_rows = conn.execute("SELECT text, data FROM story_scenes WHERE project_id=? ORDER BY idx,id", (project_id,)).fetchall()
    except sqlite3.Error as exc:
        story_rows = []
        result["review"].append(
            f"REVIEW Q6(c): không đọc được các cảnh kịch bản ({type(exc).__name__}); phần tìm tên trong kịch bản chưa được kiểm tra."
        )
    for story in story_rows:
        try:
            payload = json.loads(story["data"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
            result["review"].append("REVIEW Q6(c): không đọc được dữ liệu nhân vật của cảnh kịch bản.")
        names, texts = _q6c_script_inputs(payload)
        named_candidates.extend(names)
        if story["text"]:
            narrative_texts.append(story["text"])
            prose_texts.append(story["text"])
        narrative_texts.extend(texts)
        prose_texts.extend(texts)
    try:
        project = conn.execute("SELECT script_text FROM projects WHERE id=?", (project_id,)).fetchone()
        if project and project["script_text"]:
            narrative_texts.append(project["script_text"])
            # The raw field also contains preamble and headings. Reuse the parser's scene split so
            # prose candidate scanning sees scene bodies instead of treating metadata as names.
            prose_texts.extend(scene.text for scene in script_parser.split_scenes(project["script_text"].splitlines()))
    except sqlite3.Error as exc:
        result["review"].append(
            f"REVIEW Q6(c): không đọc được kịch bản dự án ({type(exc).__name__}); phần tìm tên trong kịch bản chưa được kiểm tra."
        )

    named_keys = set()
    unknown_named = {}
    for text in narrative_texts:
        words = assets._said_words(text)
        for key, character in by_key.items():
            if key not in ambiguous and assets.name_spans(character["name"], words):
                named_keys.add(key)
        dialogue_text = "\n".join(row for row in text.splitlines() if not script_parser.is_heading(row))
        named_candidates.extend(speaker for speaker, _line in dialogue.lines(dialogue_text))
    for text in prose_texts:
        named_candidates.extend(_q6c_prose_names(text, script_parser, dialogue))
    for candidate in named_candidates:
        key = character_match(candidate)
        if key:
            named_keys.add(key)
        else:
            normalized = _character_key(candidate)
            if normalized:
                unknown_named.setdefault(normalized, candidate.strip())

    try:
        attached_assets = assets.project_assets(conn, project_id)
    except (sqlite3.Error, ValueError, TypeError) as exc:
        attached_assets = []
        result["review"].append(
            f"REVIEW Q6(c): không xác minh được ảnh nhân vật trong Kho ({type(exc).__name__}); chưa kết luận thiếu ảnh Kho."
        )
    kho_check_available = not any("không xác minh được ảnh nhân vật trong Kho" in item for item in result["review"])

    roles = {key: set() for key in by_key if key not in ambiguous}
    main_shots = {key: set() for key in roles}
    main_occurrences = {key: [] for key in roles}
    unmapped_cast = {}
    missing_byd_shots = []
    for scene in scenes:
        idx = scene["idx"]
        try:
            data = json.loads(scene["data"] or "{}")
        except (TypeError, json.JSONDecodeError):
            result["review"].append(f"REVIEW Q6(c): không đọc được BYĐ v2 ở shot {idx} — kiểm tra dữ liệu shot.")
            continue
        byd = shot_intent.byd_of(data)
        if shot_intent.version(byd) != 2:
            missing_byd_shots.append(idx)
            continue
        cast = byd.get("thanh_phan")
        if not isinstance(cast, list):
            result["review"].append(f"REVIEW Q6(c): BYĐ v2 shot {idx} thiếu danh sách thanh_phan; không chặn shot này.")
            continue
        for part_index, part in enumerate(cast):
            if not isinstance(part, dict):
                result["review"].append(f"REVIEW Q6(c): thanh_phan[{part_index}] shot {idx} sai kiểu; không chặn theo mục này.")
                continue
            raw_name = part.get("vat")
            if not isinstance(raw_name, str):
                result["review"].append(f"REVIEW Q6(c): thiếu tên hoặc vai hợp lệ ở thanh_phan[{part_index}] shot {idx}.")
                continue
            key = character_match(raw_name) or _character_key(raw_name)
            role = part.get("vai")
            if not key or role not in shot_intent.VAI:
                result["review"].append(f"REVIEW Q6(c): thiếu tên hoặc vai hợp lệ ở thanh_phan[{part_index}] shot {idx}.")
                continue
            if key in ambiguous:
                continue
            if key in roles:
                roles[key].add(role)
                if role != Q6C_EXCLUDED_ROLE:
                    named_keys.add(key)
                if role == Q6C_MAIN_ROLE:
                    main_shots[key].add(idx)
                    main_occurrences[key].append({
                        "scene_id": scene["id"], "idx": idx, "part_index": part_index, "part": part,
                    })
            else:
                entry = unmapped_cast.setdefault(
                    key, {"name": str(part.get("vat") or "").strip(), "roles": set(), "shots": set()}
                )
                entry["roles"].add(role)
                entry["shots"].add(idx)
                if role != Q6C_EXCLUDED_ROLE:
                    unknown_named.setdefault(key, entry["name"])

    if missing_byd_shots:
        result["review"].append(
            "REVIEW Q6(c): thiếu BYĐ v2 ở shot(s) " + ", ".join(map(str, missing_byd_shots))
            + " — không chặn các shot thiếu BYĐ v2."
        )
    if not scenes:
        result["review"].append("REVIEW Q6(c): dự án chưa có shot BYĐ v2 — chưa đủ dữ liệu xác định vai chính.")

    for entry in unmapped_cast.values():
        if Q6C_MAIN_ROLE not in entry["roles"]:
            non_excluded_roles = entry["roles"] - {Q6C_EXCLUDED_ROLE}
            if non_excluded_roles:
                shots = ", ".join(map(str, sorted(entry["shots"])))
                role_label = "vai phụ" if non_excluded_roles == {Q6C_SECONDARY_ROLE} else "vai không chính"
                result["warn"].append(
                    f"{entry['name']} có {role_label} ở shot {shots} nhưng không khớp nhân vật trong dự án."
                )
            continue
        shots = ", ".join(map(str, sorted(entry["shots"])))
        result["review"].append(
            f"REVIEW Q6(c): mục vai chính {entry['name']} ở shot {shots} không khớp nhân vật trong dự án; "
            "chưa thể xác minh loại người hoặc ảnh mốc."
        )

    for key, character in by_key.items():
        if key in ambiguous or character["anchor_approved"]:
            continue
        character_roles = roles.get(key, set())
        if Q6C_MAIN_ROLE in character_roles:
            finding_source = json.dumps(main_occurrences[key], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            finding_hash = hashlib.sha256(finding_source.encode("utf-8")).hexdigest()
            target_ref = f"q6c-character:{character['id']}:{finding_hash}"
            try:
                override = latest(conn, project_id, "character_anchor", target_ref)
            except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
                result["review"].append(
                    f"REVIEW Q6(c): không xác minh được override cho {character['name']} ({type(exc).__name__}); giữ chặn.")
                override = None
            finding = {"name": character["name"], "target_kind": "character_anchor", "target_ref": target_ref,
                       "error_code": Q6C_ANCHOR_ERROR,
                       "shots": sorted(main_shots[key])}
            shot_list = ", ".join(map(str, finding["shots"]))
            finding["message"] = f"{character['name']} là vai chính ở shot {shot_list}, chưa duyệt ảnh mốc."
            if override and override.get("error_code") == Q6C_ANCHOR_ERROR:
                result["overridden"].append({**finding, "revision": override["revision"], "reason": override["reason"]})
            else:
                result["block"].append(finding)
        elif character_roles - {Q6C_EXCLUDED_ROLE}:
            role_label = "vai phụ" if character_roles - {Q6C_EXCLUDED_ROLE} == {Q6C_SECONDARY_ROLE} else "vai không chính"
            result["warn"].append(f"{character['name']} chỉ có {role_label} trong BYĐ v2 và chưa duyệt ảnh mốc.")
        if (key in named_keys and Q6C_MAIN_ROLE not in character_roles and not character["anchor_approved"]
                and kho_check_available):
            try:
                has_kho_image = _q6c_has_kho_image(conn, character["name"], character, attached_assets, assets)
            except (sqlite3.Error, ValueError, TypeError, KeyError) as exc:
                result["review"].append(
                    f"REVIEW Q6(c): không xác minh được ảnh Kho cho {character['name']} ({type(exc).__name__})."
                )
                has_kho_image = True
            if not has_kho_image:
                result["warn"].append(
                    f"{character['name']} được gọi tên trong kịch bản/shot nhưng chưa duyệt ảnh mốc và chưa có ảnh Kho."
                )

    if kho_check_available:
        for name in unknown_named.values():
            try:
                has_kho_image = _q6c_has_kho_image(conn, name, {}, attached_assets, assets)
            except (sqlite3.Error, ValueError, TypeError, KeyError) as exc:
                result["review"].append(f"REVIEW Q6(c): không xác minh được ảnh Kho cho {name} ({type(exc).__name__}).")
                continue
            if not has_kho_image:
                result["warn"].append(f"{name} được gọi tên trong kịch bản/shot nhưng chưa có ảnh mốc hoặc ảnh Kho.")

    # Keep identical findings only once when a character appears in several script surfaces.
    result["warn"] = list(dict.fromkeys(result["warn"]))

    return result
