# Essay figures. Reads summary_by_quarter.csv and boot_out/*.csv (run boot.py with BOOT_CSV first).
# Writes PNG + SVG to rtc/draft/figures/.
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

R = '/home/hatim/applications/cltr2/rtc/research/'
E = R + 'essay/'
OUT = '/home/hatim/applications/cltr2/rtc/draft/figures/'
os.makedirs(OUT, exist_ok=True)

# Reference palette (dataviz skill), light mode. 1 css px ~ 0.72 pt at this size.
SURFACE, INK, INK2, MUTED, GRID, BASE = '#fcfcfb', '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
EARLY, LATE = '#86b6ef', '#256abf'  # ordinal ramp steps 250 / 500
PX = 0.72
LINE, MARK, RING, HAIR = 2 * PX, 8 * PX, 2 * PX, 1 * PX

plt.rcParams.update({
    'font.family': 'Inter', 'font.size': 9, 'text.color': INK2,
    'axes.edgecolor': BASE, 'axes.labelcolor': INK2, 'axes.facecolor': SURFACE,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'figure.facecolor': SURFACE, 'savefig.facecolor': SURFACE, 'svg.fonttype': 'none',
})
SOURCE = ('Source: GitHub issues filed against Claude Code, Codex CLI and Gemini CLI, Mar 2025 to Sep 2026. '
          'Rogue reports estimated from a stratified sample of 4,919 issues coded by an LLM.')
QLAB = {'2025Q2': 'Q2\n2025', '2025Q3': 'Q3\n2025', '2025Q4': 'Q4\n2025',
        '2026Q1': 'Q1\n2026', '2026Q2': 'Q2\n2026', '2026Q3': 'Q3\n2026'}


def frame(title, subtitle, rect=(0.075, 0.17, 0.70, 0.60)):
    fig = plt.figure(figsize=(7.2, 4.3), dpi=200)
    fig.text(0.075, 0.935, title, fontsize=12.5, fontweight='semibold', color=INK, va='top')
    fig.text(0.075, 0.865, subtitle, fontsize=9, color=INK2, va='top', linespacing=1.4)
    fig.text(0.075, 0.025, SOURCE, fontsize=7, color=MUTED, va='bottom', wrap=True)
    ax = fig.add_axes(rect)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_linewidth(HAIR)
    ax.tick_params(length=0, pad=6)
    return fig, ax


def line_legend(ax, items):
    hs = [Line2D([0], [0], color=c, linewidth=LINE, solid_capstyle='round') for _, c in items]
    ax.legend(hs, [n for n, _ in items], loc='upper left', frameon=False, fontsize=8.5, handlelength=1.6,
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
            ax.plot([x + 0.06, xt - 0.03], [y, yl], color=MUTED, linewidth=HAIR, clip_on=False)
        ax.text(xt, yl, t, va='center', ha='left', fontsize=9, color=INK, clip_on=False)


def save(fig, name):
    fig.savefig(OUT + name + '.png')
    fig.savefig(OUT + name + '.svg')
    plt.close(fig)


sq = pd.read_csv(R + 'summary_by_quarter.csv').set_index('quarter')
boot = {k: pd.read_csv(E + f'boot_out/{k}.csv', index_col=0) for k in ('main', 'cc', 'nolow', 'phase1', 'ccnolow')}

# Fig 1: indexed counts
Q = ['2025Q3', '2025Q4', '2026Q1', '2026Q2', '2026Q3']
series = [('Keyword matches', 'keyword_matches', ORANGE),
          ('Rogue reports', 'est_loc_reports', AQUA),
          ('Issues filed', 'total_issues', BLUE)]
fig, ax = frame('Rogue reports grew in step with issues filed. Keyword hits grew twice as fast',
                'Quarterly counts for three open-source coding agents, indexed to Q3 2025 = 100')
x = range(len(Q))
labels = []
for name, col, c in series:
    v = 100 * sq.loc[Q, col] / sq.loc[Q[0], col]
    ax.plot(x, v, color=c, linewidth=LINE, solid_joinstyle='round', solid_capstyle='round', label=name,
            marker='o', markersize=MARK, markerfacecolor=c, markeredgecolor=SURFACE, markeredgewidth=RING)
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
fig, ax = frame('Per issue filed, rogue reports have risen only modestly since mid-2025',
                'Estimated rogue reports per 1,000 issues filed, with 95% bootstrap intervals')
x = range(len(Q2))
labels = []
for name, key, c in [('All three tools', 'main', BLUE), ('Claude Code', 'cc', ORANGE)]:
    b = boot[key].loc[[f'per1k_{q}' for q in Q2]]
    ax.fill_between(x, b.lo, b.hi, color=c, alpha=0.10, linewidth=0)
    ax.plot(x, b.est, color=c, linewidth=LINE, solid_joinstyle='round', label=name,
            marker='o', markersize=MARK, markerfacecolor=c, markeredgecolor=SURFACE, markeredgewidth=RING)
    labels.append((b.est.iloc[-1], f'{name}  {b.est.iloc[-1]:.1f}'))
end_labels(ax, len(Q2) - 1, labels, min_gap=2.5)
ax.annotate('Includes an Aug–Sep 2025\nspike in Claude Code', xy=(1, boot['cc'].loc['per1k_2025Q3', 'est'] + 0.6),
            xytext=(1.25, 31.5), fontsize=8, color=INK2, va='center',
            arrowprops=dict(arrowstyle='-', color=MUTED, linewidth=HAIR))
ax.set_xticks(list(x), [QLAB[q] for q in Q2])
ax.set_ylim(0, 35)
ax.set_yticks(range(0, 31, 10))
ax.set_xlim(-0.2, len(Q2) - 0.8)
ygrid(ax)
line_legend(ax, [('All three tools', BLUE), ('Claude Code', ORANGE)])
save(fig, 'fig2_rate_per_1k')

# Fig 3: behaviour mix, two periods (dumbbell)
rows = [('Got around a safeguard', 'c4'), ('Misreported its own actions', 'c5'),
        ('Either of the two', 'c4or5'), ('Irreversible loss of work or data', 'irrev')]
b = boot['main']
fig, ax = frame('Deception and workarounds are a growing share of rogue reports',
                'Share of estimated rogue reports by behaviour, with 95% bootstrap intervals. Categories overlap.\n'
                'The share involving irreversible loss held roughly steady',
                rect=(0.33, 0.17, 0.50, 0.56))
for i, (name, k) in enumerate(rows):
    y = len(rows) - 1 - i
    e1, e2 = b.loc[f'share_{k}_P1'], b.loc[f'share_{k}_P2']
    for e, c, dy, lab in [(e1, EARLY, 0.11, 'Jul–Dec 2025'), (e2, LATE, -0.11, 'Apr–Sep 2026')]:
        ax.plot([e.lo, e.hi], [y + dy, y + dy], color=c, linewidth=LINE, solid_capstyle='round', zorder=2)
        ax.plot(e.est, y + dy, 'o', markersize=MARK, color=c, markeredgecolor=SURFACE, markeredgewidth=RING,
                zorder=3, label=lab if i == 0 else None)
    ax.text(1.03, y, f'{e1.est:.0f}% → {e2.est:.0f}%', transform=ax.get_yaxis_transform(),
            va='center', ha='left', fontsize=9, color=INK)
ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)], fontsize=9)
ax.tick_params(axis='y', labelcolor=INK)
ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xlim(0, 50)
ax.set_xticks(range(0, 51, 10), [f'{t}%' for t in range(0, 51, 10)])
ax.grid(axis='x', color=GRID, linewidth=HAIR, linestyle='-')
ax.set_axisbelow(True)
ax.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5, handletextpad=0.3,
          columnspacing=1.6, labelcolor=INK2)
save(fig, 'fig3_behaviour_mix')

# Fig 4: robustness of the rate ratio
checks = [('Main estimate', 'main'), ('Drop low-confidence calls', 'nolow'),
          ('Final sampling procedure only', 'phase1'), ('Claude Code only', 'cc'),
          ('Claude Code, no low-confidence', 'ccnolow')]
fig, ax = frame('Every check puts the rise in the per-issue rate between 11% and 26%',
                'Rogue reports per 1,000 issues, Apr–Sep 2026 vs Jul–Dec 2025, with 95% bootstrap intervals.\n'
                'Over the same period, issues filed grew 3.6×',
                rect=(0.33, 0.17, 0.48, 0.54))
for i, (name, k) in enumerate(checks):
    y = len(checks) - 1 - i
    e = boot[k].loc['rate_ratio_P2/P1']
    ax.plot([e.lo, e.hi], [y, y], color=BLUE, linewidth=LINE, solid_capstyle='round')
    ax.plot(e.est, y, 'o', markersize=MARK, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=RING)
    ax.text(1.03, y, f'{e.est:.2f}×  [{e.lo:.2f}, {e.hi:.2f}]', transform=ax.get_yaxis_transform(),
            va='center', ha='left', fontsize=9, color=INK)
ax.axvline(1.0, color=BASE, linewidth=HAIR)
ax.text(1.008, len(checks) - 0.45, 'No change', ha='left', va='center', fontsize=8, color=MUTED)
ax.set_yticks(range(len(checks)), [c[0] for c in reversed(checks)], fontsize=9)
ax.tick_params(axis='y', labelcolor=INK)
ax.set_ylim(-0.6, len(checks) - 0.2)
ax.set_xlim(0.9, 1.5)
ax.set_xticks([0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5], ['0.9×', '1.0×', '1.1×', '1.2×', '1.3×', '1.4×', '1.5×'])
ax.grid(axis='x', color=GRID, linewidth=HAIR, linestyle='-')
ax.set_axisbelow(True)
save(fig, 'fig4_robustness')
print('wrote', sorted(os.listdir(OUT)))
