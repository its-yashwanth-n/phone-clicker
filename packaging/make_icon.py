"""Draws the app icon (packaging/icon.png and icon.ico). Run: python packaging/make_icon.py"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent
SIZE = 1024
SCALE = 4  # draw big, then shrink, for smooth edges
BLUE = (79, 124, 255)
WHITE = (255, 255, 255)


def draw():
    s = SIZE * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def box(x0, y0, x1, y1):
        return [int(v * s) for v in (x0, y0, x1, y1)]

    # Rounded blue background
    d.rounded_rectangle(box(0.04, 0.04, 0.96, 0.96), radius=int(0.22 * s), fill=BLUE)
    # White phone
    d.rounded_rectangle(box(0.31, 0.15, 0.69, 0.85), radius=int(0.08 * s), fill=WHITE)
    # Blue "next" chevron on the phone screen
    w = int(0.055 * s)
    pts = [(0.45 * s, 0.38 * s), (0.56 * s, 0.50 * s), (0.45 * s, 0.62 * s)]
    d.line(pts, fill=BLUE, width=w, joint="curve")
    for x, y in (pts[0], pts[2]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=BLUE)
    # Speaker slot
    d.rounded_rectangle(box(0.45, 0.19, 0.55, 0.21), radius=int(0.01 * s), fill=BLUE)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    icon = draw()
    icon.save(HERE / "icon.png")
    icon.save(HERE / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Wrote icon.png and icon.ico")
