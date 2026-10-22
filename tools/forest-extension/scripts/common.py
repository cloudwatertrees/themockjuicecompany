"""Shared paths and helpers for tools/forest-extension. Reuses the forest-art Python renderer (pbart/pbrender)."""
import hashlib, json, os, re, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXT = HERE.parent                                   # tools/forest-extension
REPO = EXT.parent.parent
ART_SWIFT = REPO / 'ios/mockjuice/Views/Components/ForestPathIllustration.swift'
EXT_SWIFT = REPO / 'ios/mockjuice/Views/Components/ForestPathExtension.swift'
HOME_SWIFT = REPO / 'ios/mockjuice/Views/HomeSceneView.swift'
FACTS = EXT / 'facts.json'
SCRATCH = Path(os.environ.get('FX_SCRATCH', '/private/tmp/claude-501/-Users-laverath-Desktop-themockjuicecompany/'
                              'f040d3b9-8afa-4633-96e3-e95aca8ec140/scratchpad/fx'))
SCRATCH.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO / 'tools/forest-art/scripts/tools'))
from art import flatten, LAYERS                     # noqa: E402
from pbart import PShape                            # noqa: E402
import pbrender                                     # noqa: E402

W, H = 937.0, 1678.0


def swift_layer_lines(path):
    """{layer: [data lines]} from a Swift file with `static let NAME: String = \"\"\"` blocks."""
    out, cur = {}, None
    for line in open(path).read().split('\n'):
        m = re.match(r'\s*static let (\w+): String = """\s*$', line)
        if m:
            cur = m.group(1); out[cur] = []; continue
        if cur is not None:
            if line.strip() == '"""':
                cur = None
            elif line.strip():
                out[cur].append(line.strip())
    return out


def load_live_layers(layers=None):
    d = swift_layer_lines(ART_SWIFT)
    return [PShape(L, ln) for L in LAYERS if (layers is None or L in layers) for ln in d.get(L, [])]


def poly_area(s):
    """Even-odd area of a shape in u^2 (sum of |signed areas| of its subpaths, holes are rare)."""
    a = 0.0
    for P in flatten(s.subs, 1.0, tol=0.2):
        x, y = P[:, 0], P[:, 1]
        a += 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return a


def data_sha256(path=ART_SWIFT):
    """Checksum of the live art's data section ('// MARK: - Layer data' to the end of the file): the art itself."""
    text = open(path, 'rb').read()
    i = text.index(b'// MARK: - Layer data')
    return hashlib.sha256(text[i:]).hexdigest()


def require_facts():
    """Stops if the live art data differs from facts.json (code-only edits to the renderer are allowed)."""
    f = json.load(open(FACTS))
    sha = data_sha256()
    if sha != f['data_sha256']:
        sys.exit(f'STOP: live art data checksum {sha[:12]} differs from facts.json {f["data_sha256"][:12]}; rerun stage0 and review.')
    return f


def render(shapes, scale, box, S=8):
    """RGB float image of `shapes` over the design-space box (x0, y0, x1, y1) at `scale` px/u."""
    x0, y0, x1, y1 = box
    return pbrender.render(shapes, scale, -x0 * scale, -y0 * scale, int(round((x1 - x0) * scale)), int(round((y1 - y0) * scale)), S)


def save(img, path):
    from PIL import Image
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)
    return path


def ids_view(shapes, seed=0):
    """Copies of `shapes` with distinct flat random colours (structure views)."""
    rng = np.random.default_rng(seed)
    out = []
    for s in shapes:
        c = rng.uniform(0.15, 0.95, 3)
        out.append(PShape(s.layer, pathstr=s.pathstr, cols=c[None], nx=0, ny=0))
    return out


def in_box(shapes, box, pad=0):
    x0, y0, x1, y1 = box
    return [s for s in shapes if s.box[2] > x0 - pad and s.box[0] < x1 + pad and s.box[3] > y0 - pad and s.box[1] < y1 + pad]
