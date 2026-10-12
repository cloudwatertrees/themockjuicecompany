"""Write layer data from a data dir into the repo Swift file's string literals (everything else untouched)."""
import re, sys, os
src_swift, datadir, out = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(src_swift).read()
def repl(m):
    name = m.group(1)
    lines = [l for l in open(os.path.join(datadir, name + '.txt')).read().split('\n') if l.strip()]
    body = '\n'.join('        ' + l for l in lines)
    return f'static let {name}: String = """\n{body}\n        """'
new, n = re.subn(r'static let (\w+): String = """\n.*?\n\s*"""', repl, text, flags=re.S)
open(out, 'w').write(new)
print('replaced', n, 'blocks;', len(text), '->', len(new), 'bytes')
