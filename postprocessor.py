# """
# postprocess.py
# --------------
# Reads results.csv from the MC run and performs:
#   1. MC statistics  — mean, std, CoV, convergence plots, histograms
#   2. PCE surrogate  — fits polynomial chaos expansion via regression,
#                       checks order convergence, compares PDF to MC

# QoIs of interest:
#   - max_disp_x  : roof drift (wind-driven)
#   - min_disp_y  : max vertical deflection (snow-driven)
#   - min_moment_z: peak bending moment (combined)

# Usage:
#     python postprocess.py
# """

# import os
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# import chaospy as cp

# # ── Paths ──────────────────────────────────────────────────────────────────────
# RESULTS_CSV = "results_sparse.csv"
# PLOT_DIR    = "plots_sparse"
# os.makedirs(PLOT_DIR, exist_ok=True)

# # ── QoIs ──────────────────────────────────────────────────────────────────────
# QOIS = {
#     "max_disp_x":   "Max Roof Drift $u_x$ [m]",
#     "min_disp_y":   "Max Vertical Deflection $u_y$ [m]",
#     "min_moment_z": "Min Bending Moment $M_z$ [N·m]",
# }

# # ── Distributions (must match sampler.py) ─────────────────────────────────────
# U_WIND    = 10.651
# BETA_WIND =  3.688
# LAMBDA_SNOW =  0.747
# XI_SNOW     =  0.256
# LAMBDA_E    = 26.021
# XI_E        =  0.030

# dist_wind = cp.GeneralizedExtreme(shape=0, scale=BETA_WIND, shift=U_WIND)
# dist_snow = cp.LogNormal(mu=LAMBDA_SNOW, sigma=XI_SNOW)
# dist_E = cp.LogNormal(mu=np.log(200) - 0.03**2/2, sigma=0.030)
# joint     = cp.J(dist_wind, dist_snow, dist_E)

# # ── Load results ───────────────────────────────────────────────────────────────
# df = pd.read_csv(RESULTS_CSV)
# N  = len(df)
# print(f"Loaded {N} samples from {RESULTS_CSV}\n")

# # Input sample matrix (3 x N) for PCE fitting
# samples = np.array([
#     df["F_wind_kN"].values,
#     df["w_snow_kNm"].values,
#     df["E_Pa"].values / 1e9,
# ])

# # ──────────────────────────────────────────────────────────────────────────────
# # 1. MC STATISTICS
# # ──────────────────────────────────────────────────────────────────────────────
# print("=" * 60)
# print("1. MONTE CARLO STATISTICS")
# print("=" * 60)

# mc_stats = {}
# for qoi, label in QOIS.items():
#     vals = df[qoi].values
#     mean = np.mean(vals)
#     std  = np.std(vals)
#     cov  = std / abs(mean)
#     p5   = np.percentile(vals, 5)
#     p95  = np.percentile(vals, 95)
#     mc_stats[qoi] = {"mean": mean, "std": std, "cov": cov, "p5": p5, "p95": p95}
#     print(f"\n{qoi}:")
#     print(f"  Mean   = {mean:.6e}")
#     print(f"  Std    = {std:.6e}")
#     print(f"  CoV    = {cov:.4f}")
#     print(f"  5th %  = {p5:.6e}")
#     print(f"  95th % = {p95:.6e}")

# # ── MC convergence + histogram plots ──────────────────────────────────────────
# fig, axes = plt.subplots(len(QOIS), 2, figsize=(12, 10))
# for row, (qoi, label) in enumerate(QOIS.items()):
#     vals = df[qoi].values

#     # Running mean convergence
#     running_mean = np.cumsum(vals) / np.arange(1, N + 1)
#     axes[row, 0].plot(running_mean, color="steelblue", lw=1)
#     axes[row, 0].axhline(mc_stats[qoi]["mean"], color="red", lw=1.5,
#                          ls="--", label="Final mean")
#     axes[row, 0].set_title(f"MC Convergence — {qoi}")
#     axes[row, 0].set_xlabel("Number of samples")
#     axes[row, 0].set_ylabel("Running mean")
#     axes[row, 0].legend(fontsize=8)

#     # Histogram
#     axes[row, 1].hist(vals, bins=50, density=True, color="steelblue",
#                       edgecolor="white", alpha=0.8)
#     axes[row, 1].set_title(f"PDF — {label}")
#     axes[row, 1].set_xlabel(label)
#     axes[row, 1].set_ylabel("Density")

# plt.tight_layout()
# plt.savefig(os.path.join(PLOT_DIR, "mc_statistics.png"), dpi=150)
# print(f"\nSaved MC statistics plot to {PLOT_DIR}/mc_statistics.png")
# plt.close()

# # ──────────────────────────────────────────────────────────────────────────────
# # 2. PCE SURROGATE
# # ──────────────────────────────────────────────────────────────────────────────
# print("\n" + "=" * 60)
# print("2. POLYNOMIAL CHAOS EXPANSION")
# print("=" * 60)

# PCE_ORDERS = [2, 3, 4, 5]
# pce_models = {}   # {qoi: {order: fitted_expansion}}
# pce_stats  = {}   # {qoi: {order: (mean, std)}}

# for qoi, label in QOIS.items():
#     Y = df[qoi].values
#     pce_models[qoi] = {}
#     pce_stats[qoi]  = {}
#     print(f"\n  QoI: {qoi}")

#     for order in PCE_ORDERS:
#         # Build orthogonal polynomial basis
#         expansion = cp.generate_expansion(order, joint)

#         # Fit via least-squares regression using MC samples
#         # fitted = cp.fit_regression(expansion, samples, Y)
#         nodes = samples  # the quadrature nodes
#         weights = np.load("quadrature_weights.npy")
#         fitted = cp.fit_quadrature(expansion, nodes, weights, Y)

#         # Moments from PCE coefficients
#         mean_pce = cp.E(fitted, joint)
#         std_pce  = cp.Std(fitted, joint)

#         pce_models[qoi][order] = fitted
#         pce_stats[qoi][order]  = (mean_pce, std_pce)

#         print(f"    Order {order}: mean={mean_pce:.6e}  std={std_pce:.6e}  "
#               f"(MC: mean={mc_stats[qoi]['mean']:.6e}  std={mc_stats[qoi]['std']:.6e})")

# # ── PCE order convergence plot ─────────────────────────────────────────────────
# fig, axes = plt.subplots(1, len(QOIS), figsize=(14, 4))
# for col, (qoi, label) in enumerate(QOIS.items()):
#     mc_mean = mc_stats[qoi]["mean"]
#     mc_std  = mc_stats[qoi]["std"]

#     pce_means = [pce_stats[qoi][o][0] for o in PCE_ORDERS]
#     pce_stds  = [pce_stats[qoi][o][1] for o in PCE_ORDERS]

#     ax  = axes[col]
#     ax2 = ax.twinx()

#     ax.plot(PCE_ORDERS, pce_means, "o-", color="steelblue", label="PCE mean")
#     ax.axhline(mc_mean, color="steelblue", ls="--", lw=1, label="MC mean")
#     ax2.plot(PCE_ORDERS, pce_stds, "s-", color="darkorange", label="PCE std")
#     ax2.axhline(mc_std, color="darkorange", ls="--", lw=1, label="MC std")

#     ax.set_title(f"PCE Convergence\n{qoi}")
#     ax.set_xlabel("Expansion order")
#     ax.set_ylabel("Mean", color="steelblue")
#     ax2.set_ylabel("Std", color="darkorange")
#     ax.set_xticks(PCE_ORDERS)

# plt.tight_layout()
# plt.savefig(os.path.join(PLOT_DIR, "pce_convergence.png"), dpi=150)
# print(f"\nSaved PCE convergence plot to {PLOT_DIR}/pce_convergence.png")
# plt.close()

# # ── PCE vs MC PDF comparison ───────────────────────────────────────────────────
# BEST_ORDER    = PCE_ORDERS[-1]
# N_PCE_SAMPLES = 100_000

# pce_samples = joint.sample(N_PCE_SAMPLES, rule="latin_hypercube", seed=123)

# fig, axes = plt.subplots(1, len(QOIS), figsize=(14, 4))
# for col, (qoi, label) in enumerate(QOIS.items()):
#     fitted = pce_models[qoi][BEST_ORDER]
#     Y_pce  = cp.call(fitted, pce_samples)
#     Y_mc   = df[qoi].values

#     axes[col].hist(Y_mc,  bins=60, density=True, alpha=0.6,
#                    color="steelblue",  label="MC (1,000)")
#     axes[col].hist(Y_pce, bins=60, density=True, alpha=0.6,
#                    color="darkorange", label=f"PCE order {BEST_ORDER} (100k)")
#     axes[col].set_title(label)
#     axes[col].set_xlabel(label)
#     axes[col].set_ylabel("Density")
#     axes[col].legend(fontsize=8)

# plt.tight_layout()
# plt.savefig(os.path.join(PLOT_DIR, "pce_vs_mc_pdf.png"), dpi=150)
# print(f"Saved PCE vs MC PDF plot to {PLOT_DIR}/pce_vs_mc_pdf.png")
# plt.close()

# print("\n" + "=" * 60)
# print("Postprocessing complete.")
# print(f"All plots saved to ./{PLOT_DIR}/")
# print("=" * 60)


"""
postprocess.py
--------------
Reads results.csv (1000 MC samples) and quadrature_results.csv (83 nodes) and performs:
  1. MC statistics        — mean, std, CoV, convergence plots, histograms
  2. Regression PCE       — fit via least squares on 1000 MC samples, orders 2-5
  3. Quadrature PCE       — fit via cp.fit_quadrature on 83 sparse nodes, order 3
  4. Comparison           — regression PCE vs quadrature PCE vs MC histogram

QoIs:
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
MC_CSV   = "results.csv"
QUAD_CSV = "results_sparse.csv"
PLOT_DIR = "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# ── QoIs ──────────────────────────────────────────────────────────────────────
QOIS = {
    "max_disp_x":   "Max Roof Drift $u_x$ [m]",
    "min_disp_y":   "Max Vertical Deflection $u_y$ [m]",
    "min_moment_z": "Min Bending Moment $M_z$ [N·m]",
}

# ── Distributions ─────────────────────────────────────────────────────────────
U_WIND      = 10.651
BETA_WIND   =  3.688
LAMBDA_SNOW =  0.747
XI_SNOW     =  0.256

dist_wind = cp.GeneralizedExtreme(shape=0, scale=BETA_WIND, shift=U_WIND)
dist_snow = cp.LogNormal(mu=LAMBDA_SNOW, sigma=XI_SNOW)
dist_E    = cp.LogNormal(mu=np.log(200) - 0.03**2/2, sigma=0.030)  # E in GPa
joint     = cp.J(dist_wind, dist_snow, dist_E)

# ── Load MC results ────────────────────────────────────────────────────────────
df_mc = pd.read_csv(MC_CSV)
N_mc  = len(df_mc)
print(f"Loaded {N_mc} MC samples from {MC_CSV}")

mc_samples = np.array([
    df_mc["F_wind_kN"].values,
    df_mc["w_snow_kNm"].values,
    df_mc["E_Pa"].values / 1e9,  # Pa → GPa
])

# ── Load quadrature results ────────────────────────────────────────────────────
df_quad = pd.read_csv(QUAD_CSV)
N_quad  = len(df_quad)
print(f"Loaded {N_quad} quadrature nodes from {QUAD_CSV}")

quad_nodes = np.array([
    df_quad["F_wind_kN"].values,
    df_quad["w_snow_kNm"].values,
    df_quad["E_Pa"].values / 1e9,  # Pa → GPa
])

# Regenerate quadrature weights (must match order used to generate nodes)
QUAD_ORDER = 3
_, quad_weights = cp.generate_quadrature(
    QUAD_ORDER, joint, rule="gaussian", sparse=True
)
print(f"Quadrature order: {QUAD_ORDER}, nodes: {N_quad}\n")

# ──────────────────────────────────────────────────────────────────────────────
# 1. MC STATISTICS
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("1. MONTE CARLO STATISTICS")
print("=" * 60)

mc_stats = {}
for qoi, label in QOIS.items():
    vals = df_mc[qoi].values
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

# ── MC convergence + histogram ─────────────────────────────────────────────────
fig, axes = plt.subplots(len(QOIS), 2, figsize=(12, 10))
for row, (qoi, label) in enumerate(QOIS.items()):
    vals = df_mc[qoi].values
    running_mean = np.cumsum(vals) / np.arange(1, N_mc + 1)

    axes[row, 0].plot(running_mean, color="steelblue", lw=1)
    axes[row, 0].axhline(mc_stats[qoi]["mean"], color="red", lw=1.5,
                         ls="--", label="Final mean")
    axes[row, 0].set_title(f"MC Convergence — {qoi}")
    axes[row, 0].set_xlabel("Number of samples")
    axes[row, 0].set_ylabel("Running mean")
    axes[row, 0].legend(fontsize=8)

    axes[row, 1].hist(vals, bins=50, density=True, color="steelblue",
                      edgecolor="white", alpha=0.8)
    axes[row, 1].set_title(f"PDF — {label}")
    axes[row, 1].set_xlabel(label)
    axes[row, 1].set_ylabel("Density")

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "mc_statistics.png"), dpi=150)
print(f"\nSaved mc_statistics.png")
plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# 2. REGRESSION PCE (on 1000 MC samples)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. REGRESSION PCE")
print("=" * 60)

PCE_ORDERS   = [2, 3, 4, 5]
reg_models   = {}
reg_stats    = {}

for qoi, label in QOIS.items():
    Y = df_mc[qoi].values
    reg_models[qoi] = {}
    reg_stats[qoi]  = {}
    print(f"\n  QoI: {qoi}")

    for order in PCE_ORDERS:
        expansion = cp.generate_expansion(order, joint)
        fitted    = cp.fit_regression(expansion, mc_samples, Y)
        mean_pce  = cp.E(fitted, joint)
        std_pce   = cp.Std(fitted, joint)

        reg_models[qoi][order] = fitted
        reg_stats[qoi][order]  = (mean_pce, std_pce)

        print(f"    Order {order}: mean={mean_pce:.6e}  std={std_pce:.6e}  "
              f"(MC: mean={mc_stats[qoi]['mean']:.6e}  std={mc_stats[qoi]['std']:.6e})")

# ── Regression PCE convergence plot ───────────────────────────────────────────
fig, axes = plt.subplots(1, len(QOIS), figsize=(14, 4))
for col, (qoi, label) in enumerate(QOIS.items()):
    mc_mean = mc_stats[qoi]["mean"]
    mc_std  = mc_stats[qoi]["std"]
    pce_means = [reg_stats[qoi][o][0] for o in PCE_ORDERS]
    pce_stds  = [reg_stats[qoi][o][1] for o in PCE_ORDERS]

    ax  = axes[col]
    ax2 = ax.twinx()
    ax.plot(PCE_ORDERS, pce_means, "o-", color="steelblue", label="PCE mean")
    ax.axhline(mc_mean, color="steelblue", ls="--", lw=1)
    ax2.plot(PCE_ORDERS, pce_stds, "s-", color="darkorange", label="PCE std")
    ax2.axhline(mc_std, color="darkorange", ls="--", lw=1)
    ax.set_title(f"Regression PCE Convergence\n{qoi}")
    ax.set_xlabel("Expansion order")
    ax.set_ylabel("Mean", color="steelblue")
    ax2.set_ylabel("Std", color="darkorange")
    ax.set_xticks(PCE_ORDERS)

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "regression_pce_convergence.png"), dpi=150)
print(f"\nSaved regression_pce_convergence.png")
plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# 3. QUADRATURE PCE (on 83 sparse nodes, order 3)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. QUADRATURE PCE")
print("=" * 60)

quad_models = {}
quad_stats  = {}

expansion_quad = cp.generate_expansion(QUAD_ORDER, joint)

for qoi, label in QOIS.items():
    Y = df_quad[qoi].values

    fitted   = cp.fit_quadrature(expansion_quad, quad_nodes, quad_weights, Y)
    mean_pce = cp.E(fitted, joint)
    std_pce  = cp.Std(fitted, joint)

    quad_models[qoi] = fitted
    quad_stats[qoi]  = (mean_pce, std_pce)

    print(f"\n  QoI: {qoi}")
    print(f"    Quadrature order {QUAD_ORDER}: mean={mean_pce:.6e}  std={std_pce:.6e}")
    print(f"    MC reference:                  mean={mc_stats[qoi]['mean']:.6e}  "
          f"std={mc_stats[qoi]['std']:.6e}")

# ──────────────────────────────────────────────────────────────────────────────
# 4. COMPARISON: Regression PCE vs Quadrature PCE vs MC
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. COMPARISON PLOTS")
print("=" * 60)

BEST_REG_ORDER = PCE_ORDERS[-1]
N_SURROGATE    = 100_000
surr_samples   = joint.sample(N_SURROGATE, rule="latin_hypercube", seed=123)

# ── Moments comparison table ───────────────────────────────────────────────────
print("\n  Moments comparison (mean / std):")
print(f"  {'QoI':<20} {'MC':>20} {'Regression':>20} {'Quadrature':>20}")
print("  " + "-" * 82)
for qoi in QOIS:
    mc_m,  mc_s  = mc_stats[qoi]["mean"],        mc_stats[qoi]["std"]
    reg_m, reg_s = reg_stats[qoi][BEST_REG_ORDER]
    qd_m,  qd_s  = quad_stats[qoi]
    print(f"  {qoi:<20} "
          f"{mc_m:+.4e} / {mc_s:.4e}   "
          f"{reg_m:+.4e} / {reg_s:.4e}   "
          f"{qd_m:+.4e} / {qd_s:.4e}")

# ── PDF comparison plot ────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, len(QOIS), figsize=(16, 5))

for col, (qoi, label) in enumerate(QOIS.items()):
    Y_mc   = df_mc[qoi].values
    Y_reg  = cp.call(reg_models[qoi][BEST_REG_ORDER], surr_samples)
    Y_quad = cp.call(quad_models[qoi], surr_samples)

    axes[col].hist(Y_mc,   bins=60, density=True, alpha=0.5,
                   color="steelblue",  label=f"MC (N={N_mc})")
    axes[col].hist(Y_reg,  bins=60, density=True, alpha=0.5,
                   color="darkorange", label=f"Regression PCE order {BEST_REG_ORDER} (N={N_mc})")
    axes[col].hist(Y_quad, bins=60, density=True, alpha=0.5,
                   color="green",      label=f"Quadrature PCE order {QUAD_ORDER} (N={N_quad})")
    axes[col].set_title(label)
    axes[col].set_xlabel(label)
    axes[col].set_ylabel("Density")
    axes[col].legend(fontsize=7)

plt.suptitle("PCE Surrogate Comparison: Regression vs Quadrature vs MC",
             fontsize=12, y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "pce_comparison.png"), dpi=150,
            bbox_inches="tight")
print(f"\nSaved pce_comparison.png")
plt.close()

# ── Model call efficiency summary ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  MODEL CALL EFFICIENCY SUMMARY")
print("=" * 60)
print(f"  Monte Carlo (reference):  {N_mc} MOOSE calls")
print(f"  Regression PCE order {BEST_REG_ORDER}:  {N_mc} MOOSE calls  "
      f"(reuses MC samples)")
print(f"  Quadrature PCE order {QUAD_ORDER}:  {N_quad} MOOSE calls")
print(f"  Reduction factor:         {N_mc/N_quad:.1f}x fewer calls for quadrature")

print("\n" + "=" * 60)
print("Postprocessing complete.")
print(f"All plots saved to ./{PLOT_DIR}/")
print("=" * 60)