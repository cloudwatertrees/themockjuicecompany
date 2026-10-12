"""bisect_inv.py TARGET CROP(x,y,w,h) CANDIDATES(lo-hi) : ddmin over preceding shapes that make TARGET's edges invert."""
import sys, subprocess, re, os
SP = '/tmp/work/'
PY = SP + 'venv/bin/python'; T = SP + 'tools/'
target = int(sys.argv[1]); crop = sys.argv[2].split(','); lo, hi = (int(v) for v in sys.argv[3].split('-'))
cache = {}
def bad(S):
    key = tuple(sorted(S))
    if key in cache: return cache[key]
    d = SP + 'exp/d_bis'; png = SP + 'exp/bis.png'
    subprocess.run([PY, T + 'subset.py', SP + 'data/pb22', d, ','.join(map(str, sorted(set(S) | {target})))], check=True, cwd=T)
    open(SP + 'exp/jb.txt', 'w').write(f'full 393 852 3 {png}\n')
    subprocess.run([T + 'render.sh', 'dev', SP + 'exp/jb.txt', d], check=True, capture_output=True)
    out = subprocess.run([PY, T + 'inv.py', png, d] + crop, capture_output=True, text=True, cwd=T).stdout
    n = int(re.search(r'px>40 (\d+)', out).group(1))
    cache[key] = n > 10
    print(len(S), n, flush=True)
    return n > 10
def ddmin(C):
    n = 2
    while len(C) >= 2:
        k = len(C) // n; subsets = [C[i:i + k] for i in range(0, len(C), k)]
        done = False
        for s in subsets:
            if bad(s): C = s; n = 2; done = True; break
        if not done:
            for s in subsets:
                comp = [c for c in C if c not in s]
                if bad(comp): C = comp; n = max(n - 1, 2); done = True; break
        if not done:
            if n >= len(C): break
            n = min(len(C), 2 * n)
    return C
C = list(range(lo, hi))
assert bad(C)
if bad([]): print('target alone is bad'); sys.exit()
res = ddmin(C)
print('MINIMAL', res)
