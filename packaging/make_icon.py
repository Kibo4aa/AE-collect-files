"""Membuat ikon aplikasi (folder + tanda plus). Butuh Pillow.

    python packaging/make_icon.py

Hasil: src/collect_files_plus/assets/icon.png, packaging/icon.ico, packaging/icon.icns
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
S = 1024  # digambar besar lalu diperkecil supaya halus


def draw() -> Image.Image:
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    top, bottom = (52, 56, 92), (26, 28, 48)
    for y in range(S):
        t = y / (S - 1)
        gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([16, 16, S - 17, S - 17], radius=220, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    back = (217, 131, 36, 255)
    front = (247, 181, 56, 255)
    d.rounded_rectangle([180, 250, 470, 380], radius=44, fill=back)          # tab folder
    d.rounded_rectangle([180, 320, 844, 760], radius=52, fill=back)          # bagian belakang
    d.rounded_rectangle([180, 420, 844, 790], radius=52, fill=front)         # bagian depan
    d.rounded_rectangle([180, 420, 844, 470], radius=24, fill=(255, 205, 105, 255))  # kilau

    cx, cy, r = 742, 744, 178                                                # lencana plus
    d.ellipse([cx - r - 26, cy - r - 26, cx + r + 26, cy + r + 26], fill=(26, 28, 48, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(46, 196, 182, 255))
    arm, w = 104, 34
    d.rounded_rectangle([cx - arm, cy - w, cx + arm, cy + w], radius=w, fill=(255, 255, 255, 255))
    d.rounded_rectangle([cx - w, cy - arm, cx + w, cy + arm], radius=w, fill=(255, 255, 255, 255))
    return img


def main() -> None:
    big = draw()
    png = ROOT / "src" / "collect_files_plus" / "assets" / "icon.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    big.resize((256, 256), Image.LANCZOS).save(png, optimize=True)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    big.resize((256, 256), Image.LANCZOS).save(ROOT / "packaging" / "icon.ico", sizes=sizes)
    big.resize((1024, 1024), Image.LANCZOS).save(ROOT / "packaging" / "icon.icns")
    print("ikon dibuat:", png)


if __name__ == "__main__":
    main()
