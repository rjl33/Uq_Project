"""
runner.py
---------
Reads samples.csv, patches steel_frame.i for each sample,
runs MOOSE, extracts QoIs, and saves to results.csv.

Scaling is done proportionally from nominal values in the template .i file:
  F_wind_nominal = 4.5 kN  (500 + 4*1000 N distributed across column nodes)
  w_snow_nominal = 1.333 kN/m  (back-calculated: (2*2000 + 4*4000)N / 15000mm)
  E_nominal      = 2.0e11 Pa

Usage:
    python runner.py
"""

import os
import re
import subprocess
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
MOOSE_DIR   = "/home/rjl64/projects/moose/UQ_project"
TEMPLATE_I  = os.path.join(MOOSE_DIR, "steel_frame.i")
SAMPLES_CSV = os.path.join(MOOSE_DIR, "samples.csv")
RESULTS_CSV = os.path.join(MOOSE_DIR, "results_1000.csv")
MOOSE_CMD   = "mpiexec -n 16 ../modules/solid_mechanics/solid_mechanics-opt"

# ── Nominal values (must match template .i file) ───────────────────────────────
F_WIND_NOMINAL = 4.5    # kN  →  500 + 4*1000 = 4500 N total
W_SNOW_NOMINAL = 1.333  # kN/m → (2*2000 + 4*4000) N / 15 m

# Nominal nodal rates in .i (N) — used to compute scale factors
WIND_TOP_NOM      =  500.0
WIND_INT_NOM      = 1000.0
SNOW_END_NOM      = -2000.0
SNOW_INT_NOM      = -4000.0

# ── QoIs ──────────────────────────────────────────────────────────────────────
QOI_COLS = [
    "max_disp_x", "min_disp_x",
    "max_disp_y", "min_disp_y",
    "max_force_x", "max_force_y",
    "max_moment_z", "min_moment_z",
]

# ── Load samples ──────────────────────────────────────────────────────────────
df_samples = pd.read_csv(SAMPLES_CSV, index_col="sample_id")
N = len(df_samples)
print(f"Loaded {N} samples from {SAMPLES_CSV}")


def make_input_file(sample_id, F_wind_kN, w_snow_kNm, E_Pa, out_path):
    """Patch template .i file with sampled values and write to out_path."""

    # Scale factors
    sf_wind  = F_wind_kN  / F_WIND_NOMINAL
    sf_snow  = w_snow_kNm / W_SNOW_NOMINAL

    # New nodal rates
    wind_top      = WIND_TOP_NOM  * sf_wind
    wind_interior = WIND_INT_NOM  * sf_wind
    snow_end      = SNOW_END_NOM  * sf_snow
    snow_interior = SNOW_INT_NOM  * sf_snow

    with open(TEMPLATE_I, "r") as f:
        content = f.read()

    # Young's modulus
    content = re.sub(
        r"(youngs_modulus\s*=\s*)[\d.eE+\-]+",
        lambda m: f"{m.group(1)}{E_Pa:.6e}",
        content
    )

    # Wind: top node
    content = re.sub(
        r"(\[wind_col_top\][\s\S]*?rate\s*=\s*)[\d.eE+\-]+",
        lambda m, v=wind_top: f"{m.group(1)}{v:.4e}",
        content
    )

    # Wind: interior column nodes
    for node in ["col_4", "col_3", "col_2", "col_1"]:
        content = re.sub(
            rf"(\[wind_{node}\][\s\S]*?rate\s*=\s*)[\d.eE+\-]+",
            lambda m, v=wind_interior: f"{m.group(1)}{v:.4e}",
            content
        )

    # Snow: end nodes (top_left uses snow kernel name to avoid wind block collision)
    content = re.sub(
        r"(\[snow_roof_left_end\][\s\S]*?rate\s*=\s*)[\d.eE+\-]+",
        lambda m, v=snow_end: f"{m.group(1)}{v:.4e}",
        content
    )
    content = re.sub(
        r"(\[snow_roof_right_end\][\s\S]*?rate\s*=\s*)[\d.eE+\-]+",
        lambda m, v=snow_end: f"{m.group(1)}{v:.4e}",
        content
    )

    # Snow: interior roof nodes
    for node in ["1", "2", "3", "4"]:
        content = re.sub(
            rf"(\[snow_roof_{node}\][\s\S]*?rate\s*=\s*)[\d.eE+\-]+",
            lambda m, v=snow_interior: f"{m.group(1)}{v:.4e}",
            content
        )

    # Output file_base — unique per sample
    out_base = f"run_{sample_id:04d}"
    content = re.sub(
        r"(file_base\s*=\s*)portal_frame_out",
        lambda m: f"{m.group(1)}{out_base}",
        content
    )

    with open(out_path, "w") as f:
        f.write(content)

    return out_base


def parse_moose_csv(csv_path):
    """Extract QoIs from last row of MOOSE CSV output."""
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            return None
        last = df.iloc[-1]
        return {col: last[col] for col in QOI_COLS if col in last}
    except Exception as e:
        print(f"  Warning: could not parse {csv_path}: {e}")
        return None


# ── Main loop ─────────────────────────────────────────────────────────────────
results = []

for i, row in df_samples.iterrows():
    F_wind = row["F_wind_kN"]
    w_snow = row["w_snow_kNm"]
    E      = row["E_Pa"]

    print(f"[{i+1:04d}/{N}] F_wind={F_wind:.3f} kN  w_snow={w_snow:.3f} kN/m  E={E:.4e} Pa")

    # Write patched input
    run_input = os.path.join(MOOSE_DIR, f"run_{i:04d}.i")
    out_base  = make_input_file(i, F_wind, w_snow, E, run_input)

    # Run MOOSE
    cmd = f"{MOOSE_CMD} -i run_{i:04d}.i"
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=MOOSE_DIR,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=300
        )
        if proc.returncode != 0:
            print(f"  WARNING: non-zero exit code for sample {i}")
    except subprocess.TimeoutExpired:
        print(f"  WARNING: timeout for sample {i}")
        continue

    # Parse QoIs
    moose_csv = os.path.join(MOOSE_DIR, f"{out_base}.csv")
    qois = parse_moose_csv(moose_csv)

    if qois is None:
        print(f"  WARNING: no output for sample {i}, skipping")
        continue

    # Clean up patched input
    os.remove(run_input)

    # Store
    record = {"sample_id": i, "F_wind_kN": F_wind, "w_snow_kNm": w_snow, "E_Pa": E}
    record.update(qois)
    results.append(record)

    # Incremental save every 10 samples
    if len(results) % 10 == 0:
        pd.DataFrame(results).to_csv(RESULTS_CSV, index=False)
        print(f"  Checkpoint: {len(results)} results saved")

# Final save
pd.DataFrame(results).to_csv(RESULTS_CSV, index=False)
print(f"\nDone. {len(results)}/{N} samples completed.")
print(f"Results saved to {RESULTS_CSV}")