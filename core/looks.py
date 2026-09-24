"""The two picture looks the team makes (decided 2026-09-24, PLAN.md section 5): ANIME, and FF_INGAME = exactly like the Free Fire
in-game character art. A project property, separate from the editing style (style_profile = rhythm/shot sizes of a Free Fire video
style). It reaches every step: the image prompt's render sentence, which library pictures are preferred (asset_images.look), the
Director and QC, and the video model choice (W11)."""
from typing import Dict, Optional

LOOKS: Dict[str, Dict] = {
    "FF_INGAME": {
        "label": "Giống y hệt in-game Free Fire",
        "asset_look": "ingame",
        "image": ("Render style: Garena Free Fire in-game 3D character art — match the reference images exactly (same proportions, "
                  "materials, shading, colours and level of detail); not anime, not a realistic photo, not a different 3D style."),
        "director": ("Look của dự án: GIỐNG Y HỆT ảnh in-game Free Fire. Ảnh tài nguyên là chuẩn tuyệt đối về ngoại hình và chất liệu; "
                     "prompt ảnh không thêm phong cách vẽ khác (không anime, không ảnh thật)."),
        "qc": "Look: in-game Free Fire — trừ điểm `character`/`consistency` nếu ảnh ra kiểu anime, ảnh thật hoặc 3D khác ảnh tài nguyên.",
    },
    "ANIME": {
        "label": "Anime",
        "asset_look": "anime",
        "image": ("Render style: 2D anime illustration (clean line art, cel shading) of these exact characters — keep every person's "
                  "identity, hairstyle, outfit colours and accessories from the reference images; only the drawing style changes."),
        "director": ("Look của dự án: ANIME. Nhân vật giữ đúng nhận diện theo ảnh tài nguyên (tóc, màu trang phục, phụ kiện), chỉ đổi nét vẽ "
                     "sang anime; mọi prompt ảnh dùng cùng một cách tả phong cách anime để các shot đồng đều."),
        "qc": "Look: anime — nét vẽ anime đồng đều giữa các shot; nhân vật vẫn phải nhận ra đúng người theo ảnh tài nguyên.",
    },
}


def of(project_row) -> Optional[str]:
    try:
        value = project_row["look"]
    except (KeyError, IndexError, TypeError):
        return None
    return value if value in LOOKS else None


def image_sentence(project_row) -> str:
    look = of(project_row)
    return (" " + LOOKS[look]["image"]) if look else ""


def director_note(project_row) -> str:
    look = of(project_row)
    return ("# Look hình của dự án\n" + LOOKS[look]["director"]) if look else ""


def qc_note(project_row) -> str:
    look = of(project_row)
    return ("# Look hình của dự án\n" + LOOKS[look]["qc"]) if look else ""


def asset_look(project_row) -> Optional[str]:
    look = of(project_row)
    return LOOKS[look]["asset_look"] if look else None
