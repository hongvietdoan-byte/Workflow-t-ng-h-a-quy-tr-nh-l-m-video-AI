"""Reading a gameplay skill-showcase video into evidence-based character/skill notes.

Based on "AI Video Analysis & Prompt Generation Standard" (Free Fire / Kenta, v2.0, shared by the project
owner): the video is ground truth, and Claude's job is to describe what it OBSERVES (identity, VFX shape/
color/motion, spatial relationships) and separate that from what a text overlay/voice EXPLICITLY states
(mechanic numbers, activation rules) -- never inventing duration/cooldown/damage/range that isn't shown.

Scope of this first version (not the full v2.0 pipeline): uniform frame sampling instead of motion-aware
event detection, one text write-up instead of a JSON evidence graph, and no separate Reference QA agent --
the person reviews the draft and the extracted frames themselves before anything is saved. The output text
goes into the resource's description next to `[ff.garena.com]`/`[AI đọc ảnh]` (same append-a-marked-block
convention as core/ff_site.py and core/asset_vision.py), and selected frames can be added as ordinary
reference images (core/assets.py::add_image) -- including a still that is well-suited to become an
image-to-video motion reference later (core/pipeline.py::set_motion_ref_video already reads its own
`reference_video` upload; wiring this extraction directly into that picker is not done yet).
"""
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

from . import assets, llm_runner
from .ffmpeg_studio import FFmpegNotFound, find_ffmpeg

MARK = "[Phân tích video kỹ năng]"
MAX_FRAMES = 10
MAX_VIDEO_BYTES = 200 * 1024 * 1024

_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_STREAM_VIDEO = re.compile(r"Stream #\d+:\d+.*Video:.*?(\d{2,5})x(\d{2,5}).*?(?:(\d+(?:\.\d+)?)\s*fps)?")


class VideoAnalysisError(Exception):
    def __init__(self, message: str, code: str = "error"):
        super().__init__(message)
        self.code = code


def probe(path: str) -> Dict:
    """duration_sec / width / height / fps read from `ffmpeg -i` (no ffprobe needed); missing fields are None."""
    try:
        proc = subprocess.run([find_ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FFmpegNotFound as e:
        raise VideoAnalysisError(str(e), code="config") from e
    err = proc.stderr or ""
    dur = _DURATION.search(err)
    duration = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else None
    vid = _STREAM_VIDEO.search(err)
    width, height = (int(vid.group(1)), int(vid.group(2))) if vid else (None, None)
    fps = float(vid.group(3)) if vid and vid.group(3) else None
    return {"duration_sec": duration, "width": width, "height": height, "fps": fps}


def extract_frames(path: str, out_dir: str, count: int = 8) -> List[str]:
    """`count` frames sampled evenly across the clip (simple uniform sampling -- not the event-aware
    activation/effect_peak/impact sampling the full standard calls for, but a workable first version)."""
    meta = probe(path)
    duration = meta["duration_sec"] or 0.0
    if duration <= 0:
        raise VideoAnalysisError("không đọc được thời lượng video (file hỏng hoặc không phải video)", code="bad_video")
    count = max(2, min(count, MAX_FRAMES))
    os.makedirs(out_dir, exist_ok=True)
    ffmpeg = find_ffmpeg()
    frames = []
    margin = min(0.5, duration / (count + 1))
    for i in range(count):
        t = margin + (duration - 2 * margin) * i / (count - 1) if count > 1 else duration / 2
        out_path = os.path.join(out_dir, f"frame_{i + 1:02d}.jpg")
        proc = subprocess.run([ffmpeg, "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-q:v", "2", out_path],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode == 0 and os.path.exists(out_path):
            frames.append(out_path)
    if not frames:
        raise VideoAnalysisError("không trích được khung hình nào từ video", code="bad_video")
    return frames


def build_prompt(character_name: str, meta: Dict, note: Optional[str] = None) -> str:
    dur = f"{meta['duration_sec']:.1f} giây" if meta.get("duration_sec") else "không rõ thời lượng"
    res = f"{meta['width']}x{meta['height']}" if meta.get("width") else "không rõ độ phân giải"
    extra = f"\n\nGhi chú thêm từ người xem: {note.strip()}" if note and note.strip() else ""
    return (
        f"Đây là {len(meta.get('frame_labels', []) or [])} khung hình lấy đều theo thời gian từ một video gameplay Free Fire "
        f"({dur}, {res}), nhân vật \"{character_name}\". Video là NGUỒN THẬT DUY NHẤT — chỉ ghi lại những gì các khung hình "
        "này thực sự cho thấy, tuyệt đối không tự suy diễn hoặc bịa thêm chi tiết không nhìn thấy.\n\n"
        "Với MỖI nhận định, gắn một trong bốn nhãn ngay sau câu: [OBSERVED] (nhìn thấy trực tiếp trong khung hình), "
        "[EXPLICIT] (chữ overlay/HUD trong khung hình nói rõ), [INFERRED] (suy luận hợp lý nhưng không thấy trực tiếp — "
        "nói rõ vì sao), hoặc [UNKNOWN] (không có khung hình nào xác nhận — đừng bịa số liệu như sát thương/thời gian hồi/"
        "tầm bắn chỉ vì \"nghe hợp lý\", cứ ghi UNKNOWN).\n\n"
        "Viết bằng tiếng Việt, theo đúng cấu trúc:\n\n"
        "### Nhận dạng nhân vật\n"
        "- Tóc, khuôn mặt, trang phục (từng lớp áo/giáp/khăn), vũ khí, bảng màu chính-phụ, đặc điểm nhận diện silhouette "
        "(cái gì giúp nhận ra nhân vật này ở cỡ ảnh nhỏ).\n\n"
        "### Kỹ năng / hiệu ứng đang dùng (nếu khung hình cho thấy)\n"
        "- Tên skill (nếu overlay hiện rõ), cách kích hoạt, hình học + màu + chuyển động của VFX, VFX neo vào đâu "
        "(mặt đất/người/vũ khí/mục tiêu), quan hệ không gian giữa nhân vật và hiệu ứng (xuyên tường, dịch chuyển, tầm...), "
        "sát thương/thời gian hồi/tầm CHỈ khi có số hiện rõ trong khung hình.\n\n"
        "### Các giai đoạn theo thời gian (bài học hồ sơ Kenta / Orion — knowledge/skill_dossier_method.md)\n"
        "- Chia kỹ năng thành các giai đoạn NỐI TIẾP, mỗi giai đoạn một dòng: tên ngắn · mốc giây (từ nhãn khung) · điều nhìn thấy · "
        "độ dài ước tính. Mỗi giai đoạn tả cả TRẠNG THÁI TAY / VŨ KHÍ (cầm gì, kiếm trong vỏ hay đã rút, tay không) và nơi hiệu ứng neo.\n"
        "- Phân biệt rõ: cái người chơi thấy rất nhanh (vài khung) khác với cái kéo dài; không gộp.\n\n"
        "### Chỉ báo giao diện — KHÔNG phải kỹ năng, KHÔNG vẽ\n"
        "- Liệt kê mọi thứ thuộc giao diện game chứ không thuộc hiệu ứng: thanh máu / năng lượng, số sát thương, chữ banner, nút bấm, "
        "vệt đỏ chỉ hướng sát thương quanh người trúng đòn, thanh / vòng / mũi tên định hướng hoặc phạm vi kỹ năng (vd tấm sọc ngang "
        "trong suốt cạnh chân hay tay nhân vật là chỉ báo nhắm, không phải vũ khí). Chưa chắc là của kỹ năng hay giao diện → ghi "
        "[UNKNOWN], không tự quyết.\n\n"
        "### Tương tác (chỉ những gì thấy)\n"
        "- Hiệu ứng gặp thứ gì (tường, đạn, kẻ địch, kỹ năng khác) và điều xảy ra, kèm mốc giây. Chưa thấy trong video thì KHÔNG ghi "
        "như đã biết.\n\n"
        "### Danh sách không được vẽ\n"
        "- Những thứ mô tả cũ / phiên bản cũ / thói quen của model hay vẽ nhầm cho kỹ năng này (vd rút kiếm, khiên, vỡ tường, giáp phát "
        "sáng bọc người, hiệu ứng đặc tối màu) — mỗi mục kèm lý do ngắn.\n\n"
        "### Không xác nhận được\n"
        "- Liệt kê ngắn các điểm quan trọng mà khung hình KHÔNG cho thấy rõ (để tránh người đọc sau này tưởng là đã biết)."
        + extra
    )


def analyze(client, character_name: str, frame_paths: List[str], meta: Dict, note: Optional[str] = None) -> str:
    if not frame_paths:
        raise VideoAnalysisError("chưa có khung hình để phân tích", code="no_frames")
    meta = dict(meta, frame_labels=frame_paths)
    images: List[Tuple[str, str]] = [(f"Khung hình {i} (~{meta['duration_sec'] * (i - 1) / max(len(frame_paths) - 1, 1):.1f}s):"
                                      if meta.get("duration_sec") else f"Khung hình {i}:", p)
                                     for i, p in enumerate(frame_paths, 1)]
    with llm_runner.tagged("video_analysis"):
        reply = client.complete(build_prompt(character_name, meta, note), images)
    text = reply.text.strip()
    if not text:
        raise llm_runner.LlmError("Claude không trả lời gì", code="empty")
    return text


def with_block(description: str, text: str, source_note: str) -> str:
    return assets.replace_block(description, MARK, f"({source_note}) {text}")
