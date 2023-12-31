# -*- coding: utf-8 -*-
"""
# XView Preprocessing
This .py file extract and read annotations downloaded from XView, select annotations related to fires, copy basic information (pre/post diaster, raw image id, location, image date, coordinate) to geopandas and save them as geojsons and shapefiles.

## Setting up
"""

# from google.colab import drive # import drive from google colab
# ROOT = "/content/drive"     # default location for the drive
#print(ROOT)                 # print content of ROOT (Optional)

# drive.mount(ROOT)           # we mount the google drive at /content/drive

# Commented out IPython magic to ensure Python compatibility.
# %cd "/content/drive/My Drive/FinalProj"
rootPath = r'C:\Users\Aqeel\Desktop\GEOG761\BuildingDamage' # Change to where you wanna store data
# os.chdir(rootPath)

#! pip install geopandas

#! pip install simplejson

import zipfile
import os
import tarfile
import pandas as pd
import time
from datetime import datetime, date, time, timedelta
import numpy as np
import matplotlib.pyplot as plt
import json
from shapely import wkt
from pandas.io.json import json_normalize
import geopandas as gpd
from sys import argv
from os.path import exists
import simplejson as json

def lstFiles(rootPath, ext):
  '''
  get list of files based on directory and extension inputs 
  '''
  emptyList = []
  root = rootPath
  for path, subdirs, files in os.walk(root):
      for names in files: 
          if names.endswith(ext) and not names.startswith("._"):
              emptyList.append(path + '\\' + names)
  return(emptyList)

def createFolder(rootPath, folderName): 
  '''
  Create new folder in root path 
  '''
  folderPath = os.path.join(rootPath, folderName) 
  if not os.path.exists(folderPath):
      os.makedirs(folderPath)
  return folderPath + "\\"

"""## Unzip .tar

Dataset from xview challenge can be obtained here: https://xview2.org/
"""

trainData = 'train_images_labels_targets.tar'
testData = 'test_images_labels_targets.tar'
# holdData = 'hold_images_labels_targets.tar'
#tier3Data = 'tier3.tar'
if not os.path.exists(os.path.join(rootPath,'TarFiles')):
      os.makedirs(os.path.join(rootPath,'TarFiles'))
      print("Created TarFiles folder, add/move .tar files to that")

tar_files = [trainData, testData]# , (testData, 'test_all'), (holdData, 'hold_all')]

# COMMENT OUT IF FILES ARE ALREADY UNZIPPED FROM TAR
# for tar in tar_files: 
  # tf = tarfile.open(os.path.join(rootPath,'TarFiles', tar))
  # tf.extractall(rootPath) 

"""## Read-in data into dataframe"""

def getDataInfo(rootPath, folderName):
  '''
  Get info of data from original XView challenge dataset (.json)
  extracting attributes from metadata: location_name, ID, disaster type, 
  img_date, pre_post_disaster, and img_name to create dataframe
  '''
  json_files = lstFiles(os.path.join(rootPath, folderName), '.json')

  locationName = []
  disasterType = []  
  ID = [] 
  pre_post = [] 
  date = [] 
  img_name = [] 

  for jsn in json_files: 
      nm = jsn.split("\\")
      fileName = nm[-1]
      nmm = fileName.split("_")
      ID.append(str(nmm[1]))
      pre_post.append(nmm[2])
      img_name.append(fileName[:-5])
      data = json.load(open(jsn))
      disasterType.append(data['metadata']['disaster_type'])
      date.append(data['metadata']['capture_date'])
      locationName.append(data['metadata']['disaster'])

  dataInfo = pd.DataFrame({ 'location_name': locationName, 'ID':ID, 'disaster_type': disasterType, 
                            'img_date': date, 'pre_post_disaster': pre_post, 'img_name':img_name})
  return dataInfo

# hold_firesDF = getDataInfo(rootPath, 'hold_all')
train_DF = getDataInfo(rootPath, 'train')
test_DF = getDataInfo(rootPath, 'test')

"""## Filter Data & Move"""

from shutil import copyfile

def moveFiles(rootPath, inputFolder, folderDict, outputFolder, dataDF):
  '''
  Based on dataframe with disaster type info, move files into new folder
  if only it is fire. 
  '''
  filterDF = dataDF[dataDF['disaster_type'].isin(["flooding", "wind"])]
  for index, row in filterDF.iterrows():
      for dic in folderDict: 
          flPath = os.path.join(rootPath, inputFolder, dic[0])
          src = os.path.join(flPath, row.img_name + dic[1])
          mainFolder = createFolder(os.path.join(rootPath, 'Data'), outputFolder)
          eventFolder = createFolder(mainFolder, row.location_name)
          IDFolder = createFolder(eventFolder, row.ID)
          dst = os.path.join(IDFolder, row.img_name + dic[1])
          copyfile(src, dst)

folderExt = [['images', '.png'], ['labels', '.json'], ['targets', '_target.png']]

# moveFiles(rootPath, 'test_all', folderExt, 'test', test_firesDF)     
# moveFiles(rootPath, 'hold_all', folderExt,'hold', hold_firesDF)     
moveFiles(rootPath, 'train', folderExt, 'train', train_DF)
moveFiles(rootPath, 'test', folderExt, 'test', test_DF)


"""## Convert to Readable Format (i.e. GEOJSON)"""

plt.ioff()
shps = {}

def damage_encoder(value):
    if value=='no-damage':
        return 1
    elif value=='minor-damage':
        return 2
    elif value=='major-damage':
        return 3
    elif value=='destroyed':
        return 4
    else:
        return 0

def createGeoFiles(fullDF, inputFolder, outputFolder):
  '''
  Based on the dataframe, if disaster_type is fire then read .json file as geodataframe
  Add in damage attribute 'no-damage' for pre disaster events. 
  Create folder and event folders to organize each instance based on unique IDs
  Convert to geojson, shpfile, .png files 
  '''
  filterDF = fullDF[fullDF['disaster_type'].isin(["flooding", "wind"])]
  for index, row in filterDF.iterrows():
      try:
          pth = os.path.join(rootPath, "Data", inputFolder, row.location_name, row.ID)
          jsonFile = os.path.join(pth, row.img_name + '.json')
          data = json.load(open(jsonFile)) # read as json file 
          df = json_normalize(data['features']['lng_lat']) # convert to df
          df['wkt'] = df['wkt'].apply(wkt.loads)
          gdf = gpd.GeoDataFrame(df, geometry='wkt') # read as geodf
          gdf['date'] = row.img_date
          gdf['pre_post_disaster'] = row.pre_post_disaster
          gdf['disaster_type'] = row.disaster_type
          gdf['location_name'] = row.location_name
          gdf['ID'] = row.ID
          if row.pre_post_disaster == 'pre': 
              gdf['damage'] = 'no-damage'
              gdf['dmg_code'] = 1
          else: 
              gdf['damage'] = df['properties.subtype']
              gdf['dmg_code'] = gdf['damage'].map(damage_encoder)

          mainFolder = createFolder(rootPath, outputFolder)
          eventFolder = createFolder(mainFolder, row.location_name)
          IDFolder = createFolder(eventFolder, row.ID)
          gdf.crs = {'init' :'epsg:4326'}
          gdf.to_file(os.path.join(IDFolder, row.img_name + '.geojson'), driver='GeoJSON')
          shpPath = createFolder(IDFolder, row.img_name)
          gdf.to_file(os.path.join(shpPath, row.img_name + '.shp'))
          gdf.plot(column='damage', cmap='PiYG')
          plt.savefig(os.path.join(IDFolder, row.pre_post_disaster + "_" + row.location_name + '.png'))
          plt.close()
          if row.location_name not in shps.keys():
              shps[row.location_name] = [gdf]
          else:
              shps[row.location_name].append(gdf)
      except: 
          continue
  return shps

# Convert .json to geojson

shps_train = createGeoFiles(train_DF, 'train', 'train_geo')
shps_test = createGeoFiles(test_DF, 'test', 'test_geo')
# createGeoFiles(hold_firesDF, 'hold', 'hold_geo')

"""## Merge Training/Testing Data"""

# import glob
# get all shapefiles in train folder 
# merge into one 
train_files = lstFiles('train_geo', '.shp')
test_files = lstFiles('test_geo', '.shp')
# hold_files = lstFiles('hold_geo', '.shp')

# merge with geopandas instead 
# arcpy.Merge_management(train_files, os.path.join(rootPath, 'test_building.shp'))
for shps, label in [(shps_train,"Train"), (shps_test,"Test")]:
  for loc in shps.keys():
    merged_shps = gpd.pd.concat(shps[loc])
    if not os.path.exists(os.path.join(rootPath, f"Merged{label}Files")):
          os.makedirs(os.path.join(rootPath, f"Merged{label}Files"))
    merged_shps.to_file(os.path.join(rootPath, f"Merged{label}Files", f"merged_{label.lower()}_{loc}.shp"))