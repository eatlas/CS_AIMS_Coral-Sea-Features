#!/usr/bin/env python3
"""
This script calculates the average area of the Cays-over-time features and assigns that value
to the corresponding cay features in the Reef-Cays shapefile via a spatial join based on intersection.
For non-cay (i.e. reef) features in Reef-Cays the new attribute (AvArea_km2) is set equal to the existing Area_km2.
If a Cays-over-time feature does not intersect any cay (i.e. a stray fragment), a warning is printed and processing continues.
This updated version also accounts for cases where a single cay area is split into multiple polygons.
In that case, Cays-over-time features with the same ReefID and IMG_DATE are grouped together and their areas summed
to represent the full observation before calculating the average area.
The script writes updated versions of both the Reef-Cays and Cays-over-time shapefiles to the working folder.

Requirements:
  - geopandas
  - shapely
  - pyproj
  - fiona
"""

import os
import sys
import geopandas as gpd
from version import VERSION

# Define file paths (note the updated path for Reef-Cays)
reefs_cays_fp = f"data/{VERSION}/Reefs-Cays/CS_AIMS_Coral-Sea-Features_2025_Reefs-cays.shp"
cays_over_time_fp = f"data/{VERSION}/extra/Cays-over-time/CS_AIMS_Coral-Sea-Features_2025_Cays-over-time_2014-2023.shp"

# Define EPSG codes
source_crs = "EPSG:4326"
area_crs = "EPSG:3112"  # For accurate area calculation

# Define output folder and filenames
output_folder = "working"
output_reefs_cays_fp = os.path.join(output_folder, "CS_AIMS_Coral-Sea-Features_2025_Reefs-cays.shp")
output_cays_ot_fp = os.path.join(output_folder, "CS_AIMS_Coral-Sea-Features_2025_Cays-over-time_2014-2023.shp")

def main():
    # Create working folder if it doesn't exist
    if not os.path.exists(output_folder):
        print(f"Creating output folder: {output_folder}")
        os.makedirs(output_folder, exist_ok=True)
    
    print("Loading Reef-Cays shapefile...")
    try:
        gdf_reefs = gpd.read_file(reefs_cays_fp)
    except Exception as e:
        print(f"Error loading Reef-Cays shapefile: {e}")
        sys.exit(1)
    print(f"Loaded Reef-Cays shapefile with {len(gdf_reefs)} features.")
    
    print("Loading Cays-over-time shapefile...")
    try:
        gdf_cays_ot = gpd.read_file(cays_over_time_fp)
    except Exception as e:
        print(f"Error loading Cays-over-time shapefile: {e}")
        sys.exit(1)
    print(f"Loaded Cays-over-time shapefile with {len(gdf_cays_ot)} features.")
    
    # Filter Reef-Cays to select only the cay features based on RB_Type_L1 == 'Land'
    print("Filtering Reef-Cays to extract cay features (RB_Type_L1 == 'Land')...")
    gdf_reefs_cays = gdf_reefs[gdf_reefs["RB_Type_L1"] == "Land"].copy()
    print(f"Found {len(gdf_reefs_cays)} cay features in Reef-Cays.")
    
    # Reproject both datasets to EPSG:3112 for accurate area and intersection calculations
    print("Reprojecting filtered Reef-Cays (cays) to EPSG:3112...")
    gdf_reefs_cays_proj = gdf_reefs_cays.to_crs(area_crs)
    
    print("Reprojecting Cays-over-time to EPSG:3112...")
    gdf_cays_ot_proj = gdf_cays_ot.to_crs(area_crs)
    
    # Assign ReefID to each Cays-over-time feature using spatial join with intersection,
    # choosing the cay with the largest overlapping area.
    print("Assigning ReefID to each Cays-over-time feature via spatial join (largest intersection area)...")
    assigned_reef_ids = []  # To store the assigned ReefID for each Cays-over-time feature
    
    # Iterate over each Cays-over-time feature
    for idx, ot_row in gdf_cays_ot_proj.iterrows():
        # Find candidate cay features that intersect the current Cays-over-time geometry
        candidates = gdf_reefs_cays_proj[gdf_reefs_cays_proj.intersects(ot_row.geometry)]
        
        if candidates.empty:
            img_date = ot_row.get("IMG_DATE", "N/A")
            print(f"Warning: Cays-over-time feature at index {idx} (IMG_DATE: {img_date}) did not intersect any cay from Reef-Cays.")
            assigned_reef_ids.append(None)
            continue
        
        # If multiple candidates, compute the intersection area for each and choose the one with maximum area
        max_int_area = 0
        selected_reef_id = None
        for cand_idx, cand_row in candidates.iterrows():
            intersection = ot_row.geometry.intersection(cand_row.geometry)
            int_area = intersection.area  # area in square meters (EPSG:3112)
            if int_area > max_int_area:
                max_int_area = int_area
                selected_reef_id = cand_row["ReefID"]
        if selected_reef_id is None:
            img_date = ot_row.get("IMG_DATE", "N/A")
            print(f"Warning: No valid intersection found for Cays-over-time feature at index {idx} (IMG_DATE: {img_date}).")
        assigned_reef_ids.append(selected_reef_id)
    
    # Add the assigned ReefID to the Cays-over-time projected GeoDataFrame
    gdf_cays_ot_proj["ReefID"] = assigned_reef_ids
    # Calculate the area in km² for each Cays-over-time feature using EPSG:3112
    gdf_cays_ot_proj["Area_km2"] = gdf_cays_ot_proj.geometry.area / 1e6  # convert m^2 to km^2
    print("Assigned ReefID and calculated area for all Cays-over-time features.")
    
    # Group by ReefID and IMG_DATE to account for multi-part cay observations.
    # For each combination, sum the areas (i.e. all parts together form one observation).
    print("Grouping Cays-over-time features by ReefID and IMG_DATE and summing areas...")
    valid_ot = gdf_cays_ot_proj[gdf_cays_ot_proj["ReefID"].notnull()].copy()
    grouped = valid_ot.groupby(["ReefID", "IMG_DATE"])["Area_km2"].sum().reset_index()
    
    # Then, compute the average area for each ReefID over all observations (IMG_DATE groups).
    print("Calculating average area (AvArea_km2) for each cay based on grouped observations...")
    avg_area_by_reefid = grouped.groupby("ReefID")["Area_km2"].mean().to_dict()
    
    print("Average areas calculated for the following ReefIDs:")
    for reef_id, avg_area in avg_area_by_reefid.items():
        print(f"  ReefID {reef_id}: {avg_area:.4f} km²")
    
    # Add the new field AvArea_km2 to the original Reef-Cays GeoDataFrame.
    # For cay features (RB_Type_L1 == 'Land'), use the average area from Cays-over-time if available;
    # otherwise, use the existing Area_km2 and print a warning.
    print("Assigning AvArea_km2 values to Reef-Cays features...")
    def assign_av_area(row):
        if row["RB_Type_L1"] == "Land":
            reef_id = row["ReefID"]
            if reef_id in avg_area_by_reefid:
                return avg_area_by_reefid[reef_id]
            else:
                print(f"Warning: Cay feature with ReefID {reef_id} did not receive an average area; using existing Area_km2.")
                return row["Area_km2"]
        else:
            return row["Area_km2"]
    
    gdf_reefs["AvArea_km2"] = gdf_reefs.apply(assign_av_area, axis=1)
    print("AvArea_km2 assigned for all Reef-Cays features.")
    
    # Save updated datasets to the working folder
    print(f"Saving updated Reef-Cays shapefile to {output_reefs_cays_fp}...")
    try:
        gdf_reefs.to_file(output_reefs_cays_fp)
    except Exception as e:
        print(f"Error writing updated Reef-Cays shapefile: {e}")
        sys.exit(1)
    
    # For Cays-over-time, reproject back to the original CRS (EPSG:4326) before saving for review.
    print("Reprojecting updated Cays-over-time back to original CRS for saving...")
    gdf_cays_ot_updated = gdf_cays_ot_proj.to_crs(source_crs)
    print(f"Saving updated Cays-over-time shapefile to {output_cays_ot_fp}...")
    try:
        gdf_cays_ot_updated.to_file(output_cays_ot_fp)
    except Exception as e:
        print(f"Error writing updated Cays-over-time shapefile: {e}")
        sys.exit(1)
    
    print("Script completed successfully.")

if __name__ == "__main__":
    main()
