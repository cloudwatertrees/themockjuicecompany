"""High-fidelity trace: shapes from a super-resolved label map, occlusion-aware, parallel."""
import os
import pickle
from multiprocessing import Pool

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

from bezier import fit_closed, merge_segments

PAD = 4
_G = {}


def fill_crop(ref, mask, y0, x0, grad_min=3.0):
    """Flat colour or two-stop linear gradient (rank-1 colour plane) for the pixels of `mask`."""
    ys, xs = np.nonzero(mask)
    inner = ndi.binary_erosion(mask)
    if inner.sum() >= max(20, 0.3 * mask.sum()):
        fy, fx = np.nonzero(inner)
    else:
        fy, fx = ys, xs
    c = ref[fy + y0, fx + x0]
    x = fx + x0 + 0.5
    y = fy + y0 + 0.5
    mean = c.mean(0)
    mx, my = x.mean(), y.mean()
    if len(c) < 12:
        return {'type': 'flat', 'color': np.clip(mean, 0, 255)}
    M = np.stack([x - mx, y - my], 1)
    G, *_ = np.linalg.lstsq(M, c - mean, rcond=None)
    Uu, Sv, Vt = np.linalg.svd(G, full_matrices=False)
    v = Uu[:, 0]
    col = Vt[0] * Sv[0]
    if v @ np.array([0.3, 1.0]) < 0:
        v = -v
        col = -col
    s_all = (xs + x0 + 0.5 - mx) * v[0] + (ys + y0 + 0.5 - my) * v[1]
    s0, s1 = s_all.min(), s_all.max()
    c0 = mean + col * s0
    c1 = mean + col * s1
    if np.abs(c1 - c0).max() < grad_min:
        return {'type': 'flat', 'color': np.clip(mean, 0, 255)}
    return {'type': 'linear', 'p0': (mx + v[0] * s0, my + v[1] * s0), 'p1': (mx + v[0] * s1, my + v[1] * s1),
            'colors': [np.clip(c0, 0, 255), np.clip(c1, 0, 255)]}


def _init(tag, work):
    _G['lab'] = np.load(f'{work}/tmp_{tag}_lab.npy', mmap_mode='r')
    _G['ref'] = np.load(f'{work}/ref.npy', mmap_mode='r')
    _G['LU'] = np.load(f'{work}/tmp_{tag}_LU.npy', mmap_mode='r')
    _G['ZR'] = np.load(f'{work}/tmp_{tag}_ZR.npy', mmap_mode='r')
    _G['cfg'] = pickle.load(open(f'{work}/tmp_{tag}_cfg.pkl', 'rb'))


def _shape(li, sl):
    LU, ZR, cfg = _G['LU'], _G['ZR'], _G['cfg']
    U = cfg['U']
    m = cfg['margin'] * U
    zi = cfg['zrank'][li]
    Hp, Wp = LU.shape
    y0 = max(sl[0].start - m, 0)
    y1 = min(sl[0].stop + m, Hp)
    x0 = max(sl[1].start - m, 0)
    x1 = min(sl[1].stop + m, Wp)
    lab = np.asarray(LU[y0:y1, x0:x1])
    zr = np.asarray(ZR[y0:y1, x0:x1])
    R = lab == li
    E = zr < zi  # regions already painted behind this one may be covered by it
    E[0, :] = E[-1, :] = True
    E[:, 0] = E[:, -1] = True
    E &= ~R
    dR = ndi.distance_transform_edt(~R)
    dE = ndi.distance_transform_edt(~E)
    phi = dE - dR
    if cfg.get('sigma_u'):
        phi = ndi.gaussian_filter(phi, cfg['sigma_u'])
    phi[0, :] = phi[-1, :] = -1
    phi[:, 0] = phi[:, -1] = -1
    out = []
    for c in measure.find_contours(phi, 0.0, fully_connected='high'):
        if len(c) < 4:
            continue
        c = c[:-1] if np.allclose(c[0], c[-1]) else c
        keep = np.r_[True, np.linalg.norm(np.diff(c, axis=0), axis=1) > 1e-6]
        c = c[keep]
        if len(c) < 3:
            continue
        area = 0.5 * abs(np.dot(c[:, 0], np.roll(c[:, 1], 1)) - np.dot(c[:, 1], np.roll(c[:, 0], 1)))
        if area < 0.5 * U * U * cfg['min_area']:
            continue
        d = 0.5 * (ndi.map_coordinates(dE, c.T, order=1) + ndi.map_coordinates(dR, c.T, order=1)) / U
        xs = (c[:, 1] + x0 + 0.5) / U - PAD
        ys = (c[:, 0] + y0 + 0.5) / U - PAD
        # tight tolerance on visible edges, loose where the outline is hidden behind other shapes
        tol = np.maximum(np.clip(0.8 * (d - 0.5 / U), 0, cfg['t_hid']), cfg['t_vis'])
        segs = fit_closed(np.stack([xs, ys], 1), tol, cfg['r_corner'], cfg['a_corner'])
        if cfg.get('merge', True):
            segs = merge_segments(segs, float(np.median(tol)) * 0.8)
        out.append([np.round(np.asarray(b), 2) for b in segs])
    return li, out


def _work(chunk):
    out = []
    for li, sl, sl1 in chunk:
        li, subs = _shape(li, sl)
        m = np.asarray(_G['lab'][sl1]) == li
        out.append((li, subs, fill_crop(_G['ref'], m, sl1[0].start, sl1[1].start)))
    return out


def build(lab, LU, grp, groups_order, ref, U, t_vis, work, t_hid=1.5, margin=4, r_corner=2.0, a_corner=60,
          min_area=0.6, workers=7, tag='x', merge=True, sigma_u=0.0):
    """Traces every region into shapes, back to front. `grp` is each region's index into `groups_order`."""
    n = lab.max() + 1
    area = np.bincount(lab.ravel(), minlength=n)
    order = np.lexsort((-area, grp))
    zrank = np.empty(n, np.int32)
    zrank[order] = np.arange(n)
    LUp = np.pad(LU, PAD * U, mode='edge').astype(np.int32)
    np.save(f'{work}/tmp_{tag}_LU.npy', LUp)
    np.save(f'{work}/tmp_{tag}_ZR.npy', zrank[LUp])
    cfg = dict(U=U, margin=margin, zrank=zrank, t_vis=t_vis, t_hid=t_hid, r_corner=r_corner, a_corner=a_corner,
               min_area=min_area, merge=merge, sigma_u=sigma_u)
    pickle.dump(cfg, open(f'{work}/tmp_{tag}_cfg.pkl', 'wb'))
    np.save(f'{work}/tmp_{tag}_lab.npy', lab.astype(np.int32))
    np.save(f'{work}/ref.npy', ref)
    objs = ndi.find_objects(LUp + 1)
    objs1 = ndi.find_objects(lab + 1)
    items = [(li, objs[li], objs1[li]) for li in order if li < len(objs) and objs[li] is not None and objs1[li] is not None]
    chunks = [items[i::workers * 8] for i in range(workers * 8)]
    with Pool(workers, initializer=_init, initargs=(tag, work)) as p:
        res = p.map(_work, chunks)
    subs = {li: (s, f) for r in res for li, s, f in r}
    shapes = []
    for li in order:
        if li in subs and subs[li][0]:
            shapes.append(dict(label=int(li), group=groups_order[grp[li]], fill=subs[li][1], subpaths=subs[li][0]))
    for f in ('LU', 'ZR', 'lab'):
        os.remove(f'{work}/tmp_{tag}_{f}.npy')
    return shapes
