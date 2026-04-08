"""
Generate a combined 3-scenario comparison for Experiment 2:
  - High contention:     1 ticket  (LOCUST_HOT_TICKET=1), 200 users
  - Moderate contention: 4 tickets (random spread), 200 users
  - Low contention:      50 tickets (random spread), 200 users
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Data from all 3 scenarios (POST /orders only) ───────────

# High contention: from statistics_2.txt (1 hot ticket, 200 users)
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
}

# Moderate contention: from low_contention_4tickets/ (4 tickets, 200 users)
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

# Low contention: from low_contention/ (50 tickets, 200 users)
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

# ── Style ────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f8f8",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
})
C_PESS = "#2196F3"
C_OPT = "#FF9800"
scenarios = ["High\n(1 ticket,\n~200/row)", "Moderate\n(4 tickets,\n~50/row)", "Low\n(50 tickets,\n~4/row)"]
x = np.arange(len(scenarios))
width = 0.32


# ═══════════════════════════════════════════════════════════════
#  Chart 1: Full dashboard — throughput, avg latency, p95, p99
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1a: Throughput (req/s)
ax = axes[0, 0]
pess_vals = [high["pessimistic"]["rps"], mod["pessimistic"]["rps"], low["pessimistic"]["rps"]]
opt_vals = [high["optimistic"]["rps"], mod["optimistic"]["rps"], low["optimistic"]["rps"]]
bars1 = ax.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 5, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
for b in bars2:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 5, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
ax.set_ylabel("Requests/s")
ax.set_title("Throughput (POST /orders)")
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend()

# 1b: Avg Latency
ax = axes[0, 1]
pess_vals = [high["pessimistic"]["avg"], mod["pessimistic"]["avg"], low["pessimistic"]["avg"]]
opt_vals = [high["optimistic"]["avg"], mod["optimistic"]["avg"], low["optimistic"]["avg"]]
bars1 = ax.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 3, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
for b in bars2:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 3, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
ax.set_ylabel("Avg Response Time (ms)")
ax.set_title("Average Latency (POST /orders)")
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend()

# 1c: p95 Latency
ax = axes[1, 0]
pess_vals = [high["pessimistic"]["p95"], mod["pessimistic"]["p95"], low["pessimistic"]["p95"]]
opt_vals = [high["optimistic"]["p95"], mod["optimistic"]["p95"], low["optimistic"]["p95"]]
bars1 = ax.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 5, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
for b in bars2:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 5, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
ax.set_ylabel("p95 Response Time (ms)")
ax.set_title("p95 Latency (POST /orders)")
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend()

# 1d: p99 Latency
ax = axes[1, 1]
pess_vals = [high["pessimistic"]["p99"], mod["pessimistic"]["p99"], low["pessimistic"]["p99"]]
opt_vals = [high["optimistic"]["p99"], mod["optimistic"]["p99"], low["optimistic"]["p99"]]
bars1 = ax.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 10, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
for b in bars2:
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 10, f"{b.get_height():.0f}", ha="center", fontsize=9, fontweight="bold")
ax.set_ylabel("p99 Response Time (ms)")
ax.set_title("p99 Latency (POST /orders)")
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend()

fig.suptitle("Experiment 2 — Locking Strategy Comparison Across Contention Levels\n(200 users, 4 order-service tasks, 5 min each)", fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_3way_dashboard.png"), dpi=150)
plt.close(fig)
print("Saved exp2_3way_dashboard.png")


# ═══════════════════════════════════════════════════════════════
#  Chart 2: Latency percentile curves for all 3 scenarios
# ═══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 7))

percentiles = ["p50", "p75", "p90", "p95", "p99"]
pct_labels = ["p50", "p75", "p90", "p95", "p99"]
px = np.arange(len(percentiles))

# Use 6 distinct colors so every line is easy to tell apart
styles = [
    (high, "pessimistic", "High (1 ticket)",    "#1a237e", "-",  "o",  3.0),  # dark blue
    (high, "optimistic",  "High (1 ticket)",     "#d32f2f", "-",  "s",  3.0),  # red
    (mod,  "pessimistic", "Moderate (4 tickets)","#0288d1", "--", "^",  2.5),  # medium blue
    (mod,  "optimistic",  "Moderate (4 tickets)","#f57c00", "--", "D",  2.5),  # orange
    (low,  "pessimistic", "Low (50 tickets)",    "#4caf50", ":",  "v",  2.5),  # green
    (low,  "optimistic",  "Low (50 tickets)",    "#ab47bc", ":",  "P",  2.5),  # purple
]

for data, strategy, label, color, ls, marker, lw in styles:
    vals = [data[strategy][p] for p in percentiles]
    ax.plot(px, vals, color=color, linestyle=ls, linewidth=lw,
            marker=marker, markersize=8, markeredgecolor="white", markeredgewidth=0.8,
            label=f"{strategy.capitalize()} — {label}")

ax.set_xticks(px)
ax.set_xticklabels(pct_labels, fontsize=12)
ax.set_xlabel("Percentile", fontsize=12)
ax.set_ylabel("Response Time (ms)", fontsize=12)
ax.set_title("Experiment 2 — POST /orders Latency Percentiles Across Contention Levels", fontsize=13)
ax.legend(fontsize=10, loc="upper left", framealpha=0.9)
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_3way_percentiles.png"), dpi=150)
plt.close(fig)
print("Saved exp2_3way_percentiles.png")


# ═══════════════════════════════════════════════════════════════
#  Chart 3: Total requests + error rate
# ═══════════════════════════════════════════════════════════════
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# 3a: Total requests
pess_vals = [high["pessimistic"]["reqs"], mod["pessimistic"]["reqs"], low["pessimistic"]["reqs"]]
opt_vals = [high["optimistic"]["reqs"], mod["optimistic"]["reqs"], low["optimistic"]["reqs"]]
bars1 = ax1.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax1.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 1000, f"{b.get_height():,.0f}", ha="center", fontsize=8, fontweight="bold")
for b in bars2:
    ax1.text(b.get_x() + b.get_width()/2, b.get_height() + 1000, f"{b.get_height():,.0f}", ha="center", fontsize=8, fontweight="bold")
ax1.set_ylabel("Total Requests")
ax1.set_title("Total Orders Processed (5 min)")
ax1.set_xticks(x)
ax1.set_xticklabels(scenarios)
ax1.legend()

# 3b: Error rate
pess_vals = [high["pessimistic"]["error_rate"], mod["pessimistic"]["error_rate"], low["pessimistic"]["error_rate"]]
opt_vals = [high["optimistic"]["error_rate"], mod["optimistic"]["error_rate"], low["optimistic"]["error_rate"]]
bars1 = ax2.bar(x - width/2, pess_vals, width, label="Pessimistic", color=C_PESS, alpha=0.85)
bars2 = ax2.bar(x + width/2, opt_vals, width, label="Optimistic", color=C_OPT, alpha=0.85)
for b in bars1:
    ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 0.05, f"{b.get_height():.1f}%", ha="center", fontsize=9, fontweight="bold")
for b in bars2:
    ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 0.05, f"{b.get_height():.1f}%", ha="center", fontsize=9, fontweight="bold")
ax2.set_ylabel("Error Rate (%)")
ax2.set_title("Error Rate")
ax2.set_xticks(x)
ax2.set_xticklabels(scenarios)
ax2.legend()

fig.suptitle("Experiment 2 — Total Throughput & Reliability", fontsize=13, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(BASE, "exp2_3way_requests_errors.png"), dpi=150)
plt.close(fig)
print("Saved exp2_3way_requests_errors.png")


# ═══════════════════════════════════════════════════════════════
#  Print full summary table
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("  Experiment 2 — Full 3-Scenario Summary (POST /orders)")
print("=" * 80)
header = f"{'Metric':<20} {'High-Pess':>10} {'High-Opt':>10} {'Mod-Pess':>10} {'Mod-Opt':>10} {'Low-Pess':>10} {'Low-Opt':>10}"
print(header)
print("-" * 80)

datasets = [high, mod, low]
for metric, key, fmt in [
    ("Requests/s", "rps", ".1f"),
    ("Avg Latency (ms)", "avg", ".1f"),
    ("p50 (ms)", "p50", ".0f"),
    ("p95 (ms)", "p95", ".0f"),
    ("p99 (ms)", "p99", ".0f"),
    ("Max (ms)", "max", ".0f"),
    ("Total Requests", "reqs", ",.0f"),
    ("Error Rate (%)", "error_rate", ".2f"),
]:
    vals = []
    for d in datasets:
        vals.append(format(d["pessimistic"][key], fmt))
        vals.append(format(d["optimistic"][key], fmt))
    print(f"{metric:<20} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10} {vals[3]:>10} {vals[4]:>10} {vals[5]:>10}")

print("=" * 80)
