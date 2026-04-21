"""
postprocess.py
--------------
Reads results.csv from the MC run and performs:
  1. MC statistics  — mean, std, CoV, convergence plots, histograms
  2. PCE surrogate  — fits polynomial chaos expansion via regression,
                      checks order convergence, compares PDF to MC

QoIs of interest:
  - max_disp_x  : roof drift (wind-driven)
  - min_disp_y  : max vertical deflection (snow-driven)
  - min_moment_z: peak bending moment (combined)

Usage:
    python postprocess.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import chaospy as cp

# ── Paths ──────────────────────────────────────────────────────────────────────
RESULTS_CSV = "results.csv"
PLOT_DIR    = "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# ── QoIs ──────────────────────────────────────────────────────────────────────
QOIS = {
    "max_disp_x":   "Max Roof Drift $u_x$ [m]",
    "min_disp_y":   "Max Vertical Deflection $u_y$ [m]",
    "min_moment_z": "Min Bending Moment $M_z$ [N·m]",
}

# ── Distributions (must match sampler.py) ─────────────────────────────────────
U_WIND      = 3.467
BETA_WIND   =  1.200
LAMBDA_SNOW =  0.747
XI_SNOW     =  0.256
LAMBDA_E    = 26.021
XI_E        =  0.030

dist_wind = cp.GeneralizedExtreme(shape=0, scale=BETA_WIND, shift=U_WIND)
dist_snow = cp.LogNormal(mu=LAMBDA_SNOW, sigma=XI_SNOW)
dist_E = cp.LogNormal(mu=np.log(200) - 0.03**2/2, sigma=0.030)
joint     = cp.J(dist_wind, dist_snow, dist_E)

# ── Load results ───────────────────────────────────────────────────────────────
df = pd.read_csv(RESULTS_CSV)
N  = len(df)
print(f"Loaded {N} samples from {RESULTS_CSV}\n")

# Input sample matrix (3 x N) for PCE fitting
samples = np.array([
    df["F_wind_kN"].values,
    df["w_snow_kNm"].values,
    df["E_Pa"].values / 1e9,
])

# ──────────────────────────────────────────────────────────────────────────────
# 1. MC STATISTICS
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("1. MONTE CARLO STATISTICS")
print("=" * 60)

mc_stats = {}
for qoi, label in QOIS.items():
    vals = df[qoi].values
    mean = np.mean(vals)
    std  = np.std(vals)
    cov  = std / abs(mean)
    p5   = np.percentile(vals, 5)
    p95  = np.percentile(vals, 95)
    mc_stats[qoi] = {"mean": mean, "std": std, "cov": cov, "p5": p5, "p95": p95}
    print(f"\n{qoi}:")
    print(f"  Mean   = {mean:.6e}")
    print(f"  Std    = {std:.6e}")
    print(f"  CoV    = {cov:.4f}")
    print(f"  5th %  = {p5:.6e}")
    print(f"  95th % = {p95:.6e}")

# ── MC convergence + histogram plots ──────────────────────────────────────────
fig, axes = plt.subplots(len(QOIS), 2, figsize=(12, 10))
for row, (qoi, label) in enumerate(QOIS.items()):
    vals = df[qoi].values

    # Running mean convergence
    running_mean = np.cumsum(vals) / np.arange(1, N + 1)
    axes[row, 0].plot(running_mean, color="steelblue", lw=1)
    axes[row, 0].axhline(mc_stats[qoi]["mean"], color="red", lw=1.5,
                         ls="--", label="Final mean")
    axes[row, 0].set_title(f"MC Convergence — {qoi}")
    axes[row, 0].set_xlabel("Number of samples")
    axes[row, 0].set_ylabel("Running mean")
    axes[row, 0].legend(fontsize=8)

    # Histogram
    axes[row, 1].hist(vals, bins=50, density=True, color="steelblue",
                      edgecolor="white", alpha=0.8)
    axes[row, 1].set_title(f"PDF — {label}")
    axes[row, 1].set_xlabel(label)
    axes[row, 1].set_ylabel("Density")

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "mc_statistics.png"), dpi=150)
print(f"\nSaved MC statistics plot to {PLOT_DIR}/mc_statistics.png")
plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# 2. PCE SURROGATE
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. POLYNOMIAL CHAOS EXPANSION")
print("=" * 60)

PCE_ORDERS = [2, 3, 4, 5]
pce_models = {}   # {qoi: {order: fitted_expansion}}
pce_stats  = {}   # {qoi: {order: (mean, std)}}

for qoi, label in QOIS.items():
    Y = df[qoi].values
    pce_models[qoi] = {}
    pce_stats[qoi]  = {}
    print(f"\n  QoI: {qoi}")

    for order in PCE_ORDERS:
        # Build orthogonal polynomial basis
        expansion = cp.generate_expansion(order, joint)

        # Fit via least-squares regression using MC samples
        fitted = cp.fit_regression(expansion, samples, Y)

        # Moments from PCE coefficients
        mean_pce = cp.E(fitted, joint)
        std_pce  = cp.Std(fitted, joint)

        pce_models[qoi][order] = fitted
        pce_stats[qoi][order]  = (mean_pce, std_pce)

        print(f"    Order {order}: mean={mean_pce:.6e}  std={std_pce:.6e}  "
              f"(MC: mean={mc_stats[qoi]['mean']:.6e}  std={mc_stats[qoi]['std']:.6e})")

# ── PCE order convergence plot ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, len(QOIS), figsize=(14, 4))
for col, (qoi, label) in enumerate(QOIS.items()):
    mc_mean = mc_stats[qoi]["mean"]
    mc_std  = mc_stats[qoi]["std"]

    pce_means = [pce_stats[qoi][o][0] for o in PCE_ORDERS]
    pce_stds  = [pce_stats[qoi][o][1] for o in PCE_ORDERS]

    ax  = axes[col]
    ax2 = ax.twinx()

    ax.plot(PCE_ORDERS, pce_means, "o-", color="steelblue", label="PCE mean")
    ax.axhline(mc_mean, color="steelblue", ls="--", lw=1, label="MC mean")
    ax2.plot(PCE_ORDERS, pce_stds, "s-", color="darkorange", label="PCE std")
    ax2.axhline(mc_std, color="darkorange", ls="--", lw=1, label="MC std")

    ax.set_title(f"PCE Convergence\n{qoi}")
    ax.set_xlabel("Expansion order")
    ax.set_ylabel("Mean", color="steelblue")
    ax2.set_ylabel("Std", color="darkorange")
    ax.set_xticks(PCE_ORDERS)

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "pce_convergence.png"), dpi=150)
print(f"\nSaved PCE convergence plot to {PLOT_DIR}/pce_convergence.png")
plt.close()

# ── PCE vs MC PDF comparison ───────────────────────────────────────────────────
BEST_ORDER    = PCE_ORDERS[-1]
N_PCE_SAMPLES = 100_000

pce_samples = joint.sample(N_PCE_SAMPLES, rule="latin_hypercube", seed=123)

fig, axes = plt.subplots(1, len(QOIS), figsize=(14, 4))
for col, (qoi, label) in enumerate(QOIS.items()):
    fitted = pce_models[qoi][BEST_ORDER]
    Y_pce  = cp.call(fitted, pce_samples)
    Y_mc   = df[qoi].values

    axes[col].hist(Y_mc,  bins=60, density=True, alpha=0.6,
                   color="steelblue",  label="MC (1,000)")
    axes[col].hist(Y_pce, bins=60, density=True, alpha=0.6,
                   color="darkorange", label=f"PCE order {BEST_ORDER} (100k)")
    axes[col].set_title(label)
    axes[col].set_xlabel(label)
    axes[col].set_ylabel("Density")
    axes[col].legend(fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "pce_vs_mc_pdf.png"), dpi=150)
print(f"Saved PCE vs MC PDF plot to {PLOT_DIR}/pce_vs_mc_pdf.png")
plt.close()

print("\n" + "=" * 60)
print("Postprocessing complete.")
print(f"All plots saved to ./{PLOT_DIR}/")
print("=" * 60)
