"""Draw tools/icon.ico (purple rounded square + play triangle, like the dashboard logo). Needs Pillow."""
import os

from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=56, fill="#4F46E5")
d.polygon([(96, 72), (96, 184), (190, 128)], fill="white")
img.save(os.path.join(os.path.dirname(__file__), "icon.ico"), sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
