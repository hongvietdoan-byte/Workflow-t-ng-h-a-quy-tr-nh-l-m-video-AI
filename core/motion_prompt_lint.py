"""KLD-13 (F5-B, 09/10): máy lùi / cần cẩu / quay vòng mà motion prompt không tả khung ở giây cuối → cảnh báo ở Bước 3.

Why: một chuyển động máy lớn (`pull_out`, `crane`, `orbit`) đổi hẳn khung — prompt chỉ nói "camera pulls out" thì model tự chọn khung
kết, và khung kết là thứ shot sau nối vào (#22: lùi + nâng máy để sân trống; dp.md Q5 "điểm cuối"). Chỉ CẢNH BÁO, 0 USD, không chặn
gửi và không sửa prompt (sửa là việc của người / Claude rà prompt).
"""
import re
from typing import Dict, Optional

MOVES = ("pull_out", "crane", "orbit")
MOVE_WORDS = {"pull_out": "lùi máy", "crane": "cần cẩu", "orbit": "quay vòng"}

# a sentence about the LAST frame / where the move lands (English prompt; Vietnamese for prompts typed by hand)
_END = re.compile(r"\b(end(?:s|ing)?\s+(?:on|with|in|at|framed|showing|wide|close|high|low)|by\s+the\s+end|at\s+the\s+end|"
                  r"(?:final|last|end(?:ing)?)\s+(?:frame|shot|framing|image|moment|second|position|composition)|"
                  r"(?:comes?|coming)\s+to\s+rest|settl(?:e|es|ing)\s+(?:on|in|at|into)|finish(?:es|ing)?\s+(?:on|with|at|in)|"
                  r"lands?\s+on|resolv(?:e|es|ing)\s+(?:on|into)|until\s+(?:the\s+)?(?:frame|shot|camera)|"
                  r"khung\s+(?:cuối|kết)|giây\s+cuối|cuối\s+(?:clip|shot)|kết\s+(?:ở|bằng|trên))", re.I)


def end_frame_problem(data: Dict, prompt: str) -> Optional[str]:
    """The warning for one shot (None = fine / not concerned)."""
    move = str((data or {}).get("camera_move") or "").strip().lower()
    if move not in MOVES:
        return None
    if _END.search(prompt or ""):
        return None
    return (f"Máy {MOVE_WORDS[move]} (`{move}`) nhưng motion prompt không tả khung ở giây cuối — model sẽ tự chọn khung kết "
            "(shot sau nối vào đó). Thêm một câu 'ends on …' tả khung cuối (cỡ cảnh, ai/cái gì trong khung).")
