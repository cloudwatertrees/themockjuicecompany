"""Seam analysis of the original scene's bottom 0.3 screen -> seam.json (the exact input Stage 2 must continue).
usage: python -m analysis.seam OUT.json   (from tools/forest-extension)"""
import sys, json, numpy as np
from fe.core import *

Y_EDGE = 1677.5                      # sampling row just above the canvas bottom (H = 1678)
Y_ZONE = H * 0.7                     # bottom 0.3 screen starts here

def cuts(s, y):
    """x positions where the outline crosses row y, with the outline slope dx/dy there."""
    out = []
    for P in polys(s, 4.0):
        Q = np.vstack([P, P[:1]])
        for a, b in zip(Q[:-1], Q[1:]):
            if (a[1] - y) * (b[1] - y) < 0:
                out.append((a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]), (b[0] - a[0]) / (b[1] - a[1])))
    out.sort(); return out

def runs(arr):
    """[(start, end, value)] runs of equal values."""
    r, s = [], 0
    for i in range(1, len(arr) + 1):
        if i == len(arr) or arr[i] != arr[s]:
            r.append((s, i, arr[s])); s = i
    return r

def main(out):
    S = load_original()
    name = lambda k: f'{S[k].layer}#{S[k].region}'
    # 1. bottom-row profile at 4 px/unit: top shape per sample and composite colour
    sc = 4.0
    img, al, top = render_box(S, (0, Y_EDGE - 0.5, W, Y_EDGE + 0.5), sc, ids=True)
    row_top = top[2]; row_col = img[2]
    prof = []
    for a, b, k in runs(list(row_top)):
        c = row_col[a:b].mean(0)
        prof.append(dict(x0=round(a / sc, 2), x1=round(b / sc, 2), top=name(k), layer=S[k].layer,
                         rgb=rgb2hex(c), lab=[round(v, 1) for v in rgb2lab(c)]))
    colours_1u = [rgb2hex(row_col[int(x * sc):int((x + 1) * sc)].mean(0)) for x in range(W)]

    # 2. every shape crossing / touching the bottom edge
    crossing = []
    for k, s in enumerate(S):
        b = tbox(s)
        if b[3] < H - 0.5: continue
        cs = cuts(s, Y_EDGE)
        d = dict(id=name(k), layer=s.layer, order=k, box=[round(v, 2) for v in b], fill='mesh' if s.nx else 'flat',
                 mesh=[s.nx, s.ny] if s.nx else None, mean_rgb=rgb2hex(mean_rgb(s)),
                 mean_lab=[round(v, 1) for v in rgb2lab(mean_rgb(s))],
                 cut=[dict(x=round(x, 2), slope_dxdy=round(m, 3)) for x, m in cs])
        if s.nx:   # colours of the mesh along the cut row
            xs = np.array([c['x'] for c in d['cut']] or [b[0], b[2]])
            xx = np.linspace(xs.min(), xs.max(), 9)
            d['edge_colours'] = [rgb2hex(c) for c in s.colour_at(xx, np.full_like(xx, Y_EDGE))]
            d['bottom_mesh_row'] = [rgb2hex(c) for c in s.cols.reshape(s.ny, s.nx, 3)[-1]]
        d['path'] = s.pathstr
        crossing.append(d)

    # 3. path geometry per row in the bottom 0.3, classified from the composite colour (the brown band is made of
    #    pathEdges and meadow shapes, so layers alone do not give it): surface = a* > -1.5 and L* > 75 (pebbles included);
    #    band = L* < 72 and a* > 6; rim = pale strip between band and grass (L* > 84, a* > -4) right outside the band.
    y0 = int(Y_ZONE); sc2 = 2.0
    img2, _ = render_box(S, (0, y0, W, H), sc2)
    lab2 = rgb2lab(img2)
    surf = (lab2[..., 1] > -1.5) & (lab2[..., 0] > 75); bandm = (lab2[..., 0] < 72) & (lab2[..., 1] > 6)
    rows = []
    for r in range(0, img2.shape[0], int(sc2 * 4)):
        y = y0 + (r + 0.5) / sc2
        rr = [(a, b) for a, b, v in runs(list(surf[r])) if v and b - a > 20]
        if not rr: continue
        a, b = max(rr, key=lambda t: t[1] - t[0])
        rb = [(c, d) for c, d, v in runs(list(bandm[r])) if v and d - c >= 6]
        left = [(c, d) for c, d in rb if d <= a + 4 and d > a - 40]; right = [(c, d) for c, d in rb if c >= b - 4 and c < b + 40]
        def rim(x, step):   # pale run directly outside a band end
            n = 0
            while 0 <= x + n * step < img2.shape[1] and lab2[r, x + n * step, 0] > 80 and lab2[r, x + n * step, 1] > -6: n += 1
            return round(n / sc2, 1)
        rows.append(dict(y=round(y, 1), left=round(a / sc2, 1), right=round(b / sc2, 1), centre=round((a + b) / 2 / sc2, 1),
                         width=round((b - a) / sc2, 1),
                         band_left=[round(v / sc2, 1) for v in left[-1]] if left else [],
                         band_right=[round(v / sc2, 1) for v in right[0]] if right else [],
                         rim_left=rim(left[-1][0] - 1, -1) if left else 0, rim_right=rim(right[0][1], 1) if right else 0,
                         surface_lab=[round(v, 1) for v in lab2[r, a:b].mean(0)],
                         band_lab=[round(v, 1) for v in lab2[r, right[0][0]:right[0][1]].mean(0)] if right else None))
    # centreline slope at the bottom from the last 120 units
    tail = [r for r in rows if r['y'] > H - 120]
    cy = np.array([r['y'] for r in tail]); cx = np.array([r['centre'] for r in tail])
    lx = np.array([r['left'] for r in tail]); rx = np.array([r['right'] for r in tail])
    fit = lambda v: [round(float(c), 5) for c in np.polyfit(cy - H, v, 2)]

    # 4. pebbles and details in the bottom 0.3: small path-layer shapes (not the surface meshes)
    peb = []
    for k, s in enumerate(S):
        if s.layer != 'path': continue
        b = tbox(s)
        if b[3] < Y_ZONE: continue
        A = area(s)
        if A > 4000: continue
        peb.append(dict(id=name(k), box=[round(v, 1) for v in b], area=round(A, 1), rgb=rgb2hex(mean_rgb(s)),
                        lab=[round(v, 1) for v in rgb2lab(mean_rgb(s))], mesh=[s.nx, s.ny] if s.nx else None))
    edge_peb = []
    for k, s in enumerate(S):
        if s.layer != 'pathEdges': continue
        b = tbox(s)
        if b[3] < Y_ZONE: continue
        edge_peb.append(dict(id=name(k), box=[round(v, 1) for v in b], area=round(area(s), 1), rgb=rgb2hex(mean_rgb(s)),
                             lab=[round(v, 1) for v in rgb2lab(mean_rgb(s))], mesh=[s.nx, s.ny] if s.nx else None))

    # 5. inventory of the bottom 0.3 per layer
    inv = {}
    for k, s in enumerate(S):
        b = tbox(s)
        if b[3] < Y_ZONE: continue
        inv.setdefault(s.layer, []).append(dict(id=name(k), box=[round(v, 1) for v in b], rgb=rgb2hex(mean_rgb(s)),
                                                mesh=[s.nx, s.ny] if s.nx else None))
    J = dict(
        canvas=dict(W=W, H=H, note='Shapes extend to y=1682 (bottom border snapped 4 units beyond the canvas). '
                    'Sampling row y=1677.5. Zone = bottom 0.3 screen, y >= %.1f.' % Y_ZONE),
        bottom_profile=prof, bottom_colours_per_unit=colours_1u,
        crossing_shapes=crossing,
        path=dict(rows=rows, at_edge=rows[-1],
                  quad_fit_about_y1678=dict(centre=fit(cx), left=fit(lx), right=fit(rx),
                                            note='x = a*(y-1678)^2 + b*(y-1678) + c over the last 120 units')),
        path_pebbles=peb, path_edge_shapes=edge_peb,
        zone_inventory={L: dict(count=len(v), shapes=v) for L, v in inv.items()})
    json.dump(J, open(out, 'w'), indent=1)
    print('profile runs', len(prof), 'crossing', len(crossing), 'rows', len(rows), 'pebbles', len(peb))
    print('path at edge', rows[-1]); print('fit', J['path']['quad_fit_about_y1678'])
    for p in prof:
        if p['x1'] - p['x0'] >= 2: print(p['x0'], p['x1'], p['top'], p['rgb'], p['lab'])

if __name__ == '__main__':
    main(sys.argv[1])
