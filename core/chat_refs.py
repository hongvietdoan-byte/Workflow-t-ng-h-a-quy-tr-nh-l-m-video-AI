"""Tư liệu người dùng thả vào chat Kịch bản (người dùng 09/10): ảnh / video có 3 vai —
(a) ẢNH TRANG KỊCH BẢN (chụp chữ) → Claude đọc chữ thành văn bản (`read_page`, MỘT lời gọi có giá, chỉ khi người bấm);
(b) ẢNH THAM KHẢO bối cảnh / đồ vật / nhân vật → Kho dự án (chat_intake.apply, như cũ) + một dòng tư liệu ở đây;
(c) VIDEO THAM KHẢO → chép vào `<data>/<pid>/story_refs/` + một dòng tư liệu ở đây.
Danh sách tư liệu (vai, nhãn, ghi chú) lưu trong app_settings `chat_refs:<pid>` và vào prompt Biên kịch / Đạo diễn DẠNG CHỮ (`block`);
ảnh không gửi kèm các prompt đó (lớp prompt Biên kịch / Đạo diễn hiện chỉ gửi chữ)."""
import json
import os
import shutil
import time
from typing import Dict, List, Optional

from . import access, llm_runner

STAGE = "script_ocr"
KEY = "chat_refs:{}"
ROLE_LABELS = {"location": "Bối cảnh", "prop": "Đồ vật", "character": "Nhân vật", "video_ref": "Video tham khảo"}
UNREADABLE = "KHONG_DOC_DUOC"
LABEL_MAX = 80
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
    label = " ".join((label or "").split())[:LABEL_MAX]
    if not label:
        raise ValueError(f"Tư liệu “{file}” cần một nhãn (tên)")
    same = next((r for r in items(conn, pid) if (r.get("role"), r.get("label"), r.get("file")) == (role, label, file)), None)
    if same is not None:                                               # rà 09/10: cùng vai + nhãn + tệp → không thêm dòng trùng
        return same
    used, rid = {str(r.get("id")) for r in items(conn, pid)}, int(time.time() * 1000)
    while str(rid) in used:                                            # mã duy nhất → remove() không xóa nhầm hai dòng cùng mili-giây
        rid += 1
    it = {"id": f"{rid}", "role": role, "label": label, "note": " ".join((note or "").split())[:300],
          "file": file, "path": path}
    data = json.dumps(it, ensure_ascii=False)
    conn.execute("INSERT INTO app_settings(key,value) VALUES (?,json_array(json(?))) "
                 "ON CONFLICT(key) DO UPDATE SET value=json_insert(app_settings.value,'$[#]',json(?))", (KEY.format(pid), data, data))
    conn.commit()
    return it


def remove(conn, pid: int, rid: str) -> bool:
    """Bỏ một dòng tư liệu khỏi danh sách (tệp đã chép giữ nguyên trên đĩa). False khi không thấy mã."""
    refs = items(conn, pid)
    keep = [r for r in refs if str(r.get("id")) != str(rid)]
    if len(keep) == len(refs):
        return False
    conn.execute("UPDATE app_settings SET value=? WHERE key=?", (json.dumps(keep, ensure_ascii=False), KEY.format(pid)))
    conn.commit()
    return True


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
    try:                                                               # rà 09/10: giữ bản gốc ảnh trang trước khi rời hộp chờ
        shutil.copy2(it["path"], os.path.join(video_dir(data_dir, pid), os.path.basename(it["path"])))
    except OSError as e:
        raise ValueError(f"Đã đọc chữ nhưng không lưu được bản gốc “{it['file']}” vào story_refs ({e}) — ảnh vẫn chờ trong hộp. "
                         "Lượt đọc này vẫn tính vào sổ chi.") from e
    Intake.drop(data_dir, pid, iid)
    return text


def video_dir(data_dir: str, pid: int) -> str:
    d = os.path.join(data_dir, str(pid), "story_refs")
    os.makedirs(d, exist_ok=True)
    return d
