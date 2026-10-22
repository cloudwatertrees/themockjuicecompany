"""Writes traced shapes as a Swift file: named layers, one shape per line of SVG-style path data."""
import os

import numpy as np

from hf_groups import GROUPS

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'ForestPathArt.swift.tmpl')

DOC = {
    'meadow': 'Grass base, shading and the grassy verges.',
    'pathEdges': 'Brown earth banks along the path, with their spots.',
    'path': 'The winding cream path and its pebbles.',
    'water': 'Pond, waterfall and stream.',
    'rocks': 'Boulders, rock piles and cliff stones.',
    'wood': 'Tree trunks and roots, the bridge, log, lamp post, signpost and fence.',
    'foliage': 'Leafy trees and bushes.',
    'conifers': 'Dark pines and firs.',
    'accents': 'Red mushroom caps and the lantern glow.',
    'flowers': 'Daisies, purple and yellow flowers.',
}


def num(v):
    v = round(float(v), 1)
    if v == 0:
        v = 0.0
    s = f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s


def hexc(c):
    c = np.clip(np.round(c), 0, 255).astype(int)
    return f'{c[0]:02X}{c[1]:02X}{c[2]:02X}'


def q(v):
    return int(round(float(v) * 10))


def tenths(i):
    s = f'{abs(i) // 10}' + (f'.{abs(i) % 10}' if abs(i) % 10 else '')
    return ('-' if i < 0 else '') + s


def path_data(subpaths):
    """Absolute moveto, then relative cubics ('c') measured from rounded absolute points (no drift)."""
    out = []
    for segs in subpaths:
        cx, cy = q(segs[0][0][0]), q(segs[0][0][1])
        parts = [f'M{tenths(cx)} {tenths(cy)}']
        for b in segs:
            pts = [(q(p[0]), q(p[1])) for p in b[1:]]
            parts.append('c' + ' '.join(f'{tenths(x - cx)} {tenths(y - cy)}' for x, y in pts))
            cx, cy = pts[2]
        parts.append('Z')
        out.append(''.join(parts))
    return ''.join(out)


def shape_line(sh):
    f = sh['fill']
    d = path_data(sh['subpaths'])
    if f['type'] == 'flat':
        return f'        {hexc(f["color"])} {d}'
    if f['type'] == 'mesh':
        return f'        *{f["nx"]} {f["ny"]} ' + ' '.join(hexc(c) for c in f['colors']) + f' {d}'
    (x0, y0), (x1, y1) = f['p0'], f['p1']
    return f'        {hexc(f["colors"][0])} {hexc(f["colors"][1])} {num(x0)} {num(y0)} {num(x1)} {num(y1)} {d}'


def emit(shapes, path, zones=None):
    """Returns (bytes written, segment count, shapes per layer)."""
    by = {g: [] for g in GROUPS}
    for sh in shapes:
        by[sh['group']].append(sh)
    src = open(TEMPLATE).read()
    src = src.replace('@CASES@', ', '.join(GROUPS))
    src = src.replace('@SWITCH@', '\n'.join(f'        case .{g}: return {g}' for g in GROUPS))
    parts = [src, '// MARK: - Layer data', '//',
             '// Traced from the reference artwork. Shapes are listed back to front within each layer.', '',
             'extension ForestPathArt {']
    for i, g in enumerate(GROUPS):
        lines = [shape_line(s) for s in by[g]]
        parts.append(f'    /// {DOC[g]}\n    static let {g}: String = """\n' + '\n'.join(lines) + '\n        """'
                     + ('\n' if i < len(GROUPS) - 1 else ''))
    if zones is not None:
        zl = [f'        {path_data([s])}' for s in zones]
        parts[-1] += '\n'
        parts.append('    /// Soft-zone outlines (the canvas minus a 4 px band around every hard edge):\n'
                     '    /// one closed subpath per line, even-odd filled.\n'
                     '    static let softZoneData: String = """\n' + '\n'.join(zl) + '\n        """')
    parts.append('}\n')
    out = '\n'.join(parts)
    open(path, 'w').write(out)
    nseg = sum(len(x) for s in shapes for x in s['subpaths'])
    return len(out.encode()), nseg, {g: len(v) for g, v in by.items()}
