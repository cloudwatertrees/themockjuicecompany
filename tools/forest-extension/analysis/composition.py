"""Composition measurements of the original scene: path centreline/width/curvature over the whole height, cover
fractions left/right of the path per vertical band.   usage: python -m analysis.composition CACHE_DIR OUT.json"""
import sys, os, json, numpy as np
from scipy import ndimage as ndi
from fe.core import *
from fe.anatomy import Composite

def main(cache_dir, out):
    S = load_original(); C = Composite(S, 2.0, cache=os.path.join(cache_dir, 'orig_ids2x.npz'))
    lab = C.lab; sc = C.scale
    surf = (lab[..., 1] > -1.5) & (lab[..., 0] > 75)
    surf = ndi.binary_opening(ndi.binary_closing(surf, iterations=6), iterations=3)
    lay = np.array([S[k].layer if k >= 0 else '' for k in range(len(S))] + [''])
    toplayer = lay[C.top]
    foliage = np.isin(toplayer, ['backTrees', 'pines', 'frontTrees', 'hedge', 'doorBush', 'bushes'])
    rows = []
    for r in range(0, lab.shape[0], int(sc * 4)):
        lbl, n = ndi.label(surf[r])
        if n == 0: continue
        sizes = ndi.sum(np.ones_like(lbl), lbl, range(1, n + 1))
        runs = [(np.nonzero(lbl == i + 1)[0], sz) for i, sz in enumerate(sizes) if sz > 40 * sc]
        rows.append(dict(y=round((r + 0.5) / sc, 1), runs=[[round(x[0] / sc, 1), round((x[-1] + 1) / sc, 1)] for x, _ in runs]))
    # bands: cover fractions
    bands = []
    for i in range(10):
        y0, y1 = int(H * i / 10 * sc), int(H * (i + 1) / 10 * sc)
        f = foliage[y0:y1]; s = surf[y0:y1]
        half = f.shape[1] // 2
        bands.append(dict(y=[round(y0 / sc), round(y1 / sc)], path_frac=round(float(s.mean()), 3), foliage_frac=round(float(f.mean()), 3),
                          foliage_left=round(float(f[:, :half].mean()), 3), foliage_right=round(float(f[:, half:].mean()), 3),
                          L_mean=round(float(lab[y0:y1, ..., 0].mean()), 2)))
    json.dump(dict(path_rows=rows, bands=bands), open(out, 'w'), indent=1)
    for r in rows[::10]: print(r)
    for b in bands: print(b)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
