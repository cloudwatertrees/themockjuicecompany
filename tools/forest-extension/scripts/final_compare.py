"""Final blind comparison: pairs of equal-size crops (one live, one new) of the same element type, left/right order
shuffled with a fixed seed. Sheets at phone 1x (0.508 pt/u, as on 393x852 @1x) and at 3x of that; key in a separate
file. usage: python final_compare.py"""
import json
import numpy as np
from common import *
from extdata import load_ext_layers

PHONE = 852 / H                                   # pt per design unit on 393x852
# (type, live box, new box) in each art's own coordinates, same size per pair
PAIRS = [
    ('bush with flowers', (225, 880, 435, 1050), (535, 60, 745, 230)),
    ('boulder + ferns', (520, 845, 760, 1030), (0, 70, 240, 255)),
    ('fern-pine', (310, 400, 520, 670), (530, 250, 740, 520)),
    ('bell-tree group', (690, 1080, 937, 1420), (690, 90, 937, 430)),
    ('water', (0, 300, 300, 520), (20, 1260, 320, 1480)),
    ('path + edge band', (330, 1180, 760, 1400), (380, 900, 810, 1120)),
    ('trees, left edge', (0, 1150, 260, 1480), (0, 690, 260, 1020)),
    ('ground, flowers, tufts', (380, 1020, 620, 1160), (280, 1500, 520, 1640)),
]

live = load_live_layers()
ext = load_ext_layers()
rng = np.random.default_rng(1017)
key = []
sheets = {'1x': [], '3x': []}
for i, (name, lb, nb) in enumerate(PAIRS):
    new_left = bool(rng.random() < 0.5)
    for tag, sc in (('1x', PHONE), ('3x', PHONE * 3)):
        a = render(in_box(live, lb, 4), sc, lb)
        b = render(in_box(ext, nb, 4), sc, nb)
        h = min(a.shape[0], b.shape[0]); w = min(a.shape[1], b.shape[1])
        a, b = a[:h, :w], b[:h, :w]
        L, R = (b, a) if new_left else (a, b)
        sep = np.ones((h, 6 if tag == '1x' else 12, 3))
        sheets[tag].append(np.concatenate([L, sep, R], 1))
    key.append({'pair': i + 1, 'type': name, 'new_is': 'left' if new_left else 'right', 'live_box': lb, 'new_box': nb})


def stack(rows, gap):
    wmax = max(r.shape[1] for r in rows)
    out = []
    for r in rows:
        out.append(np.pad(r, ((0, gap), (0, wmax - r.shape[1]), (0, 0)), constant_values=1))
    return np.concatenate(out, 0)


out = EXT / 'crops' / 'final'
out.mkdir(parents=True, exist_ok=True)
save(stack(sheets['1x'], 10), out / 'compare_phone_1x.png')
for k in range(0, len(sheets['3x']), 2):
    save(stack(sheets['3x'][k:k + 2], 20), out / f'compare_3x_pairs_{k + 1}-{k + 2}.png')
json.dump(key, open(EXT / 'final_compare_KEY.json', 'w'), indent=1)
print('pairs', len(key), 'sheets in', out)
