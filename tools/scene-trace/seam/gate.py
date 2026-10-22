"""Seam gate checks and join crops for one seam variant.

usage: gate.py VARIANT_DIR
Reads VARIANT_DIR/B_seam.png (937x1678) and, if present, VARIANT_DIR/edits.npz (one float alpha mask per edit,
937x1678, 1 = edited pixel; keys are edit names). Writes into VARIANT_DIR:
  gate.txt         numeric results
  join_1x.png      design space x 81..856, A's last 260 rows over B's first 500 rows (775 px wide)
  join_3x.png      three 3x windows across the join (left, path, right), side by side (<= 1500 px wide)
  phone_1x.png     the 393x852 phone framing at 1x around the join (393 px wide)
  phone_3x.png     the same at 3x, centre 500 px of the join (1179 px wide)

Numeric gate (item 1): the seam row (A's last row vs B's first, x 81..856) must be <= 3.1 (A's own neighbour-row
p95, bottom 200 rows, x 81..856). Each edit boundary's mean |dL| across its alpha = 0.5 contour must be <= B's own
neighbour-row p95 over the same rows (base/B_warp.png, rows 0..499, x 81..856; about 4.9). Pass/fail of the seam
as a whole rests mainly on the structure checks, the 1x phone crops and the blind test.
"""
import os
import sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W, H = 937, 1678
VIS = (81, 857)
LIMIT = 3.1
LUM = np.array([0.299, 0.587, 0.114])


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)


def boundary_diff(L, alpha):
    """Mean |dL| over adjacent pixel pairs (horizontal and vertical) that straddle alpha = 0.5, inside x 81..856."""
    m = alpha >= 0.5
    d = []
    hx = m[:, 1:] != m[:, :-1]
    hx[:, :VIS[0]] = False; hx[:, VIS[1] - 1:] = False
    d.append(np.abs(L[:, 1:] - L[:, :-1])[hx])
    vy = m[1:] != m[:-1]
    vy[:, :VIS[0]] = False; vy[:, VIS[1]:] = False
    d.append(np.abs(L[1:] - L[:-1])[vy])
    d = np.concatenate(d)
    return (float(d.mean()), int(d.size)) if d.size else (0.0, 0)


def main(vdir):
    A = load(os.path.join(ROOT, 'A.png'))
    B = load(os.path.join(vdir, 'B_seam.png'))
    assert B.shape == (H, W, 3), B.shape
    LA, LB = A @ LUM, B @ LUM
    ref = np.abs(np.diff(LA[:, VIS[0]:VIS[1]], axis=0)).mean(1)[-200:]
    BW = load(os.path.join(HERE, 'base', 'B_warp.png')) @ LUM
    brows = np.abs(np.diff(BW[:500, VIS[0]:VIS[1]], axis=0)).mean(1)
    elimit = float(np.percentile(brows, 95))
    lines = [f'A neighbour rows (bottom 200, x 81..856): mean {ref.mean():.2f} p95 {np.percentile(ref, 95):.2f} max {ref.max():.2f}; seam limit {LIMIT}',
             f'B (warped, unedited) neighbour rows 0..499: p95 {elimit:.2f} = edit-boundary limit']
    seam = float(np.abs(LA[-1, VIS[0]:VIS[1]] - LB[0, VIS[0]:VIS[1]]).mean())
    ok = seam <= LIMIT
    lines.append(f'seam row A[1677] vs B[0]: {seam:.2f} {"ok" if seam <= LIMIT else "FAIL"}')
    rows = np.abs(np.diff(LB[:500, VIS[0]:VIS[1]], axis=0)).mean(1)
    lines.append(f'B top 500 neighbour rows: mean {rows.mean():.2f} p95 {np.percentile(rows, 95):.2f} max {rows.max():.2f} (row {int(rows.argmax())}) [info]')
    ep = os.path.join(vdir, 'edits.npz')
    if os.path.exists(ep):
        for name, alpha in np.load(ep).items():
            v, n = boundary_diff(LB, alpha)
            ok &= v <= elimit
            lines.append(f'edit {name}: boundary mean |dL| {v:.2f} over {n} pairs {"ok" if v <= elimit else "FAIL"}')
    else:
        lines.append('no edits.npz: edit boundaries not measured')
    lines.append('NUMERIC ' + ('PASS' if ok else 'FAIL'))
    open(os.path.join(vdir, 'gate.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    comp = np.vstack([A, B]).clip(0, 255).astype(np.uint8)
    Image.fromarray(comp[H - 260:H + 500, VIS[0]:VIS[1]]).save(os.path.join(vdir, 'join_1x.png'))
    wins = [(150, 'left'), (520, 'path'), (760, 'right')]
    tiles = []
    for cx, _ in wins:
        t = Image.fromarray(comp[H - 60:H + 110, cx - 82:cx + 82]).resize((164 * 3, 170 * 3), Image.NEAREST)
        tiles.append(t)
    sheet = Image.new('RGB', (sum(t.width for t in tiles) + 8 * 2, tiles[0].height), (255, 255, 255))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0)); x += t.width + 8
    sheet.save(os.path.join(vdir, 'join_3x.png'))
    # phone framing: 393x852 pt, segment height 852 pt (s = 852/1678), x crop centred
    for scale, name, rows_pt in [(1, 'phone_1x.png', 300), (3, 'phone_3x.png', 170)]:
        # resample the stacked pair as one image so the join gets no resampling edge of its own
        s = 852 * scale / H
        w = round(W * s); h = round(H * s)
        x0 = (w - 393 * scale) // 2
        both = Image.fromarray(comp).resize((w, 2 * h), Image.LANCZOS)
        both.crop((x0, h - rows_pt * scale, x0 + 393 * scale, h + rows_pt * scale)).save(os.path.join(vdir, name))

if __name__ == '__main__':
    main(sys.argv[1])
