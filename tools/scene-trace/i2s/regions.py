"""Per-region sufficient statistics for affine colour models (R, G, B, luma as planes over x, y)."""
import numpy as np

W_CH = np.array([1.0, 1.0, 1.0, 3.0])  # R, G, B, luma weights in the merge cost
SCALE = 100.0


def region_stats(labels, img4):
    """img4: H x W x 4 (R, G, B, luma). Coordinates are centred on the image and scaled by SCALE."""
    h, w = labels.shape
    yy, xx = np.mgrid[0:h, 0:w]
    x = ((xx + 0.5) - w / 2) / SCALE
    y = ((yy + 0.5) - h / 2) / SCALE
    L = labels.ravel()
    n = L.max() + 1

    def bc(v):
        return np.bincount(L, weights=v.ravel(), minlength=n)

    st = {'n': np.bincount(L, minlength=n).astype(float), 'sx': bc(x), 'sy': bc(y),
          'sxx': bc(x * x), 'sxy': bc(x * y), 'syy': bc(y * y)}
    st['sc'] = np.stack([bc(img4[..., k]) for k in range(4)], 1)
    st['scx'] = np.stack([bc(img4[..., k] * x) for k in range(4)], 1)
    st['scy'] = np.stack([bc(img4[..., k] * y) for k in range(4)], 1)
    st['scc'] = np.stack([bc(img4[..., k] ** 2) for k in range(4)], 1)
    return st


def sse(v):
    """v = (n, sx, sy, sxx, sxy, syy, sc[4], scx[4], scy[4], scc[4]) -> weighted SSE of the affine fit."""
    n, sx, sy, sxx, sxy, syy, sc, scx, scy, scc = v
    if n < 8:
        e = scc - sc * sc / n
    else:
        A = np.array([[n, sx, sy], [sx, sxx + 1e-4 * n, sxy], [sy, sxy, syy + 1e-4 * n]])
        B = np.stack([sc, scx, scy])  # 3 x 4
        try:
            X = np.linalg.solve(A, B)
        except np.linalg.LinAlgError:
            X = None
        e = scc - (B * X).sum(0) if X is not None else scc - sc * sc / n
    return float((np.maximum(e, 0) * W_CH).sum())


def adjacency(labels):
    a = labels[:, :-1].ravel()
    b = labels[:, 1:].ravel()
    c = labels[:-1, :].ravel()
    d = labels[1:, :].ravel()
    p = np.concatenate([np.stack([a, b], 1), np.stack([c, d], 1)])
    p = p[p[:, 0] != p[:, 1]]
    p = np.sort(p, 1)
    return np.unique(p, axis=0)
