"""Tab Kịch bản kiểu chat — Đợt 2 (người dùng 07/10, Khủng Long Đỏ mục 10; cờ `chat_first`, cùng cờ với core/chat_intake.py).

Dự án bắt đầu từ chat và đi liền mạch trong chat: tin đầu tiên ở màn ⌂ tạo dự án (tên rút từ chữ, thiết lập mặc định như ➕ Dự án mới);
sau mỗi việc Đạo diễn nói việc kế tiếp trong luồng chat (một nút chính duy nhất); kết quả Director (nhân vật, cảnh cần xem, thứ còn thiếu)
được kể lại trong chat thay vì một toast mất ngay. Không gọi model — chỉ đọc CSDL."""
import re
from typing import Dict, List, Optional

_HEADING = re.compile(r"^\s*(?:cảnh|canh|scene|shot)\s*\d+\b", re.I)


def project_name(text: str, files: List[str], when: str) -> str:
    """A short name for a project started from the chat: the first plain line (not a scene heading), else the first file, else the time."""
    for line in (text or "").splitlines():
        line = " ".join(line.strip(" #*-:").split())
        if line and not _HEADING.match(line):
            return line[:40].rstrip() + ("…" if len(line) > 40 else "")
    for f in files or []:
        stem = re.sub(r"\.[^.]+$", "", f).replace("_", " ").strip()
        if stem:
            return stem[:40]
    return f"Dự án {when}"


def start_project(p, text: str, files: List[str], when: str, created_by: Optional[str] = None) -> int:
    """New project from the first chat message — the same defaults the ➕ Dự án mới form starts with (khung dọc, SHORT_FORM, cân bằng,
    FF), the balanced QC level and the settings inherited from this person's latest project (S3.8). Limits (S14.18) raise as usual."""
    from . import formats, model_router, project_defaults, qc_policy
    pid = p.create_project(project_name(text, files, when), created_by=created_by, aspect=formats.DEFAULT_NEW, genre="SHORT_FORM",
                           model_priority=model_router.DEFAULT_PRIORITY, game="FF")
    qc_policy.apply(p, pid, "balanced")
    if created_by:
        project_defaults.inherit(p.conn, pid, created_by)
    return pid


def state(p, pid: int) -> Dict:
    """What the guide needs, read now: scenes, characters, anchors waiting, lock, files waiting in the chat inbox count is added by the UI."""
    n_scenes = p.conn.execute("SELECT COUNT(*) FROM scenes WHERE project_id=?", (pid,)).fetchone()[0]
    chars = p.conn.execute("SELECT name, anchor_approved, locked FROM characters WHERE project_id=? ORDER BY id", (pid,)).fetchall()
    return {"scenes": n_scenes, "characters": [c["name"] for c in chars],
            "no_anchor": [c["name"] for c in chars if not c["anchor_approved"]], "locked": any(c["locked"] for c in chars)}


def guide(kind: str, st_: Dict, missing: List[str] = (), waiting: int = 0) -> str:
    """The Đạo diễn's line before the ONE primary button of the moment (kind = step1_v2.next_kind). '' = nothing to add."""
    head = ""
    if waiting:
        head = f"Còn **{waiting} tệp** chờ bạn chọn dùng làm gì (thẻ ở trên). "
    if kind == "analyse":
        return head
    if kind == "auto":
        return head + "Đang chạy tự động — mình báo trong luồng này khi cần bạn."
    if kind == "plan":
        line = f"Đã tách **{st_['scenes']} cảnh**. Bước kế: Đạo diễn chia shot và lập Character Bible (nhân vật, trang phục, giọng)."
        if missing:
            line += " Kịch bản còn thiếu ảnh cho: **" + ", ".join(missing[:8]) + "** — thả ảnh vào chat kèm tên trước thì Đạo diễn dùng luôn."
        return head + line
    if kind == "budget":
        return head + "Đạo diễn đã lập kế hoạch. Xem ngân sách dự tính rồi duyệt để chạy tiếp."
    if kind == "lock":
        if st_["no_anchor"]:
            return head + ("Còn ảnh mốc chưa duyệt: **" + ", ".join(st_["no_anchor"]) + "** — duyệt ở ⚙ Chi tiết › Nhân vật, hoặc khóa luôn "
                           "nếu đã ổn.")
        return head + "Nhân vật đã đủ ảnh mốc. Duyệt & khóa để sang Storyboard."
    return head + "Kịch bản và nhân vật đã khóa — sang Storyboard để gen ảnh."


def director_note(result: Dict, st_: Dict, missing: List[str] = ()) -> str:
    """The Director's run told in the chat (it was a toast): who, how many scenes, which scenes the Đạo diễn review flagged, what is missing."""
    parts = [f"🎬 Đạo diễn đã lập kế hoạch: **{result.get('characters', len(st_['characters']))} nhân vật**"
             + (f" ({', '.join(st_['characters'][:8])})" if st_["characters"] else "") + f", **{result.get('scenes', st_['scenes'])} cảnh**."]
    if result.get("flagged"):
        parts.append("Cảnh cần bạn xem: " + ", ".join(f"**{x}**" for x in result["flagged"]) + " (mở ở 🎬 Kịch bản & các cảnh).")
    if missing:
        parts.append("Còn thiếu ảnh cho: " + ", ".join(missing[:8]) + " — thả ảnh vào chat kèm tên.")
    if st_["no_anchor"]:
        parts.append("Ảnh mốc chờ duyệt: " + ", ".join(st_["no_anchor"]) + ".")
    return " ".join(parts)
