"""Iterative confidence-weighted DIS registration: field f with ren(x) ~ ref(x + f(x))."""
import sys, numpy as np, cv2
from scipy import ndimage as ndi
from skimage.registration import phase_cross_correlation
from flow import feat, rgb, SP

def dis():
    d = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    d.setFinestScale(0); d.setPatchSize(12); d.setPatchStride(3)
    d.setGradientDescentIterations(30); d.setVariationalRefinementIterations(10)
    d.setVariationalRefinementAlpha(30.0)
    return d

def pull(img, f):
    h, w = f.shape[:2]
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img.astype(np.float32), mx + f[..., 0], my + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def smooth(f, conf, s):
    num = np.stack([ndi.gaussian_filter(f[..., c] * conf, s) for c in range(2)], -1)
    return num / (ndi.gaussian_filter(conf, s)[..., None] + 1e-6)

def register(ren, ref, sigmas=(12, 8, 6, 4, 4, 3)):
    Fa = feat(ren); Fb = feat(ref)
    conf = ndi.gaussian_filter(Fa.astype(float), 2) + 1.0
    f = np.zeros(Fa.shape + (2,), np.float32)
    for s in sigmas:
        Fw = pull(Fb, f).astype(np.uint8)
        r = dis().calc(Fa, Fw, None)
        # compose: f_new(x) = r(x) + f(x + r(x))
        fn = r + np.stack([pull(f[..., c], r) for c in range(2)], -1)
        f = smooth(fn, conf, s).astype(np.float32)
    return f

def residual_tiles(ren, ref, f, T=64):
    Fa = feat(ren).astype(float); Fw = pull(feat(ref), f)
    out = []
    for y in range(0, Fa.shape[0] - T + 1, T // 2):
        for x in range(0, Fa.shape[1] - T + 1, T // 2):
            a, b = Fa[y:y + T, x:x + T], Fw[y:y + T, x:x + T]
            if a.std() < 15 or b.std() < 15: continue
            s, _, _ = phase_cross_correlation(a, b, upsample_factor=20, normalization=None)
            out.append((y, x, s[0], s[1]))
    return np.array(out)

def ncc(x, y):
    x = x - x.mean(); y = y - y.mean(); return (x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())

if __name__ == '__main__':
    ren = rgb(SP + 'out/base/ref1x.png'); ref = rgb(SP + 'ref/ref.png')
    for name, sig in [('A', (12, 8, 6, 4, 4, 3)), ('B', (16, 12, 10, 8, 8, 8))]:
        f = register(ren, ref, sig)
        R = residual_tiles(ren, ref, f); m = np.hypot(R[:, 2], R[:, 3])
        print(name, 'NCC %.4f  residual tiles %d: median %.2f p90 %.2f p99 %.2f max %.2f px' % (
            ncc(feat(ren).astype(float), pull(feat(ref), f)), len(R), np.median(m), np.percentile(m, 90), np.percentile(m, 99), m.max()))
        np.save(SP + f'out/field_{name}.npy', f)
