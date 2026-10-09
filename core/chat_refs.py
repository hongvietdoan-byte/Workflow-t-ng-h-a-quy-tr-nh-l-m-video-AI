"""Tư liệu người dùng thả vào chat Kịch bản (người dùng 09/10): ảnh / video có 3 vai —
(a) ẢNH TRANG KỊCH BẢN (chụp chữ) → Claude đọc chữ thành văn bản (`read_page`, MỘT lời gọi có giá, chỉ khi người bấm);
(b) ẢNH THAM KHẢO bối cảnh / đồ vật / nhân vật → Kho dự án (chat_intake.apply, như cũ) + một dòng tư liệu ở đây;
(c) VIDEO THAM KHẢO → chép vào `<data>/<pid>/story_refs/` + một dòng tư liệu ở đây.
Danh sách tư liệu (vai, nhãn, ghi chú) lưu trong app_settings `chat_refs:<pid>` và vào prompt Biên kịch / Đạo diễn DẠNG CHỮ (`block`);
ảnh không gửi kèm các prompt đó (lớp prompt Biên kịch / Đạo diễn hiện chỉ gửi chữ)."""
import json
import os
import time
from typing import Dict, List, Optional

from . import access, llm_runner

STAGE = "script_ocr"
KEY = "chat_refs:{}"
ROLE_LABELS = {"location": "Bối cảnh", "prop": "Đồ vật", "character": "Nhân vật", "video_ref": "Video tham khảo"}
UNREADABLE = "KHONG_DOC_DUOC"
_PROMPT = ("Ảnh dưới đây là một trang KỊCH BẢN người dùng chụp lại. Chép lại NGUYÊN VĂN toàn bộ chữ trên trang, đúng thứ tự đọc: giữ tiêu đề "
           "cảnh (vd “CẢNH 1 - NGÀY, SÂN”), tên nhân vật + lời thoại dạng “TÊN: lời”, mô tả hành động, xuống dòng như trang gốc. "
           "Không thêm, không tóm tắt, không sửa chữ, không bình luận, không bọc trong ``` . Chữ nào mờ không chắc thì ghi [?]. "
           f"Ảnh không có chữ kịch bản hoặc không đọc được thì chỉ trả đúng một chữ: {UNREADABLE}")


def items(conn, pid: int) -> List[Dict]:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (KEY.format(pid),)).fetchone()
    try:
        return json.loads(row[0]) if row else []
    except ValueError:
        return []


def add(conn, pid: int, role: str, label: str, note: str, file: str, path: Optional[str]) -> Dict:
    """One reference line (role in ROLE_LABELS). Missing label → ValueError (luật 1: không lưu tư liệu không tên)."""
    if role not in ROLE_LABELS:
        raise ValueError(f"Vai tư liệu không hợp lệ: {role}")
    label = " ".join((label or "").split())
    if not label:
        raise ValueError(f"Tư liệu “{file}” cần một nhãn (tên)")
    it = {"id": f"{int(time.time() * 1000)}", "role": role, "label": label, "note": " ".join((note or "").split())[:300],
          "file": file, "path": path}
    data = json.dumps(it, ensure_ascii=False)
    conn.execute("INSERT INTO app_settings(key,value) VALUES (?,json_array(json(?))) "
                 "ON CONFLICT(key) DO UPDATE SET value=json_insert(app_settings.value,'$[#]',json(?))", (KEY.format(pid), data, data))
    conn.commit()
    return it


def block(conn, pid: int) -> str:
    """The prompt section (text only) — "" when the person sent no reference (prompts stay byte-identical)."""
    refs = items(conn, pid)
    if not refs:
        return ""
    rows = [f"- {ROLE_LABELS.get(r['role'], r['role'])}: {r['label']}" + (f" — ghi chú của người dùng: “{r['note']}”" if r.get("note") else "")
            + f" (tệp {r.get('file')})" for r in refs]
    return ("## Tư liệu tham khảo người dùng gửi kèm\nNgười dùng đã thả các tư liệu này vào chat (chỉ gửi dạng chữ: vai, tên, ghi chú — không "
            "kèm ảnh/video). Bối cảnh / đồ vật / nhân vật trong kịch bản nên khớp tên và mô tả ở đây khi hợp truyện; video tham khảo là gợi ý "
            "nhịp / động tác / không khí, không chép nội dung.\n" + "\n".join(rows))


def estimate(conn) -> Optional[float]:
    """USD of one page read (one picture), shown on the button before the click."""
    from . import cost
    return cost.llm_estimate(conn, STAGE, 1, images=1)


def read_page(p, data_dir: str, pid: int, iid: str, client) -> str:
    """(a) One waiting picture → its text (ONE Claude call, tagged STAGE → ledger). The file leaves the inbox only when text came back;
    no client / unreadable / empty → ValueError (said), the file keeps waiting."""
    from . import chat_intake as Intake
    access.need_edit(p, pid, "đọc ảnh trang kịch bản")
    it = next((x for x in Intake.pending(data_dir, pid) if x["id"] == iid), None)
    if it is None or it.get("type") != "image":
        raise ValueError("Ảnh này không còn trong hộp chờ (đã dùng hoặc đã bỏ)")
    if client is None:
        raise ValueError("Chưa kết nối Claude — kiểm tra Cài đặt rồi bấm lại. Chưa gọi model, chưa tốn tiền.")
    with llm_runner.tagged(STAGE, pid):
        reply = client.complete(_PROMPT, [("Ảnh trang kịch bản:", it["path"])])
    text = (reply.text or "").strip().strip("`").strip()
    if not text or text.upper().startswith(UNREADABLE):
        raise ValueError(f"Claude không đọc được chữ kịch bản trong “{it['file']}” — chụp rõ, thẳng trang hơn rồi thả lại "
                         "(hoặc chọn vai khác). Lượt đọc này vẫn tính vào sổ chi.")
    Intake.drop(data_dir, pid, iid)
    return text


def video_dir(data_dir: str, pid: int) -> str:
    d = os.path.join(data_dir, str(pid), "story_refs")
    os.makedirs(d, exist_ok=True)
    return d
