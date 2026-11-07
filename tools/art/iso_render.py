"""2.5D 아이소메트릭 목업용 소형 렌더러.

Godot 화면과 같은 조건으로 그린다: 직교 카메라 수평 45°, 아래로 30°(2:1), 텍셀 밀도 16/m,
저해상도 내부 화면을 정수배로 키움. 볼록 다면체(상자, 맞배·우진각·사각뿔 지붕)를
평행 광선으로 교차시키고, 면마다 8×8 텍스처를 붙이고, 물체 윤곽에 1픽셀 외곽선을 칠한다.
"""
import math

import numpy as np

TEX_PER_M = 16
OUTLINE = np.array([59, 42, 42], dtype=np.float32)


class Camera:
    def __init__(self, w, h, center, px_per_m_x=16.0, yaw=45, pitch=30):
        self.w, self.h = w, h
        th, ph = math.radians(pitch), math.radians(yaw)
        hdir = np.array([-math.sin(ph), 0.0, -math.cos(ph)])
        self.d = math.cos(th) * hdir + np.array([0.0, -math.sin(th), 0.0])
        self.r = np.array([math.cos(ph), 0.0, -math.sin(ph)])
        self.u = np.cross(self.r, self.d)
        self.s = px_per_m_x / abs(self.r[0])
        self.center = np.array(center, dtype=np.float64)

    def rays(self):
        j, i = np.mgrid[0:self.h, 0:self.w]
        dx = (i + 0.5 - self.w / 2) / self.s
        dy = (j + 0.5 - self.h / 2) / self.s
        o = (self.center[None, None, :] + dx[..., None] * self.r - dy[..., None] * self.u - 200 * self.d)
        return o.reshape(-1, 3)


class Poly:
    """볼록 다면체. faces: (법선, c, 재질, uv 방식). 안쪽은 n·p <= c."""

    def __init__(self, faces, origin, tag=None):
        self.faces = []
        for n, c, mat, uv in faces:
            n = np.array(n, dtype=np.float64)
            k = np.linalg.norm(n)
            self.faces.append((n / k, c / k, mat, uv))
        self.origin = np.array(origin, dtype=np.float64)
        self.tag = tag


def box(x0, y0, z0, x1, y1, z1, top, side_z=None, side_x=None, bottom=None, tag=None):
    side_z = side_z if side_z is not None else top
    side_x = side_x if side_x is not None else side_z
    bottom = bottom if bottom is not None else top
    f = [((1, 0, 0), x1, side_x, "x"), ((-1, 0, 0), -x0, side_x, "x"),
         ((0, 1, 0), y1, top, "top"), ((0, -1, 0), -y0, bottom, "top"),
         ((0, 0, 1), z1, side_z, "z"), ((0, 0, -1), -z0, side_z, "z")]
    return Poly(f, (x0, y1, z0), tag)


def gable(x0, z0, x1, z1, y0, y1, roof, gable_mat, axis="x", tag=None):
    """맞배지붕. axis="x"면 용마루가 x축 방향."""
    if axis == "x":
        zm = (z0 + z1) / 2
        f = [((0, -1, 0), -y0, roof, "top"), ((-1, 0, 0), -x0, gable_mat, "x"), ((1, 0, 0), x1, gable_mat, "x"),
             ((0, z1 - zm, y1 - y0), y0 * (z1 - zm) + (y1 - y0) * z1, roof, "slope"),
             ((0, zm - z0, -(y1 - y0)), y0 * (zm - z0) - (y1 - y0) * z0, roof, "slope")]
    else:
        xm = (x0 + x1) / 2
        f = [((0, -1, 0), -y0, roof, "top"), ((0, 0, -1), -z0, gable_mat, "z"), ((0, 0, 1), z1, gable_mat, "z"),
             ((x1 - xm, y1 - y0, 0), y0 * (x1 - xm) + (y1 - y0) * x1, roof, "slope"),
             ((xm - x0, -(y1 - y0), 0), y0 * (xm - x0) - (y1 - y0) * x0, roof, "slope")]
    return Poly(f, (x0, y1, z0), tag)


def hip(x0, z0, x1, z1, y0, y1, roof, inset_x=None, inset_z=None, tag=None):
    """우진각(또는 사각뿔). 용마루는 inset만큼 안쪽에서 끝난다."""
    zm = (z0 + z1) / 2
    xm = (x0 + x1) / 2
    ix = inset_x if inset_x is not None else (x1 - x0) / 2
    iz = inset_z if inset_z is not None else (z1 - z0) / 2
    xr0, xr1 = x0 + ix, x1 - ix
    zr0, zr1 = z0 + iz, z1 - iz
    h = y1 - y0
    f = [((0, -1, 0), -y0, roof, "top"),
         ((0, z1 - zr1, h), y0 * (z1 - zr1) + h * z1, roof, "slope"),
         ((0, zr0 - z0, -h), y0 * (zr0 - z0) - h * z0, roof, "slope"),
         ((h, x1 - xr1, 0), y0 * (x1 - xr1) + h * x1, roof, "slope"),
         ((-h, xr0 - x0, 0), y0 * (xr0 - x0) - h * x0, roof, "slope")]
    return Poly(f, (x0, y1, z0), tag)


def _sample(mat, u, v, tiles):
    """mat: 재질 이름(아틀라스), 8×8 RGBA 배열, 또는 (r,g,b) 단색."""
    if isinstance(mat, tuple):
        return np.tile(np.array(mat, dtype=np.float32)[None, :3], (len(u), 1)), np.ones(len(u), bool)
    if isinstance(mat, str) and mat.endswith("*"):
        # 칸마다 변형과 뒤집기를 섞어 반복 무늬를 깬다 (바닥 재질용)
        base = mat[:-1]
        t0, t1 = tiles(base), tiles(base + "#1")
        cu, cv = np.floor(u / 8).astype(int), np.floor(v / 8).astype(int)
        hsh = (cu * 73856093) ^ (cv * 19349663)
        hsh = (hsh ^ (hsh >> 7)) & 0xFF
        lu = np.floor(u).astype(int) % 8
        lv = np.floor(v).astype(int) % 8
        lu = np.where(hsh & 2, 7 - lu, lu)
        lv = np.where(hsh & 4, 7 - lv, lv)
        px = np.where((hsh & 1)[:, None] == 1, t1[lv, lu], t0[lv, lu]).astype(np.float32)
        return px[:, :3], px[:, 3] > 0
    t = tiles(mat) if isinstance(mat, str) else mat
    tu = np.floor(u).astype(int) % t.shape[1]
    tv = np.floor(v).astype(int) % t.shape[0]
    px = t[tv, tu].astype(np.float32)
    return px[:, :3], px[:, 3] > 0


def render(cam, polys, tiles, sky=(190, 228, 255), light=(0.45, 1.0, 0.65)):
    o = cam.rays()
    d = cam.d
    n_pix = o.shape[0]
    best_t = np.full(n_pix, np.inf)
    color = np.tile(np.array(sky, dtype=np.float32), (n_pix, 1))
    obj = np.full(n_pix, -1)
    L = np.array(light) / np.linalg.norm(light)
    for pi, poly in enumerate(polys):
        t_in = np.full(n_pix, -np.inf)
        t_out = np.full(n_pix, np.inf)
        hit_face = np.full(n_pix, -1)
        ok = np.ones(n_pix, bool)
        for fi, (n, c, _, _) in enumerate(poly.faces):
            den = n @ d
            num = c - o @ n
            if abs(den) < 1e-9:
                ok &= num >= 0
                continue
            t = num / den
            if den < 0:
                upd = t > t_in
                t_in = np.where(upd, t, t_in)
                hit_face = np.where(upd, fi, hit_face)
            else:
                t_out = np.minimum(t_out, t)
        hit = ok & (t_in <= t_out) & (t_in < best_t) & (hit_face >= 0)
        if not hit.any():
            continue
        idx = np.nonzero(hit)[0]
        p = o[idx] + t_in[idx, None] * d
        rel = p - poly.origin
        col = np.zeros((len(idx), 3), np.float32)
        opaque = np.zeros(len(idx), bool)
        for fi, (n, c, mat, uvm) in enumerate(poly.faces):
            sel = hit_face[idx] == fi
            if not sel.any():
                continue
            r = rel[sel]
            if uvm == "top":
                u, v = r[:, 0] * TEX_PER_M, r[:, 2] * TEX_PER_M
            elif uvm == "z":
                u, v = r[:, 0] * TEX_PER_M, -r[:, 1] * TEX_PER_M
            elif uvm == "x":
                u, v = -r[:, 2] * TEX_PER_M, -r[:, 1] * TEX_PER_M
            else:
                ua = np.cross(n, [0, 1, 0])
                ua = ua / (np.linalg.norm(ua) + 1e-9)
                va = np.cross(ua, n)
                if va[1] > 0:
                    va = -va
                u, v = r @ ua * TEX_PER_M, -(r @ va) * TEX_PER_M
            cc, op = _sample(mat, u, v, tiles)
            if n[1] > 0.9:
                k = 1.0
            elif abs(n[1]) < 0.1:
                k = 0.86 if abs(n[2]) > abs(n[0]) else 0.7
            else:
                k = 0.62 + 0.38 * max(0.0, float(n @ L))
            col[sel] = cc * k
            opaque[sel] = op
        keep = opaque
        gi = idx[keep]
        best_t[gi] = t_in[gi]
        color[gi] = col[keep]
        obj[gi] = pi
    # 외곽선: 더 먼 쪽 픽셀에 칠한다(물체 밖 1픽셀)
    H, W = cam.h, cam.w
    img = color.reshape(H, W, 3)
    ob = obj.reshape(H, W)
    tt = best_t.reshape(H, W)
    tags = {i: p.tag for i, p in enumerate(polys)}
    tag_map = np.vectorize(lambda k: tags.get(k) or (f"#{k}" if k >= 0 else "sky"))(ob)
    edge = np.zeros((H, W), bool)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nb_tag = np.roll(np.roll(tag_map, dy, 0), dx, 1)
        nb_t = np.roll(np.roll(tt, dy, 0), dx, 1)
        edge |= (nb_tag != tag_map) & (nb_t + 0.25 < tt)
    edge[0, :] = edge[-1, :] = False
    edge[:, 0] = edge[:, -1] = False
    img[edge] = OUTLINE
    return np.clip(img, 0, 255).astype(np.uint8)
