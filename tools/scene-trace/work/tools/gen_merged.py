"""Write the single home-screen art file: ForestPathIllustration.swift with both screens' data.

usage: gen_merged.py HEAD.swift CODE_SRC.swift TOP_DATADIR BOTTOM_DATADIR TOP.png BOTTOM.png OUT.swift
HEAD.swift   view, layout, caching and ForestPathArt API (merged_head.swift), with @CASES@ and @COLOURS@ placeholders.
CODE_SRC     a previous ForestPathIllustration.swift; its ShapeDataReader / ShapeRaster / RowShader code (from
             '/// Single-pass reader' up to '// MARK: - Layer data') is copied verbatim (ShapeDataReader made
             nonisolated, since both screens parse off the main thread).
Data dirs    per-layer .txt files from extract.py. Bottom data is in its own design space (y = 0 at the join)."""
import os, sys
import numpy as np
from PIL import Image

LAYERS = ['meadow', 'pathEdges', 'path', 'water', 'rocks', 'wood', 'foliage', 'conifers', 'accents', 'flowers']
DOC = {
    'meadow': 'Grass base, shading and the grassy verges.',
    'pathEdges': 'Brown earth banks along the path, with their spots.',
    'path': 'The winding cream path and its pebbles.',
    'water': 'Pond, waterfall and stream.',
    'rocks': 'Boulders, rock piles and cliff stones.',
    'wood': 'Tree trunks and roots, the bridge, log, lamp post, signpost and fence.',
    'foliage': 'Leafy trees, bushes and grass tufts.',
    'conifers': 'Dark pines and firs.',
    'accents': 'Red mushroom caps and the lantern glow.',
    'flowers': 'Daisies, purple and yellow flowers.',
}

head, code_src, top_dir, bot_dir, top_png, bot_png, out = sys.argv[1:8]
A = np.asarray(Image.open(top_png).convert('RGB')).astype(float)
B = np.asarray(Image.open(bot_png).convert('RGB')).astype(float)


def rgb(c):
    r, g, b = (int(round(v)) for v in c)
    return f'RGB(r: {r}, g: {g}, b: {b})'


colours = '\n'.join([
    '    static let topGround = ' + rgb(A.reshape(-1, 3).mean(0)) + '        // mean of the top screen',
    '    static let seamGround = ' + rgb(B[:200].reshape(-1, 3).mean(0)) + '       // mean of the bottom screen\'s first 200 u',
    '    static let topBounce = ' + rgb(A[:24].reshape(-1, 3).mean(0)) + '        // above the top screen',
    '    static let bottomBounce = ' + rgb(B[-24:].reshape(-1, 3).mean(0)) + '     // below the bottom screen',
])
text = open(head).read().replace('@CASES@', ', '.join(LAYERS)).replace('@COLOURS@', colours)
src = open(code_src).read()
code = src[src.index('/// Single-pass reader'):src.index('// MARK: - Layer data')]
code = code.replace('struct ShapeDataReader {', 'nonisolated struct ShapeDataReader {', 1)
assert 'nonisolated struct ShapeDataReader' in code and 'struct ShapeRaster' in code and 'struct RowShader' in code


def screen_block(name, doc, datadir):
    switch = '\n'.join(f'        case .{n}: return {n}' for n in LAYERS)
    parts = [f'/// {doc}\nnonisolated enum {name} {{\n'
             f'    /// Raw data for a layer, one shape per line, back to front. Each line is `RRGGBB <path>` for a flat fill,\n'
             f'    /// `RRGGBB RRGGBB x0 y0 x1 y1 <path>` for a linear gradient from (x0, y0) to (x1, y1), or `*W H RRGGBB … <path>`\n'
             f'    /// for a W × H bilinear mesh gradient spanning the path\'s bounding rect grown by one unit. `<path>` is SVG\n'
             f'    /// path data (M, L, C, Z and relative l, c) in design-space units.\n'
             f'    static func data(of id: ForestPathArt.LayerID) -> String {{\n        switch id {{\n{switch}\n        }}\n    }}\n']
    for n in LAYERS:
        p = os.path.join(datadir, n + '.txt')
        lines = [l for l in open(p).read().split('\n') if l.strip()] if os.path.exists(p) else []
        body = ''.join('        ' + l + '\n' for l in lines)
        parts.append(f'\n    /// {DOC[n]}\n    static let {n}: String = """\n{body}        """\n')
    parts.append('}\n')
    return ''.join(parts)


data = ('// MARK: - Layer data\n//\n// Traced from the two reference screens (tools/scene-trace: A.png, B_seam.png) with tools/scene-trace/i2s/pipeline.py;\n'
        '// written by tools/scene-trace/work/tools/gen_merged.py. Shapes are listed back to front within each layer.\n\n'
        + screen_block('TopScreen', 'Top screen data (design space 937×1678).', top_dir) + '\n'
        + screen_block('BottomScreen', 'Bottom screen data (design space 937×1678, y = 0 on the top screen\'s bottom edge).', bot_dir))
open(out, 'w').write(text + code + data)
print('wrote', out, os.path.getsize(out), 'bytes')
