# CS_AIMS_Coral-Sea-Features_2025
This repository contains utility scripts that were used in the development of the Coral Sea Features dataset. For full information about this dataset see: 

Lawrey, E., Bycroft, R. (2025). Coral Sea Features - Dataset collection - Coral reefs, Cays, Oceanic reef atoll platforms, and Depth contours (AIMS). [Data set]. eAtlas. https://doi.org/10.26274/pgjp-8462 

All the satellite image preparation used in the development is described separately in [Lawrey and Hammerton, 2022](https://doi.org/10.26274/NH77-ZW79).

It should be noted that this dataset was largely created manually and this these scripts represent utilities that were used to process portions of the dataset production, and do not full represent the full workflow associated with the dataset as much of the processing was performed in QGIS. It should also be noted that most of these scripts refer to files that were intermediate files during the production and thus will not work directly from the public files. They are provided as a form of documentation, rather than to allow a blind rerun of the processing from scratch.

# Installation Guide

## 1. Prerequisites
- If using Conda, install [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) (Untested) or use Anaconda Navigator.
- Install GDAL using installing OSGeo4W (this is needed for running 02-Cays-from-Shallow.py).

## 2. Clone the Repository
```bash
git clone https://github.com/eatlas/CS_AIMS_Coral-Sea-Features
cd CS_AIMS_Coral-Sea-Features
```

## 3. Using Conda 
Conda is recommended because, in theory, it makes the installing of GDAL, PROJ and GEOS more straight forward across a wider range of platforms. In my testing on Windows both conda and pip worked just as well as each other. The only real difference is that conda can be used to install a specific version of Python into an environment, where as Pip will use the version of Python that is installed.

1. Create the Conda environment. This step can take 10 min. If you are using Anaconda open the default Anaconda Prompt, change to the 
    ```bash
    cd {path to the CS_AIMS_Coral-Sea-Features dataset} 
    conda env create -f environment-3-13.yaml
    ```
2. Activate the environment
    ```bash
    conda activate venv_map_3-13
    ```
    
## Debug:
ERROR conda.core.link:_execute(938): An error occurred while installing package 'conda-forge::libjpeg-turbo-3.0.0-hcfcfb64_1'.
Rolling back transaction: done

[Errno 13] Permission denied: 'C:\\Users\\elawrey\\Anaconda3\\pkgs\\libjpeg-turbo-3.0.0-hcfcfb64_1\\Library\\bin\\wrjpgcom.exe'
()

For some reason this particular cache of the library was set with administrator permissions, preventing conda for using this library in the setup. The fix is to switch to admin permissions, delete the `C:\\Users\\elawrey\\Anaconda3\\pkgs\\libjpeg-turbo-3.0.0-hcfcfb64_1` folder, which is safe since it is just a cache. 

I found that when this failure occurs the resulting conda environment ends up in a corrupted state and it must be manually removed, prior to recreating the environment.

In my case I needed to delete `C:\Users\elawrey\Anaconda3\envs\venv_map_3-13`

# Description of scripts

## 01-download-input-data.py
This script downloads the third party datasets used in the preview maps, such as the world land area, the GBR reefs, the Coral Sea vegetation and bathymetry datasets. This script downloads the data directly from the original source data services and stores it in `C:\Data\2025\CS_AIMS_Coral-Sea-Features\working`. This is the folder where the QGIS `preview-maps.qgz` will look for the data files. If you download to a different location you will need to adjust the paths in QGIS. This script should download all data files used to recreate the preview maps and plots used for reporting purposes.

`data_downloader.py` is a utility library that is used by `01-download-preview-map-data.py`.

## 02-Cays-from-Shallow.py
This script uses GDAL from the command line and so the easiest way to run this is to run it from an OSGeo4W batch window. I wrote this before I knew how to use GDAL directly from Python.

This script was used as part of the preliminary work associated with identifying where potential cays might be. This worked by applying a threshold to the infrared B8 channel of the 'Shallow' imagery from Lawrey and Hammerton, 2022. This infrared channel only shows features that are dry or very shallow. The threshold was chosen to approximately match the boundary of known cays. After the thresholding was applied the raster was converted to a polygon and clipped to the atoll platforms to remove noise. These initial estimates of cays were then used as locations to map as cays.

*Limitations:* While this method provided an automated approach to identifying cays it had some serious limitations. Because the imagery used was a composite image based on the median of multiple days spread over time, this would result in poor detection of ephemeral cays as their movement over time would result in a darker signal in the composite. Another limitation was that breaking ways produce a signal as strong as cays and so the mask generated by the script corresponds to breaking waves and cays.

It was only after understanding these limitations that we identifed that we needed to map the cays from a time series of individual days as this would allow the tracking of the cay boundary to be identifed. 

## 03-clip-depths.py
This script was used to clean up the raw depth polygons by clipping them by the boundary of the atoll platforms. This removes any artefacts due to clouds that are outside the atoll platform boundaries.

## 04-allocate-ReefIDs.py
This script allocates permanent identifiers to each reef feature, based on an approach inspired by the reef ID system used on the GBR, but with the capacity to allocate identifiers to features globally. The basic structure of the identifier is {letter to indicate the class of features}-{geographic grid coordinate}-{feature count within grid}.

For the reef mapping base 10 (B10) was used to encode the ReefID as it was found that while higher bases lead to slightly shorter identifiers (1 to 2 characters shorter), the identifiers started to look more like a random password than an identifier that might be used for communications.

## 05-cay-average-area.py
This script calculates the average area of the cays. This is to estimate how much smaller the cays are compared with the cay region in Reefs-Cays. This uses spatial joining to work out which cays in Cays-over-time correspond to each cay in Reefs-Cays. It assigns them the matching ReefID and Area_km2. The average cay area is then calculated over each date and ReefID, then copied back to Reefs-Cays. This creates an updated version of the Reefs-Cays and Cays-over-time in working. These should be manually copied to the publication folder once they have been checked.

## 06-plot-cay-region-vs-cay-area.py
This script plots how the average cay area varies as a function of the cay stability and whether it is vegetated.  

