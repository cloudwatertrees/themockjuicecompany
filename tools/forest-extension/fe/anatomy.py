"""Object-level anatomy metrics, identical for original and generated instances.

An instance is a list of shapes (in stacking order) plus the composite they sit in. Metrics are computed from the
instance's own render (on a neutral background is NOT used: colours come from visible pixels of the full composite,
so occlusion by later layers is respected) and from the shape data."""
import numpy as np
from scipy import ndimage as ndi
from .core import *
from .metrics import perimeter, n_segments, mesh_cells, turning

THIN_W = 2.2       # 2A/P below this (and perimeter > 12) = rim / line shape
TINY_A = 40.0      # area below this (non-thin) = accent

def classify(shapes, vis_lab, surround_lab):
    """Roles per shape: rim_light/rim_dark (thin), accent_light/accent_dark (tiny), body_dark/body_mid/body_light
    (by area-weighted L* tertiles of the instance's body shapes). vis_lab / surround_lab: per-shape mean Lab of its
    visible pixels and of a 2-px ring around them (None if not visible)."""
    A = np.array([area(s) for s in shapes]); P = np.array([perimeter(s) for s in shapes])
    w = 2 * A / np.maximum(P, 1e-9)
    own = np.array([v if v is not None else rgb2lab(mean_rgb(s)) for v, s in zip(vis_lab, shapes)])
    roles = [None] * len(shapes)
    body = [i for i in range(len(shapes)) if not (w[i] < THIN_W and P[i] > 12) and A[i] >= TINY_A]
    if body:
        Lb = own[body, 0]; order = np.argsort(Lb); cum = np.cumsum(A[body][order]) / A[body].sum()
        t1 = Lb[order][np.searchsorted(cum, 1 / 3)]; t2 = Lb[order][min(np.searchsorted(cum, 2 / 3), len(order) - 1)]
    for i in range(len(shapes)):
        sur = surround_lab[i]
        d = (own[i, 0] - sur[0]) if sur is not None else 0.0
        if w[i] < THIN_W and P[i] > 12: roles[i] = 'rim_light' if d >= 0 else 'rim_dark'
        elif A[i] < TINY_A: roles[i] = 'accent_light' if d >= 0 else 'accent_dark'
        else: roles[i] = 'body_dark' if own[i, 0] < t1 else ('body_light' if own[i, 0] > t2 else 'body_mid')
    return roles, A, P, w, own

class Composite:
    """Full-scene render + top-shape id buffer at `scale` (cached), for visible-pixel statistics."""
    def __init__(self, shapes, scale=2.0, box=(0, 0, W, H), cache=None):
        import os
        self.shapes, self.scale, self.box = shapes, scale, box
        if cache and os.path.exists(cache):
            z = np.load(cache); self.img, self.top = z['img'], z['top']
        else:
            self.img, al, self.top = render_box(shapes, box, scale, ids=True)
            if cache: np.savez_compressed(cache, img=self.img.astype(np.float32), top=self.top)
        self.lab = rgb2lab(self.img)
        self.index = {id(s): k for k, s in enumerate(shapes)}

    def px(self, idx):
        m = np.isin(self.top, idx)
        return m

    def shape_stats(self, k, ring=2):
        m = self.top == k
        if m.sum() < 1: return None, None, 0
        yy, xx = np.nonzero(m)
        y0, y1, x0, x1 = max(yy.min() - ring - 1, 0), yy.max() + ring + 2, max(xx.min() - ring - 1, 0), xx.max() + ring + 2
        mm = m[y0:y1, x0:x1]; r = ndi.binary_dilation(mm, iterations=ring) & ~mm
        lab = self.lab[y0:y1, x0:x1]
        return lab[mm].mean(0), (lab[r].mean(0) if r.sum() else None), int(mm.sum())

    def to_units(self, yy, xx):
        return xx / self.scale + self.box[0], yy / self.scale + self.box[1]

def light_vector(lab_px, xs, ys):
    """L*-weighted direction of increasing lightness over an object's visible pixels: sum((L-meanL)*(p-c)),
    normalised by sum(|L-meanL|) -> (angle deg [0=right, 90=up], magnitude in units)."""
    L = lab_px[:, 0]; d = L - L.mean()
    cx, cy = xs.mean(), ys.mean()
    v = np.array([(d * (xs - cx)).sum(), (d * (ys - cy)).sum()]) / max(np.abs(d).sum(), 1e-9)
    return float(np.degrees(np.arctan2(-v[1], v[0])) % 360), float(np.hypot(*v))

def dark_offset(lab_px, xs, ys, q=25):
    """Centroid of the darkest q% visible pixels minus the centroid of all visible pixels (units): shadow offset."""
    L = lab_px[:, 0]; t = np.percentile(L, q); m = L <= t
    return float(xs[m].mean() - xs.mean()), float(ys[m].mean() - ys.mean())

def instance_metrics(C, idx, exclude_roles=()):
    """Metrics for an instance given by shape indices into C.shapes."""
    S = C.shapes; shapes = [S[k] for k in idx]
    st = [C.shape_stats(k) for k in idx]
    roles, A, P, w, own = classify(shapes, [s[0] for s in st], [s[1] for s in st])
    keep = [k for k, r in zip(idx, roles) if r not in exclude_roles]
    m = C.px(keep)
    yy, xx = np.nonzero(m); xs, ys = C.to_units(yy, xx); lab_px = C.lab[m]
    b = np.array([tbox(s) for s in shapes])
    box = [float(b[:, 0].min()), float(b[:, 1].min()), float(b[:, 2].max()), float(b[:, 3].max())]
    out = dict(n=len(idx), n_mesh=sum(1 for s in shapes if s.nx), cells=int(sum(mesh_cells(s) for s in shapes)),
               segs=int(sum(n_segments(s) for s in shapes)), box=box, w=box[2] - box[0], h=box[3] - box[1],
               area=float(A.sum()), visible_units2=float(m.sum() / C.scale ** 2))
    out['roles'] = {r: roles.count(r) for r in sorted(set(roles))}
    out['role_area'] = {r: float(sum(a for a, rr in zip(A, roles) if rr == r)) for r in sorted(set(roles))}
    out['role_lab'] = {}
    for r in sorted(set(roles)):
        ks = [k for k, rr in zip(idx, roles) if rr == r]
        mm = C.px(ks)
        if mm.sum(): out['role_lab'][r] = [round(float(v), 2) for v in C.lab[mm].mean(0)]
    if len(lab_px):
        out['lab_mean'] = [round(float(v), 2) for v in lab_px.mean(0)]
        out['lab_p10_p90'] = [[round(float(v), 1) for v in np.percentile(lab_px, 10, 0)], [round(float(v), 1) for v in np.percentile(lab_px, 90, 0)]]
        out['light_deg'], out['light_mag'] = light_vector(lab_px, xs, ys)
        out['dark_offset'] = dark_offset(lab_px, xs, ys)
        out['centroid'] = [float(xs.mean()), float(ys.mean())]
    rims = [i for i, r in enumerate(roles) if r.startswith('rim')]
    out['rim_width_med'] = float(np.median(w[rims])) if rims else None
    out['rim_dL'] = [round(float(own[i, 0] - (st[i][1][0] if st[i][1] is not None else own[i, 0])), 1) for i in rims]
    meshes = [s for s in shapes if s.nx]
    out['mesh_cell_units'] = float(np.median([np.sqrt((s.box[2] - s.box[0]) * (s.box[3] - s.box[1]) / ((s.nx - 1) * (s.ny - 1))) for s in meshes])) if meshes else None
    tr = [turning(s) for s in shapes if area(s) >= TINY_A]
    out['turn_med'] = float(np.median([t[0] for t in tr])) if tr else None
    out['segs_per_100u'] = float(100 * out['segs'] / max(P.sum(), 1e-9))
    out['_roles_list'] = roles
    return out
