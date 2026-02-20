*(for script: `07-sat-depth-class-vs-aho.py` run from VS Code)*

## 0) **Background & Goal**

This workflow formalises how satellite‑derived reef “detectability classes” are calibrated against **Australian Hydrographic Office (AHO)** charted depths. The source workbook analysis used **two spectral detectability cues**:

*   **Very‑shallow reefs**: detectable in a **contrast‑enhanced red band** (encoded in the dataset as a binary `V_SHALLOW` flag).
*   **Deep (mesophotic) reefs**: detectable in a **contrast‑enhanced green band**; in the attribute table this appears as **“Oceanic mesophotic coral reefs”** in `NVCL_Eco`. Shallow (but not “very‑shallow”) reefs appear as **“Oceanic shallow coral reefs”** in `NVCL_Eco`. `NVCL_Eco` does not include a “very shallow” label, so very‑shallow is identified exclusively by `V_SHALLOW`.

Only reefs that have an AHO depth were used for calibration; the working dataset (shapefile below) has already been **prefiltered to 880 features** with `AHO_DEPTH` present.

This analysis was performed during stage 9 of the development. This means that there are slight variations between the boundaries of some of the reefs in the input reef datasets and the final mapping. These boundary difference do not affect this analysis.

The workflow:

1.  **Applies candidate depth thresholds** for the *deep* and *very‑shallow* categories to generate AHO‑based “truth” labels.
2.  **Computes per‑class metrics** (one‑vs‑rest) across sweeps of those thresholds using the satellite‑based predictions from `NVCL_Eco` and `V_SHALLOW`.
3.  Lets the analyst **choose thresholds** (by inspecting F1 vs threshold). This will be just a specied threshold for deep and one for very shallow as constants in the script. The analyst can adjust the thresholds after running the script once to review the sweeps.
4.  Produces a **final 3×3 confusion matrix** at the specified final thresholds.
5.  Performs an **AHO uncertainty sensitivity** by perturbing AHO depths according to the provided rule and quantifies the **resulting self‑consistency accuracy**.
6.  Outputs CSVs and figures to `working/07/` with the specified naming.

## 1) **Inputs**

*   **Vector data (prefiltered to 880 features):**  
    `data/v1-2/extra/Depth-class-assessment/CS-Features-Satellite-depth-class-vs-AHO.shp`  
    Required attributes:
    *   `AHO_DEPTH` (float; metres; reef‑top depth from AHO chart; **positive‑down convention**: deeper reefs have larger positive values)
    *   `ID` (unique identifier - initial temporary ID assigned during stage 9 of development)
    *   `NVCL_Eco` (string; **“Oceanic mesophotic coral reefs”** for deep; **“Oceanic shallow coral reefs”** for shallow or very‑shallow)
    *   `V_SHALLOW` (int; **1**=very‑shallow; **0**=not very‑shallow)
    *   `ReefID` (string or int; Final ReefID assigned to these features. This is to allow cross referencing with the final dataset.)  
        (Rows are already limited to those with `AHO_DEPTH` present; no additional filtering is required.)

*   **Environment** (Conda env available):
    *   `python=3.13.1`, `geopandas=1.0.1`, `shapely=2.0.7`, `gdal=3.10.2` (for reading the shapefile); `matplotlib` is recommended for plots. 

## 2) **Predicted classes from satellite attributes (fixed rules)**

Per feature, form **satellite predicted classes**:

*   **Predicted very‑shallow:** `V_SHALLOW == 1`.
*   **Predicted deep (mesophotic):** `NVCL_Eco == "Oceanic mesophotic coral reefs"`.
*   **Predicted shallow:** `NVCL_Eco == "Oceanic shallow coral reefs" AND V_SHALLOW == 0`.

Additionally, ensure the **consistency rule** holds: if `V_SHALLOW == 1` then `NVCL_Eco` should be “Oceanic shallow coral reefs”; otherwise flag as inconsistent for QA (but keep the row—do not drop). This should be an assertion in the code.


## 3) **Truth labels from AHO depths (threshold‑based)**

Define **two scalar thresholds** to partition AHO depths:

*   **Very‑shallow threshold (`D_vs`)**: metres; reefs with `AHO_DEPTH ≤ D_vs` are considered very‑shallow.
*   **Deep threshold (`D_deep`)**: metres; reefs with `AHO_DEPTH ≥ D_deep` are considered deep (mesophotic).
*   **Shallow** is the **middle band**: `D_vs < AHO_DEPTH < D_deep`.

For **threshold sweeps** we test multiple values (see §5). The analysis will **select** final thresholds manually from the sweep results; the script will **not auto‑pick**.

## 4) **Metrics**

### 4.1 One‑vs‑rest metrics (used during threshold sweeps)

For each class **C ∈ {very‑shallow, deep}** and for each tested threshold value:

*   Build **truth\_C** from AHO using the threshold rule above (binary: class C vs not C).
*   Use the **predicted\_C** derived from satellite attributes (binary).
*   Compute **TP, TN, FP, FN** and:
    *   **Precision** = TP / (TP + FP)
    *   **Recall** = TP / (TP + FN)
    *   **F1** = 2 × Precision × Recall / (Precision + Recall)
    *   **Accuracy** = (TP + TN) / (TP + TN + FP + FN)

You requested to **use F1** as the criterion when reviewing sweeps; the sweeps will therefore **plot F1 only** (CSV still includes all metrics for completeness).

### 4.2 Final multiclass metrics (after you pick thresholds)

Given your selected `D_vs` and `D_deep`, transform AHO depths to **three truth classes** and compare with the 3‑way satellite predictions to produce a **3×3 confusion matrix** and **overall multiclass accuracy** (proportion of exact matches).

## 5) **Threshold sweeps**

### 5.1 Deep (mesophotic) sweep

*   Test `D_deep` across **10 m to 40 m** in **1 m** steps (i.e., 10, 11, …, 40). 

### 5.2 Very‑shallow sweep

*   Test `D_vs` across **0 m to +5.0 m**. Use **0.2 m** step for fine resolution (i.e., 0.0, 0.2, 0.4, …, 5.0). 

For each sweep point, compute **one‑vs‑rest** metrics for the corresponding class (see §4.1). Save results as CSVs and produce **F1‑only** plots (see §8).

## 6) **AHO uncertainty sensitivity (self‑consistency test)**

We estimate the accuracy of the satellite derived reef top depth classifcation by comparing them against the AHO Marine charts (assuming these are accurate), i.e. the Threshold sweeps. We then estimate the accuracy of the AHO Marine Chart classifications by assuming that the depth changes by the 95% range for ZOC B and see if the classification changes. This a comparison between the quoted depth value of the AHO depths vs a nose perturbed version of the AHO depths (using the state ZOC B accuracy), assuming the specified depth thresholds. This tells us the upper bound in the accuracy that we could expect from the satellite classification to the chart depths. 

**Given:** “Randomly perturb the AHO by **0.5 m (2 SD)** + **2% of depth**.”  
Interpretation for each feature with original `AHO_DEPTH = z`:

*   **Random perturbation** `ε ~ Normal(0, σ(z)^2)` with  
    `σ(z) = sqrt( (0.25)^2 + (0.02·z)^2 )` if “0.5 m (2 SD)” is interpreted as **±0.5 m at 95%** (i.e., 2σ ≈ 0.5 ⇒ σ ≈ 0.25 m), plus a relative component 2%·z combined in quadrature.
*   Create **perturbed depth** `z' = z + ε`. No clamping is applied (perturbed depths may become negative)

**Computation at your chosen thresholds (`D_vs`, `D_deep`):**

1. Convert baseline AHO to three truth classes using chosen thresholds (reference labels)
2. For each of N=1,000 repetitions: independently dither all 880 depths (one ε per feature per repetition), re-classify using same thresholds, compare perturbed labels to baseline labels, record overall accuracy
3. Across N repetitions: compute mean accuracy ± 95% CI, and mean fraction of label flips by class and overall

Use a fixed random seed (e.g., np.random.seed(42)) for reproducibility.

This answers: *“Given AHO’s uncertainty, how stable are the class labels at these thresholds?”* The result contextualises satellite‑vs‑AHO scores. (Your earlier instruction: “what is the accuracy when we just compare the AHO with a noisy version of itself.”)

## 7) **Processing Steps (end‑to‑end)**

1.  **Load data** with GeoPandas from the shapefile path (no filtering required; already 880 records). Confirm presence and types of required fields.
2.  **Build predicted classes** per §2 and flag any `V_SHALLOW==1` rows where `NVCL_Eco != "Oceanic shallow coral reefs"` as **inconsistent** (QA column).
3.  **Sweep deep threshold**: for each `D_deep ∈ {10…40}`
    *   Truth binary: `AHO_DEPTH ≥ D_deep`.
    *   Pred binary: **deep** (from `NVCL_Eco`).
    *   Compute TP/TN/FP/FN; Precision, Recall, F1, Accuracy.
    *   Append to deep sweep table.
4.  **Sweep very‑shallow threshold**: for each `D_vs ∈ {0…5.0 step 0.2}`
    *   Truth binary: `AHO_DEPTH ≤ D_vs`.
    *   Pred binary: **very‑shallow** (`V_SHALLOW==1`).
    *   Compute the same metrics; append to very‑shallow sweep table.
5.  **Write sweep CSVs** to `working/07/` (see §8 filenames). Also **generate two PNG plots** (F1 vs threshold). x axis labels 'Depth assigned to the deep reef class (m)', 'Depth assigned to the very shallow reef class (m)'. Titles: 'What depth most aligns with the deep reef classification (Satellite class vs AHO marine chart depths)', 'What depth most aligns with the very shallow reef classification (Satellite class vs AHO marine chart depths)'
Legend label: 'F1 score (balance of recall and precision)'

6.  **Select thresholds** by inspecting F1 sweeps (manual decision). Record chosen values as `x=D_vs`, `y=D_deep`. The script will start with D_vs = 2.5 and D_deep = 25.
7.  **Final 3‑class evaluation at (x, y)**
    *   Truth class from AHO using (x, y):
        *   Very‑shallow: `AHO_DEPTH ≤ x`
        *   Deep: `AHO_DEPTH ≥ y`
        *   Shallow: otherwise
    *   Predicted class from satellite per §2.
    *   Produce **3×3 confusion matrix** and overall accuracy. Save to CSV (see §8).
8.  **AHO uncertainty sensitivity** at (x, y) per §6 (N=1,000 repetitions × 880 features per repetition); report the **self‑consistency accuracy** and label‑flip rates to CSV.
9.  **Print processing progress** The script should print progress statements to standard out.

## 8) **Outputs & Naming**

Write all outputs to: **`working/07/`** (relative to the script location).

1.  **Sweeps (CSV):**
    *   Deep: `deep_thres_sweep.csv` (columns: `threshold_m`, `TP`, `TN`, `FP`, `FN`, `precision`, `recall`, `f1`, `accuracy`).
    *   Very‑shallow: `vshallow_thres_sweep.csv` (same columns).

2.  **Final confusion (CSV):**
    *   `confusion_multiclass_{x}_{y}_thres.csv`  where `{x}` = chosen very‑shallow threshold (e.g., `2.5`) and `{y}` = chosen deep threshold (e.g., `25`). Contains the **3×3 confusion matrix** (rows = truth / AHO‑based classes; columns = predicted / satellite‑based classes; row and column order: very‑shallow, shallow, deep) and **overall accuracy**.

3.  **AHO uncertainty sensitivity (CSV):**
    *   `aho_self_consistency_{x}_{y}_thres.csv` with columns: `replicate`, `overall_accuracy`, and (optionally) class‑wise flip rates; plus a one‑row summary with mean/CI.

4.  **Figures (PNG, F1‑only; 10 × 6 inches, 150 DPI):**
    *   `deep_f1_vs_threshold.png` (F1 vs `D_deep`, with selected `y` marked).
    *   `vshallow_f1_vs_threshold.png` (F1 vs `D_vs`, with selected `x` marked).

## 9) **Quality Checks**

*   **Field validation:** assert required columns exist; confirm `V_SHALLOW` ∈ {0,1}. Count and list any inconsistencies `(V_SHALLOW==1) ∧ (NVCL_Eco!="Oceanic shallow coral reefs")`.
*   **Row count sanity:** confirm **880** features loaded (as per the prefiltered shapefile).
*   **Metric sanity:** at extreme thresholds the F1 curves should degrade (e.g., very high `D_deep` reduces recall)

## 10) **Documentation to include in the script header (suggested)**

*   Brief description of red/green detectability → class mapping (as above).
*   Statement that **only AHO‑depth features** are analysed (880 rows in this dataset).
*   Explanation of **threshold‑based truth**, **one‑vs‑rest sweeps using F1**, and **final 3×3 confusion** at selected thresholds.
*   Description of the **AHO self‑consistency** test and parameterisation of the perturbation model (0.5 m (2 SD) + 2% depth).
*   Reproducibility details: input path, output folder, dependency versions.

