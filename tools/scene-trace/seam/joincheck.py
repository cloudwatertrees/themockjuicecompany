"""Join crops and the numeric seam test for A over a B variant (source pixels, or renders of each).

usage: joincheck.py A.png B.png OUTPREFIX [--phone]
--phone: resample both to the 393x852 @3x phone segment (1179 px wide view, s = 2556/1678) and crop x to the view.
Seam test: mean |dL| between A's last row and B's first row over x 81..856 (design) vs A's own neighbour-row
differences in its bottom 200 rows (mean, p95, max).
"""
import sys
import numpy as np
from PIL import Image

a, b, pre = sys.argv[1:4]
phone = '--phone' in sys.argv
A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB')
lum = np.array([0.299, 0.587, 0.114])
if phone:
    s = 2556 / 1678
    w, h = round(937 * s), round(1678 * s)
    x0 = (w - 1179) // 2
    A = A.resize((w, h), Image.LANCZOS).crop((x0, 0, x0 + 1179, h))
    B = B.resize((w, h), Image.LANCZOS).crop((x0, 0, x0 + 1179, h))
    vis = (0, 1179)
else:
    vis = (81, 857)
an = np.asarray(A, np.float64); bn = np.asarray(B, np.float64)
la = an[:, vis[0]:vis[1]] @ lum; lb = bn[:, vis[0]:vis[1]] @ lum
d = np.abs(np.diff(la, axis=0)).mean(1)[-200:]
seam = np.abs(la[-1] - lb[0]).mean()
db = np.abs(np.diff(lb, axis=0)).mean(1)[:200]
print(f'{pre}: seam |dL| {seam:.2f}  A bottom-200 neighbour rows mean {d.mean():.2f} p95 {np.percentile(d, 95):.2f} max {d.max():.2f}'
      f'  | B top-200 rows mean {db.mean():.2f} max {db.max():.2f}  -> {"PASS" if seam <= d.max() else "FAIL"}')
H = an.shape[0]
st = np.vstack([an[H - 260:], bn[:260]]).astype(np.uint8)
Image.fromarray(st).save(pre + '_1x.png')
cw = st.shape[1]
for i, (cx, name) in enumerate([(0.18, 'L'), (0.5, 'M'), (0.78, 'R')]):
    c = int(cx * cw); half = 75 if not phone else 110
    crop = Image.fromarray(st[260 - 60:260 + 90, max(c - half, 0):c + half])
    crop.resize((crop.width * 3, crop.height * 3), Image.NEAREST).save(f'{pre}_3x_{name}.png')
