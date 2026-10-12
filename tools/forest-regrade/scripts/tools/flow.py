"""Dense displacement field render->reference from colour-invariant edge structure (DIS optical flow)."""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab
SP = '/tmp/work/'

def rgb(p): return np.asarray(Image.open(p).convert('RGB')).astype(np.float64) / 255

def feat(img, s=1.0):
    L = rgb2lab(img)
    g = sum(ndi.gaussian_gradient_magnitude(L[..., c], s) ** 2 for c in range(3)) ** 0.5
    g = g / (ndi.gaussian_filter(g, 10) + 3.0)
    return np.clip(g * 90, 0, 255).astype(np.uint8)

def flow(ren, ref):
    a, b = feat(ren), feat(ref)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    dis.setFinestScale(0); dis.setPatchSize(12); dis.setPatchStride(4)
    dis.setGradientDescentIterations(25); dis.setVariationalRefinementIterations(10)
    dis.setVariationalRefinementAlpha(40.0)
    return dis.calc(a, b, None)   # flow[y,x] = displacement d such that ren(x) ~ ref(x+d)

def warp(img, f):
    h, w = f.shape[:2]
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img.astype(np.float32), mx + f[..., 0], my + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

if __name__ == '__main__':
    ren = rgb(SP + 'out/base/flat1x.png'); ref = rgb(SP + 'ref/ref.png')
    f = flow(ren, ref)
    np.save(SP + 'out/flow_base.npy', f)
    mag = np.hypot(f[..., 0], f[..., 1])
    print('flow |d| median %.1f p90 %.1f max %.1f; dx med %.1f dy med %.1f' % (np.median(mag), np.percentile(mag, 90), mag.max(), np.median(f[..., 0]), np.median(f[..., 1])))
    # check: reference pulled back into render geometry
    back = warp(ref, f)
    from skimage.metrics import structural_similarity as ssim
    fa, fb, fw = feat(ren), feat(ref), feat(back)
    def ncc(x, y): x = x - x.mean(); y = y - y.mean(); return (x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())
    print('edge-feature NCC render vs ref: %.3f   render vs ref warped by flow: %.3f' % (ncc(fa.astype(float), fb.astype(float)), ncc(fa.astype(float), fw.astype(float))))
    Image.fromarray((np.clip(back, 0, 1) * 255).astype(np.uint8)).save(SP + 'out/base/ref_pulled.png')
    # flow visualisation: hue = direction, value = magnitude (0..40 px)
    hsv = np.zeros(ren.shape, np.uint8)
    hsv[..., 0] = ((np.arctan2(f[..., 1], f[..., 0]) + np.pi) / (2 * np.pi) * 179).astype(np.uint8)
    hsv[..., 1] = 255; hsv[..., 2] = np.clip(mag / 40 * 255, 0, 255).astype(np.uint8)
    vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    Image.fromarray(vis).resize((469, 839)).save(SP + 'out/base/flowvis.png')
    # quiver-ish grid print
    for y in range(40, 1678, 160):
        print(' '.join('%+3.0f,%+3.0f' % (f[y, x, 0], f[y, x, 1]) for x in range(40, 937, 110)))
