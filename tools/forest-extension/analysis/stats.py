"""Per-layer statistics of the original scene -> stats.json.   usage: python -m analysis.stats OUT.json [TOPNPY]"""
import sys, json, os, numpy as np
from scipy import ndimage as ndi
from fe.core import *
from fe.metrics import *

def q(v, ps=(5, 25, 50, 75, 95)):
    v = np.asarray(v, float)
    return {f'p{p}': round(float(np.percentile(v, p)), 3) for p in ps} if len(v) else None

def relation_to_surround(img_lab, top, k, ring=2):
    m = top == k
    if m.sum() < 3: return None
    yy, xx = np.nonzero(m); y0, y1, x0, x1 = max(yy.min() - ring - 1, 0), yy.max() + ring + 2, max(xx.min() - ring - 1, 0), xx.max() + ring + 2
    mm = m[y0:y1, x0:x1]; r = ndi.binary_dilation(mm, iterations=ring) & ~mm
    if r.sum() < 3: return None
    lab = img_lab[y0:y1, x0:x1]
    return lab[mm].mean(0), lab[r].mean(0), int(mm.sum())

def main(out, cache=None):
    S = load_original()
    if cache and os.path.exists(cache):
        z = np.load(cache); img, top = z['img'], z['top']
    else:
        img, al, top = render_box(S, (0, 0, W, H), 1.0, ids=True)
        if cache: np.savez_compressed(cache, img=img.astype(np.float32), top=top)
    lab_img = rgb2lab(img)
    vis = np.bincount(top.ravel()[top.ravel() >= 0], minlength=len(S))
    D = [describe(s) for s in S]
    layers = {}
    for L in LAYERS:
        idx = [k for k, s in enumerate(S) if s.layer == L]
        if not idx:
            layers[L] = dict(shapes=0, note='empty in this scene'); continue
        d = [D[k] for k in idx]
        A = np.array([x['area'] for x in d]); labs = np.array([x['lab'] for x in d])
        meshes = [k for k in idx if S[k].nx]
        cell_w = [ (S[k].box[2]-S[k].box[0])/(S[k].nx-1) for k in meshes]
        cell_h = [ (S[k].box[3]-S[k].box[1])/(S[k].ny-1) for k in meshes]
        ang, coh = light_direction([S[k] for k in idx])
        # area-weighted Lab quantiles over visible pixels of this layer
        pix = np.isin(top, idx)
        lab_pix = lab_img[pix]
        visfrac = [vis[k] / max(D[k]['area'], 1) for k in idx]
        thin = [k for k in idx if D[k]['width'] < 2.5 and D[k]['perim'] > 20]
        rims = []
        for k in thin:
            r = relation_to_surround(lab_img, top, k)
            if r is None: continue
            own, sur, n = r
            rims.append(dict(id=f'{L}#{S[k].region}', width=round(D[k]['width'], 2), length=round(D[k]['perim'] / 2, 1),
                             lab=[round(v, 1) for v in own], dL=round(float(own[0] - sur[0]), 1),
                             dab=[round(float(own[1] - sur[1]), 1), round(float(own[2] - sur[2]), 1)]))
        rel = []
        for k in idx:
            if D[k]['width'] < 2.5: continue
            r = relation_to_surround(lab_img, top, k, 3)
            if r is None: continue
            own, sur, n = r
            rel.append((own - sur, n))
        darker = [(dv, n) for dv, n in rel if dv[0] < -6]; lighter = [(dv, n) for dv, n in rel if dv[0] > 6]
        layers[L] = dict(
            shapes=len(idx), flat=len(idx) - len(meshes), mesh=len(meshes),
            path_segments=int(sum(x['segs'] for x in d)), mesh_cells=int(sum(x['cells'] for x in d)),
            mesh_vertices=int(sum(S[k].nx * S[k].ny for k in meshes)),
            mesh_dims=q([max(S[k].nx, S[k].ny) for k in meshes]),
            mesh_cell_size_units=dict(w=q(cell_w), h=q(cell_h)),
            area_units2=q(A), area_total=round(float(A.sum()), 1), visible_px=int(pix.sum()),
            bbox_w=q([x['bw'] for x in d]), bbox_h=q([x['bh'] for x in d]),
            stroke_width_2A_over_P=q([x['width'] for x in d]),
            segs_per_100_units_perimeter=q([100 * x['segs'] / max(x['perim'], 1e-9) for x in d]),
            turning_rad_per_unit=q([x['turn'] for x in d]), corner_share_gt45=q([x['sharp'] for x in d]),
            palette_lab_shape_means=dict(L=q(labs[:, 0]), a=q(labs[:, 1]), b=q(labs[:, 2])),
            palette_lab_visible_pixels=dict(L=q(lab_pix[:, 0]), a=q(lab_pix[:, 1]), b=q(lab_pix[:, 2]),
                                             mean=[round(float(v), 2) for v in lab_pix.mean(0)]) if len(lab_pix) else None,
            mesh_L_range_within_shape=q([D[k]['grad'][2] for k in meshes]),
            light_direction_deg=None if ang is None else round(ang, 1), light_coherence=round(coh, 3),
            visible_fraction=q(visfrac), hidden_shapes=int(sum(1 for v in visfrac if v < 0.02)),
            rims=dict(count=len(rims), width=q([r['width'] for r in rims]), dL=q([r['dL'] for r in rims]),
                      lighter=sum(1 for r in rims if r['dL'] > 3), darker=sum(1 for r in rims if r['dL'] < -3),
                      examples=sorted(rims, key=lambda r: -r['length'])[:6]),
            darker_than_surround=dict(count=len(darker), dLab_mean=[round(float(v), 2) for v in np.mean([dv for dv, n in darker], 0)] if darker else None),
            lighter_than_surround=dict(count=len(lighter), dLab_mean=[round(float(v), 2) for v in np.mean([dv for dv, n in lighter], 0)] if lighter else None),
        )
    tot = dict(shapes=len(S), mesh_cells=int(sum(x['cells'] for x in D)), path_segments=int(sum(x['segs'] for x in D)))
    ang, coh = light_direction(S)
    tot['light_direction_deg'] = round(ang, 1); tot['light_coherence'] = round(coh, 3)
    # density per vertical band (tenths of the canvas): shapes whose centre lies in the band, cells, mean L*
    bands = []
    for i in range(10):
        y0, y1 = H * i / 10, H * (i + 1) / 10
        ks = [k for k, s in enumerate(S) if y0 <= (tbox(s)[1] + tbox(s)[3]) / 2 < y1]
        bands.append(dict(y=[round(y0), round(y1)], shapes=len(ks), cells=int(sum(D[k]['cells'] for k in ks)),
                          L_mean=round(float(lab_img[int(y0):int(y1)][..., 0].mean()), 2),
                          lab_mean=[round(float(v), 2) for v in lab_img[int(y0):int(y1)].reshape(-1, 3).mean(0)],
                          per_layer={L: sum(1 for k in ks if S[k].layer == L) for L in LAYERS}))
    J = dict(note='Original scene (working-tree forest-v2 art, 17 layers, md5 %s).' % SOURCE_MD5 + ' Areas in design units^2; light direction = mean direction of '
             'increasing L* across mesh fills, 0=right 90=up 180=left 270=down (image y down); coherence = length '
             'of the weighted mean unit vector.', total=tot, layers=layers, vertical_bands=bands,
             edge_sharpness=dict(value_px=0.531, source='PROCESS.md (acuity.py erf-fit sigma, simulator 3x); renderer '
                                 'is unchanged, so new shapes inherit it; re-measured on the new art in Stage 2.'))
    json.dump(J, open(out, 'w'), indent=1)
    for L in LAYERS:
        x = layers[L]
        if not x['shapes']: print(L, 'empty'); continue
        print(f"{L:10s} n={x['shapes']:4d} mesh={x['mesh']:3d} cells={x['mesh_cells']:6d} segs={x['path_segments']:6d} "
              f"light={x['light_direction_deg']} coh={x['light_coherence']} rims={x['rims']['count']} "
              f"rimW50={x['rims']['width'] and x['rims']['width']['p50']} hidden={x['hidden_shapes']} "
              f"Lab={x['palette_lab_visible_pixels'] and x['palette_lab_visible_pixels']['mean']}")
    print(tot)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
