"""Split ForestPathIllustration.swift into code part and per-layer data files."""
import re, sys, os
src, outdir = sys.argv[1], sys.argv[2]
text = open(src).read()
os.makedirs(outdir, exist_ok=True)
names = []
for m in re.finditer(r'static let (\w+): String = """\n(.*?)\n\s*"""', text, re.S):
    name, body = m.group(1), m.group(2)
    lines = [l[8:] if l.startswith('        ') else l.strip() for l in body.split('\n')]
    open(os.path.join(outdir, name + '.txt'), 'w').write('\n'.join(lines) + '\n')
    names.append((name, len(lines)))
print(names)
