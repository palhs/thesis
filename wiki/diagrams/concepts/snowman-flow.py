# Generator for Figure 3.4 (snowman-flow). Renders snowman-flow.{svg,pdf}.
# Run: python3 snowman-flow.py
# Compact aspect (~1.7) so labels stay legible at text width; see
# wiki/diagrams/index.md.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
import numpy as np
import os

fig, ax = plt.subplots(figsize=(10.0, 5.8))

BLUE = '#1f77b4'   # preference A
RED  = '#d62728'   # preference B
EDGE = '#333'

# each entry: (x-centre, round label, list of 5 sampled-peer colours, counter text)
ROUNDS = [
    (1.4,  'round 1', [BLUE, BLUE, BLUE, RED, RED],  'sample: 3/5 blue\ncounter → 1'),
    (4.2,  'round 2', [BLUE, BLUE, BLUE, BLUE, RED], 'sample: 4/5 blue\ncounter → 2'),
    (7.0,  '…',       [BLUE, BLUE, BLUE, BLUE, BLUE],'sample: 5/5 blue\ncounter → …'),
    (9.8,  'round β',[BLUE, BLUE, BLUE, BLUE, BLUE], 'sample: 5/5 blue\ncounter → β'),
]

V_Y   = 3.7      # focal validator row
P_Y   = 1.9      # sampled-peer band centre
CTR_Y = 0.15     # counter strip

for xc, rlabel, colours, ctr in ROUNDS:
    ax.add_patch(plt.Circle((xc, V_Y), 0.26, facecolor=BLUE,
                 edgecolor=EDGE, lw=1.5, zorder=4))
    ax.text(xc, V_Y + 0.5, 'validator v', ha='center', va='bottom', fontsize=10)
    px = np.linspace(xc - 0.95, xc + 0.95, 5)
    for x, c in zip(px, colours):
        ax.add_patch(plt.Circle((x, P_Y), 0.17, facecolor=c,
                     edgecolor=EDGE, lw=1.1, zorder=4))
        arr = FancyArrowPatch((xc, V_Y - 0.26), (x, P_Y + 0.17),
                              arrowstyle='-|>', mutation_scale=10,
                              lw=1.0, color='#888', zorder=2)
        ax.add_patch(arr)
    ax.text(xc, V_Y + 0.9, rlabel, ha='center', va='bottom',
            fontsize=12, fontweight='bold')
    ax.text(xc, P_Y - 0.5, 'query K random peers', ha='center', va='top',
            fontsize=9.5, color='#555', style='italic')
    ax.text(xc, CTR_Y, ctr, ha='center', va='center', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.3', fc='#eef4fb', ec=BLUE, lw=1.0))

for i in range(len(ROUNDS) - 1):
    x0 = ROUNDS[i][0] + 1.25
    x1 = ROUNDS[i+1][0] - 1.25
    ax.annotate('', xy=(x1, V_Y), xytext=(x0, V_Y),
                arrowprops=dict(arrowstyle='-|>', color='#aaa', lw=1.4))

ax.annotate('counter reaches β  →  ACCEPT\nprobabilistic finality,  ε ≤ (1 − α_c/K)^β',
            xy=(9.8, CTR_Y), xytext=(9.8, -1.15),
            fontsize=10.5, ha='center', va='center', color='#b8860b', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#b8860b', lw=1.3),
            bbox=dict(boxstyle='round,pad=0.4', fc='#fdf6e3', ec='#b8860b', lw=1.1))

LEG_Y = 5.25
ax.add_patch(plt.Circle((0.5, LEG_Y), 0.15, facecolor=BLUE, edgecolor=EDGE, lw=1.1))
ax.text(0.75, LEG_Y, 'prefers block A', ha='left', va='center', fontsize=10.5)
ax.add_patch(plt.Circle((3.3, LEG_Y), 0.15, facecolor=RED, edgecolor=EDGE, lw=1.1))
ax.text(3.55, LEG_Y, 'prefers block B', ha='left', va='center', fontsize=10.5)
ax.text(6.2, LEG_Y, 'K = 5 sampled each round (not the whole network)',
        ha='left', va='center', fontsize=10.5, style='italic', color='#555')

ax.set_xlim(-0.3, 11.2)
ax.set_ylim(-1.7, 5.55)
ax.axis('off')
plt.tight_layout(pad=0.3)
out = os.path.dirname(os.path.abspath(__file__))
plt.savefig(f'{out}/snowman-flow.svg', bbox_inches='tight')
plt.savefig(f'{out}/snowman-flow.pdf', bbox_inches='tight')
print('snowman-flow done')
