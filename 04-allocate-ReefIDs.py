"""
python 02-allocate-ReefIDs.py --base B10 ../working/CS_AIMS_Coral-Sea-Features_2024_Reefs-cays.shp ../out-data/Reefs-Cays/CS_AIMS_Coral-Sea-Features_2024_Reefs-cays.shp R
python 02-allocate-ReefIDs.py --base B10 ../working/CS_AIMS_Coral-Sea-Features_2024_Atoll-platforms.shp ../out-data/Atoll-Platforms/CS_AIMS_Coral-Sea-Features_2024_Atoll-platforms.shp A 2

This will allocate IDs to reefs such as R-9140-1724 and A-9140-12

This will only allocate IDs to features that don't already have an ID allocated. It will not override existing IDs.
"""
import geopandas as gpd
import argparse
import pandas as pd
from shapely.geometry import Polygon

# Constants - We have multiple base options to allow testing various schemes.
BASE_B32_CAPS = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
BASE_B32_LOWER = '23456789abcdefghjklmnpqrstuvwxyz'
BASE_B10 = '0123456789'
BASE_B16 = '0123456789ABCDEF'
BASE_B14 = '23456789ABCDEF'

BASE_CHAR_SETS = {
    'B32_CAPS': BASE_B32_CAPS,
    'B32_LOWER': BASE_B32_LOWER,
    'B10': BASE_B10,
    'B16': BASE_B16,
    'B14': BASE_B14
}

# Default base character set
base_char_set = BASE_B10
encoding_base = len(base_char_set)

LON_SLICE_SIZE = 360 / encoding_base
LAT_SLICE_SIZE = 180 / encoding_base

def encode_base_str(value):
    return base_char_set[value]

def decode_base_str(char):
    return base_char_set.index(char)

"""
Encode grid location as two digits. The fineness of the grid is determined by the 
base of the encoding. For example in base 10, two digits gives 100 combinations and
so the grid is 360/100 = 3.6 degress longitude by 180/100 = 1.8 degree of latitude.
"""
def encode_grid(lon, lat):

    lon = lon + 180
    lat = lat + 90
    
    lon_major = int(lon // LON_SLICE_SIZE)
    lat_major = int(lat // LAT_SLICE_SIZE)
    lon_sub = int((lon % LON_SLICE_SIZE) // (LON_SLICE_SIZE / encoding_base))
    lat_sub = int((lat % LAT_SLICE_SIZE) // (LAT_SLICE_SIZE / encoding_base))
    
    return f"{encode_base_str(lon_major)}{encode_base_str(lon_sub)}{encode_base_str(lat_major)}{encode_base_str(lat_sub)}"

def encode_counter(counter, zero_padding):
    encoded = ''
    while counter > 0:
        encoded = base_char_set[counter % encoding_base] + encoded
        counter //= encoding_base
    while len(encoded) < zero_padding:
        encoded = base_char_set[0] + encoded  # Add padding with '2' (the 0th character in Compact B32)
    return encoded

def decode_counter(encoded_counter):
    counter = 0
    for char in encoded_counter:
        counter = counter * encoding_base + decode_base_str(char)
    return counter

def process_shapefile(input_path, output_path, prefix, zero_padding):
    # Load the shapefile
    print("Loading the shapefile...")
    gdf = gpd.read_file(input_path)

    # Check if 'ReefID' column exists
    if 'ReefID' not in gdf.columns:
        print("'ReefID' column not found. Adding 'ReefID' column...")
        gdf['ReefID'] = None

    # Ensure geometries are in EPSG:4326
    gdf = gdf.to_crs(epsg=4326)

    # Initialize dictionaries to store grid-based feature counts and existing ReefIDs for each prefix
    grid_feature_count = {}
    grid_existing_ids = {}

    # Process existing ReefIDs
    print("Processing existing ReefIDs...")
    for idx, row in gdf.iterrows():
        if pd.notna(row['ReefID']):
            reef_id = row['ReefID']
            existing_prefix, grid_scheme, feature_counter = reef_id.split('-')
            
            if existing_prefix not in grid_existing_ids:
                grid_existing_ids[existing_prefix] = {}
                grid_feature_count[existing_prefix] = {}
            
            if grid_scheme not in grid_existing_ids[existing_prefix]:
                grid_existing_ids[existing_prefix][grid_scheme] = set()
            grid_existing_ids[existing_prefix][grid_scheme].add(feature_counter)

            if grid_scheme not in grid_feature_count[existing_prefix]:
                grid_feature_count[existing_prefix][grid_scheme] = 0
            grid_feature_count[existing_prefix][grid_scheme] = max(
                grid_feature_count[existing_prefix][grid_scheme], decode_counter(feature_counter) + 1)

    # Create a new column for centroid sum (latitude + longitude) in EPSG:4326
    gdf['centroid'] = gdf.geometry.centroid
    gdf['centroid_sum'] = gdf['centroid'].apply(lambda geom: geom.x + geom.y)

    # Generate new ReefIDs for features without one, sorting by centroid sum
    print("Generating new ReefIDs for features without one...")
    grid_schemes = gdf['centroid'].apply(lambda geom: encode_grid(geom.x, geom.y))
    for grid_scheme in grid_schemes.unique():
        sub_gdf = gdf[grid_schemes == grid_scheme].sort_values(by='centroid_sum')
        
        for idx, row in sub_gdf.iterrows():
            if pd.isna(row['ReefID']):
                if prefix not in grid_feature_count:
                    grid_feature_count[prefix] = {}
                    grid_existing_ids[prefix] = {}
                
                if grid_scheme not in grid_feature_count[prefix]:
                    grid_feature_count[prefix][grid_scheme] = 0

                new_counter = grid_feature_count[prefix][grid_scheme]
                encoded_counter = encode_counter(new_counter, zero_padding)

                while grid_scheme in grid_existing_ids[prefix] and encoded_counter in grid_existing_ids[prefix][grid_scheme]:
                    new_counter += 1
                    encoded_counter = encode_counter(new_counter, zero_padding)
                
                new_reef_id = f"{prefix}-{grid_scheme}-{encoded_counter}"
                print(f"Assigned ReefID {new_reef_id} to feature at index {idx}")
                gdf.at[idx, 'ReefID'] = new_reef_id
                grid_feature_count[prefix][grid_scheme] = new_counter + 1

    # Drop the temporary columns
    gdf.drop(columns=['centroid', 'centroid_sum'], inplace=True)

    # Save the updated shapefile
    print(f"Saving the updated shapefile to {output_path}...")
    gdf.to_file(output_path)

    print("Processing complete.")

def run_tests():
    print("Running tests...")
    test_cases = [
        (147, -20, 'XE4G')  # Corrected example
    ]

    for lon, lat, expected in test_cases:
        result = encode_grid(lon, lat)
        assert result == expected, f"Test failed for ({lon}, {lat}): Expected {expected}, got {result}"
    
    print("All tests passed!")

def main():
    parser = argparse.ArgumentParser(description="Generate ReefIDs for a shapefile.")
    parser.add_argument("input", nargs="?", help="Path to the input shapefile")
    parser.add_argument("output", nargs="?", help="Path to the output shapefile")
    parser.add_argument("prefix", nargs="?", default='R', help="Prefix for the ReefID")
    parser.add_argument("zero_padding", nargs="?", type=int, default='3', help="Zero padding for the feature counter")
    parser.add_argument("--base", choices=BASE_CHAR_SETS.keys(), default='B10', help="Base character set for encoding")
    parser.add_argument("--test", action="store_true", help="Run tests and exit")

    args = parser.parse_args()

    # Set the base character set based on the argument
    global base_char_set, encoding_base, LON_SLICE_SIZE, LAT_SLICE_SIZE
    base_char_set = BASE_CHAR_SETS[args.base]
    encoding_base = len(base_char_set)
    LON_SLICE_SIZE = 360 / encoding_base
    LAT_SLICE_SIZE = 180 / encoding_base

    if args.test:
        run_tests()
    else:
        if not all([args.input, args.output, args.prefix, args.zero_padding]):
            parser.error("the following arguments are required: input, output, prefix, zero_padding")
        process_shapefile(args.input, args.output, args.prefix, args.zero_padding)

if __name__ == "__main__":
    main()
