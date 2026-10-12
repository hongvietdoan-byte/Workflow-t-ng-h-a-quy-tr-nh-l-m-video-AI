"""Kiểm/đặt lớp phủ cục bộ bằng đúng bảng subtitles, không gọi model."""
import math
from . import features, subtitles


def policy(platform='tiktok'):
    return {'version': 1, 'box': subtitles.safe_box(platform)} if features.on('overlay_safe_zone') else None


def bounds(size, platform='tiktok'):
    w, h = size
    box = subtitles.safe_box(platform)
    return (math.ceil(w * box['left']), math.ceil(h * box['top']),
            math.floor(w * (1 - box['right'])), math.floor(h * (1 - box['bottom'])))


def place(image, platform='tiktok', output_size=None):
    """Ảnh RGBA chỉ chứa nội dung, KHÔNG gồm nền/shade toàn khung.

    TẮT trả nguyên ảnh. Cảnh báo luôn là VÀNG, không chặn dựng.
    """
    rect = image.getbbox()
    size = output_size or image.size
    box = bounds(size, platform)
    if rect is None or (rect[0] >= box[0] and rect[1] >= box[1] and rect[2] <= box[2] and rect[3] <= box[3]):
        return image, None
    note = {'muc': 'vang', 'bounds': list(rect), 'suggested': list(box),
            'message': 'Lớp phủ lấn giao diện app; đặt trong vùng an toàn theo nền tảng.', 'adjusted': False}
    if not features.on('overlay_safe_zone'):
        return image, note
    from PIL import Image
    content = image.crop(rect)
    ratio = min(1., (box[2] - box[0]) / content.width, (box[3] - box[1]) / content.height)
    content = content.resize((max(1, int(content.width * ratio)), max(1, int(content.height * ratio))))
    x = min(max(rect[0], box[0]), box[2] - content.width)
    y = min(max(rect[1], box[1]), box[3] - content.height)
    result = Image.new('RGBA', size)
    result.alpha_composite(content, (x, y))
    note.update(adjusted=True, placed=list(result.getbbox()))
    return result, note
