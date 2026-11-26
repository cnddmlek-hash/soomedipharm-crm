#!/usr/bin/env python3
"""수메디팜 미니 CRM — PWA 아이콘 생성기.

디자인: 네이비 그라데이션 바탕 + 흰/시안 알약(캡슐) 모양을 크게 배치.
작은 크기(32px)에서도 형태가 살아 있도록 요소를 최소화했습니다.

  - icon-192.png / icon-512.png      : 둥근 모서리(any)
  - icon-maskable-512.png            : 전체 채움 + 안전영역(80%) 안쪽 배치
  - apple-touch-icon.png (180x180)   : iOS 홈 화면용(모서리 없이 iOS가 둥글게 처리)
  - favicon-32.png                   : 브라우저 탭용

사용: python3 tools/make_icons.py
"""
import os

from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAVY_TOP = (30, 58, 95)      # #1e3a5f
NAVY_BOTTOM = (37, 74, 122)  # #254a7a
CYAN = (14, 165, 233)        # #0ea5e9
WHITE = (255, 255, 255)


def gradient(size, top, bottom):
    img = Image.new("RGB", (size, size), top)
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(size - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (size, y)], fill=c)
    # 좌상단 은은한 하이라이트
    glow = Image.new("L", (size, size), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-size * 0.40, -size * 0.50, size * 0.90, size * 0.55], fill=46)
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.16))
    light = Image.new("RGB", (size, size), (255, 255, 255))
    return Image.composite(light, img, glow).convert("RGBA")


def capsule_layer(size, scale=1.0):
    """캡슐(알약) 레이어. 왼쪽 흰색 / 오른쪽 시안, 가운데 접합선."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    w = int(size * 0.78 * scale)
    h = int(size * 0.33 * scale)
    x0 = (size - w) // 2
    y0 = (size - h) // 2
    r = h // 2

    # 그림자
    sh = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [x0, y0 + int(size * 0.045), x0 + w, y0 + h + int(size * 0.045)],
        radius=r, fill=(6, 16, 30, 135),
    )
    sh = sh.filter(ImageFilter.GaussianBlur(size * 0.025))
    layer.alpha_composite(sh)

    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=r, fill=WHITE)

    # 오른쪽 절반만 시안으로
    half = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(half).rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=r, fill=CYAN)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rectangle([x0 + w // 2, y0 - 2, x0 + w + 2, y0 + h + 2], fill=255)
    layer.paste(half, (0, 0), Image.composite(half.split()[3], Image.new("L", (size, size), 0), mask))

    # 접합선
    d = ImageDraw.Draw(layer)
    d.line([(x0 + w // 2, y0 + int(h * 0.10)), (x0 + w // 2, y0 + h - int(h * 0.10))],
           fill=(255, 255, 255, 200), width=max(2, int(size * 0.009)))

    # 광택
    gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rounded_rectangle(
        [x0 + int(w * 0.05), y0 + int(h * 0.13), x0 + int(w * 0.95), y0 + int(h * 0.44)],
        radius=int(h * 0.16), fill=(255, 255, 255, 78),
    )
    gloss = gloss.filter(ImageFilter.GaussianBlur(size * 0.007))
    layer.alpha_composite(gloss)
    return layer


def build(size, maskable=False):
    img = gradient(size, NAVY_TOP, NAVY_BOTTOM)
    scale = 0.86 if maskable else 1.0
    cap = capsule_layer(size, scale=scale).rotate(
        -38, resample=Image.BICUBIC, center=(size / 2, size / 2)
    )
    img.alpha_composite(cap)
    if not maskable:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255
        )
        img.putalpha(mask)
    return img


def main():
    out = {
        "icon-192.png": build(192),
        "icon-512.png": build(512),
        "icon-maskable-512.png": build(512, maskable=True),
        "apple-touch-icon.png": build(180),
        "favicon-32.png": build(32),
    }
    for name, im in out.items():
        path = os.path.join(OUT_DIR, name)
        im.save(path, "PNG", optimize=True)
        print(f"wrote {path} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
