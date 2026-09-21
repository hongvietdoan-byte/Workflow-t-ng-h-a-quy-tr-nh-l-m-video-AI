"""Draw the tool's logo: a "G" that transforms into a play button (video), with a spark.

Writes tools/logo_g.ico (both shortcuts), assets/logo_g.png (1024 px, avatar) and assets/logo_g_192.png (browser tab icon).
Needs Pillow.   py tools/make_icon.py
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw

ROOT = os.path.join(os.path.dirname(__file__), "..")
S = 2048                      # drawn at 2x, scaled down for smooth edges
TOP, BOTTOM = (79, 70, 229), (219, 39, 119)          # indigo -> pink


def gradient() -> Image.Image:
    img = Image.new("RGB", (S, S))
    px = img.load()
    for y in range(S):
        for x in range(0, S):
            t = (x * 0.35 + y * 0.65) / S
            px[x, y] = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
    return img


def spark(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill) -> None:
    pts = []
    for k in range(8):
        ang = math.pi / 4 * k - math.pi / 2
        rad = r if k % 2 == 0 else r * 0.28
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def draw() -> Image.Image:
    bg = gradient().convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=470, fill=255)
    logo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    logo.paste(bg, (0, 0), mask)

    fg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    cx = cy = S // 2
    outer, width = 640, 210
    box = [cx - outer, cy - outer, cx + outer, cy + outer]
    d.arc(box, start=-4, end=312, fill="white", width=width)      # the G: a ring open at the upper right
    mid = outer - width / 2                                        # round caps on both ends of the ring
    for ang in (-4, 312):
        x, y = cx + mid * math.cos(math.radians(ang)), cy + mid * math.sin(math.radians(ang))
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill="white")
    d.polygon([(cx - 300, cy - 240), (cx - 300, cy + 240), (cx + 90, cy)], fill="white")     # the play button ...
    d.rectangle([cx + 40, cy - 78, cx + outer - width / 2, cy + 78], fill="white")            # ... continues as the G's bar
    spark(d, cx + 470, cy - 500, 210, (255, 224, 102, 255))        # the "transformation" spark in the ring's opening
    spark(d, cx + 655, cy - 245, 90, (255, 255, 255, 235))

    shadow = ImageChops.offset(fg.split()[3], 0, 28).point(lambda v: int(v * 0.28))
    dark = Image.new("RGBA", (S, S), (30, 20, 80, 0))
    dark.putalpha(shadow)
    logo = Image.alpha_composite(Image.alpha_composite(logo, dark), fg)
    return logo.resize((1024, 1024), Image.LANCZOS)


if __name__ == "__main__":
    logo = draw()
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    logo.save(os.path.join(ROOT, "assets", "logo_g.png"))
    logo.resize((192, 192), Image.LANCZOS).save(os.path.join(ROOT, "assets", "logo_g_192.png"))
    logo.save(os.path.join(ROOT, "tools", "logo_g.ico"), sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("ok")
