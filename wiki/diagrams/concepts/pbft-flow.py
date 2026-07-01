# Generator for Figure 3.2 (pbft-flow). Renders pbft-flow.{svg,pdf} in this dir.
# Run: python3 pbft-flow.py
# Wide message-flow layout kept compact (aspect ~1.9) so it stays legible when
# scaled to text width in the thesis; see wiki/diagrams/index.md.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

fig, ax = plt.subplots(figsize=(9.5, 5.0))

# ── grid: 5 phase columns between 6 vertical dividers ────────────────────────
PHASES = ['request', 'pre-prepare', 'prepare', 'commit', 'reply']
DIV    = [0, 1, 2, 3, 4, 5]        # x of the 6 vertical dividers
ROWS   = ['Client', 'Node 0  (primary)', 'Node 1', 'Node 2', 'Node 3  (faulty)']
Y      = {'C': 4, 0: 3, 1: 2, 2: 1, 3: 0}

for y in Y.values():
    ax.axhline(y, color='black', lw=1.4, zorder=1)
for x in DIV:
    ax.axvline(x, color='black', lw=0.8, ls='--', alpha=0.55, zorder=1)
for i, label in enumerate(PHASES):
    mid = (DIV[i] + DIV[i+1]) / 2
    ax.text(mid, 4.64, label, ha='center', va='center', fontsize=11.5, fontweight='bold')
for label, y in zip(ROWS, Y.values()):
    ax.text(-0.1, y + 0.16, label, ha='right', va='center', fontsize=10)
ax.text(0.5, 0.16, '✕', ha='center', va='center', fontsize=16,
        color='black', fontweight='bold')

def arrow(xa, ya, xb, yb, color, lw=1.7):
    ax.annotate('', xy=(xb, yb), xytext=(xa, ya),
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw,
                                shrinkA=0, shrinkB=0), zorder=3)

# colour by sender so the woven pattern stays readable
C_GREEN  = '#2ca02c'   # request
C_YELLOW = '#e6b800'   # pre-prepare (primary)
C_N0     = '#ff7f0e'   # node 0 sends
C_N1     = '#1f77b4'   # node 1 sends
C_N2     = '#17a2a2'   # node 2 sends
C_BROWN  = '#8c564b'   # reply

arrow(0.15, 4, 1, 3, C_GREEN, lw=2.1)                 # request
arrow(1, 3, 2, 2, C_YELLOW, lw=1.9)                   # pre-prepare
arrow(1, 3, 2, 1, C_YELLOW, lw=1.9)
arrow(1, 3, 2, 0, C_YELLOW, lw=1.9)
arrow(2, 3, 3, 2, C_N0); arrow(2, 3, 3, 1, C_N0)      # prepare
arrow(2, 2, 3, 3, C_N1); arrow(2, 2, 3, 1, C_N1)
arrow(2, 1, 3, 3, C_N2); arrow(2, 1, 3, 2, C_N2)
arrow(3, 3, 4, 2, C_N0); arrow(3, 3, 4, 1, C_N0)      # commit
arrow(3, 2, 4, 3, C_N1); arrow(3, 2, 4, 1, C_N1)
arrow(3, 1, 4, 3, C_N2); arrow(3, 1, 4, 2, C_N2)
arrow(4, 3, 5, 4, C_BROWN, lw=2.0)                    # reply
arrow(4, 2, 5, 4, C_BROWN, lw=2.0)
arrow(4, 1, 5, 4, C_BROWN, lw=2.0)

ax.set_xlim(-1.15, 5.15)
ax.set_ylim(-0.55, 5.0)
ax.axis('off')
plt.tight_layout(pad=0.3)
out = os.path.dirname(os.path.abspath(__file__))
plt.savefig(f'{out}/pbft-flow.svg', bbox_inches='tight')
plt.savefig(f'{out}/pbft-flow.pdf', bbox_inches='tight')
print('pbft-flow done')
