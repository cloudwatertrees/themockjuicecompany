"""v2: write ForestPathIllustration.swift for the new scene: the Phase B code (CPU renderer) with the 17-layer list,
its data(of:) switch, and every layer's data block from a data dir (empty layers get an empty block).
Canvas size W H (default 937 1678) sets ForestPathArt.size and the doc comment.
usage: v2_gen_swift.py PHASEB.swift DATADIR OUT.swift [W H]"""
import os, re, sys

LAYERS = ['meadow', 'hedge', 'pathEdges', 'path', 'pond', 'backTrees', 'pines', 'bridge', 'bushes',
          'doorBush', 'door', 'stones', 'rocks', 'fox', 'log', 'flowers', 'frontTrees']
DOC = {
    'meadow': 'Grass base, shading and the grassy verges.',
    'hedge': 'The clipped hedge mass along the top right.',
    'pathEdges': 'Brown dirt borders either side of the path, with their spots.',
    'path': 'The winding cream path and its pebbles.',
    'pond': 'The pond at the top left, with its lily pads, cattails and rim stones.',
    'backTrees': 'Conifers along the left, behind the path.',
    'pines': 'The two young pines.',
    'bridge': 'Log-railed wooden bridge on stone abutments.',
    'bushes': 'Leafy bushes around the bridge, the boulder and the log.',
    'doorBush': 'The bush around the rock pile on the right.',
    'door': 'Not in this scene (kept so the layer API is unchanged).',
    'stones': 'Not in this scene (kept so the layer API is unchanged).',
    'rocks': 'The stacked rock pile, the boulder and the small rocks at the bottom left.',
    'fox': 'Not in this scene (kept so the layer API is unchanged).',
    'log': 'The fallen log.',
    'flowers': 'Daisies, purple and yellow flowers.',
    'frontTrees': 'Foreground conifers at the bottom left and right.',
}

src, datadir, out = sys.argv[1:4]
text = open(src).read()
code = text[:text.index('// MARK: - Layer data')]
code = re.sub(r'(enum LayerID: CaseIterable \{\n\s*case )[^\n]+', lambda m: m.group(1) + ', '.join(LAYERS), code, count=1)
switch = '\n'.join(f'        case .{n}: return {n}' for n in LAYERS)
code = re.sub(r'(static func data\(of id: LayerID\) -> String \{\n\s*switch id \{\n)(.*?)(\n\s*\}\n\s*\})',
              lambda m: m.group(1) + switch + m.group(3), code, count=1, flags=re.S)
code = code.replace('`ForestPathLayers([.fox]).offset(x: 20)`', '`ForestPathLayers([.log]).offset(x: 20)`')
cw, ch = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (937, 1678)
code = code.replace('static let size = CGSize(width: 937, height: 1678)', 'static let size = CGSize(width: %d, height: %d)' % (cw, ch))
code = code.replace('traced from the 937×1678 reference', 'traced from the %d×%d reference' % (cw, ch))
parts = [code + '// MARK: - Layer data\n//\n// Traced from the reference artwork. Shapes are listed back to front within each layer.\n\nextension ForestPathArt {']
blocks = []
for n in LAYERS:
    p = os.path.join(datadir, n + '.txt')
    lines = [l for l in open(p).read().split('\n') if l.strip()] if os.path.exists(p) else []
    body = '\n'.join('        ' + l for l in lines)
    blocks.append(f'    /// {DOC[n]}\n    static let {n}: String = """\n' + (body + '\n' if body else '') + '        """')
parts.append('\n\n'.join(blocks))
parts.append('}\n')
open(out, 'w').write('\n'.join(parts))
print('wrote', out, os.path.getsize(out), 'bytes;', {n: len([l for l in open(os.path.join(datadir, n + '.txt')).read().split('\n') if l.strip()]) if os.path.exists(os.path.join(datadir, n + '.txt')) else 0 for n in LAYERS})
