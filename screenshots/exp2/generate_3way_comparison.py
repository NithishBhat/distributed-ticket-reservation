"""
Generate comparison charts for Experiment 2:
  1. High contention: 3 strategies (pessimistic, optimistic, redis) — 1 hot ticket, 200 users
  2. Contention level comparison: pessimistic vs optimistic across high/moderate/low
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

# ── High contention data (1 hot ticket, 200 users, 4 tasks) ─────────

high = {
    "pessimistic": {
        "reqs": 124307, "fails": 0, "rps": 414.3,
        "avg": 156, "p50": 100, "p75": 150, "p90": 280, "p95": 440, "p99": 880, "max": 3896,
        "error_rate": 0.0,
    },
    "optimistic": {
        "reqs": 86901, "fails": 2435, "rps": 289.6,
        "avg": 360, "p50": 300, "p75": 350, "p90": 500, "p95": 770, "p99": 1700, "max": 6930,
        "error_rate": 2.80,
    },
    "redis": {
        "reqs": 130120, "fails": 0, "rps": 433.9,
        "avg": 134, "p50": 110, "p75": 160, "p90": 260, "p95": 280, "p99": 320, "max": 706,
        "error_rate": 0.0,
    },
}

# ── Moderate contention (4 tickets, 200 users) ──────────────────────

mod = {
    "pessimistic": {
        "reqs": 143650, "fails": 0, "rps": 479.3,
        "avg": 91.8, "p50": 77, "p75": 81, "p90": 99, "p95": 170, "p99": 390, "max": 1723,
        "error_rate": 0.0,
    },
    "optimistic": {
        "reqs": 122550, "fails": 0, "rps": 408.9,
        "avg": 163.0, "p50": 80, "p75": 270, "p90": 300, "p95": 310, "p99": 420, "max": 1517,
        "error_rate": 0.0,
    },
}

# ── Low contention (50 tickets, 200 users) ──────────────────────────

low = {
    "pessimistic": {
        "reqs": 146583, "fails": 0, "rps": 489.4,
        "avg": 83.5, "p50": 77, "p75": 79, "p90": 84, "p95": 98, "p99": 270, "max": 985,
        "error_rate": 0.0,
    },
    "optimistic": {
        "reqs": 146968, "fails": 0, "rps": 490.5,
        "avg": 82.2, "p50": 76, "p75": 78, "p90": 84, "p95": 98, "p99": 240, "max": 1035,
        "error_rate": 0.0,
    },
}

# ── Style ────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f8f8",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
})
C_PESS = "#2196F3"
C_OPT = "#FF9800"
C_REDIS = "#4CAF50"


def add_bar_labels(ax, bars, fmt=".0f", offset=5, fontsize=9):
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + offset,
                format(b.get_height(), fmt), ha="center", fontsize=fontsize, fontweight="bold")


# ═══════════════════════════════════════════════════════════════
#  Chart 1: High contention — 3 strategies dashboard
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

strategies = ["Pessimistic", "Optimistic", "Redis"]
colors = [C_PESS, C_OPT, C_REDIS]
x3 = np.arange(3)
width3 = 0.5

# 1a: Throughput
ax = axes[0, 0]
vals = [high["pessimistic"]["rps"], high["optimistic"]["rps"], high["redis"]["rps"]]
bars = ax.bar(x3, vals, width3, color=colors, alpha=0.85)
add_bar_labels(ax, bars)
ax.set_ylabel("Requests/s")
ax.set_title("Throughput")
ax.set_xticks(x3)
ax.set_xticklabels(strategies)

# 1b: Avg Latency
ax = axes[0, 1]
vals = [high["pessimistic"]["avg"], high["optimistic"]["avg"], high["redis"]["avg"]]
bars = ax.bar(x3, vals, width3, color=colors, alpha=0.85)
add_bar_labels(ax, bars)
ax.set_ylabel("Avg Response Time (ms)")
ax.set_title("Average Latency")
ax.set_xticks(x3)
ax.set_xticklabels(strategies)

# 1c: Latency percentiles
ax = axes[1, 0]
pcts = ["p50", "p75", "p90", "p95", "p99"]
px = np.arange(len(pcts))
w = 0.25
for i, (strat, color) in enumerate([("pessimistic", C_PESS), ("optimistic", C_OPT), ("redis", C_REDIS)]):
    vals = [high[strat][p] for p in pcts]
    bars = ax.bar(px + (i - 1) * w, vals, w, label=strat.capitalize(), color=color, alpha=0.85)
    add_bar_labels(ax, bars, offset=10, fontsize=8)
ax.set_ylabel("Response Time (ms)")
ax.set_title("Latency Percentiles")
ax.set_xticks(px)
ax.set_xticklabels(pcts)
ax.legend()

# 1d: Error rate + total requests
ax = axes[1, 1]
reqs = [high["pessimistic"]["reqs"], high["optimistic"]["reqs"], high["redis"]["reqs"]]
errs = [high["pessimistic"]["error_rate"], high["optimistic"]["error_rate"], high["redis"]["error_rate"]]

ax2 = ax.twinx()
bars = ax.bar(x3 - 0.15, reqs, 0.3, color=colors, alpha=0.5, label="Total Requests")
for b in bars:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1000,
            f"{b.get_height():,.0f}", ha="center", fontsize=8, fontweight="bold")

ax2.bar(x3 + 0.15, errs, 0.3, color=colors, alpha=0.9, edgecolor="black", linewidth=0.5)
for i, e in enumerate(errs):
    ax2.text(i + 0.15, e + 0.1, f"{e:.1f}%", ha="center", fontsize=9, fontweight="bold", color="red")

ax.set_ylabel("Total Requests")
ax2.set_ylabel("Error Rate (%)", color="red")
ax2.tick_params(axis="y", labelcolor="red")
ax.set_title("Total Requests & Error Rate")
ax.set_xticks(x3)
ax.set_xticklabels(strategies)

fig.suptitle("Experiment 2 — High Contention: 3 Locking Strategies Compared\n(1 hot ticket, 200 users, 4 order-service tasks, 5 min)",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_high_contention_3strategies.png"), dpi=150)
plt.close(fig)
print("Saved exp2_high_contention_3strategies.png")


# ═══════════════════════════════════════════════════════════════
#  Chart 2: Percentile curves — all 3 strategies under high contention
# ═══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 6))

pcts = ["p50", "p75", "p90", "p95", "p99"]
px = np.arange(len(pcts))

for strat, color, marker, label in [
    ("pessimistic", C_PESS, "o", "Pessimistic"),
    ("optimistic", C_OPT, "s", "Optimistic"),
    ("redis", C_REDIS, "D", "Redis Lock"),
]:
    vals = [high[strat][p] for p in pcts]
    ax.plot(px, vals, color=color, linewidth=2.5, marker=marker, markersize=9,
            markeredgecolor="white", markeredgewidth=0.8, label=label)
    for i, v in enumerate(vals):
        ax.annotate(f"{v}", (px[i], v), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, color=color, fontweight="bold")

ax.set_xticks(px)
ax.set_xticklabels(pcts, fontsize=12)
ax.set_xlabel("Percentile", fontsize=12)
ax.set_ylabel("Response Time (ms)", fontsize=12)
ax.set_title("High Contention — Latency Percentile Curves (POST /orders)", fontsize=13)
ax.legend(fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_high_contention_percentiles.png"), dpi=150)
plt.close(fig)
print("Saved exp2_high_contention_percentiles.png")


# ═══════════════════════════════════════════════════════════════
#  Chart 3: Contention levels — pessimistic vs optimistic vs redis
# ═══════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

scenarios = ["High\n(1 ticket)", "Moderate\n(4 tickets)", "Low\n(50 tickets)"]
xs = np.arange(len(scenarios))
w = 0.25

# 3a: Throughput across contention levels
pess_rps = [high["pessimistic"]["rps"], mod["pessimistic"]["rps"], low["pessimistic"]["rps"]]
opt_rps = [high["optimistic"]["rps"], mod["optimistic"]["rps"], low["optimistic"]["rps"]]
redis_rps = [high["redis"]["rps"], None, None]  # Only have high contention for redis

bars1 = ax1.bar(xs - w, pess_rps, w, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax1.bar(xs, opt_rps, w, label="Optimistic", color=C_OPT, alpha=0.85)
bars3 = ax1.bar(xs[0:1] + w, [high["redis"]["rps"]], w, label="Redis Lock", color=C_REDIS, alpha=0.85)

add_bar_labels(ax1, bars1)
add_bar_labels(ax1, bars2)
add_bar_labels(ax1, bars3)
ax1.set_ylabel("Requests/s")
ax1.set_title("Throughput Across Contention Levels")
ax1.set_xticks(xs)
ax1.set_xticklabels(scenarios)
ax1.legend()

# 3b: Avg latency across contention levels
pess_avg = [high["pessimistic"]["avg"], mod["pessimistic"]["avg"], low["pessimistic"]["avg"]]
opt_avg = [high["optimistic"]["avg"], mod["optimistic"]["avg"], low["optimistic"]["avg"]]

bars1 = ax2.bar(xs - w, pess_avg, w, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax2.bar(xs, opt_avg, w, label="Optimistic", color=C_OPT, alpha=0.85)
bars3 = ax2.bar(xs[0:1] + w, [high["redis"]["avg"]], w, label="Redis Lock", color=C_REDIS, alpha=0.85)

add_bar_labels(ax2, bars1)
add_bar_labels(ax2, bars2)
add_bar_labels(ax2, bars3)
ax2.set_ylabel("Avg Response Time (ms)")
ax2.set_title("Avg Latency Across Contention Levels")
ax2.set_xticks(xs)
ax2.set_xticklabels(scenarios)
ax2.legend()

fig.suptitle("Experiment 2 — Locking Strategies Across Contention Levels\n(200 users, 4 order-service tasks, 5 min each)",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_contention_levels.png"), dpi=150)
plt.close(fig)
print("Saved exp2_contention_levels.png")


# ═══════════════════════════════════════════════════════════════
#  Print full summary
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("  Experiment 2 — High Contention: 3-Strategy Summary (POST /orders)")
print("=" * 90)
print(f"{'Metric':<22} {'Pessimistic':>14} {'Optimistic':>14} {'Redis Lock':>14}")
print("-" * 90)

for metric, key, fmt in [
    ("Requests/s", "rps", ".1f"),
    ("Avg Latency (ms)", "avg", ".1f"),
    ("p50 (ms)", "p50", ".0f"),
    ("p75 (ms)", "p75", ".0f"),
    ("p90 (ms)", "p90", ".0f"),
    ("p95 (ms)", "p95", ".0f"),
    ("p99 (ms)", "p99", ".0f"),
    ("Max (ms)", "max", ".0f"),
    ("Total Requests", "reqs", ",.0f"),
    ("Error Rate (%)", "error_rate", ".2f"),
]:
    print(f"{metric:<22} {format(high['pessimistic'][key], fmt):>14} {format(high['optimistic'][key], fmt):>14} {format(high['redis'][key], fmt):>14}")

print("=" * 90)
