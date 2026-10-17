# Essay figures for the LaTeX build. Copy of rtc/research/essay/figures.py.
# Reads summary_by_quarter.csv and boot_out/*.csv under rtc/research/.
# Writes vector PDFs (matplotlib PGF backend, XeLaTeX, Libre Franklin) to this directory.
# Titles, subtitles and the source line are LaTeX captions now, so they are not drawn here.
import os
import pandas as pd
import matplotlib
matplotlib.use('pgf')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

R = '/home/hatim/applications/cltr2/rtc/research/'
E = R + 'essay/'
OUT = '/home/hatim/applications/cltr2/rtc/latex/figures/'
os.makedirs(OUT, exist_ok=True)

# Palette from the CV (cv.sty).
INK, INK2, BASE, GRID = '#17181A', '#5A5C60', '#B9BCB4', '#E4E5E1'
RED, BLUE = '#B4232A', '#1B4B9E'
EARLY, LATE = '#E3A7AA', RED
RED_MID = '#D2686D'  # Claude Code subset of rogue reports (fig 2)  # light tint of the accent / full accent
MM = 1 / 25.4
W = 134 * MM  # main text column
FS = 8
PX = 0.72
LINE, MARK, RING, HAIR = 2 * PX, 8 * PX, 2 * PX, 1 * PX
WHITE = '#ffffff'

plt.rcParams.update({
    'pgf.texsystem': 'xelatex', 'pgf.rcfonts': False,
    'pgf.preamble': '\n'.join([
        r'\usepackage{fontspec}',
        r'\setmainfont{LibreFranklin}[Extension=.otf, UprightFont=*-Regular, BoldFont=*-SemiBold, '
        r'ItalicFont=*-Italic, BoldItalicFont=*-SemiBoldItalic]',
    ]),
    'font.family': 'serif', 'font.size': FS, 'text.color': INK2,
    'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'axes.facecolor': 'none',
    'xtick.color': INK2, 'ytick.color': INK2, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'xtick.labelsize': FS, 'ytick.labelsize': FS,
    'figure.facecolor': 'none', 'savefig.facecolor': 'none', 'savefig.transparent': True,
})
QLAB = {'2025Q2': 'Q2\n2025', '2025Q3': 'Q3\n2025', '2025Q4': 'Q4\n2025',
        '2026Q1': 'Q1\n2026', '2026Q2': 'Q2\n2026', '2026Q3': 'Q3\n2026'}


def frame(height_mm, rect):
    fig = plt.figure(figsize=(W, height_mm * MM))
    ax = fig.add_axes(rect)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_linewidth(HAIR)
    ax.tick_params(length=0, pad=5)
    return fig, ax


def line_legend(ax, items, loc='upper left'):
    hs = [Line2D([0], [0], color=c, linewidth=LINE, solid_capstyle='round') for _, c in items]
    ax.legend(hs, [n for n, _ in items], loc=loc, frameon=False, fontsize=FS, handlelength=1.6,
              labelcolor=INK2)


def ygrid(ax):
    ax.grid(axis='y', color=GRID, linewidth=HAIR, linestyle='-')
    ax.set_axisbelow(True)


def end_labels(ax, x, items, min_gap):
    """items: (y_end, text). Spread labels at least min_gap apart; leader line when moved."""
    items = sorted(items)
    placed = []
    for y, t in items:
        yl = max(y, placed[-1] + min_gap) if placed else y
        placed.append(yl)
    xt = x + 0.18
    for (y, t), yl in zip(items, placed):
        if abs(yl - y) > 1e-9:
            ax.plot([x + 0.06, xt - 0.03], [y, yl], color=BASE, linewidth=HAIR, clip_on=False)
        ax.text(xt, yl, t, va='center', ha='left', fontsize=FS, color=INK, clip_on=False)


def save(fig, name):
    fig.savefig(OUT + name + '.pdf', backend='pgf')
    plt.close(fig)


sq = pd.read_csv(R + 'summary_by_quarter.csv').set_index('quarter')
boot = {k: pd.read_csv(E + f'boot_out/{k}.csv', index_col=0) for k in ('main', 'cc', 'nolow', 'phase1', 'ccnolow')}

# Fig 1: indexed counts
Q = ['2025Q3', '2025Q4', '2026Q1', '2026Q2', '2026Q3']
series = [('Keyword matches', 'keyword_matches', BLUE),
          ('Rogue reports', 'est_loc_reports', RED),
          ('Issues filed', 'total_issues', INK2)]
fig, ax = frame(78, (0.065, 0.14, 0.68, 0.84))
x = range(len(Q))
labels = []
for name, col, c in series:
    v = 100 * sq.loc[Q, col] / sq.loc[Q[0], col]
    ax.plot(x, v, color=c, linewidth=LINE, solid_joinstyle='round', solid_capstyle='round', label=name,
            marker='o', markersize=MARK, markerfacecolor=c, markeredgecolor=WHITE, markeredgewidth=RING)
    labels.append((v.iloc[-1], f'{name}  {v.iloc[-1] / 100:.1f}×'))
end_labels(ax, len(Q) - 1, labels, min_gap=48)
ax.set_xticks(list(x), [QLAB[q] for q in Q])
ax.set_ylim(0, 950)
ax.set_yticks(range(0, 901, 200))
ax.set_xlim(-0.2, len(Q) - 0.8)
ygrid(ax)
line_legend(ax, [(n, c) for n, _, c in series])
save(fig, 'fig1_indexed_counts')

# Fig 2: rogue reports per 1,000 issues, pooled vs Claude Code
Q2 = ['2025Q2'] + Q
fig, ax = frame(76, (0.065, 0.14, 0.68, 0.84))
x = range(len(Q2))
labels = []
for name, key, c in [('All three tools', 'main', RED), ('Claude Code', 'cc', RED_MID)]:
    b = boot[key].loc[[f'per1k_{q}' for q in Q2]]
    ax.fill_between(x, b.lo, b.hi, color=c, alpha=0.12, linewidth=0)
    ax.plot(x, b.est, color=c, linewidth=LINE, solid_joinstyle='round', solid_capstyle='round', label=name,
            marker='o', markersize=MARK, markerfacecolor=c, markeredgecolor=WHITE, markeredgewidth=RING)
    labels.append((b.est.iloc[-1], f'{name}  {b.est.iloc[-1]:.1f}'))
end_labels(ax, len(Q2) - 1, labels, min_gap=2.5)
ax.annotate('Includes an Aug–Sep 2025\nspike in Claude Code', xy=(1, boot['cc'].loc['per1k_2025Q3', 'est'] + 0.6),
            xytext=(1.25, 31.5), fontsize=FS, color=INK2, va='center',
            arrowprops=dict(arrowstyle='-', color=BASE, linewidth=HAIR))
ax.set_xticks(list(x), [QLAB[q] for q in Q2])
ax.set_ylim(0, 35)
ax.set_yticks(range(0, 31, 10))
ax.set_xlim(-0.2, len(Q2) - 0.8)
ygrid(ax)
line_legend(ax, [('All three tools', RED), ('Claude Code', RED_MID)], loc='lower right')
save(fig, 'fig2_rate_per_1k')

# Fig 3: behaviour mix, two periods (dumbbell)
rows = [('Got around a safeguard', 'c4'), ('Misreported its own actions', 'c5'),
        ('Either of the two', 'c4or5'), ('Irreversible loss of work or data', 'irrev')]
b = boot['main']
fig, ax = frame(56, (0.335, 0.12, 0.50, 0.76))
tr = ax.get_yaxis_transform()
for i, (name, k) in enumerate(rows):
    y = len(rows) - 1 - i
    e1, e2 = b.loc[f'share_{k}_P1'], b.loc[f'share_{k}_P2']
    for e, c, dy, lab in [(e1, EARLY, 0.11, 'Jul–Dec 2025'), (e2, LATE, -0.11, 'Apr–Sep 2026')]:
        ax.plot([e.lo, e.hi], [y + dy, y + dy], color=c, linewidth=LINE, solid_capstyle='round', zorder=2)
        ax.plot(e.est, y + dy, 'o', markersize=MARK, color=c, markeredgecolor=WHITE, markeredgewidth=RING,
                zorder=3, label=lab if i == 0 else None)
    # Libre Franklin has no arrow glyph, so the arrow is drawn.
    ax.text(1.075, y, f'{e1.est:.0f}%', transform=tr, va='center', ha='right', fontsize=FS, color=INK)
    ax.annotate('', xy=(1.135, y), xytext=(1.09, y), xycoords=tr, textcoords=tr,
                arrowprops=dict(arrowstyle='->', color=INK, linewidth=HAIR, shrinkA=0, shrinkB=0,
                                mutation_scale=6))
    ax.text(1.15, y, f'{e2.est:.0f}%', transform=tr, va='center', ha='left', fontsize=FS, color=INK)
ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)], fontsize=FS)
ax.tick_params(axis='y', labelcolor=INK)
ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xlim(0, 50)
ax.set_xticks(range(0, 51, 10), [f'{t}%' for t in range(0, 51, 10)])
ax.grid(axis='x', color=GRID, linewidth=HAIR, linestyle='-')
ax.set_axisbelow(True)
ax.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=FS, handletextpad=0.3,
          columnspacing=1.6, labelcolor=INK2)
save(fig, 'fig3_behaviour_mix')

# Fig 4: robustness of the rate ratio
checks = [('Main estimate', 'main'), ('Drop low-confidence calls', 'nolow'),
          ('Final sampling procedure only', 'phase1'), ('Claude Code only', 'cc'),
          ('Claude Code, no low-confidence', 'ccnolow')]
fig, ax = frame(58, (0.355, 0.12, 0.45, 0.86))
for i, (name, k) in enumerate(checks):
    y = len(checks) - 1 - i
    e = boot[k].loc['rate_ratio_P2/P1']
    ax.plot([e.lo, e.hi], [y, y], color=RED, linewidth=LINE, solid_capstyle='round')
    ax.plot(e.est, y, 'o', markersize=MARK, color=RED, markeredgecolor=WHITE, markeredgewidth=RING)
    ax.text(1.03, y, f'{e.est:.2f}×  [{e.lo:.2f}, {e.hi:.2f}]', transform=ax.get_yaxis_transform(),
            va='center', ha='left', fontsize=FS, color=INK)
ax.axvline(1.0, color=BASE, linewidth=HAIR)
ax.text(1.008, len(checks) - 0.45, 'No change', ha='left', va='center', fontsize=FS, color=INK2)
ax.set_yticks(range(len(checks)), [c[0] for c in reversed(checks)], fontsize=FS)
ax.tick_params(axis='y', labelcolor=INK)
ax.set_ylim(-0.6, len(checks) - 0.2)
ax.set_xlim(0.9, 1.5)
ax.set_xticks([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5], ['0.9×', '1.0×', '1.1×', '1.2×', '1.3×', '1.4×', '1.5×'])
ax.grid(axis='x', color=GRID, linewidth=HAIR, linestyle='-')
ax.set_axisbelow(True)
save(fig, 'fig4_robustness')
print('wrote', sorted(f for f in os.listdir(OUT) if f.endswith('.pdf')))
