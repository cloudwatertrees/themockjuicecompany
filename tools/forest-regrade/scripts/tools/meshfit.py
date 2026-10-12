"""Bilinear mesh field over a bbox: basis + LSQ fit with second-difference smoothing."""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

def grid_dims(bw, bh, h):
    return max(2, int(round(bw / h)) + 1), max(2, int(round(bh / h)) + 1)

def bilinear_weights(X, Y, box, nx, ny):
    """Sparse (N x nx*ny) bilinear weights of points in a regular nx x ny vertex grid spanning box."""
    x0, y0, x1, y1 = box
    u = np.clip((X - x0) / max(x1 - x0, 1e-9), 0, 1) * (nx - 1); v = np.clip((Y - y0) / max(y1 - y0, 1e-9), 0, 1) * (ny - 1)
    i = np.minimum(u.astype(int), nx - 2); j = np.minimum(v.astype(int), ny - 2)
    fu, fv = u - i, v - j
    N = len(X); rows = np.repeat(np.arange(N), 4)
    cols = np.stack([j * nx + i, j * nx + i + 1, (j + 1) * nx + i, (j + 1) * nx + i + 1], 1).ravel()
    vals = np.stack([(1 - fu) * (1 - fv), fu * (1 - fv), (1 - fu) * fv, fu * fv], 1).ravel()
    return sparse.csr_matrix((vals, (rows, cols)), shape=(N, nx * ny))

def smooth_reg(nx, ny):
    """Second differences along x and y (rows of a sparse operator)."""
    R = []
    idx = np.arange(nx * ny).reshape(ny, nx)
    for a, b, c in [(idx[:, :-2], idx[:, 1:-1], idx[:, 2:]), (idx[:-2], idx[1:-1], idx[2:])]:
        a, b, c = a.ravel(), b.ravel(), c.ravel(); k = len(a)
        if k == 0: continue
        R.append(sparse.csr_matrix((np.concatenate([np.ones(k), -2 * np.ones(k), np.ones(k)]),
                                    (np.tile(np.arange(k), 3), np.concatenate([a, b, c]))), shape=(k, nx * ny)))
    return sparse.vstack(R) if R else sparse.csr_matrix((0, nx * ny))

def fit(X, Y, C, box, nx, ny, lam=0.05, w=None):
    B = bilinear_weights(X, Y, box, nx, ny)
    if w is not None: B = sparse.diags(w) @ B; C = C * w[:, None]
    R = smooth_reg(nx, ny)
    A = (B.T @ B + lam * len(X) / (nx * ny) * (R.T @ R) + 1e-6 * sparse.identity(nx * ny)).tocsc()
    V = np.stack([spsolve(A, B.T @ C[:, c]) for c in range(C.shape[1])], 1)
    return V
