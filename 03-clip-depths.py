# Copyright 2022 Eric Lawrey - Australian Institute of Marine Science
#
# MIT License https://mit-license.org/
# This script clips the satellite derived depth estimates (CS_AIMS_Coral-Sea-Features_Img_S2_R1_Depth10m_Coral-Sea)
# with the reef boundaries. This removes most of the noise from clouds. This will however not remove
# cloud effects over reef areas.
# This script is provided primarily for reference purposes of the processing used during a part of the processing.
# This should be run with a Python environment that has GDAL installed.
# On Windows use OSGeo4W commandline.

import os
import subprocess
import glob

input_depth_dir = '../01_Initial-digitisation/CS_Depth/'
input_reef_boundaries = 'CS_Reef_Boundaries_adj/CS_Reef_Boundaries.shp'
output_depth_dir = 'CS_Depth_adj/'

files = glob.glob(input_depth_dir+'*.shp')
count = 1
for file in files:
	(f, ext) = os.path.splitext(os.path.basename(file))
	print(str(count)+' of '+str(len(files))+' '+f)
	count = count+1
	output_shp = output_depth_dir+f+'.shp'
	if (os.path.exists(output_shp)):
		print("Skipping as output Shapefile exists: "+output_shp)
		continue 
		
	callStr = 'ogr2ogr -clipsrc '+input_reef_boundaries+' '+output_shp+' '+file
	print(callStr)
	subprocess.call(callStr)