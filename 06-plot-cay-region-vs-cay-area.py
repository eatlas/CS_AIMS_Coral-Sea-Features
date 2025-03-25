#!/usr/bin/env python3
"""
Script: plot_cay_area_fraction.py

Description:
    This script loads the Reef-Cays shapefile from "data/Reefs-Cays/CS_AIMS_Coral-Sea-Features_2025_Reefs-cays.shp"
    and filters the data to include only cay features (where RB_Type_L1 == "Land"). It then computes a fraction
    value for each feature as: fraction = AvArea_km2 / Area_km2.
    
    Two boxplots are generated:
      1. The distribution of the fraction grouped by the Stability attribute (ordered as:
         Ephemeral, Very low, Low, Medium, High, Very high).
      2. The distribution of the fraction for RB_Type_L3, limited to "Unvegetated Cay" vs "Vegetated Cay",
         with the title "Average cay area as fraction of Cay region boundary".
    
    The resulting plots are saved in the folder "data/figures" (which is created if it does not exist).
    The saved plots have a DPI of 200.
    
Requirements:
    - geopandas
    - matplotlib
    - numpy
"""

import os
import sys
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

def main():
    # Define input file path
    fp = "working/CS_AIMS_Coral-Sea-Features_2025_Reefs-cays.shp"
    
    # Load the Reef-Cays shapefile
    print("Loading Reef-Cays shapefile...")
    try:
        gdf = gpd.read_file(fp)
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        sys.exit(1)
    print(f"Loaded shapefile with {len(gdf)} features.")
    
    # Filter to include only cay features (RB_Type_L1 == "Land")
    gdf = gdf[gdf["RB_Type_L1"] == "Land"].copy()
    print(f"Filtered shapefile to {len(gdf)} cay features (RB_Type_L1 == 'Land').")
    
    # Check that the required fields are present
    if "AvArea_km2" not in gdf.columns or "Area_km2" not in gdf.columns:
        print("Error: Required fields 'AvArea_km2' or 'Area_km2' not found in the shapefile.")
        sys.exit(1)
    
    # Compute the fraction for each feature
    # (using np.nan if Area_km2 is zero to avoid division by zero)
    gdf["fraction"] = gdf.apply(lambda row: row["AvArea_km2"] / row["Area_km2"] if row["Area_km2"] != 0 else np.nan, axis=1)
    
    # Create the output folder for figures if it does not exist
    output_fig_folder = "data/figures"
    if not os.path.exists(output_fig_folder):
        print(f"Creating output folder for figures: {output_fig_folder}")
        os.makedirs(output_fig_folder, exist_ok=True)
    
    # ================= Plot 1: Fraction by Stability =================
    # Only include records with non-null fraction and a valid Stability value.
    stability_data = gdf.dropna(subset=["fraction", "Stability"])
    
    # Define the desired order for Stability categories.
    desired_order = ["Ephemeral", "Very low", "Low", "Medium", "High", "Very high"]
    # Only include categories that are present in the data.
    stability_keys = [cat for cat in desired_order if cat in stability_data["Stability"].unique()]
    
    # Group the fraction values by Stability using the defined order.
    stability_groups = stability_data.groupby("Stability")["fraction"].apply(list)
    data_to_plot = [stability_groups[cat] for cat in stability_keys]
    
    plt.figure()
    plt.boxplot(data_to_plot, labels=stability_keys)
    plt.xlabel("Stability")
    plt.ylabel("Fraction (AvArea_km2 / Area_km2)")
    plt.title("Average Cay Area as fraction of Cay Region boundary by Stability")
    fig1_path = os.path.join(output_fig_folder, "fraction_by_stability.png")
    plt.savefig(fig1_path, dpi=200)
    plt.close()
    print(f"Saved plot of fraction by Stability to {fig1_path}")
    
    # ================= Plot 2: Fraction by RB_Type_L3 (Unvegetated vs Vegetated Cay) =================
    # Filter for RB_Type_L3 values of interest
    type_data = gdf[gdf["RB_Type_L3"].isin(["Unvegetated Cay", "Vegetated Cay"])].dropna(subset=["fraction"])
    
    # Group the fraction values by RB_Type_L3
    type_groups = type_data.groupby("RB_Type_L3")["fraction"].apply(list)
    # We'll order alphabetically here, but if a custom order is desired you can specify it.
    type_keys = sorted(type_groups.index.tolist())
    data_to_plot2 = [type_groups[key] for key in type_keys]
    
    plt.figure()
    plt.boxplot(data_to_plot2, labels=type_keys)
    plt.xlabel("RB_Type_L3")
    plt.ylabel("Fraction (AvArea_km2 / Area_km2)")
    plt.title("Average Cay Area as fraction of Cay region boundary by Vegetation")
    fig2_path = os.path.join(output_fig_folder, "fraction_by_RB_Type_L3.png")
    plt.savefig(fig2_path, dpi=200)
    plt.close()
    print(f"Saved plot of fraction by RB_Type_L3 to {fig2_path}")

if __name__ == "__main__":
    main()
