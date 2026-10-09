"""F5-A (09/10): dòng "sẵn sàng gen" trên thẻ cảnh (Bước 2 ảnh, Bước 4 video) — MỘT dòng gọn + expander chi tiết, KHÔNG nút mới
(nút sửa ở chỗ khác; dòng chỉ nói "sửa ở Bước X"). Kết quả tính một lần cho cả lưới bằng core.readiness.project_ready."""
from typing import Dict, Iterable, Optional

import streamlit as st

from core import readiness


def grid(conn, data_dir: str, pid: int, kind: str, scene_ids: Iterable[int], lines: Optional[Dict] = None) -> Dict[int, Dict]:
    """{scene_id: kết quả} cho cả lưới ({} khi đọc lỗi — thẻ vẫn vẽ như cũ)."""
    try:
        return readiness.project_ready(conn, data_dir, pid, kind, list(scene_ids), lines=lines)
    except Exception:  # noqa: BLE001 - the line is information: never breaks the grid
        return {}


def line(res: Optional[Dict]) -> None:
    """Dòng gọn + expander chi tiết."""
    if not res:
        return
    st.caption(readiness.summary(res))
    with st.expander("Chi tiết sẵn sàng gen", expanded=False):
        st.markdown(readiness.details_md(res))


def reason(res: Optional[Dict]) -> None:
    """Shot red: lý do ngay dưới nút gen (không bấm cũng biết vì sao)."""
    text = readiness.blocked_reason(res or {})
    if text:
        st.caption(text)
