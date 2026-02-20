"""
07-sat-depth-class-vs-aho.py
============================
Calibrates satellite-derived reef "detectability classes" against
Australian Hydrographic Office (AHO) charted depths.

Spectral detectability → class mapping
---------------------------------------
* Very-shallow reefs are visible in a contrast-enhanced red band;
  encoded in the shapefile as V_SHALLOW == 1.
* Deep (mesophotic) reefs are visible in a contrast-enhanced green band;
  encoded as NVCL_Eco == "Oceanic mesophotic coral reefs".
* Shallow (but not very-shallow) reefs are encoded as
  NVCL_Eco == "Oceanic shallow coral reefs" with V_SHALLOW == 0.

Input dataset
-------------
Only features with AHO_DEPTH present were retained; the shapefile
already contains exactly 880 rows — no further filtering is required.
Path: data/v1-2/extra/Depth-class-assessment/
      CS-Features-Satellite-depth-class-vs-AHO.shp

Analysis approach
-----------------
1. Threshold-based truth labels:
   - AHO_DEPTH <= D_vs  → very-shallow truth
   - AHO_DEPTH >= D_deep → deep truth
   - intermediate        → shallow truth
2. One-vs-rest threshold sweeps using F1 as the key criterion.
3. Final 3×3 confusion matrix at analyst-chosen thresholds.

AHO self-consistency test
--------------------------
Quantifies label stability given AHO's own ZOC-B depth uncertainty.
Perturbation model: ε ~ Normal(0, σ²) where
  σ(z) = sqrt(0.25² + (0.02·z)²)
(i.e. ±0.5 m at 95% CI plus 2% of depth combined in quadrature).
N = 1 000 Monte-Carlo repetitions; seed = 42 for reproducibility.

Outputs: working/07/  (relative to this script's location)

Dependencies: python=3.13.1, geopandas=1.0.1, shapely=2.0.7,
              gdal=3.10.2, matplotlib, numpy, pandas
"""

import os
import sys
import pathlib

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")          # non-interactive backend; safe in VS Code too
import matplotlib.pyplot as plt
from version import VERSION

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).parent
INPUT_SHP  = SCRIPT_DIR / f"data/{VERSION}/extra/Depth-class-assessment" \
             / "CS-Features-Satellite-depth-class-vs-AHO.shp"
OUT_DIR    = SCRIPT_DIR / "working" / "07"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Analyst-chosen thresholds (adjust after inspecting the sweep plots)
# ---------------------------------------------------------------------------
D_VS   = 2.4   # very-shallow threshold (m); reefs with AHO_DEPTH <= D_VS
D_DEEP = 24    # deep threshold (m);         reefs with AHO_DEPTH >= D_DEEP

# ---------------------------------------------------------------------------
# Sweep ranges
# ---------------------------------------------------------------------------
DEEP_SWEEP_VALUES    = np.arange(10, 41, 1)          # 10 … 40 m, step 1 m
VSHALLOW_SWEEP_VALUES = np.arange(0.0, 5.01, 0.2)   # 0 … 5 m, step 0.2 m

# AHO sensitivity Monte-Carlo settings
N_REPS    = 1000
MC_SEED   = 42

EXPECTED_ROWS = 880

# String constants for NVCL_Eco values
DEEP_ECO    = "Oceanic mesophotic coral reefs"
SHALLOW_ECO = "Oceanic shallow coral reefs"


# ===========================================================================
# Helper: one-vs-rest binary metrics
# ===========================================================================
def binary_metrics(truth_binary: np.ndarray, pred_binary: np.ndarray) -> dict:
    """Return TP, TN, FP, FN, precision, recall, F1, accuracy."""
    TP = int(np.sum( truth_binary &  pred_binary))
    TN = int(np.sum(~truth_binary & ~pred_binary))
    FP = int(np.sum(~truth_binary &  pred_binary))
    FN = int(np.sum( truth_binary & ~pred_binary))

    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall    = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    accuracy  = (TP + TN) / (TP + TN + FP + FN)

    return dict(TP=TP, TN=TN, FP=FP, FN=FN,
                precision=precision, recall=recall,
                f1=f1, accuracy=accuracy)


# ===========================================================================
# Helper: assign three truth classes from AHO_DEPTH
# ===========================================================================
def aho_truth_classes(aho: np.ndarray, d_vs: float, d_deep: float) -> np.ndarray:
    """Return string array with 'very-shallow', 'shallow', or 'deep'."""
    labels = np.full(len(aho), "shallow", dtype=object)
    labels[aho <= d_vs]   = "very-shallow"
    labels[aho >= d_deep] = "deep"
    return labels


# ===========================================================================
# Step 1 – Load data
# ===========================================================================
print("=" * 60)
print("Step 1: Loading input shapefile …")
print(f"  Path: {INPUT_SHP}")

if not INPUT_SHP.exists():
    sys.exit(f"ERROR: Shapefile not found:\n  {INPUT_SHP}")

gdf = gpd.read_file(INPUT_SHP)
print(f"  Loaded {len(gdf)} features.")

# Row-count sanity check
if len(gdf) != EXPECTED_ROWS:
    print(f"WARNING: Expected {EXPECTED_ROWS} rows but found {len(gdf)}. "
          "Proceeding anyway.")
else:
    print(f"  Row count OK: {EXPECTED_ROWS} features.")


# ===========================================================================
# Step 2 – Field validation
# ===========================================================================
print("\nStep 2: Validating required fields …")

REQUIRED_COLS = ["AHO_DEPTH", "ID", "NVCL_Eco", "V_SHALLOW", "ReefID"]
missing = [c for c in REQUIRED_COLS if c not in gdf.columns]
if missing:
    sys.exit(f"ERROR: Missing required columns: {missing}")
print(f"  All required columns present: {REQUIRED_COLS}")

# V_SHALLOW must be 0 or 1
invalid_vs = gdf.loc[~gdf["V_SHALLOW"].isin([0, 1]), "V_SHALLOW"].unique()
if len(invalid_vs):
    sys.exit(f"ERROR: V_SHALLOW contains unexpected values: {invalid_vs}")
print("  V_SHALLOW values OK (only 0 and 1 present).")

# AHO_DEPTH must be numeric and non-null (already filtered, but verify)
null_depth = gdf["AHO_DEPTH"].isna().sum()
if null_depth:
    print(f"WARNING: {null_depth} rows have null AHO_DEPTH — these will be "
          "excluded from metric calculations.")

print(f"  AHO_DEPTH range: {gdf['AHO_DEPTH'].min():.2f} m "
      f"to {gdf['AHO_DEPTH'].max():.2f} m")


# ===========================================================================
# Step 3 – Build satellite-predicted classes & QA flag
# ===========================================================================
print("\nStep 3: Building satellite-predicted classes …")

aho    = gdf["AHO_DEPTH"].to_numpy(dtype=float)
vs_arr = gdf["V_SHALLOW"].to_numpy(dtype=int)
eco    = gdf["NVCL_Eco"].to_numpy(dtype=str)

pred_very_shallow = (vs_arr == 1)
pred_deep         = (eco == DEEP_ECO)
pred_shallow      = (eco == SHALLOW_ECO) & (vs_arr == 0)

# QA: V_SHALLOW==1 rows should also have NVCL_Eco == SHALLOW_ECO
inconsistent_mask = (vs_arr == 1) & (eco != SHALLOW_ECO)
n_inconsistent = int(inconsistent_mask.sum())

if n_inconsistent > 0:
    print(f"  QA WARNING: {n_inconsistent} row(s) have V_SHALLOW==1 but "
          f"NVCL_Eco != '{SHALLOW_ECO}'.")
    incons_df = gdf.loc[inconsistent_mask, ["ID", "ReefID", "NVCL_Eco", "V_SHALLOW"]]
    print(incons_df.to_string(index=False))
    print("  These rows are retained but flagged.")
else:
    print("  QA OK: All V_SHALLOW==1 rows have consistent NVCL_Eco values.")

gdf["qa_inconsistent"] = inconsistent_mask.astype(int)

print(f"  Predicted very-shallow : {pred_very_shallow.sum():4d} features")
print(f"  Predicted deep         : {pred_deep.sum():4d} features")
print(f"  Predicted shallow      : {pred_shallow.sum():4d} features")
print(f"  Total predicted        : "
      f"{pred_very_shallow.sum() + pred_deep.sum() + pred_shallow.sum():4d} "
      "(expect overlap possible only if inconsistency present)")


# ===========================================================================
# Step 4 – Deep threshold sweep
# ===========================================================================
print("\nStep 4: Deep threshold sweep …")

deep_rows = []
for d in DEEP_SWEEP_VALUES:
    truth_deep = (aho >= d)
    m = binary_metrics(truth_deep, pred_deep)
    deep_rows.append({"threshold_m": d, **m})

deep_sweep_df = pd.DataFrame(deep_rows)
deep_csv = OUT_DIR / "deep_thres_sweep.csv"
deep_sweep_df.to_csv(deep_csv, index=False, float_format="%.4f")
print(f"  Deep sweep saved to: {deep_csv.relative_to(SCRIPT_DIR)}")


# ===========================================================================
# Step 5 – Very-shallow threshold sweep
# ===========================================================================
print("\nStep 5: Very-shallow threshold sweep …")

vs_rows = []
for d in VSHALLOW_SWEEP_VALUES:
    truth_vs = (aho <= d)
    m = binary_metrics(truth_vs, pred_very_shallow)
    vs_rows.append({"threshold_m": round(float(d), 2), **m})

vs_sweep_df = pd.DataFrame(vs_rows)
vs_csv = OUT_DIR / "vshallow_thres_sweep.csv"
vs_sweep_df.to_csv(vs_csv, index=False, float_format="%.4f")
print(f"  Very-shallow sweep saved to: {vs_csv.relative_to(SCRIPT_DIR)}")


# ===========================================================================
# Step 6 – Sweep plots (F1 only)
# ===========================================================================
print("\nStep 6: Generating sweep plots …")

# --- Deep F1 plot ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(deep_sweep_df["threshold_m"], deep_sweep_df["f1"],
        marker="o", linewidth=1.5, markersize=4, color="steelblue",
        label="F1 score (balance of recall and precision)")
ax.axvline(D_DEEP, color="tomato", linestyle="--", linewidth=1.5,
           label=f"Selected threshold: {D_DEEP} m")
ax.set_xlabel("Depth assigned to the deep reef class (m)", fontsize=11)
ax.set_ylabel("F1 score", fontsize=11)
ax.set_title(
    "What depth most aligns with the deep reef classification\n"
    "(Satellite class vs AHO marine chart depths)",
    fontsize=12)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.4)
deep_png = OUT_DIR / "deep_f1_vs_threshold.png"
fig.savefig(deep_png, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  Deep F1 plot saved to: {deep_png.relative_to(SCRIPT_DIR)}")

# --- Very-shallow F1 plot ---
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(vs_sweep_df["threshold_m"], vs_sweep_df["f1"],
        marker="o", linewidth=1.5, markersize=4, color="darkorange",
        label="F1 score (balance of recall and precision)")
ax.axvline(D_VS, color="tomato", linestyle="--", linewidth=1.5,
           label=f"Selected threshold: {D_VS} m")
ax.set_xlabel("Depth assigned to the very shallow reef class (m)", fontsize=11)
ax.set_ylabel("F1 score", fontsize=11)
ax.set_title(
    "What depth most aligns with the very shallow reef classification\n"
    "(Satellite class vs AHO marine chart depths)",
    fontsize=12)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.4)
vs_png = OUT_DIR / "vshallow_f1_vs_threshold.png"
fig.savefig(vs_png, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  Very-shallow F1 plot saved to: {vs_png.relative_to(SCRIPT_DIR)}")


# ===========================================================================
# Step 7 – Final 3-class evaluation at chosen thresholds
# ===========================================================================
print(f"\nStep 7: Final 3-class confusion matrix "
      f"(D_VS={D_VS} m, D_DEEP={D_DEEP} m) …")

CLASSES = ["very-shallow", "shallow", "deep"]

# Truth labels from AHO
truth_labels = aho_truth_classes(aho, D_VS, D_DEEP)

# Satellite predicted labels (one label per feature)
sat_labels = np.full(len(aho), "shallow", dtype=object)
sat_labels[pred_very_shallow] = "very-shallow"
sat_labels[pred_deep]         = "deep"
# Note: rows that are inconsistent (V_SHALLOW==1 AND deep eco) are handled by
# keeping the V_SHALLOW==1 rule dominant (pred_very_shallow applied last above
# for deep; since pred_deep is set first and pred_very_shallow overwrites).

# Build 3×3 confusion matrix
cm = pd.DataFrame(0, index=CLASSES, columns=CLASSES, dtype=int)
for t, p in zip(truth_labels, sat_labels):
    cm.loc[t, p] += 1

overall_acc = np.sum(truth_labels == sat_labels) / len(truth_labels)
print(f"  Overall accuracy: {overall_acc:.4f} ({overall_acc*100:.2f}%)")
print("\n  Confusion matrix (rows = AHO truth, cols = satellite prediction):")
print("  " + cm.to_string().replace("\n", "\n  "))

# Save confusion matrix + accuracy
x_str = str(D_VS).rstrip("0").rstrip(".")
y_str = str(int(D_DEEP)) if float(D_DEEP).is_integer() else str(D_DEEP)
cm_csv = OUT_DIR / f"confusion_multiclass_{x_str}_{y_str}_thres.csv"

cm_out = cm.copy()
cm_out.index.name = "truth \\ predicted"
# Append overall accuracy as a separate row
acc_row = pd.Series(
    [overall_acc] + [""] * (len(CLASSES) - 1),
    index=CLASSES, name="overall_accuracy")
cm_export = pd.concat([cm_out, acc_row.to_frame().T])
cm_export.to_csv(cm_csv, float_format="%.4f")
print(f"\n  Confusion matrix saved to: {cm_csv.relative_to(SCRIPT_DIR)}")


# ===========================================================================
# Step 8 – AHO uncertainty sensitivity (self-consistency)
# ===========================================================================
print(f"\nStep 8: AHO self-consistency sensitivity "
      f"(N={N_REPS} reps, seed={MC_SEED}) …")
print("  This may take a few seconds …")

np.random.seed(MC_SEED)
z = aho.copy()

# Per-feature σ: sqrt(0.25² + (0.02·z)²)
sigma = np.sqrt(0.25**2 + (0.02 * z)**2)

# Baseline truth classes
baseline_labels = aho_truth_classes(z, D_VS, D_DEEP)

rep_records = []
for rep in range(N_REPS):
    eps        = np.random.normal(0.0, sigma)      # independent per feature
    z_perturb  = z + eps
    pert_labels = aho_truth_classes(z_perturb, D_VS, D_DEEP)

    overall_rep = np.mean(pert_labels == baseline_labels)

    # Per-class flip rates (fraction of that class that changed label)
    flip_rates = {}
    for cls in CLASSES:
        mask = baseline_labels == cls
        flip_rates[f"flip_rate_{cls.replace('-', '_')}"] = (
            float(np.mean(pert_labels[mask] != baseline_labels[mask]))
            if mask.sum() > 0 else np.nan
        )

    rep_records.append({"replicate": rep + 1,
                        "overall_accuracy": overall_rep,
                        **flip_rates})

    if (rep + 1) % 200 == 0:
        print(f"    … completed {rep + 1}/{N_REPS} repetitions")

mc_df = pd.DataFrame(rep_records)

mean_acc  = mc_df["overall_accuracy"].mean()
ci_half   = 1.96 * mc_df["overall_accuracy"].std() / np.sqrt(N_REPS)
ci_lo     = mean_acc - ci_half
ci_hi     = mean_acc + ci_half

print(f"\n  Self-consistency accuracy:  {mean_acc:.4f} "
      f"({mean_acc*100:.2f}%)")
print(f"  95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]  "
      f"[{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]")

# Mean flip rates by class
for cls in CLASSES:
    col = f"flip_rate_{cls.replace('-', '_')}"
    mean_flip = mc_df[col].mean()
    print(f"  Mean flip rate ({cls:15s}): {mean_flip:.4f} "
          f"({mean_flip*100:.2f}%)")

overall_flip = 1.0 - mean_acc
print(f"  Mean overall flip rate     : {overall_flip:.4f} "
      f"({overall_flip*100:.2f}%)")

# Build summary row
summary_row = {
    "replicate": "SUMMARY",
    "overall_accuracy": mean_acc,
}
for cls in CLASSES:
    col = f"flip_rate_{cls.replace('-', '_')}"
    summary_row[col] = mc_df[col].mean()
# summary_row["mean_accuracy"]  = mean_acc
# summary_row["ci_95_lo"]       = ci_lo
# summary_row["ci_95_hi"]       = ci_hi

mc_export = pd.concat(
    [mc_df, pd.DataFrame([summary_row])],
    ignore_index=True)

sc_csv = OUT_DIR / f"aho_self_consistency_{x_str}_{y_str}_thres.csv"
mc_export.to_csv(sc_csv, index=False, float_format="%.4f")
print(f"\n  Self-consistency results saved to: {sc_csv.relative_to(SCRIPT_DIR)}")


# ===========================================================================
# Summary
# ===========================================================================
print("\n" + "=" * 60)
print("All outputs written to:", OUT_DIR.relative_to(SCRIPT_DIR))
print("  deep_thres_sweep.csv")
print("  vshallow_thres_sweep.csv")
print("  deep_f1_vs_threshold.png")
print("  vshallow_f1_vs_threshold.png")
print(f"  confusion_multiclass_{x_str}_{y_str}_thres.csv")
print(f"  aho_self_consistency_{x_str}_{y_str}_thres.csv")
print("\nDone.")
