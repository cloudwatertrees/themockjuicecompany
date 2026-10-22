"""Sanity table: live irregularity stats beside the same stats for recipe outputs (prototype set or a module list)."""
import json, sys
from common import *
import measure_irregularity as M
from fx.trees import bell_tree
from fx.plants import fern_pine, leaf_clump, flower
from fx.stones import rock


def proto_set(seed=0):
    sh = bell_tree(152, 1218, 66, tiers=3, seed=seed) + bell_tree(860, 1100, 70, tiers=4, seed=seed + 1)
    sh += fern_pine(415, 432, 80, tiers=3, seed=seed, halo=False)
    sh += leaf_clump(318, 990, 78, seed=seed) + leaf_clump(600, 700, 60, seed=seed + 1)
    for i, (x, y, k) in enumerate([(322, 965, 'white'), (361, 982, 'white'), (408, 980, 'lilac'), (383, 1012, 'lilac'), (200, 400, 'yellow')]):
        sh += flower(x, y, 15, k, seed + i)
    sh += rock(620, 997, 150, 140, seed) + rock(690, 1005, 40, 32, seed + 1)
    return sh


def row(t, k, L, f):
    v = t[k].get(L)
    return f(v) if v else '-'


if __name__ == '__main__':
    live = json.load(open(EXT / 'irregularity.json'))
    new = {k: f(proto_set()) for k, f in (('mottling', M.mottling), ('outlines', M.outlines), ('asymmetry', M.asymmetry), ('lobes', M.lobe_variation))}
    print('%-11s %-22s %-22s %-24s %-24s %-14s' % ('layer', 'mottle amp/corr live', 'new', 'turn1u p50/p90 live', 'new', 'lobeCV l/n'))
    for L in ('frontTrees', 'pines', 'bushes', 'flowers', 'rocks'):
        mo = lambda v: '%.1f / %.0fu' % (v['all']['amp_lum_median'], v['all']['corr_len_u_median'])
        tu = lambda v: '%.1f / %.1f (>10: %.0f%%)' % (v['turn_1u_deg_p50_p90_p99'][0], v['turn_1u_deg_p50_p90_p99'][1], 100 * v['frac_1u_turns_over_10deg'])
        lb = lambda v: '%.2f' % v['lobe_len_cv_median']
        print('%-11s %-22s %-22s %-24s %-24s %s/%s' % (L, row(live, 'mottling', L, mo), row(new, 'mottling', L, mo), row(live, 'outlines', L, tu),
                                                     row(new, 'outlines', L, tu), row(live, 'lobes', L, lb), row(new, 'lobes', L, lb)))
