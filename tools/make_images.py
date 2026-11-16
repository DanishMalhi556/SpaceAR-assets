"""Product images and colours for every downloaded item.

    python -I make_images.py <work dir> <assets repo> <backend dir> [id,id,...]

- Transparent renders (Poly Haven): trimmed to the product, centred on an
  800 x 800 transparent square with padding, saved as WebP.
- Screenshots with a background (Khronos): the background colour is taken
  from the border; the image is padded to a square in that colour.
- Colours: K-Means (the backend's own implementation) over the product's
  pixels only, K=3, keeping colours with at least a 12% share.
Writes <assets>/images/<id>.webp and <work>/colors.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

work, assets, backend = (Path(a) for a in sys.argv[1:4])
sys.path.insert(0, str(backend))
from services.vision.colors import kmeans, lab_to_rgb, rgb_to_lab, to_hex  # noqa: E402

SIDE, PAD = 800, 0.07


def product_pixels(img: Image.Image) -> tuple[np.ndarray, tuple | None]:
    """RGB pixels belonging to the product, and the background colour (or None if transparent)."""
    small = img.copy()
    small.thumbnail((160, 160))
    a = np.asarray(small.convert("RGBA")).astype(np.float32)
    if (a[..., 3] < 250).mean() > 0.05:  # transparent cut-out
        return a[a[..., 3] > 200][:, :3], None
    rgb = a[..., :3]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.linalg.norm(rgb_to_lab(rgb.reshape(-1, 3)) - rgb_to_lab(bg[None]), axis=1)
    return rgb.reshape(-1, 3)[dist > 12], tuple(int(v) for v in bg)


def colors(pixels: np.ndarray) -> list[str]:
    centers, counts = kmeans(rgb_to_lab(pixels).astype(np.float32), 3)
    rgb = lab_to_rgb(centers)
    share = counts / counts.sum()
    return [to_hex(rgb[i]) for i in range(len(centers)) if share[i] >= 0.12]


def square(img: Image.Image, bg: tuple | None) -> Image.Image:
    if bg is None:
        img = img.convert("RGBA")
        img = img.crop(img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
        canvas = Image.new("RGBA", (SIDE, SIDE), (0, 0, 0, 0))
    else:
        img = img.convert("RGB")
        canvas = Image.new("RGB", (SIDE, SIDE), bg)
    inner = int(SIDE * (1 - 2 * PAD))
    scale = min(inner / img.width, inner / img.height)  # up or down, so every product fills the frame
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas.paste(img, ((SIDE - img.width) // 2, (SIDE - img.height) // 2), img if bg is None else None)
    return canvas


def remove_background(img: Image.Image, tolerance: int = 38) -> Image.Image:
    """Makes a plain or gently graded studio background transparent by flood
    filling from points all round the border, then softens the cut edge."""
    from PIL import ImageDraw, ImageFilter

    rgb = img.convert("RGB")
    marker = (255, 0, 255)
    filled = rgb.copy()
    w, h = rgb.size
    step = max(8, min(w, h) // 40)
    seeds = [(x, y) for x in range(0, w, step) for y in (0, h - 1)] + \
            [(x, y) for y in range(0, h, step) for x in (0, w - 1)]
    for xy in seeds:
        if filled.getpixel(xy) != marker:
            ImageDraw.floodfill(filled, xy, marker, thresh=tolerance)
    bg = np.all(np.asarray(filled) == marker, axis=-1)
    alpha = Image.fromarray(np.where(bg, 0, 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


only = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None  # optional: just these ids
colors_file = work / "colors.json"
out = json.loads(colors_file.read_text(encoding="utf-8")) if only and colors_file.exists() else {}
for d in sorted((work / "raw").iterdir()):
    if only and d.name not in only:
        continue
    src = next(p for p in (d / "render.png", d / "render.jpg") if p.exists())
    img = Image.open(src)
    if src.suffix == ".jpg":  # studio screenshot with a background
        img = remove_background(img)
    pixels, bg = product_pixels(img)
    dest = assets / "images" / f"{d.name}.webp"
    square(img, bg).save(dest, "WEBP", quality=80, method=6)
    out[d.name] = colors(pixels)
    print(f"{d.name:28s} {dest.stat().st_size / 1024:6.0f} KB  {' '.join(out[d.name])}")
(work / "colors.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
