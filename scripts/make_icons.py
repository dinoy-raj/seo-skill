"""Favicon set and a 1200x630 social card from one image.  pip install Pillow

    python3 make_icons.py photo.jpg --out .                          # favicon-192.png, favicon.ico, apple-touch-icon.png
    python3 make_icons.py photo.jpg --out . --focus 0.5,0.35         # crop centre as fractions (x,y) of the image, e.g. a face
    python3 make_icons.py photo.jpg --og "Jane Doe" "Product Designer" --out assets   # also assets/og.jpg

Google only shows a favicon in results if it is square, a multiple of 48 px and crawlable; an SVG letter tile often gets
ignored, a 192x192 PNG works. favicon.ico (16/32/48) also stops the /favicon.ico 404 in the console. apple-touch-icon is
180x180 with no transparency. The social card is 1200x630 JPEG (Open Graph / summary_large_image), image on the left,
name and role on the right, readable at 600 px wide. Edit BG/FG for the site's colours.
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont, ImageOps

BG, FG, MUTED = (251, 246, 238), (31, 26, 22), (110, 100, 92)


def square(img, focus):
    w, h = img.size; side = min(w, h)
    cx, cy = focus[0] * w, focus[1] * h
    left = int(min(max(cx - side / 2, 0), w - side)); top = int(min(max(cy - side / 2, 0), h - side))
    return img.crop((left, top, left + side, top + side))


def font(size, bold=False):
    for name in (["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]):
        for d in ("", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", "C:/Windows/Fonts/"):
            try: return ImageFont.truetype(d + name, size)
            except OSError: pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image"); ap.add_argument("--out", default=".")
    ap.add_argument("--focus", default="0.5,0.5"); ap.add_argument("--og", nargs=2, metavar=("NAME", "ROLE"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    img = ImageOps.exif_transpose(Image.open(a.image)).convert("RGB")
    sq = square(img, tuple(float(x) for x in a.focus.split(",")))
    sq.resize((192, 192), Image.LANCZOS).save(os.path.join(a.out, "favicon-192.png"), optimize=True)
    sq.resize((180, 180), Image.LANCZOS).save(os.path.join(a.out, "apple-touch-icon.png"), optimize=True)
    sq.resize((48, 48), Image.LANCZOS).save(os.path.join(a.out, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    print("wrote favicon-192.png, apple-touch-icon.png, favicon.ico")
    if a.og:
        card = Image.new("RGB", (1200, 630), BG)
        card.paste(sq.resize((470, 470), Image.LANCZOS), (80, 80))
        d = ImageDraw.Draw(card)
        name, role = a.og
        size = 76
        while size > 36 and d.textlength(name, font=font(size, True)) > 560: size -= 4
        d.text((600, 230), name, font=font(size, True), fill=FG)
        d.text((600, 230 + size + 24), role, font=font(36), fill=MUTED)
        card.save(os.path.join(a.out, "og.jpg"), quality=85, optimize=True, progressive=True)
        print("wrote og.jpg (1200x630)")


if __name__ == "__main__":
    main()
