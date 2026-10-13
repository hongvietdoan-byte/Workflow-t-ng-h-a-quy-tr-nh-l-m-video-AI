"""S4.4 (after #8: "khựng, dáng sai", feet sliding, bodies moving like cut-outs): one short body-physics sentence per kind of action,
added to the video prompt of a shot whose action is of that kind.

Physics, not style: where the weight goes, what touches the ground, what follows with a delay — the things a video model gets wrong
when the prompt only names the action. ONE sentence per shot (Seedance 2.5 提示词指南: describe an action in general terms and detail
only 1–2 highlights; a list of body parts overloads it). The first kind that matches wins, in the order below (a fight that includes
running is described as a fight). Wording from general animation practice (weight, contact, follow-through), not from one sample."""
import re
from typing import Dict, Optional

# (kind, words in the Director's action — English after translation, Vietnamese before — , the sentence)
KINDS = (
    # rà video #27 (12/10, S18–S20): gunfire got the melee sentence through a bare "hits?" ("he takes hits", "the glue wall is hit by a
    # stray bullet") — shooting is its own kind, before strike; being hit is not throwing a blow (no sentence for it)
    # rà 12/10: never a bare 'fire(s)' / 'shoots' — "stares at the fire", "the bonfire fires up sparks", "shoots a glance"
    ("shoot", r"\b(?:(?:fires?|fired|firing)(?: \w+ly)? (?:at|into|on|toward|towards|a shot|a burst|shots?)|opens? fire|gunfire"
              r"|shoots?(?! (?:a |the )?(?:glance|look))(?: \w+ly)? (?:at|into|him|her|them|the|a|an)|shooting (?:at|into)"
              r"|xả súng|nổ súng|bắn(?! tung| tóe| toé))\b",
     "Each shot jolts the gun back into the shoulder, the stance stays braced with the feet planted, and a target that is hit jerks "
     "back."),
    ("strike", r"\b(punch(?:es|ed|ing)?|kicks?|kicking|strikes?|slaps?|swing[s]? (?:a|the|his|her) (?:fist|bat|pan)|fights?|fighting"
               r"|đấm|đá vào|tung cước|đánh|tát|vung)\b",
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
_GAME_NAME = re.compile(r"\bfree\s*-?\s*fire\b", re.I)          # the game's name is not gunfire


def kind(action: str) -> Optional[str]:
    text = _GAME_NAME.sub(" ", action or "")
    for k, rx, _ in _COMPILED:
        if rx.search(text):
            return k
    return None


def sentence(action: str, camera_move: Optional[str] = None) -> str:
    """The physics sentence for this action, or "" (no body action of a known kind: a look, a line, a still moment).
    camera_move (optional, flag locomotion_end_frame): a run / walk the camera follows gets the ground sentence after it."""
    text = _GAME_NAME.sub(" ", action or "")
    out = ""
    for _, rx, s in _COMPILED:
        if rx.search(text):
            out = s
            break
    if camera_move is not None and _ground_sentence_on() and follows(camera_move) and moves_through_space(action):
        out = (out + " " + GROUND_SENTENCE).strip()
    return out


# Hộp thư 12/10 18:13 (#27 shot 3, job 782 → 783): a run the camera follows from behind, with nothing in the prompt about the place
# moving past, came back running in place; job 783 (the sentence below, no drawn end frame) covered real ground.
LOCOMOTION_FLAG = "locomotion_end_frame"
GROUND_SENTENCE = ("The camera keeps the same distance, so the surroundings move past — nearby objects slide by and the destination "
                   "grows larger; real ground is covered, never running in place.")
STRETCH = 1.3                       # generated seconds above the shot's seconds × this → the drawn end frame lands too late
_LOCOMOTION = [rx for k, rx, _ in _COMPILED if k in ("run", "walk")]
_FOLLOW = re.compile(r"\b(?:follow\w*|track\w*|push[\s_-]*in|dolly[\s_-]*in|truck\w*|bám\w*|theo sau|đẩy vào)\b", re.I)


def _ground_sentence_on() -> bool:
    from . import features
    return features.on(LOCOMOTION_FLAG)


def moves_through_space(action: str) -> bool:
    """A run or a walk anywhere in the action (not only the first kind: "runs and jumps over" still covers ground)."""
    text = _GAME_NAME.sub(" ", action or "")
    return any(rx.search(text) for rx in _LOCOMOTION)


def follows(camera_move: Optional[str]) -> bool:
    return bool(_FOLLOW.search(str(camera_move or "").replace("_", " ")))


def shot_action(data: Dict) -> str:
    """The Director's action and its English form (motion_en) — either one naming a run / walk counts."""
    en = data.get("motion_en") if isinstance(data.get("motion_en"), dict) else {}
    return " ".join(str(x) for x in (data.get("action"), en.get("action")) if x)


def in_place_risk(data: Dict, shot_secs: float, gen_secs: float) -> Optional[str]:
    """Why a DRAWN end frame would make this shot run in place, or None: a run / walk generated much longer than the shot (Kling ≥ 3 s,
    Seedance ≥ 4 s for a 1–2 s shot) puts the drawn end ("a few steps on") at the end of the longer clip, so the runner covers the
    shot's distance over the whole clip — the cut keeps the first seconds, where the legs move and the ground does not."""
    try:
        shot_secs, gen_secs = float(shot_secs or 0), float(gen_secs or 0)
    except (TypeError, ValueError):
        return None
    if shot_secs <= 0 or gen_secs <= shot_secs * STRETCH or not moves_through_space(shot_action(data)):
        return None
    return (f"shot di chuyển {shot_secs:g} s nhưng clip sinh {gen_secs:g} s (> {STRETCH:g}×) — khung cuối vẽ bị ép ở giây {gen_secs:g}, "
            "dễ thành chạy tại chỗ")


# V12 (rà gốc video #27 13/10, G12): the stretch rule misses a run as long as its clip whose drawn end frame shows NO ground covered.
# With the camera following the runner, ground covered = the place ahead grows (background scale > 1) or slides by (corner shift);
# the end frame at the start picture's size and place means "a few steps" drawn in place → the model runs in place (782).
SAME_GROUND_SCALE = 1.05            # background scale inside [1/1.05, 1.05] …
SAME_GROUND_CORNER = 0.05           # … and the picture's corners moved less than 5 % of the frame → the end frame shows the same spot


def same_ground(data: Dict, measure: Optional[Dict]) -> Optional[str]:
    """Why a drawn end frame of this run / walk shows no ground covered, or None. measure: framing_guard.end_frame_distance of the
    start picture → end frame ({"scale", "corner"}); not measured → None (the distance check says it). Only a run / walk the camera
    follows: with a still camera the runner crosses the frame and the background rightly stays."""
    if not measure or not follows(data.get("camera_move")) or not moves_through_space(shot_action(data)):
        return None
    g = measure.get("ground") or measure      # R4 (rà S3): the background with the people masked (framing_guard._ground)
    s, c = g.get("scale"), g.get("corner")
    if s is None or c is None:
        return None
    from .framing_guard import GROUND_INLIERS, GROUND_SHARE
    if "inliers" in g and ((g.get("inliers") or 0) < GROUND_INLIERS or (g.get("inlier_share") or 0) < GROUND_SHARE):
        return None                           # too few background points to call it "the same place" (not judged)
    if 1 / SAME_GROUND_SCALE <= s <= SAME_GROUND_SCALE and c <= SAME_GROUND_CORNER:
        return (f"shot chạy/đi máy bám theo nhưng khung cuối vẽ cùng cỡ, cùng chỗ với ảnh đầu (nền × {s:.2f}, góc lệch {c * 100:.0f} %) "
                "— không thấy quãng đường, dễ thành chạy tại chỗ")
    return None
