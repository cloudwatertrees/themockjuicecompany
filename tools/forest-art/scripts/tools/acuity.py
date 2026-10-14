"""Edge acuity along matched edges: erf fit of edge profiles (sigma in device px at 3x) for a render vs the
reference bicubic-upscaled to the same framing; also the reference's own edge sigma at 1x."""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.special import erf
from skimage.feature import canny
from skimage.color import rgb2lab
from score import rgb, to_device, SP, DS, DOX, DOY, DEV, W, H

def luma(x): return x @ np.array([0.2126, 0.7152, 0.0722])

def edge_samples(ref, n=4000, seed=0, min_contrast=0.08):
    """Strong, isolated edges in the reference at 1x: positions + unit normals (design units)."""
    Y = luma(ref)
    e = canny(Y, sigma=1.0, low_threshold=0.02, high_threshold=0.05)
    gy, gx = ndi.sobel(ndi.gaussian_filter(Y, 1.0), 0), ndi.sobel(ndi.gaussian_filter(Y, 1.0), 1)
    ys, xs = np.nonzero(e)
    keep = (xs > -DOX / DS + 8) & (xs < (DEV[0] - DOX) / DS - 8) & (ys > -DOY / DS + 8) & (ys < (DEV[1] - DOY) / DS - 8)   # inside the device crop
    ys, xs = ys[keep], xs[keep]
    rng = np.random.default_rng(seed); idx = rng.permutation(len(ys))[:n * 3]
    out = []
    for i in idx:
        y, x = ys[i], xs[i]
        g = np.array([gx[y, x], gy[y, x]]); m = np.hypot(*g)
        if m < 1e-6: continue
        nrm = g / m
        t = np.linspace(-4, 4, 33)
        px, py = x + 0.5 + t * nrm[0], y + 0.5 + t * nrm[1]
        prof = ndi.map_coordinates(Y, [py - 0.5, px - 0.5], order=1)
        if abs(prof[-1] - prof[0]) < min_contrast: continue
        # isolated: profile monotone-ish (single step) within +-4 px
        d = np.diff(prof) * np.sign(prof[-1] - prof[0])
        if (d < -0.01).sum() > 2: continue
        out.append((x + 0.5, y + 0.5, nrm[0], nrm[1]))
        if len(out) >= n: break
    return np.array(out)

def fit_sigma(prof, t):
    from scipy.optimize import least_squares
    a0, b0 = prof[0], prof[-1]
    def f(p):
        a, b, t0, s = p
        return a + (b - a) * 0.5 * (1 + erf((t - t0) / (np.sqrt(2) * abs(s) + 1e-9))) - prof
    r = least_squares(f, [a0, b0, 0.0, 1.0])
    return abs(r.x[3]), np.sqrt(np.mean(r.fun ** 2)) / max(abs(b0 - a0), 1e-6)

def measure(img, E, scale, ox, oy, half=6.0, n=49):
    """Profiles across edges E (design coords) in an image at `scale` px per unit, offset (ox, oy). sigma in px."""
    Y = luma(img); out = []
    t = np.linspace(-half, half, n)
    for x, y, nx, ny in E:
        px, py = x * scale + ox + t * nx, y * scale + oy + t * ny
        prof = ndi.map_coordinates(Y, [py - 0.5, px - 0.5], order=1)
        s, res = fit_sigma(prof, t)
        out.append(s if res < 0.08 else np.nan)
    return np.array(out)

if __name__ == '__main__':
    ref = rgb(SP + 'ref/ref.png')
    E = edge_samples(ref, 1500)
    s1 = measure(ref, E, 1.0, 0, 0, half=4.0, n=33)
    print('edges sampled', len(E))
    print('reference @1x  edge sigma px: median %.3f  p25 %.3f  p75 %.3f' % tuple(np.nanpercentile(s1, [50, 25, 75])))
    refd = to_device(ref)
    sr = measure(refd, E, DS, DOX, DOY)
    print('ref bicubic @3x edge sigma px: median %.3f  p25 %.3f  p75 %.3f   (10-90%% rise %.2f px)' % (tuple(np.nanpercentile(sr, [50, 25, 75])) + (2.563 * np.nanmedian(sr),)))
    for tag in sys.argv[1:]:
        ren = rgb(SP + f'out/{tag}/dev3x.png')
        s = measure(ren, E, DS, DOX, DOY)
        ok = ~np.isnan(s) & ~np.isnan(sr)
        print('%-8s @3x  edge sigma px: median %.3f  p25 %.3f  p75 %.3f   (10-90%% rise %.2f px); sharper than ref on %.0f%% of edges; fit ok %.0f%%' % (
            (tag,) + tuple(np.nanpercentile(s, [50, 25, 75])) + (2.563 * np.nanmedian(s), 100 * (s[ok] < sr[ok]).mean(), 100 * (~np.isnan(s)).mean())))
    np.save(SP + 'out/acuity_edges.npy', E)
