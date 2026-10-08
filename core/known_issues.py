"""Known faults of stages that are paused / replaced (người dùng yêu cầu 2026-09-27): "những khâu không còn dùng cho hiện tại phải ghi rõ lỗi
và hướng sửa đính kèm, tránh sau này dùng lại mà quên sửa, vẫn dính nguyên lỗi cũ".

Each stage lists what is wrong (found in a real run), how to fix it, and what is already fixed. `active(conn, project_id)` returns the
stages a run is about to use — the automatic run and Step 2 say them as warnings, so switching a stage back on shows its open faults
first. Keep this file in step with docs/THIET_KE_LAI_QC_VA_KET_NOI_2026-09-27.md and docs/BAI_HOC_GIAI_DOAN_ANH_2026-09-27.md."""
from typing import Callable, Dict, List

from . import features


def _flag(name: str) -> Callable:
    return lambda conn, pid: features.on(name)


def _shot_mode(mode: str) -> Callable:
    def check(conn, pid):
        row = conn.execute("SELECT shot_mode FROM projects WHERE id=?", (pid,)).fetchone()
        return row is not None and row["shot_mode"] == mode
    return check


def _per_image_qc(conn, pid) -> bool:
    return not features.on("scene_qc")


STAGES: Dict[str, Dict] = {
    # S14.9 (06/10): "location_plates" (ghép phông xanh lên nền 3D) bị bỏ hẳn khỏi code — 8 lỗi mở của nó ghi ở docs/TODO_LICH_SU.md
    # (mục S14.9) và docs/BAI_HOC_GIAI_DOAN_ANH_2026-09-27.md; muốn làm lại phải đọc ở đó trước.
    "per_image_qc": {
        "label": "QC Claude từng ảnh (8 tiêu chí điểm 0–1)",
        "status": "thay bằng QC theo cảnh (cờ scene_qc) — vẫn chạy khi cờ đó tắt",
        "used_when": _per_image_qc,
        "open": [
            ("Điểm không phân biệt ảnh lỗi (TB 0,67) với ảnh tốt (0,69) trên 54 ảnh #8; tự duyệt 6/16 ảnh lỗi rõ, không tự loại ảnh lỗi nào",
             "hỏi có/không kèm bằng chứng thay vì chấm điểm; lỗi kỹ thuật bắt bằng code (QC lớp 0)"),
            ("`grounding` bị code gán 1,0 cho MS/MCU/CU (`_no_feet_in_frame`) → tiêu chí mù", "bỏ tiêu chí; hỏi cụ thể chân / bóng khi khung có chân"),
            ("Không có chuẩn nơi chốn (không gửi ảnh toàn cảnh) → set_match thấp mà không có căn cứ", "gửi ảnh toàn cảnh của cảnh"),
            ("Ngưỡng tự duyệt 0,82 cao so với phân bố điểm → 19/38 ảnh tốt đẩy sang người xem không lý do", "bỏ ngưỡng trung bình; quyết định theo lỗi cụ thể"),
            ("Mỗi ảnh chấm riêng → không thấy liên tục giữa các khung", "QC theo cảnh: một lượt nhìn cả cảnh"),
        ],
        "fixed": [],
    },
    "scene_qc_layer1": {
        "label": "QC theo cảnh lớp 1 (Claude, tấm ghép cả cảnh)",
        "status": "chưa qua nghiệm thu — chỉ ghi chú, mọi khung chờ người (cờ scene_qc_trusted tắt)",
        "used_when": lambda conn, pid: features.on("scene_qc"),
        "open": [
            ("Không thấy lỗi kỹ thuật nhìn là thấy: cho qua 6 khung chữ nhật dán + tháp Big Ben trên tấm ghép (ô 384×683)",
             "kiểm kỹ thuật TỪNG khung ở độ phân giải đầy đủ với câu hỏi đích danh (mảng dán, đường nối, ánh sáng người ≠ nền); lỗi lặp → bộ đo bằng code"),
            ("Báo nhầm 12/21 khung tốt vì chi tiết vụn (vệt nước mắt, chiều sâu ba lớp)", "tách mức lỗi chặn / lỗi nhỏ; chỉ lỗi chặn mới 'fix'"),
        ],                       # 08/10: "cho qua một ô đen" đã chặn bằng code (lớp 0) — chỉ còn ở `fixed`, không đếm là lỗi mở
        "fixed": ["khung trống/đen/một màu bắt bằng code (lớp 0)", "chưa tin → không tự duyệt / tự vẽ lại"],
    },
    "set_consistency": {
        "label": "QC đồng bộ cả bộ ảnh (một tấm ghép toàn dự án)",
        "status": "thay bằng QC theo cảnh (cờ scene_qc)",
        "used_when": _per_image_qc,
        "open": [("33 ảnh trên 1 tấm 4 cột → mỗi ô quá nhỏ để thấy chi tiết", "tấm ghép theo cảnh, ≤ 6 khung, ~512 px mỗi khung")],
        "fixed": [],
    },
    "bible_check": {
        "label": "Kiểm mô tả nhân vật với ảnh tài nguyên (prompt 18)",
        "status": "đang dùng",
        "used_when": lambda conn, pid: True,
        "open": [("Báo sai chi tiết nhỏ: mũ MAXIM đội ngược đọc thành đội xuôi (ảnh thu 1024 px, tờ thiết kế nhiều ô nhỏ)",
                  "cờ chi tiết nhỏ phải kèm ảnh cắt sát vùng đó cho người xem; không đề xuất sửa Bible chỉ bằng lời Claude"),
                 ("Cờ báo sai vẫn lưu sau khi người xác nhận (bấm tiếp tục) → Bước 2 vẫn khóa nút gen ảnh, phải tick 'vẫn gen ảnh'",
                  "nút 'cờ này sai — bỏ' lưu quyết định của người; cờ đã bỏ không chặn lại")],
        "fixed": [],
    },
    "kling_multishot": {
        "label": "Kling multi-shot / Kling đầu–cuối để gộp shot",
        "status": "không dùng — thử 2026-09-27 hỏng; gộp shot bằng Seedance chỉ ảnh tham chiếu (cờ seedance_ref_groups)",
        "used_when": _shot_mode("multishot"),
        "open": [("Multi-shot: shot sau bịa nội dung hoặc không cắt (docs/PHAN_TICH_GOP_SHOT_2026-09-27.md mục 5–6)",
                  "chỉ dùng cho shot liền cùng người + cùng hành động, có ảnh cho từng shot — hoặc không dùng"),
                 ("Đầu–cuối: hai góc khác nhau → biến hình", "chỉ cho một cú máy liền nối hai khung")],
        "fixed": [],
    },
    "camera_setups": {
        "label": "Quay theo vị trí máy (H5, một clip liền cho nhiều shot cùng góc)",
        "status": "bị nhóm Seedance thay khi cờ seedance_ref_groups bật",
        "used_when": lambda conn, pid: features.on("camera_setups") and not features.on("seedance_ref_groups"),
        "open": [("Clip liền từ ảnh shot đầu → shot sau không có khung riêng, mất khung nhấn (thử 2A)", "chỉ dùng khi các shot thật sự cùng khung")],
        "fixed": [],
    },
    "motion_claude_groups": {
        "label": "Motion prompt bằng Claude cho nhóm Seedance",
        "status": "không cần — prompt nhóm dựng bằng code từ trường Director (P2m thử thật đạt)",
        "used_when": lambda conn, pid: False,
        "open": [("~20k token vào mỗi lượt, không cache", "nhóm Seedance: dựng bằng code; Claude chỉ cho shot riêng cần diễn tả chuyển động khó")],
        "fixed": [],
    },
}


def active(conn, project_id: int) -> List[Dict]:
    """The paused / replaced stages this project's run would use, with their open faults."""
    out = []
    for key, st in STAGES.items():
        try:
            used = st["used_when"](conn, project_id)
        except Exception:  # noqa: BLE001 - a missing column must not stop a run
            used = False
        if used and st["open"]:
            out.append({"key": key, **{k: v for k, v in st.items() if k != "used_when"}})
    return out


def warning_lines(conn, project_id: int) -> List[str]:
    return [f"{st['label']} ({st['status']}): {len(st['open'])} lỗi chưa sửa — " + "; ".join(bug for bug, _ in st["open"][:2])
            + (" …" if len(st["open"]) > 2 else "") for st in active(conn, project_id)]
