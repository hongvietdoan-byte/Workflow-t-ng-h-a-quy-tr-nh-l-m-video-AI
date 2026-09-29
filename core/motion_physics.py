"""S4.4 (after #8: "khựng, dáng sai", feet sliding, bodies moving like cut-outs): one short body-physics sentence per kind of action,
added to the video prompt of a shot whose action is of that kind.

Physics, not style: where the weight goes, what touches the ground, what follows with a delay — the things a video model gets wrong
when the prompt only names the action. ONE sentence per shot (Seedance 2.5 提示词指南: describe an action in general terms and detail
only 1–2 highlights; a list of body parts overloads it). The first kind that matches wins, in the order below (a fight that includes
running is described as a fight). Wording from general animation practice (weight, contact, follow-through), not from one sample."""
import re
from typing import Optional

# (kind, words in the Director's action — English after translation, Vietnamese before — , the sentence)
KINDS = (
    ("strike", r"\b(punch|kick|strike|hits?|slap|swing[s]? (?:a|the|his|her) (?:fist|bat|pan)|fight|đấm|đá vào|tung cước|đánh|tát|vung)\b",
     "The power of each blow starts from the hips and the back foot, the free hand guards, and a hit makes the other body recoil."),
    ("fall", r"\b(falls?|falling|trips?|stumbles?|collapses?|knocked down|ngã|té|vấp|đổ gục)\b",
     "The body falls with gravity at a steady speed, the hands reach out, and the landing has weight and a short settle."),
    ("jump", r"\b(jumps?|jumping|leaps?|hops?|vaults?|nhảy lên|bật nhảy|nhảy qua|phóng lên)\b",
     "A crouch before take-off, the body in the air follows one arc, and the knees bend on landing to take the weight."),
    ("dance", r"\b(danc\w*|twirls?|spins? around|nhảy múa|khiêu vũ|nhảy theo nhạc|múa)\b",
     "Every step lands firmly, the weight moves fully from foot to foot, and hair and clothes follow each move with a slight delay."),
    ("run", r"\b(runs?|running|sprints?|dash(?:es)?|rushes?|chases?|chạy|lao tới|đuổi)\b",
     "Each foot lands under the body with no sliding, the arms swing opposite the legs, the body leans forward, and hair and loose "
     "clothes trail behind."),
    ("throw", r"\b(throws?|tosses?|hurls?|ném|quăng)\b",
     "The arm winds back first, the weight moves from the back foot to the front one, and the thrown object keeps one clear path."),
    ("sit_stand", r"\b(sits? down|stands? up|gets? up|rises? from|kneels?|ngồi xuống|đứng dậy|đứng lên|quỳ)\b",
     "The weight moves over the feet before the body rises or lowers, a hand pushes on the knee or the seat."),
    ("walk", r"\b(walks?|walking|steps? (?:forward|back|closer|toward)|strolls?|approaches|đi tới|bước|đi bộ|tiến lại)\b",
     "Heel then toe on the ground with no foot sliding, the weight shifts from side to side, the arms swing loosely."),
    ("turn", r"\b(turns? (?:around|back|to|toward)|spins? to face|looks? back over|quay lại|quay người|ngoảnh lại)\b",
     "The head leads the turn, then the shoulders, then the hips and feet."),
    ("grab", r"\b(grabs?|picks? up|reaches? for|catches?|pulls?|chộp|nhặt|với lấy|bắt lấy|kéo)\b",
     "The hand closes around the object with real contact, fingers wrapped, and the object's weight shows in the arm."),
)
_COMPILED = [(k, re.compile(p, re.I), s) for k, p, s in KINDS]


def kind(action: str) -> Optional[str]:
    for k, rx, _ in _COMPILED:
        if rx.search(action or ""):
            return k
    return None


def sentence(action: str) -> str:
    """The physics sentence for this action, or "" (no body action of a known kind: a look, a line, a still moment)."""
    for _, rx, s in _COMPILED:
        if rx.search(action or ""):
            return s
    return ""
