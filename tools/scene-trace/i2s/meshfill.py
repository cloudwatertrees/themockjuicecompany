"""Smooth fills: a bilinear mesh gradient per larger region, least-squares fitted to the reference.

Matches the renderer's `*W H RRGGBB… <path>` fill: W x H vertex colours evenly spanning the path's tight bounding
rect grown by one unit, interpolated bilinearly, sampled at pixel centres. A small second-difference smoothness term
keeps vertices without pixels (or with few) on a smooth membrane. Regions below `min_area` keep their flat or
linear fill."""
import numpy as np
from scipy import ndimage as ndi
from scipy import sparse
from scipy.sparse.linalg import spsolve


def bez_bounds(subpaths, k=24):
    t = np.linspace(0, 1, k)[:, None]
    pts = []
    for segs in subpaths:
        for b in segs:
            b = np.asarray(b)
            pts.append((1 - t) ** 3 * b[0] + 3 * (1 - t) ** 2 * t * b[1] + 3 * (1 - t) * t ** 2 * b[2] + t ** 3 * b[3])
    p = np.concatenate(pts)
    return p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()


def second_diff(nx, ny):
    rows = []
    idx = np.arange(nx * ny).reshape(ny, nx)
    for a, b, c in [(idx[:, :-2], idx[:, 1:-1], idx[:, 2:]), (idx[:-2], idx[1:-1], idx[2:])]:
        a, b, c = a.ravel(), b.ravel(), c.ravel()
        m = len(a)
        r = np.repeat(np.arange(m), 3)
        rows.append(sparse.csr_matrix((np.tile([1.0, -2.0, 1.0], m), (r, np.stack([a, b, c], 1).ravel())), shape=(m, nx * ny)))
    return sparse.vstack(rows) if rows else sparse.csr_matrix((0, nx * ny))


def mesh_fills(shapes, lab, ref, scale=1.0, cell=5.0, min_area=120, lam=0.02, cap=48):
    """In place: shapes with a 'label' and >= min_area pixels get fill {'type': 'mesh', ...}. `scale` maps label-map
    pixels to the shapes' coordinate units (1 / INPUT_SCALE once coordinates are in design units)."""
    objs = ndi.find_objects(lab + 1)
    n = 0
    for sh in shapes:
        li = sh.get('label')
        if li is None or li >= len(objs) or objs[li] is None:
            continue
        sl = objs[li]
        m = lab[sl] == li
        if m.sum() < min_area:
            continue
        x0, y0, x1, y1 = bez_bounds(sh['subpaths'])
        rx0, ry0, rw, rh = x0 - 1, y0 - 1, (x1 - x0) + 2, (y1 - y0) + 2
        nx = int(min(cap, max(2, np.ceil(rw / cell) + 1)))
        ny = int(min(cap, max(2, np.ceil(rh / cell) + 1)))
        ys, xs = np.nonzero(m)
        X = (xs + sl[1].start + 0.5) * scale
        Y = (ys + sl[0].start + 0.5) * scale
        u = np.clip((X - rx0) / rw, 0, 1) * (nx - 1)
        v = np.clip((Y - ry0) / rh, 0, 1) * (ny - 1)
        i = np.minimum(u.astype(int), nx - 2); j = np.minimum(v.astype(int), ny - 2)
        fu, fv = u - i, v - j
        r = np.arange(len(X))
        A = sparse.csr_matrix((np.concatenate([(1 - fu) * (1 - fv), fu * (1 - fv), (1 - fu) * fv, fu * fv]),
                               (np.tile(r, 4), np.concatenate([j * nx + i, j * nx + i + 1, (j + 1) * nx + i, (j + 1) * nx + i + 1]))),
                              shape=(len(X), nx * ny))
        D = second_diff(nx, ny)
        M = (A.T @ A + lam * len(X) / (nx * ny) * (D.T @ D) + 1e-6 * sparse.identity(nx * ny)).tocsc()
        Yc = ref[sl][m]
        C = np.stack([spsolve(M, A.T @ Yc[:, c]) for c in range(3)], 1)
        sh['fill'] = {'type': 'mesh', 'nx': nx, 'ny': ny, 'colors': np.clip(C, 0, 255)}
        n += 1
    return n
