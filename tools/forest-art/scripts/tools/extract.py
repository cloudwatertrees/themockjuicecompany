"""Split ForestPathIllustration.swift into code part and per-layer data files (empty layers give empty files)."""
import re, sys, os
src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
names = []; cur = None; lines = {}
for line in open(src).read().split('\n'):
    m = re.match(r'\s*static let (\w+): String = """\s*$', line)
    if m: cur = m.group(1); lines[cur] = []; continue
    if cur is not None:
        if line.strip() == '"""': cur = None
        elif line.strip(): lines[cur].append(line[8:] if line.startswith('        ') else line.strip())
for name, ls in lines.items():
    open(os.path.join(outdir, name + '.txt'), 'w').write('\n'.join(ls) + ('\n' if ls else ''))
    names.append((name, len(ls)))
print(names)
