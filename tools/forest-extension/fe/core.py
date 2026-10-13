"""Data access, colour conversion and per-shape descriptors."""
import os, re, subprocess, numpy as np
from . import ROOT
from art import LAYERS, W, H, flatten, rasterize, hex2rgb, rgb2hex   # noqa: F401  (re-exported)
from pbart import PShape, tight_bounds                                  # noqa: F401

SWIFT = 'ios/mockjuice/Views/Components/ForestPathIllustration.swift'
SOURCE_MD5 = '06565e7dabc57e1377b32ef0e193e71d'   # working-tree file the extension continues (forest-v2 art, 17 layers)

def _source_text():
    import hashlib
    raw = open(os.path.join(ROOT, SWIFT), 'rb').read()
    if hashlib.md5(raw).hexdigest() != SOURCE_MD5:
        raise RuntimeError('ForestPathIllustration.swift changed since the analysis baseline (md5 mismatch)')
    return raw.decode()

def _layer_ids(text):
    m = re.search(r'enum LayerID: CaseIterable \{\s*case ([^\n]+)', text)
    return [x.strip() for x in m.group(1).split(',')]

LAYERS = _layer_ids(_source_text())      # back to front: overrides art.LAYERS (14 HEAD layers)

def source_layers():
    """Layer name -> list of data lines of the original illustration (working tree, md5-checked)."""
    text = _source_text(); out = {}; cur = None
    for line in text.split('\n'):
        m = re.match(r'\s*static let (\w+): String = """\s*$', line)
        if m: cur = m.group(1); out[cur] = []; continue
        if cur is not None:
            if line.strip() == '"""': cur = None
            elif line.strip(): out[cur].append(line.strip())
    return out

def load_original():
    L = source_layers()
    shapes = []
    for name in LAYERS:
        for k, line in enumerate(L[name]):
            s = PShape(name, line); s.region = k; shapes.append(s)
    return shapes

# --- colour -----------------------------------------------------------------------------------------------
def srgb2lin(c):
    c = np.asarray(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin2srgb(c):
    c = np.asarray(c, float); return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WP = np.array([0.95047, 1.0, 1.08883])
def rgb2lab(c):
    """sRGB 0..1 (..., 3) -> CIE Lab D65."""
    xyz = srgb2lin(c) @ _M.T / _WP
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def lab2rgb(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116; fx = fy + lab[..., 1] / 500; fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29)) * _WP
    return np.clip(lin2srgb(xyz @ np.linalg.inv(_M).T), 0, 1)
def de76(a, b):
    return float(np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)))

# --- per-shape descriptors -------------------------------------------------------------------------------
def polys(s, scale=1.0):
    return flatten(s.subs, scale)
def poly_area(P):
    x, y = P[:, 0], P[:, 1]; return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
def area(s):
    """Even-odd area approximated as |sum of signed subpath areas| per subpath (holes are opposite-wound in potrace output)."""
    return abs(sum(poly_area(P) for P in polys(s)))
def tbox(s):
    b = s.box; return (b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 1)
def mean_rgb(s):
    return s.cols.mean(0)

# --- rendering helpers (Python model == iOS CPU renderer to ~0.4/255) --------------------------------------
def render_box(shapes, box, scale=1.0, bg=None, ids=False):
    """Composite `shapes` into design-space `box` (x0, y0, x1, y1) at `scale` px/unit.
    Returns rgb (h, w, 3) float, alpha (h, w); with ids=True also the index of the top shape with coverage > 0.5."""
    from pbrender import composite_one
    x0, y0, x1, y1 = box
    Wp, Hp = int(round((x1 - x0) * scale)), int(round((y1 - y0) * scale))
    ox, oy = -x0 * scale, -y0 * scale
    img = np.zeros((Hp, Wp, 3)) if bg is None else np.broadcast_to(np.asarray(bg, float), (Hp, Wp, 3)).copy()
    al = np.zeros((Hp, Wp)); top = np.full((Hp, Wp), -1, np.int32)
    for k, s in enumerate(shapes):
        b = tbox(s)
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1: continue
        cov = rasterize(flatten(s.subs, scale), scale, ox, oy, Wp, Hp)
        if cov is None: continue
        composite_one(img, al, s, cov, scale, ox, oy)
        if ids:
            cx, cy, c = cov; h, w = c.shape
            t = top[cy:cy + h, cx:cx + w]; t[c > 0.5] = k
    # composite_one with alpha!=None accumulates premultiplied colour; un-premultiply nothing: img is premultiplied over bg=0
    return (img, al, top) if ids else (img, al)

DEV = 852 * 3 / H          # device px per design unit on 393x852 @3x with aspect-fill (height-limited): 1.5232

def save(img, path, up=1, al=None):
    from PIL import Image
    a = np.clip(img, 0, 1)
    im = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
    if up != 1: im = im.resize((im.width * up, im.height * up), Image.NEAREST)
    im.save(path)

def crop(shapes, box, path, scale=DEV, up=3):
    img, al = render_box(shapes, box, scale)
    save(img, path, up)
    return img

def false_colour(shapes, box, scale, seed=1, bg=(1, 1, 1)):
    """Each shape in a distinct random colour (stacking kept), plus outline-free composite."""
    import copy
    rng = np.random.default_rng(seed)
    fc = []
    for s in shapes:
        t = copy.copy(s); t.nx = 0; t.ny = 0; t.cols = rng.uniform(0.15, 0.95, (1, 3)); fc.append(t)
    img, al = render_box(fc, box, scale)
    return img + (1 - al[..., None]) * np.asarray(bg)

def grid(img, box, scale, step=50, col=(0.85, 0.1, 0.1)):
    """Draw design-space grid lines every `step` units on a rendered crop, with labels via PIL."""
    from PIL import Image, ImageDraw
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box; c = tuple(int(v * 255) for v in col)
    for x in range(int(np.ceil(x0 / step) * step), int(x1) + 1, step):
        X = (x - x0) * scale; d.line([(X, 0), (X, im.height)], fill=c, width=1); d.text((X + 2, 2), str(x), fill=c)
    for y in range(int(np.ceil(y0 / step) * step), int(y1) + 1, step):
        Y = (y - y0) * scale; d.line([(0, Y), (im.width, Y)], fill=c, width=1); d.text((2, Y + 2), str(y), fill=c)
    return np.asarray(im) / 255.0
