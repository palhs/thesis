# Generator for Figure 3.3 (casper-ffg-flow). Renders casper-ffg-flow.{svg,pdf}.
# Run: python3 casper-ffg-flow.py
# Compact aspect (~1.65) so labels stay legible at text width; see
# wiki/diagrams/index.md.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
import os

fig, ax = plt.subplots(figsize=(10.0, 6.0))

# state colours
C_FINAL = '#2e8b57'   # finalized  (dark green)
C_JUST  = '#f0c040'   # justified  (amber)
C_PROP  = '#ffffff'   # proposed   (white)
EDGE    = '#333333'
C_VOTE  = '#1f77b4'   # attestation arrows / links

# ── checkpoint chain ─────────────────────────────────────────────────────────
CP_Y   = 3.6
CP_X   = [0.9, 3.9, 6.9, 9.9]              # C0..C3
CP_NAME  = ['C0', 'C1', 'C2', 'C3']
CP_STATE = ['final', 'final', 'just', 'prop']
STATE_FILL = {'final': C_FINAL, 'just': C_JUST, 'prop': C_PROP}
CP_R = 0.42

for i in range(len(CP_X) - 1):
    x0, x1 = CP_X[i], CP_X[i+1]
    bx = np.linspace(x0 + 0.7, x1 - 0.7, 3)
    for x in bx:
        ax.add_patch(Rectangle((x - 0.14, CP_Y - 0.16), 0.28, 0.32,
                     facecolor='#e8e8e8', edgecolor='#999', lw=0.8, zorder=2))
    ax.plot([x0, x1], [CP_Y, CP_Y], color='#bbb', lw=1.0, zorder=1)
    ax.text((x0 + x1) / 2, CP_Y - 0.6, f'epoch {i+1}\n(batch of blocks)',
            ha='center', va='top', fontsize=9, color='#777')

for x, name, st in zip(CP_X, CP_NAME, CP_STATE):
    ax.add_patch(plt.Circle((x, CP_Y), CP_R, facecolor=STATE_FILL[st],
                 edgecolor=EDGE, lw=1.6, zorder=4))
    tc = 'white' if st == 'final' else 'black'
    ax.text(x, CP_Y, name, ha='center', va='center', fontsize=12.5,
            fontweight='bold', color=tc, zorder=5)

# ── supermajority link arcs (source → target) ────────────────────────────────
def link(xa, xb, label, color=C_VOTE, pending=False):
    arc = FancyArrowPatch((xa, CP_Y + CP_R), (xb, CP_Y + CP_R),
                          connectionstyle='arc3,rad=-0.5',
                          arrowstyle='-|>', mutation_scale=15,
                          lw=2.0, color=color, zorder=3,
                          linestyle='--' if pending else '-')
    ax.add_patch(arc)
    ax.text((xa + xb) / 2, CP_Y + 1.15, label, ha='center', va='center',
            fontsize=9.5, color=color, fontweight='bold')

link(CP_X[0], CP_X[1], 'supermajority link')
link(CP_X[1], CP_X[2], 'supermajority link')
link(CP_X[2], CP_X[3], 'next epoch:\npending', color='#999', pending=True)

# ── validator attestation layer (how nodes communicate) ─────────────────────
VAL_Y = 0.75
val_x = np.linspace(4.3, 9.5, 7)          # 7 validators under epoch-2 region
votes = [True, True, False, True, True, True, False]   # 5 of 7 attest
for x, v in zip(val_x, votes):
    fc = C_VOTE if v else '#dddddd'
    ax.add_patch(plt.Circle((x, VAL_Y), 0.17, facecolor=fc,
                 edgecolor=EDGE, lw=1.0, zorder=4))
    if v:
        arr = FancyArrowPatch((x, VAL_Y + 0.17), (CP_X[2] - 0.05, CP_Y - CP_R),
                              arrowstyle='-|>', mutation_scale=9,
                              lw=1.0, color=C_VOTE, alpha=0.65, zorder=2)
        ax.add_patch(arr)

ax.text(6.9, VAL_Y - 0.45,
        'validators broadcast attestations (votes) for the C1→C2 link\n'
        '≥ ⅔ of stake attesting  →  C2 justified',
        ha='center', va='top', fontsize=10, color=C_VOTE)

ax.annotate('C1 finalized:\nC1 justified AND child C2 justified\n(finality needs two epochs)',
            xy=(CP_X[1], CP_Y - CP_R), xytext=(1.9, 1.15),
            fontsize=9.5, ha='center', va='center', color='#2e8b57',
            arrowprops=dict(arrowstyle='->', color='#2e8b57', lw=1.3),
            bbox=dict(boxstyle='round,pad=0.35', fc='#eaf5ee', ec='#2e8b57', lw=1.0))

for i, (st, lab) in enumerate([('final', 'finalized'), ('just', 'justified'), ('prop', 'proposed')]):
    ax.add_patch(plt.Circle((0.4 + i * 2.6, 5.35), 0.17, facecolor=STATE_FILL[st],
                 edgecolor=EDGE, lw=1.2, zorder=4))
    ax.text(0.4 + i * 2.6 + 0.3, 5.35, lab, ha='left', va='center', fontsize=10.5)

ax.set_xlim(-0.2, 10.7)
ax.set_ylim(-0.3, 5.7)
ax.axis('off')
plt.tight_layout(pad=0.3)
out = os.path.dirname(os.path.abspath(__file__))
plt.savefig(f'{out}/casper-ffg-flow.svg', bbox_inches='tight')
plt.savefig(f'{out}/casper-ffg-flow.pdf', bbox_inches='tight')
print('casper-ffg-flow done')
