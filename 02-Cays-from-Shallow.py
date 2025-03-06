# Copyright 2023 Eric Lawrey - Australian Institute of Marine Science
#
# MIT License https://mit-license.org/
# This script is intended to perform an initial estimate of potential cay regions.
# Each of the locations highlighted by the outputs of this code were then manually
# reviewed and mapped over time from imagery of individual days.

# This script converts the CS_AIMS_Coral-Sea-Features_Img_S2_R1_Shallow_* polygon vector 
# file that represents cay regions (low tide sandy area around a cay as it moves over time) 
# and breaking wave areas. This raw conversion then needs manual correction to remove any extraneous 
# features due to noise and to distinguish between cays and breaking ways. This classification is
# achieved by referring to the true colour imagery.
# 
# As inputs to this digitisation we are using image composites generated from multiple dates.
# The composition uses a median of all the input images. As a result the final image captures 
# the movement of the cays across these images as a median representation. The composite image
# is represents the median of the tides, helping to ensure that the final image represents
# typical conditions rather than the tides of any single image. We use a brightness threshold
# applied to the B8 channel that closely matches the low tide extent of coral cays. This was
# verified by comparing the Sentinel 2 B8 channel with Drone mosaic imagery within a two week
# window.
# As cays move around the exposed areas are bright enough that they significantly expand the extent
# of the cay in the final mosaic. As a result the final mosaic closely represents the combined extent
# of the cay over the period of the images that made up the mosaic. 

# Since cays are very small we need to ensure to the conversion to polygons doesn't lower the 
# resolution and so we upscale the image using bilinear interpolation so that the polygon
# conversion will have much small stair case steps. 

# Script environment - Windows
# To run this Python script you will need GDAL installed and available in the same
# environment as this script.
# One possible setup is installing OSGeo4W, enabling GDAL install then 
# running this script from OSGeo4W command window from C:\OSGeo4W\OSGeo4W.bat
# cd C:\Users\elawrey\OneDrive - Australian Institute of Marine 
# Science\Documents\2022\CoralSeaReefMaps\CS_AIMS_Coral-Sea-Features\src
# python 
# This script should be run from the directory that it is in.

import os
import subprocess
import glob

# Directory of the Source imagery.
SRC_PATH = '../../CS_AIMS_Coral-Sea-Features_Img/big-files/lossless/Coral-Sea/S2_R1_Shallow'
#SRC_PATH = '../tmp/test'

# Folder with intermediate stages
TMP = '../tmp/Raw-cay-polygons'

# Path to the Atoll banks used for clipping
CLIPPING_MASK_FILE = '../10_Merge-AHO-Sat-depth-class/CS_AIMS_Coral-Sea-Features_Reef-bank-100m_MSL_STAGE10.shp'
LAYER_NAME = 'CS_AIMS_Coral-Sea-Features_Reef-bank-100m_MSL_STAGE10'

# Path to the GDAL scripts. 
GDAL_PYTHON_PATH =  "c:\\OSGeo4W\\apps\\Python39\\Scripts\\"

# Threshold to apply to the B8 channel to determine if it is part of a cay region
# or not. This value was iteratively to best match the boundary of the cay low tide sand.
B8_THRESHOLD = 95

# Where to store the raw generated polygons
OUT_PATH = '../11_Cay-regions'
OUT_FILENAME = 'CS_AIMS_Coral-Sea-Features_Raw-cays'

if not os.path.exists(TMP):
	os.mkdir(TMP)
	print("Making temporary directory "+TMP)

srcFiles = glob.glob(os.path.join(SRC_PATH,"*.tif"))

fileCount = 1
numFiles = len(srcFiles)
for srcFile in srcFiles:
	print("Processing "+str(fileCount)+" of "+str(numFiles)+" files")
	fileCount = fileCount+1
	# Extract the filename from the path so we can create the destination path
	fileName = os.path.basename(srcFile)
	
	# Stage 1 Upsample and turn to raster mask
	destUpscale = os.path.join(TMP, '01_'+fileName)
	
	if os.path.isfile(destUpscale): 
		print("Skipping upscaling as output already exists "+destUpscale)
	else:
		# -co "COMPRESS=LZW" - Use lossless compression to minimise the file sizes
		# -b 2 - Pull out the B8 channel from the Shallow style images (B5, B8, B11)
		# -r cubicspline - Resample smoothly as this most closely matches the shapes of cays
		# -outsize 300% 300% - Upsample the image prior to applying a thresold to reduce 
		# pixel stair cases.
		# -scale B8_THRESHOLD B8_THRESHOLD+1 1 255 - Stretch the image brightness so that
		# all values below the thresold become 1 and all those above become white. This effectively
		# turns the raster into a mask.
		callStr = 'gdal_translate -co "COMPRESS=LZW" -b 2 -r cubicspline -outsize 300% 300% -scale '+ \
			str(B8_THRESHOLD) + ' ' + str(B8_THRESHOLD+1) + ' 0 255 '+srcFile+' '+destUpscale
		print("Upscaling B8: "+callStr)
		subprocess.call(callStr)
	
	# Clip the image with the areas of the coral atolls. This greatly removes cloud artefacts
	# making scenes that are not clean more manageable to process.
	destClip = os.path.join(TMP, '02_'+fileName)
	
	if os.path.isfile(destClip): 
		print("Skipping clipping as output already exists "+destClip)
	else:
		callStr = 'gdalwarp -of GTiff -co "COMPRESS=LZW" -cutline '+CLIPPING_MASK_FILE+' '+ \
			' '+destUpscale+' '+destClip
		#callStr = 'gdalwarp -of GTiff '+destUpscale+' '+destClip
		print("Clipping B8: "+callStr)
		subprocess.call(callStr)
	
	destPoly = os.path.join(TMP, '03_'+os.path.splitext(fileName)[0]+'.geojson')
	# Stage 2 - Turn into polygon
	if os.path.isfile(destPoly): 
		print("Skipping polygon conversion as output already exists "+destPoly)
	else:
		callStr = 'python '+GDAL_PYTHON_PATH+'gdal_polygonize.py -f GeoJSON '+destClip+' '+destPoly
		print("Converting to vector: "+callStr)
		subprocess.call(callStr)


		
IN_FORMAT = 'geojson'		# Input polygon file type: shp or geojson

# ------------------ MERGE ------------------------
# Merge all the features from the multiple Sentinel tiles in a region into a single
# shapefile.

stageMerge = "04_merge_"+OUT_FILENAME

shpMerge = os.path.join(TMP, stageMerge+".shp")
print("Shapefile name: "+shpMerge)

# -single indicate that we want to merge all polygons into a single layer.
# The need for this flag was discovered after getting the error:
# ERROR: Non-single layer mode incompatible with non-directory shapefile output
if os.path.isfile(shpMerge): 
	print("Skipping "+shpMerge+" as merge output already exists")
else:
	callStr = 'python '+GDAL_PYTHON_PATH+'\\ogrmerge.py -o '+shpMerge+' -single '+os.path.join(TMP, '*.geojson')
	print("Merging: "+callStr)
	subprocess.call(callStr, shell=True)
		
# ----------------- DISSOLVE -----------------------
# Take the spatial union of all the overlapping features. This occurs as the image
# tiles overlap

stageDissolve = "05_dissolve_"+OUT_FILENAME
shpDissolve = os.path.join(TMP, stageDissolve+".shp")

# https://stackoverflow.com/questions/47038407/dissolve-overlapping-polygons-with-gdal-ogr-while-keeping-non-connected-result
if os.path.isfile(shpDissolve): 
	print("Skipping "+shpDissolve+" as dissolved output already exists")
else:
	callStr = 'ogr2ogr -f "ESRI Shapefile" -explodecollections '+shpDissolve+' '+shpMerge + \
		' -dialect sqlite -sql "select ST_union(Geometry) from ""'+stageMerge+'"""'
	print("Dissolving: "+callStr)
	subprocess.call(callStr, shell=True)
	

# ----------------- EXPLODE -----------------------
# Convert the multipart polygon created by the dissolve into single part polygons.
# This significantly improves performance and allows us to attach individual attributes to each
# feature.

stageExplode = "06_explode_"+OUT_FILENAME
shpExplode = os.path.join(TMP, stageExplode+".shp")

# https://wiki.tuflow.com/index.php?title=Vector_Format_Conversion_Using_ogr2ogr
if os.path.isfile(shpExplode): 
	print("Skipping "+shpExplode+" as dissolved output already exists")
else:
	callStr = 'ogr2ogr -f "ESRI Shapefile" -explodecollections '+shpExplode+' '+shpDissolve + \
		' -nlt POLYGON -sql "select * from ""'+stageDissolve+'"""'
	print("Exploding: "+callStr)
	subprocess.call(callStr, shell=True)