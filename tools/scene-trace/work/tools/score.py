"""Score a render against the reference: SSIM (luma), CIEDE2000 raw and low-passed, per region, heat map."""
import sys, os, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab, deltaE_ciede2000
SP = '/Users/laverath/Desktop/themockjuicecompany/tools/scene-trace/work/'
LAYERS = ['meadow', 'hedge', 'pathEdges', 'path', 'pond', 'backTrees', 'pines', 'bridge', 'bushes',
          'doorBush', 'door', 'stones', 'rocks', 'fox', 'log', 'flowers', 'frontTrees']
GROUPS = [('meadow', ['meadow']), ('hedge', ['hedge']), ('path', ['path', 'pathEdges']),
          ('trees', ['backTrees', 'pines', 'frontTrees']), ('bushes', ['bushes', 'doorBush']),
          ('bridge', ['bridge']), ('pond', ['pond']), ('rocks', ['rocks', 'stones']), ('log', ['log']), ('flowers', ['flowers'])]
from art import W, H
DEV = (1179, 2556); DS = max(DEV[0] / W, DEV[1] / H); DOX = (DEV[0] - W * DS) / 2; DOY = (DEV[1] - H * DS) / 2

def rgb(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64) / 255

def labelmap(datadir=None):
    """Topmost layer per pixel (coverage >= 0.5), from the Python rasterizer of the given data."""
    if os.environ.get('LABELMAP'):                    # v2: precomputed per-pixel layer map (layer indices)
        return np.load(os.environ['LABELMAP']).astype(np.int16)
    datadir = datadir or os.environ.get('LABELS', SP + 'data/warpA')
    f = SP + 'out/labels_%s.npy' % os.path.basename(datadir.rstrip('/'))
    if os.path.exists(f):
        return np.load(f)
    from art import load, rasterize, flatten
    lab = np.full((H, W), -1, np.int16)
    for sh in load(datadir):
        r = rasterize(flatten(sh.subs, 1.0), 1.0, 0, 0, W, H)
        if r is None: continue
        x0, y0, c = r; sub = lab[y0:y0 + c.shape[0], x0:x0 + c.shape[1]]
        sub[c >= 0.5] = LAYERS.index(sh.layer)
    np.save(f, lab); return lab

def to_device(img, order=3):
    """Aspect-fill design-space (W x H) image into device framing at 3x."""
    out = []
    yy, xx = np.mgrid[0:DEV[1], 0:DEV[0]]
    sx = (xx + 0.5 - DOX) / DS - 0.5; sy = (yy + 0.5 - DOY) / DS - 0.5
    chans = img.shape[2] if img.ndim == 3 else 0
    for c in range(max(chans, 1)):
        ch = img[..., c] if chans else img
        out.append(ndi.map_coordinates(ch, [sy, sx], order=order, mode='nearest', prefilter=(order > 1)))
    return np.clip(np.stack(out, -1), 0, 1) if chans else out[0]

def luma(x):
    return x @ np.array([0.2126, 0.7152, 0.0722])

def lowpass(x, s):
    return np.stack([ndi.gaussian_filter(x[..., c], s) for c in range(3)], -1)

def metrics(ren, ref, lab, sigma_lp):
    _, smap = structural_similarity(luma(ren), luma(ref), data_range=1, gaussian_weights=True, sigma=1.5,
                                    use_sample_covariance=False, full=True)
    de = deltaE_ciede2000(rgb2lab(ren), rgb2lab(ref))
    delp = deltaE_ciede2000(rgb2lab(lowpass(ren, sigma_lp)), rgb2lab(lowpass(ref, sigma_lp)))
    rows = [('ALL', np.ones_like(lab, bool))]
    for g, ls in GROUPS:
        rows.append((g, np.isin(lab, [LAYERS.index(l) for l in ls])))
    res = {}
    for name, m in rows:
        res[name] = (m.mean(), smap[m].mean(), de[m].mean(), np.percentile(de[m], 95), delp[m].mean(), np.percentile(delp[m], 95))
    return res, de, delp, smap

def heat(de, vmax=12):
    t = np.clip(de / vmax, 0, 1)
    anchors = np.array([[0, 0, 0], [40, 20, 120], [180, 30, 100], [250, 120, 20], [255, 240, 120]]) / 255
    x = t * (len(anchors) - 1); i = np.minimum(x.astype(int), len(anchors) - 2); f = (x - i)[..., None]
    return anchors[i] * (1 - f) + anchors[i + 1] * f

def report(name, res):
    print(f'{name}')
    print('  region     area   SSIM   dE00 mean  p95 | lowpass dE00 mean  p95')
    for k, (a, s, dm, dp, lm, lp) in res.items():
        print(f'  {k:9s} {a*100:5.1f}%  {s:.4f}   {dm:6.2f} {dp:6.2f} |       {lm:6.2f} {lp:6.2f}')

if __name__ == '__main__':
    tag = sys.argv[1]  # out/<tag>/ref1x.png and dev3x.png
    d = SP + f'out/{tag}/'
    ref = rgb(SP + 'ref/ref.png'); lab = labelmap()
    res, de, delp, smap = metrics(rgb(d + 'ref1x.png'), ref, lab, 2.0)
    report(f'[{tag}] reference framing {W}x{H} @1x (lowpass sigma 2 px)', res)
    hm = np.concatenate([heat(delp), np.ones((H, 6, 3)), heat(de)], 1)
    Image.fromarray((hm * 255).astype(np.uint8)).resize((hm.shape[1] // 2, 839), Image.BILINEAR).save(d + 'heat.png')
    np.save(d + 'delp.npy', delp.astype(np.float32))
    if os.path.exists(d + 'dev3x.png'):
        refd = to_device(ref); labd = to_device(lab.astype(float), order=0).astype(np.int16)
        res, de, delp, smap = metrics(rgb(d + 'dev3x.png'), refd, labd, 3.0)
        report(f'[{tag}] device 393x852 @3x vs reference bicubic-upscaled to same framing (lowpass sigma 3 px)', res)
