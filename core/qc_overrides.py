"""V3.1 M4.7 / C3-4 — nhật ký ngoại lệ QC do người dùng ghi.

Migration chỉ chạy khi được gọi tường minh; không gắn vào khởi tạo/mở DB. Mỗi lần ghi tạo revision mới. API chỉ nhận token phiên đăng nhập
được `core.auth` xác minh, không nhận email/role do caller khai báo; không có đường CLI/Claude/tool để tự tạo phiên hoặc ghi ngoại lệ.
"""
import hashlib
import json
import re
import sqlite3
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
    from .stage_grid import fold
    if not isinstance(value, str):
        return ""
    return " ".join(fold(value).split())


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

    from . import shot_intent

    try:
        scenes = conn.execute("SELECT id, idx, data FROM scenes WHERE project_id=? ORDER BY idx,id", (project_id,)).fetchall()
        characters = conn.execute(
            "SELECT id, name, anchor_approved FROM characters WHERE project_id=? ORDER BY id", (project_id,)
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
                           "anchor_approved": bool(character["anchor_approved"])}
    if ambiguous:
        names = sorted({by_key[key]["name"] for key in ambiguous})
        result["review"].append("REVIEW Q6(c): tên nhân vật trùng khi đối chiếu BYĐ v2 (không dấu): " + ", ".join(names))

    roles = {key: set() for key in by_key if key not in ambiguous}
    main_shots = {key: set() for key in roles}
    main_occurrences = {key: [] for key in roles}
    unmapped_cast = {}
    valid_cast_shots = 0
    incomplete_byd = False
    missing_byd_shots = []
    for scene in scenes:
        idx = scene["idx"]
        try:
            data = json.loads(scene["data"] or "{}")
        except (TypeError, json.JSONDecodeError):
            result["review"].append(f"REVIEW Q6(c): không đọc được BYĐ v2 ở shot {idx} — kiểm tra dữ liệu shot.")
            incomplete_byd = True
            continue
        byd = shot_intent.byd_of(data)
        if shot_intent.version(byd) != 2:
            missing_byd_shots.append(idx)
            continue
        cast = byd.get("thanh_phan")
        if not isinstance(cast, list):
            result["review"].append(f"REVIEW Q6(c): BYĐ v2 shot {idx} thiếu danh sách thanh_phan; không chặn shot này.")
            incomplete_byd = True
            continue
        valid_cast_shots += 1
        for part_index, part in enumerate(cast):
            if not isinstance(part, dict):
                result["review"].append(f"REVIEW Q6(c): thanh_phan[{part_index}] shot {idx} sai kiểu; không chặn theo mục này.")
                incomplete_byd = True
                continue
            key = _character_key(part.get("vat"))
            role = part.get("vai")
            if not key or role not in shot_intent.VAI:
                result["review"].append(f"REVIEW Q6(c): thiếu tên hoặc vai hợp lệ ở thanh_phan[{part_index}] shot {idx}.")
                incomplete_byd = True
                continue
            if key in ambiguous:
                continue
            if key in roles:
                roles[key].add(role)
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
        elif not character_roles and valid_cast_shots and not missing_byd_shots and not incomplete_byd:
            result["warn"].append(f"{character['name']} chưa có vai chính trong BYĐ v2 và chưa duyệt ảnh mốc.")

    return result
