
import numpy as np
import chaospy as cp
import pandas as pd
import matplotlib.pyplot as plt
 
# ── Reproducibility ────────────────────────────────────────────────────────────
SEED = 42
N_SAMPLES = 1000
 
# ── Distribution parameters ────────────────────────────────────────────────────
# Gumbel: parameterized by location u and scale beta
U_WIND   = 3.467   # kN  (location)
BETA_WIND = 1.200  # kN  (scale)
 
# Lognormal: chaospy uses (mu, sigma) of the *underlying normal*
# i.e. ln(X) ~ N(lambda, xi^2)
LAMBDA_SNOW = 0.747   # log-mean
XI_SNOW     = 0.256   # log-std
 
LAMBDA_E  = np.log(200) - 0.03**2 / 2   # GPa
XI_E        = 0.030   # log-std
 
# ── Construct marginal distributions ──────────────────────────────────────────
dist_wind = cp.GeneralizedExtreme(shape=0, scale=BETA_WIND, shift=U_WIND)
dist_snow  = cp.LogNormal(mu=LAMBDA_SNOW, sigma=XI_SNOW)
dist_E     = cp.LogNormal(mu=LAMBDA_E,    sigma=XI_E)
 
# ── Joint distribution (independent inputs) ───────────────────────────────────
joint = cp.J(dist_wind, dist_snow, dist_E)
 
# ── Latin Hypercube Sampling ───────────────────────────────────────────────────
samples = joint.sample(N_SAMPLES, rule="latin_hypercube", seed=SEED)
# samples shape: (3, N_SAMPLES)
# Row 0: F_wind [kN]
# Row 1: w_snow [kN/m]
# Row 2: E      [Pa]
 
F_wind = samples[0]   # kN
w_snow = samples[1]   # kN/m
E      = samples[2]   # Pa
 
# ── Save to CSV ────────────────────────────────────────────────────────────────
df = pd.DataFrame({
    "F_wind_kN":   F_wind,
    "w_snow_kNm":  w_snow,
    "E_Pa":        E,
})
df.to_csv("samples.csv", index_label="sample_id")
print(f"Saved {N_SAMPLES} samples to samples.csv")
 
# ── Quick sanity check: print sample statistics ────────────────────────────────
print("\n── Sample statistics ──────────────────────────────────────────")
print(f"F_wind : mean={F_wind.mean():.3f} kN,  std={F_wind.std():.3f} kN,  "
      f"CoV={F_wind.std()/F_wind.mean():.3f}  (target 0.37)")
print(f"w_snow : mean={w_snow.mean():.3f} kN/m, std={w_snow.std():.3f} kN/m, "
      f"CoV={w_snow.std()/w_snow.mean():.3f}  (target 0.26)")
print(f"E      : mean={E.mean():.4e} Pa,  std={E.std():.4e} Pa,  "
      f"CoV={E.std()/E.mean():.4f}  (target 0.03)")
 
# ── Histogram plots ────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
 
axes[0].hist(F_wind, bins=40, color="steelblue", edgecolor="white", density=True)
axes[0].set_title("Wind Load $F_{wind}$ [kN]")
axes[0].set_xlabel("kN")
axes[0].set_ylabel("Density")
 
axes[1].hist(w_snow, bins=40, color="slategray", edgecolor="white", density=True)
axes[1].set_title("Snow Load $w_{snow}$ [kN/m]")
axes[1].set_xlabel("kN/m")
 
axes[2].hist(E / 1e9, bins=40, color="darkorange", edgecolor="white", density=True)
axes[2].set_title("Young's Modulus $E$ [GPa]")
axes[2].set_xlabel("GPa")
 
plt.tight_layout()
plt.savefig("samples_histograms.png", dpi=150)
print("\nSaved histogram plot to samples_histograms.png")
plt.show()
