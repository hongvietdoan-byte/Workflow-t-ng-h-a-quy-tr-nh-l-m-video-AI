"""Một đề xuất JSON cho N4 qua Claude CLI; không ingest/ghi máy/state hay đo Blender.

Nạp đề xuất vẫn là bước N4 riêng, có xác nhận và bộ kiểm hiện hành. Chỉ dùng
K1 đã có, quyền sửa/khóa S của bàn đạo diễn, client theo dự án và sổ CLI.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3

from . import access, llm_provider, llm_runner, stage_auto, stage_crew, stage_desk

ALLOWED_PHASES = ("dao_dien", "quay_phim", "quay_phim_duyet", "dao_dien_tra_loi")


class ProposalError(ValueError):
    pass


def _budget_ready(stage):
    return stage in llm_runner.CLI_TOKEN_STAGE_POLICY


def _context(conn, pid, data_dir, scene, *, locked=False):
    seg = stage_desk.segment(conn, pid, scene)
    status = stage_desk.scene_status(conn, pid, data_dir, scene, seg=seg)
    if (not locked and "N4" not in status["buttons"]) or status.get("inputs_changed") or status.get("phase") not in ALLOWED_PHASES:
        raise ProposalError("Vai hiện tại không nhận đề xuất N4, đang khóa hoặc đầu vào đã đổi; xem lại trạng thái bàn đạo diễn.")
    k1 = stage_auto.k1_cached(seg, stage_auto.base_dir(data_dir, pid, seg["stage"]))
    if not k1:
        raise ProposalError("Chưa có K1; chạy Kiểm đầu vào trước. Giao vai không tự chạy Blender.")
    stage = stage_desk._read(str(Path(k1) / "stage.json"))
    if not stage:
        raise ProposalError("Không đọc được K1 stage.json; kiểm đầu vào trước.")
    inputs, missing = stage_auto.inputs_for(conn, pid, seg, k1, stage_auto.stored_state_before(data_dir, pid, seg, conn))
    if missing or stage_auto.preflight(inputs, stage.get("marks")):
        raise ProposalError("Đầu vào/cổng 0 USD còn thiếu; mở Kiểm đầu vào để xem và sửa trước khi giao vai.")
    out = stage_desk.seg_dir(data_dir, pid, seg)
    ctx = {"out": out, "crew": str(Path(out) / stage_auto.CREW_DIR), "inputs": inputs, "st": stage, "seg": seg}
    state = stage_auto._crew_load(ctx)
    if not state or state.get("fp") != stage_auto.fingerprint(inputs) or state.get("phase") != status.get("phase"):
        raise ProposalError("Lượt chia vai đã đổi hoặc chưa có đề bài N3; cập nhật trạng thái rồi thử lại.")
    phase = state["phase"]
    table, extra, images = stage_auto._crew_view(ctx, state, limit=llm_runner.MAX_IMAGES)
    review = phase == "quay_phim_duyet"
    prompt = stage_crew.prompt_for(state, inputs, table, extra if review else [], cache_break=llm_runner.CACHE_BREAK)
    images = images if review else []
    metadata = [(path, Path(path).stat().st_size, Path(path).stat().st_mtime_ns) for _, path in images]
    revision = hashlib.sha256(json.dumps([state, prompt, metadata], sort_keys=True, ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()
    return {"stage": stage_crew.ROLES[phase][0], "phase": phase, "revision": revision,
            "prompt": prompt, "images": images,
            "validate": stage_crew.validator(copy.deepcopy(state), copy.deepcopy(inputs), stage.get("marks"))}


def _trusted_user(conn, user):
    """Endpoint Dashboard mới không kế thừa ngoại lệ user=None của worker cũ."""
    trusted = access.user_of(user)
    if trusted is None:
        if stage_desk.login_on():
            raise ProposalError("Cần danh tính đã đăng nhập để giao hoặc nạp đề xuất Claude CLI.")
        return None  # đăng nhập TẮT/local: giữ hợp đồng thao tác tay hiện hành.
    if not trusted.get("email"):
        raise ProposalError("Danh tính không đầy đủ; đăng nhập lại trước khi dùng đề xuất CLI.")
    rows = conn.execute("SELECT role,active FROM users WHERE lower(trim(email))=?", (trusted["email"],)).fetchall()
    if len(rows) != 1 or rows[0][1] != 1 or rows[0][0] not in ("owner", "member"):
        raise ProposalError("Danh tính không còn hoạt động/hợp lệ; đăng nhập lại trước khi dùng đề xuất CLI.")
    return dict(trusted, role=rows[0][0])


def _edit_guard(conn, pid, user):
    try:
        trusted = _trusted_user(conn, user)
        return stage_desk._need_edit(conn, pid, trusted, "giao/nạp đề xuất sân khấu từ Claude CLI")
    except ProposalError as error:
        return {"ok": False, "errors": [str(error)]}
    except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error):
        return {"ok": False, "errors": ["Không xác minh được danh tính/quyền sửa hiện tại; không dùng đề xuất CLI."]}


def _guard(conn, pid, user):
    try:
        denied = _edit_guard(conn, pid, user)
        if denied:
            return denied
        provider, _ = llm_provider.resolve(conn, pid)
        if provider != "claude_cli":
            return {"ok": False, "errors": ["Dự án phải chọn claude_cli; không tự chuyển sang API hay provider khác."]}
        if not stage_desk._db_path(conn):
            return {"ok": False, "errors": ["Cần CSDL pipeline dạng tệp để ghi sổ CLI; không gửi khi thiếu ledger."]}
    except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error):
        return {"ok": False, "errors": ["Không xác minh được quyền/provider/ledger của dự án; không gửi Claude CLI."]}
    return None


def _quotation(context):
    if context["phase"] not in ALLOWED_PHASES:
        raise ProposalError("Không giao tự động vai duyệt chốt; dùng nút duyệt của Executive Producer.")
    if not _budget_ready(context["stage"]):
        raise ProposalError("Khâu này chưa có chính sách CLI canonical; cập nhật cấu hình CLI trước khi giao vai.")
    estimate = llm_runner.cli_input_estimate(context["stage"], context["prompt"], len(context["images"]))
    count = estimate["estimated_input_tokens"]
    return {"ok": True, "phase": context["phase"], "stage": context["stage"], "revision": context["revision"],
            "estimated_input_tokens": count, "images": len(context["images"]),
            "tag": f" · CLI ≈ {count:,} token vào/lượt (ước tính chữ hiện có, chưa tính context ẩn; dùng hạn mức gói)"}


def quote(conn, pid, data_dir, scene, user=None):
    denied = _guard(conn, pid, user)
    if denied:
        return denied
    try:
        return _quotation(_context(conn, pid, data_dir, scene))
    except ProposalError as error:
        return {"ok": False, "errors": [str(error)]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error):
        return {"ok": False, "errors": ["Không đọc được đầu vào đề xuất; kiểm N1/N3 trước khi giao vai."]}


def generate(conn, pid, data_dir, scene, who, user=None, *, expected_revision, confirmed=False):
    if confirmed is not True:
        return {"ok": False, "errors": ["Cần xác nhận dùng hạn mức Claude CLI trước khi giao vai."]}
    denied = _guard(conn, pid, user)
    if denied:
        return denied
    try:
        seg = stage_desk.segment(conn, pid, scene)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error):
        return {"ok": False, "errors": ["Không xác minh được cảnh cần giao vai; không gửi Claude CLI."]}

    def work():
        denied = _guard(conn, pid, user)
        if denied:
            return denied
        try:
            context = _context(conn, pid, data_dir, scene, locked=True)
            _quotation(context)
            if context["revision"] != expected_revision:
                return {"ok": False, "errors": ["Đầu vào/vai đã đổi sau ước tính; xem lại rồi xác nhận giao vai lần nữa."]}
            ledger = stage_desk._db_path(conn)
            if not ledger:
                return {"ok": False, "errors": ["Ledger đã đổi/mất sau ước tính; không gửi Claude CLI."]}
            client = llm_provider.client_for_project(conn, pid, ledger=ledger)
            if not isinstance(client, llm_runner.ClaudeCliClient) or client.ledger != ledger:
                return {"ok": False, "errors": ["Client hiện tại không phải Claude CLI; không gửi và không chuyển API."]}
            with llm_runner.tagged(context["stage"], pid):
                answer, _, _ = llm_runner.ask_json(client, context["prompt"], context["validate"], images=context["images"])
            return {"ok": True, "answer": answer, "revision": context["revision"], "phase": context["phase"]}
        except ProposalError as error:
            return {"ok": False, "errors": [str(error)]}
        except llm_runner.LlmError as error:
            messages = {
                "auth": "Claude CLI chưa đăng nhập/hết hạn; mở ô CLI của pipeline trong Cài đặt rồi kiểm lại.",
                "usage_limit": "Claude CLI đã hết hạn mức gói; chờ mở lại theo trạng thái hạn mức, không chuyển API.",
                "timeout": "Claude CLI quá thời gian chờ; chưa có đề xuất để nạp. Chỉ thử lại có chủ đích.",
                "bad_json": "Claude CLI trả JSON sai mẫu sau lượt sửa; chưa có đề xuất hợp lệ để nạp.",
                "ledger": "Không ghi được sổ CLI; chưa xác nhận được đề xuất. Kiểm sổ trước khi thử lại.",
            }
            message = messages.get(error.code, "Claude CLI không tạo được đề xuất hợp lệ; kiểm trạng thái CLI và thử lại có chủ đích.")
            return {"ok": False, "errors": [message]}
        except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error):
            return {"ok": False, "errors": ["Không tạo được đề xuất từ đầu vào hiện tại; chưa nạp hay ghi máy."]}

    return stage_desk._sync(data_dir, pid, seg, "N4_CLAUDE", who, conn, work)
