"""Recipe parameters (source of recipes.json). Values are fitted to the original instances (analysis/anatomy.py);
every change after the first fit is a documented correction (see CORRECTIONS at the bottom).
python -m gen.recipe_defs   -> writes recipes.json"""
import json, os

FIR = dict(
    layer='pines', size_Ht=[230, 275], instances_measured=2,
    tiers=[2, 2, 3],
    tier_bottom_t={'2': [[0.50, 0.54], [0.64, 0.68]], '3': [[0.42, 0.45], [0.54, 0.57], [0.66, 0.69]]},
    tier_hw={'2': [[0.17, 0.19], [0.21, 0.23]], '3': [[0.15, 0.16], [0.18, 0.20], [0.21, 0.23]]},
    lean=0.03,
    halo=dict(hw=0.40, top_t=-0.05, bottom_t=1.08, wobble=3.0),
    ground=dict(t=1.0, hw=0.34, hh=0.06),
    under=dict(t=[0.83, 1.0], hw=0.27),
    base=dict(tip_t=0.66, hw=0.29, inner_t=0.74, bottom_t=0.9, band_hw=0.17, core_hw=0.15),
    side_fronds=dict(per_side=[2, 3], t=[0.3, 0.62], angle=[55, 75], len=[0.12, 0.18], w=0.06),
    # levels: (t_notch, reach, rise, drop, column half width), fractions of Ht
    mid_tier=dict(t=[0.48, 0.86], spire_hw=0.07, hang_r=0.05,
                  levels=[[0.58, 0.13, 0.08, 0.12, 0.08], [0.72, 0.13, 0.07, 0.12, 0.1]]),
    body=dict(t_bot=0.6, spire_hw=0.05, hang_r=0.05, n_levels=[2, 3, 3],
              levels=[[0.28, 0.08, 0.10, 0.08, 0.05], [0.42, 0.11, 0.10, 0.12, 0.07], [0.53, 0.10, 0.06, 0.08, 0.09]]),
    crevices=dict(p=0.0, len=0.045, w=0.022),
    rims=dict(w=1.05, p_light=0.75, p_dark=0.75, extra=[8, 14]),
    flecks=dict(n=[8, 14], r=[0.8, 2.2], p_dark=0.45),
    colours=dict(
        halo=[90.0, -5.2, 25.5], ground=[77.0, -10.0, 32.0], ground_pale=[87.0, -7.0, 30.0],
        dark=[58.5, -25.8, 20.0], under=[53.0, -25.0, 16.0],
        body_top=[81.0, -19.0, 34.0], body_bottom=[74.5, -25.5, 28.0], mid=[69.5, -28.0, 26.0],
        crevice=[56.0, -26.5, 19.0], rim_light=[82.0, -12.2, 27.0], rim_dark=[62.0, -24.0, 20.5],
        fleck_light=[89.0, -6.0, 25.0], fleck_dark=[60.0, -25.0, 20.0]),
)

RECIPES = dict(fir=FIR)

CORRECTIONS = []

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'recipes.json')
    json.dump(dict(recipes=RECIPES, corrections=CORRECTIONS), open(out, 'w'), indent=1)
    print('wrote', out)
