"""Make test scenes for the AA-reversal bug: data dirs + device-framing model renders."""
import os, numpy as np, subprocess
from pbart import load, write
SP = '/tmp/work/'
E = SP + 'exp/scenes/'
p22 = load(SP + 'data/pb22')
sc = {'s0': p22, 's1': p22[:397]}
for seed in range(4):
    keep = np.random.default_rng(seed).random(len(p22)) > 0.05; keep[396] = True
    sc['r%d' % seed] = [s for s, k in zip(p22, keep) if k]
sc['p21'] = load(SP + 'data/pb21')
for k, v in sc.items():
    write(v, E + k)
    subprocess.run([SP + 'venv/bin/python', 'devmodel.py', E + k, E + k + '_model.png'], check=True)
    print(k, len(v), flush=True)
