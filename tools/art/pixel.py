"""픽셀 그림 도우미: 결정적 난수, 이음매 없는 노이즈, 자동 외곽선, 간단한 음영."""
import random

import numpy as np
from PIL import Image, ImageDraw

OUTLINE = (59, 42, 42, 255)       # 진한 갈색 외곽선 #3b2a2a


def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] * (1 - t) + c2[i] * t)) for i in range(3)) + (c1[3] if len(c1) > 3 else 255,)


def shade(c, k):
    """k>0 밝게, k<0 어둡게 (0~1)."""
    if k >= 0:
        return mix(c, (255, 255, 255, 255), k)
    return mix(c, (20, 12, 12, 255), -k)


class Rng:
    def __init__(self, *keys):
        self.r = random.Random("|".join(map(str, keys)))

    def __getattr__(self, name):
        return getattr(self.r, name)


def periodic_noise(size, cells, seed):
    """이음매 없는 값 노이즈 (size×size, 격자 cells×cells를 주기로)."""
    rng = np.random.default_rng(abs(hash(seed)) % (2 ** 32))
    g = rng.random((cells, cells))
    out = np.zeros((size, size))
    for y in range(size):
        for x in range(size):
            gx, gy = x * cells / size, y * cells / size
            x0, y0 = int(gx) % cells, int(gy) % cells
            x1, y1 = (x0 + 1) % cells, (y0 + 1) % cells
            tx, ty = gx - int(gx), gy - int(gy)
            tx = tx * tx * (3 - 2 * tx)
            ty = ty * ty * (3 - 2 * ty)
            a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
            b = g[y1, x0] * (1 - tx) + g[y1, x1] * tx
            out[y, x] = a * (1 - ty) + b * ty
    return out


class Canvas:
    """RGBA 캔버스. 도형은 마스크 레이어로 그리고, 외곽선과 음영은 마스크에서 계산한다."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 4), dtype=np.uint8)

    def img(self):
        return Image.fromarray(self.px, "RGBA")

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y, x] = c

    def mask(self, draw_fn):
        im = Image.new("L", (self.w, self.h), 0)
        draw_fn(ImageDraw.Draw(im))
        return np.array(im) > 0

    def fill(self, m, c, light=0.0, dark=0.0):
        """마스크를 c로 칠하고, 위·왼쪽 가장자리는 밝게, 아래·오른쪽 가장자리는 어둡게."""
        h, w = m.shape
        for y in range(h):
            for x in range(w):
                if not m[y, x]:
                    continue
                col = c
                up = y == 0 or not m[y - 1, x]
                left = x == 0 or not m[y, x - 1]
                down = y == h - 1 or not m[y + 1, x]
                right = x == w - 1 or not m[y, x + 1]
                if dark and (down or right):
                    col = shade(c, -dark)
                elif light and (up or left):
                    col = shade(c, light)
                self.px[y, x] = col

    def outline(self, color=OUTLINE):
        a = self.px[:, :, 3] > 0
        out = []
        for y in range(self.h):
            for x in range(self.w):
                if a[y, x]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and a[ny, nx]:
                        out.append((x, y))
                        break
        for x, y in out:
            self.px[y, x] = color
