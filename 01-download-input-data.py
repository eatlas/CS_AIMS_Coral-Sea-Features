from data_downloader import DataDownloader
from pyproj import CRS
import os

# For creation of virtual rasters
#from osgeo import gdal
#import glob

# Create an instance of the DataDownloader class
# This downloads to a subfolder of the project. If you want to store the data elsewhere
# change the path here or setup a symbolic link, see readme.md for details.
downloader = DataDownloader(download_path="data/v1-2/in-3p")

print("Downloading source data files. This will take a while ...")

# --------------------------------------------------------
#Lawrey, E. P., Stewart M. (2016) Complete Great Barrier Reef (GBR) Reef and Island Feature boundaries including Torres Strait (NESP TWQ 3.13, AIMS, TSRA, GBRMPA) [Dataset]. Australian Institute of Marine Science (AIMS), Torres Strait Regional Authority (TSRA), Great Barrier Reef Marine Park Authority [producer]. eAtlas Repository [distributor]. https://eatlas.org.au/data/uuid/d2396b2c-68d4-4f4b-aab0-52f7bc4a81f5
direct_download_url = 'https://nextcloud.eatlas.org.au/s/xQ8neGxxCbgWGSd/download/TS_AIMS_NESP_Torres_Strait_Features_V1b_with_GBR_Features.zip'
downloader.download_and_unzip(direct_download_url, 'GBR_AIMS_Complete-GBR-feat_V1b')

# --------------------------------------------------------
# Lawrey, E. (2024). Coral Sea Oceanic Vegetation (NESP MaC 2.3, AIMS) [Data set]. eAtlas. https://doi.org/10.26274/709g-aq12
direct_download_url = 'https://nextcloud.eatlas.org.au/s/9kqgb45JEwFKKJM/download'
downloader.download_and_unzip(direct_download_url, 'CS_NESP-MaC-2-3_AIMS_Oceanic-veg', flatten_directory=True)

# --------------------------------------------------------
# Natural Earth. (2025). Natural Earth 1:10m Physical Vectors - Land [Shapefile]. https://www.naturalearthdata.com/downloads/10m-physical-vectors/
direct_download_url = 'https://naciscdn.org/naturalearth/10m/physical/ne_10m_land.zip'
downloader.download_and_unzip(direct_download_url, 'ne_10m_land')

# Satellite imagery

# Geoscience Australia (2021). Kenn and Chesterfield Plateaux bathymetry survey (FK210206/GA4869) [Dataset]. Geoscience Australia, Canberra. https://doi.org/10.26186/145381
# https://dx.doi.org/10.26186/145381
direct_download_url = 'https://files.ausseabed.gov.au/survey/Kenn%20and%20Chesterfield%20Plateaux%20Bathymetry%202021%2064m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_Kenn-Chesterfield-Bathy')


# Geoscience Australia (2020). Northern Depths of the Great Barrier Reef bathymetry survey (FK200930/GA4866) [Dataset]. Geoscience Australia, Canberra. http://pid.geoscience.gov.au/dataset/ga/144545
direct_download_url = 'https://files.ausseabed.gov.au/survey/Northern%20Great%20Barrier%20Reef%20Bathymetry%202020%2064m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_North-GBR-Bathy')

# Spinoccia, M., Brooke, B., Nichol, S., & Beaman, R. (2020). Seamounts, Canyons and Reefs of the Coral Sea bathymetry survey (FK200802/GA0365) [Dataset]. Commonwealth of Australia (Geoscience Australia). https://doi.org/10.26186/144385
direct_download_url = 'https://files.ausseabed.gov.au/survey/Coral%20Sea%20Canyons%20and%20Reef%20Bathymetry%202020%2016m%20-%2064m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_Coral-Sea-Canyons')

# Beaman, R., Duncan, P., Smith, D., Rais, K., Siwabessy, P.J.W., Spinoccia, M. (2020). Visioning the Coral Sea Marine Park bathymetry survey (FK200429/GA4861). Geoscience Australia, Canberra. https://dx.doi.org/10.26186/140048
direct_download_url = 'https://files.ausseabed.gov.au/survey/Visioning%20the%20Coral%20Sea%20Bathymetry%202020%2016m%20-%2064m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_Visioning-Coral-Sea-Bathy')

# Beaman, R. (2020). High-resolution depth model for the Great Barrier Reef and Coral Sea - 100 m [Dataset]. Geoscience Australia. http://doi.org/10.26186/5e2f8bb629d07
direct_download_url = 'https://files.ausseabed.gov.au/survey/Great%20Barrier%20Reef%20Bathymetry%202020%20100m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_GBR100-2020-Bathy')

# Beaman, R. (2017). High-resolution depth model for the Great Barrier Reef - 30 m [Dataset]. Geoscience Australia. http://dx.doi.org/10.4225/25/5a207b36022d2
direct_download_url = 'https://files.ausseabed.gov.au/survey/Great%20Barrier%20Reef%20Bathymetry%202020%2030m.zip'
downloader.download_and_unzip(direct_download_url, 'CS_GA_GBR30-2020-Bathy')

# Lawrey, E., & Hammerton, M. (2022). Coral Sea features satellite imagery and raw depth contours (Sentinel 2 and Landsat 8) 2015 – 2021 (AIMS) [Data set]. eAtlas. https://doi.org/10.26274/NH77-ZW79

# We set the subfolder_name because we are downloading multiple folders into the same parent folder. This allows the script
# to check if the sub part of the dataset has been downloaded already. Without this the TrueColour download is skipped because
# the Coral-Sea-Features_Img folder already exists.
dataset = 'Coral-Sea-Features_Img'

layer = 'S2_R1_DeepFalse'
direct_download_url = f'https://nextcloud.eatlas.org.au/s/NjbyWRxPoBDDzWg/download?path=%2Flossless%2FCoral-Sea&files={layer}'
downloader.download_and_unzip(direct_download_url, dataset, subfolder_name = layer, flatten_directory = True)
downloader.create_virtual_raster(dataset, layer=layer)

layer = 'S2_R2_DeepFalse'
direct_download_url = f'https://nextcloud.eatlas.org.au/s/NjbyWRxPoBDDzWg/download?path=%2Flossless%2FCoral-Sea&files={layer}'
downloader.download_and_unzip(direct_download_url, dataset, subfolder_name = layer, flatten_directory = True)
downloader.create_virtual_raster(dataset, layer=layer)

layer = 'S2_R1_TrueColour'
direct_download_url = f'https://nextcloud.eatlas.org.au/s/NjbyWRxPoBDDzWg/download?path=%2Flossless%2FCoral-Sea&files={layer}'
downloader.download_and_unzip(direct_download_url, dataset, subfolder_name = layer, flatten_directory = True)
downloader.create_virtual_raster(dataset, layer=layer)

# Raw depth contours
direct_download_url = f'https://nextcloud.eatlas.org.au/s/NjbyWRxPoBDDzWg/download?path=%2Fpoly&files=Coral-Sea'
downloader.download_and_unzip(direct_download_url, dataset, subfolder_name = 'Raw-depth')


# ICSM (2018) ICSM ANZLIC Committee on Surveying and Mapping Data Product Specification for Composite Gazetteer of Australia, The Intergovernmental Committee on Surveying and Mapping. Accessed from https://placenames.fsdf.org.au/ on 23 Jan 2025
# https://s3.ap-southeast-2.amazonaws.com/fsdf.placenames/DPS/Composite+Gazetteer+DPS.pdf
direct_download_url = 'https://d1tuzeg87mu4oi.cloudfront.net/PlaceNames.gpkg'
downloader.download(direct_download_url, 'AU_ICSM_Gazetteer_2018')




