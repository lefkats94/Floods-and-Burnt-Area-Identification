import rasterio
from matplotlib import pyplot as plt
import numpy as np
import os
from osgeo import gdal

from PIL import Image
from collections import OrderedDict
import datetime
import time
import utm
import json
import algorithm_water_change_area.water_change_detection_main as water_change_detection_main
import algorithm_burned_area.change_detection_functions as change_detection_functions
import settings
from methods import preprocess_functions

def get_unique_values_and_freqs(array):
  """
  Given an array, returns the unique values and their frequencies.

  Parameters:
          array (np.array): A numpy array

  """
  unique, counts = np.unique(array, return_counts=True)
  freqs = (counts/sum(counts))*100
  return unique, freqs

def suggest_expansion_or_not(array, threshold):
  """
  Given an buffer slice of the original array, returns the True if the search 
  area should be expanded towards the direction of this buffer slice

  Parameters:
          array (np.array): A numpy array
          threshold (int): The threshold over which the search area should be 
          expanded towards the direction of the buffer

  """
  unique, freqs = get_unique_values_and_freqs(array)
  print(sum(freqs[1:]))
  if sum(freqs[1:])>threshold:
    return True
  else:
    return False

def suggest_directions_of_search_area_expansion(result_directory, buffer_percentage = 5, threshold = 2):
  """
  Parameters:
          result_directory (str): The directory of the .tif file that will be
          used
          buffer_percentage (str): D

  """

  # Reading the output .tif file from the given directory
  src = rasterio.open(result_directory)
  array = src.read(1)

  # Calculating array shape
  array_height = array.shape[0]
  array_width = array.shape[1]

  # Calculating the width of the buffer according to the .tif shape
  lat_buffer_in_pixels = int(array_height*(buffer_percentage/100))
  lon_buffer_in_pixels = int(array_width*(buffer_percentage/100))

  # Slicing buffer zones according to the 'buffer_percentage'
  east_buffer = array[:,0:lon_buffer_in_pixels]
  west_buffer = array[:,-lon_buffer_in_pixels:]
  north_buffer = array[0:lat_buffer_in_pixels,:]
  south_buffer = array[-lat_buffer_in_pixels:,:]

  # Checking if the area should be expanded towards each of the four possible 
  # directions
  expand_towards_east = suggest_expansion_or_not(east_buffer, threshold)
  expand_towards_west = suggest_expansion_or_not(west_buffer, threshold)
  expand_towards_north = suggest_expansion_or_not(north_buffer, threshold)
  expand_towards_south = suggest_expansion_or_not(south_buffer, threshold)

  # Creating a list of boolean variables
  suggestion = [
      expand_towards_north,
      expand_towards_west, 
      expand_towards_south,
      expand_towards_east
      ]

  return suggestion

def find_center_of_geotiff(geotiff):
    """
    Given a tiff file returns the coordinates of the center of the map in meters.
    Parameters:
        geotiff (str): the path for the input tiff file
    """
    geotiff_file = gdal.Open(geotiff)
    geoTransform = geotiff_file.GetGeoTransform()
    
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1] * geotiff_file.RasterXSize
    miny = maxy + geoTransform[5] * geotiff_file.RasterYSize
    
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    return center_x, center_y

def create_boundary_box(center_point, radius):
    x,y = center_point
    minx = x - radius
    maxx = x + radius
    miny = y - radius
    maxy = y + radius
    return minx, maxx, miny, maxy



def preprocess_and_execute_affected_area_module(path_list, input_box, products_id_list_safe, process_path, event):  
    """
    The function processes the .SAFE files (converts to tiff and clips based on the input_box) whose ids are included in products_id_list_safe and have been downloaded in the elements of the path_list directories for each date.  
    path_list: Contains the path to the pre and after folder with the downloaded products.
    """
    ext_x_min, ext_x_max, ext_y_min, ext_y_max  = input_box
    for path in path_list:
        index_path = path_list.index(path)
        print(path)
        #extract the date from the path
        product_date = os.path.basename(path)
        #products_id_list_safe to check if the products are in the list 
        product_list = [el for el in os.listdir(path) if el in products_id_list_safe[index_path]]
        print(product_list)
        print(product_date)
        try:
            preprocess_functions.pre_process_product(path + '/', process_path,
                                                    product_list, product_date, ext_x_min, ext_y_max, ext_x_max, ext_y_min)
        except:
            print("Products could not be processed. The program will exit.")
                                            
  
    before_folder = os.path.join(process_path, os.path.basename(path_list[0]))
    print(before_folder)
    after_folder = os.path.join(process_path, os.path.basename(path_list[1]))
    dates = []
    dates.append(os.path.basename(path_list[0]))
    dates.append(os.path.basename(path_list[1]))
    if not os.path.exists(before_folder) or not os.path.exists(after_folder):
        print('No valid data folders provided. Please provide the correct filepath.')
        return 0


    if os.path.isfile(os.path.join(before_folder, 'TCI.tif')):
        rgb_image = os.path.join(before_folder, 'TCI.tif')
    elif os.path.isfile(os.path.join(after_folder, 'TCI.tif')):
        rgb_image = os.path.join(after_folder, 'TCI.tif')
    else:
        print('No RGB image found to visualize the result. Please make sure there is a TCI.tiff in either the pre or after date folder')
        rgb_image = -1

    if event == 'fire':
        change = 'fire_change'
    else:
        change = 'water_change'

    # creating a new folder in which the results (all the generated images and files) will be placed
    results_folder = change + '_{}_and_{}'.format(dates[0], dates[1])
    path_for_comparisons = os.path.join(process_path, results_folder)

    if not os.path.exists(path_for_comparisons):
        try:
            os.mkdir(path_for_comparisons)
        except OSError:
            print("Creation of output directory failed. All the created files will be placed on the parent folder")
            path_for_comparisons = process_path
    if event == 'fire':
        try:	
            change_detection_functions.burned_area_change_detection_min(before_folder, after_folder, rgb_image, path_for_comparisons)  
        except:
            print('The execution for the box could not be created') 
    else:
        try:	
            water_change_detection_main.water_change_main_simple(before_folder, after_folder, rgb_image, path_for_comparisons)  
        except:
            print('The execution for the box could not be created') 
#Testing preprocess_and_execute_affected_area_module
# input_box = [410939.8073041536263190, 3372765.2249314570799470, 466947.1888734833337367, 3334042.8800878343172371] 
# path_list = ['/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-11-22_2022-12-07_T42RVU/2022-11-22', '/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-11-22_2022-12-07_T42RVU/2022-12-07']
# products_id_list_safe = [['S2A_MSIL2A_20221122T061151_N0400_R134_T42RVU_20221122T085005.SAFE'], ['S2B_MSIL2A_20221207T061229_N0509_R134_T42RVU_20221207T072937.SAFE']]
# process_path = '/home/lefkats/snapearth_api/snapearth_api/output/test_preprocess'
# preprocess_and_execute_affected_area_module(path_list, input_box, products_id_list_safe, process_path, 'fire')




#suggest_directions_of_search_area_expansion('/home/lefkats/snapearth_api/snapearth_api/output/new_output/fire_change_2022-07-14_and_2022-07-31/affected_area.tif', buffer_percentage = 5, threshold = 2)

def calculate_uncertainty(path_to_the_product):
    """
    This function calculate uncertainty for each image for the area of interest based on the shp on the shp folder. The xml will include these values.
    """
# load SCL files and calculate uncertainty
    if os.path.exists(path_to_the_product):
        SCL = gdal.Open(path_to_the_product)
        srcband = SCL.GetRasterBand(1)
        SCL_array = srcband.ReadAsArray(0, 0, SCL.RasterXSize, SCL.RasterYSize)
        uncertainty = np.zeros((SCL.RasterXSize, SCL.RasterYSize))
        uncertainty = np.where(SCL_array == 2, True, False)
        uncertainty = np.logical_or(np.where(SCL_array == 3, True, False), uncertainty)
        uncertainty = np.logical_or(np.where(SCL_array == 8, True, False), uncertainty)
        uncertainty = np.logical_or(np.where(SCL_array == 9, True, False), uncertainty)
        uncertainty = np.logical_or(np.where(SCL_array == 1, True, False), uncertainty)
        # clouds = np.logical_or(SCL_array[SCL_array==8], SCL_array[SCL_array==9])
        # shadows = np.logical_or(SCL_array[SCL_array==2], SCL_array[SCL_array==3])
    else:
        uncertainty = -1
    if not isinstance(uncertainty, int):
        uncertainty = float(uncertainty.sum()) / (uncertainty.shape[0] * uncertainty.shape[1]) * 100

    return uncertainty



def calculate_land_cover_classes_clc_affected_area(clc_filepath, input_raster_path, event):
    #affected_area_tiff_file
    affectedAreaSource = gdal.Open(input_raster_path)
    affectedAreaband = affectedAreaSource.GetRasterBand(1)
    affected_area = affectedAreaband.ReadAsArray(0, 0, affectedAreaSource.RasterXSize, affectedAreaSource.RasterYSize)
    
    # if a CLC layer is present then initialize arrays for respective outputs
        # clc cover
    CLC_SOURCE = gdal.Open(clc_filepath)
    clcband = CLC_SOURCE.GetRasterBand(1)
    CLC_array_resized = clcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize, affectedAreaSource.RasterXSize, affectedAreaSource.RasterYSize)
    
    if event == 'fire':
        high_severity = np.where(affected_area == 4, True, False)
        medium_high_severity = np.where(affected_area == 3, True, False)
        medium_low_severity = np.where(affected_area == 2, True, False)
        low_severity = np.where(affected_area == 1, True, False)
        unburned = np.where(affected_area == 0, True, False)
        
        
            
        
        temp_array_1 = np.multiply(CLC_array_resized, low_severity)
        temp_array_2 = np.multiply(CLC_array_resized, medium_low_severity)
        temp_array_3 = np.multiply(CLC_array_resized, medium_high_severity)
        temp_array_4 = np.multiply(CLC_array_resized, high_severity)
        clc_low = temp_array_1[np.nonzero(temp_array_1)]
        clc_medium_low = temp_array_2[np.nonzero(temp_array_2)]
        clc_medium_high = temp_array_3[np.nonzero(temp_array_3)]
        clc_high = temp_array_4[np.nonzero(temp_array_4)]

        clc_classes = get_percentage_for_all_classes_of_CLC_array(np.concatenate((clc_low, clc_medium_low, clc_medium_high, clc_high)))

        fire_classes = {}
        
        for i in clc_classes.keys():
            if clc_classes[i][1] > 2:
                
                fire_classes.update(dict({clc_classes[i]}))
        return fire_classes
    
    else:
        
        water_to_land_array = np.where(affected_area == 2, True, False)
        land_to_water_array = np.where(affected_area == 3, True, False)
        
        temp_array = np.multiply(CLC_array_resized, land_to_water_array)
        glc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(CLC_array_resized, water_to_land_array)
        glc_water_to_land = temp_array[np.nonzero(temp_array)]

        glc_land_to_water_classes = get_percentage_for_all_classes_of_CLC_array(glc_land_to_water)
        glc_water_to_land_classes = get_percentage_for_all_classes_of_CLC_array(glc_water_to_land)

       
        land_to_water_classes = {}
        for i in glc_land_to_water_classes.keys():
            if glc_land_to_water_classes[i][1] > 2:
                land_to_water_classes.update(dict({glc_land_to_water_classes[i]}))

    
        water_to_land_classes = {}
        for i in glc_water_to_land_classes.keys():
            if glc_water_to_land_classes[i][1] > 2:
                water_to_land_classes.update(dict({glc_water_to_land_classes[i]}))
        else:
            land_to_water_classes = {}
            water_to_land_classes = {}
        #water_classes includes two dictionaries land_to_water_classes, water_to_land_classes but fire classes one
        water_classes = {}
        water_classes['land_to_water_classes'] = land_to_water_classes
        water_classes['water_to_land_classes'] = water_to_land_classes
        return water_classes

def calculate_land_cover_classes_glc_affected_area(lc_gl_filepath, input_raster_path, event):     
    #import affected area as array
    affectedAreaSOURCE = gdal.Open(input_raster_path)
    affectedAreaband = affectedAreaSOURCE.GetRasterBand(1)
    affected_area = affectedAreaband.ReadAsArray(0, 0, affectedAreaSOURCE.RasterXSize, affectedAreaSOURCE.RasterYSize)
    
    #Extract Land use - Land cover from the provided LC100_global.tiff file which has been calculated for each band
    LC100_global_SOURCE = gdal.Open(lc_gl_filepath)
    srcband = LC100_global_SOURCE.GetRasterBand(1)
    LC100_gl_arr_resized = srcband.ReadAsArray(0, 0, LC100_global_SOURCE.RasterXSize,
                                                LC100_global_SOURCE.RasterYSize, affectedAreaSOURCE.RasterXSize, affectedAreaSOURCE.RasterYSize)
    if event == 'fire':
        high_severity = np.where(affected_area == 4, True, False)
        medium_high_severity = np.where(affected_area == 3, True, False)
        medium_low_severity = np.where(affected_area == 2, True, False)
        low_severity = np.where(affected_area == 1, True, False)
        unburned = np.where(affected_area == 0, True, False)
     
        temp_array_1 = np.multiply(LC100_gl_arr_resized, low_severity)
        temp_array_2 = np.multiply(LC100_gl_arr_resized, medium_low_severity)
        temp_array_3 = np.multiply(LC100_gl_arr_resized, medium_high_severity)
        temp_array_4 = np.multiply(LC100_gl_arr_resized, high_severity)
        glc_low = temp_array_1[np.nonzero(temp_array_1)]
        glc_medium_low = temp_array_2[np.nonzero(temp_array_2)]
        glc_medium_high = temp_array_3[np.nonzero(temp_array_3)]
        glc_high = temp_array_4[np.nonzero(temp_array_4)]

        glc_classes = get_percentage_for_all_classes_of_LC_gl_array(
            np.concatenate((glc_low, glc_medium_low, glc_medium_high, glc_high)))

        fire_classes = {}
        for i in glc_classes.keys():
            if glc_classes[i][1] > 2:
                
                fire_classes.update(dict({glc_classes[i]}))
        else:
            fire_classes = {} 
        return fire_classes
    
    else:
        
        water_to_land_array = np.where(affected_area == 2, True, False)
        land_to_water_array = np.where(affected_area == 3, True, False)
        
        temp_array = np.multiply(LC100_gl_arr_resized, land_to_water_array)
        glc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(LC100_gl_arr_resized, water_to_land_array)
        glc_water_to_land = temp_array[np.nonzero(temp_array)]

        glc_land_to_water_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_land_to_water)
        glc_water_to_land_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_water_to_land)

       
        land_to_water_classes = {}
        for i in glc_land_to_water_classes.keys():
            if glc_land_to_water_classes[i][1] > 2:
                land_to_water_classes.update(dict({glc_land_to_water_classes[i]}))

        print('Land to water classes:', land_to_water_classes)
        water_to_land_classes = {}
        for i in glc_water_to_land_classes.keys():
            if glc_water_to_land_classes[i][1] > 2:
                water_to_land_classes.update(dict({glc_water_to_land_classes[i]}))
        # else:
        #     land_to_water_classes = {}
        #     water_to_land_classes = {}
        water_classes = {}
        water_classes['land_to_water_classes'] = land_to_water_classes
        water_classes['water_to_land_classes'] = water_to_land_classes
        print('Final water classes:', water_classes)
        return water_classes 
    

def get_percentage_for_all_classes_of_CLC_array(clc_array):
    class_dict_percentage = {}
    class_ids_list = range(1,46)
    class_names = []
    class_names.append(' ')


    with open(os.path.join(os.getcwd(),'CLC2018', 'CLC2018_CLC2018_V2018_20_QGIS.txt'), 'r') as reader:
        line = reader.readline()
        while line != '':  # The EOF char is an empty string
            class_names.append(line[-2::-1].partition(',')[0][-1::-1])
            line = reader.readline()

    for each_class_id in class_ids_list:
        desired_class = (clc_array == each_class_id).sum()
        total_area = np.size(clc_array)
        percentage = (desired_class / float(total_area)) * 100.0
        class_dict_percentage[each_class_id] = (class_names[each_class_id],round(percentage,4))
    class_dict_percentage.pop(45)
    class_dict_percentage[48] = (class_names[45], round(percentage, 4))
    return class_dict_percentage

# Find the percentage of all LC classes an array containing the land cover values from the global layer
def get_percentage_for_all_classes_of_LC_gl_array(lc_array):
    class_dict_percentage = {}
    class_ids_list = []
    class_names = []
    # class_names.append(' ')

    with open(os.path.join(os.getcwd(), 'LC100_GLOBAL', 'Global_land_cover_classes.txt'),'r') as reader:
        line = reader.readline()
        while line != '':  # The EOF char is an empty string
            #print(line)
            #print(line[-3::-1].partition(',')[0])
            a = line.partition(':')[0]
            b = line.partition(':')[2][:-1]
            class_names.append(line.partition(':')[2][:-1])
            class_ids_list.append(int(line.partition(':')[0]))
            line = reader.readline()
            if line == '\n':
                break
    for each_class_id in class_ids_list:
        desired_class = (lc_array == each_class_id).sum()
        total_area = np.size(lc_array)
        percentage = (desired_class / float(total_area)) * 100.0
        class_dict_percentage[class_ids_list.index(each_class_id)] = (
        class_names[class_ids_list.index(each_class_id)], round(percentage, 4))
    return class_dict_percentage        



# process_path = '/home/lefkats/snapearth_api/snapearth_api/output/new_output'
# final_product_burned_array_path = os.path.join(process_path + "/full/full_affected_area.tiff")
# # process_clc_with_input_raster(final_product_burned_array_path, process_path + "/full")
# # process_glc_with_input_raster(final_product_burned_array_path, process_path + "/full")

# #calculate land cover classes affected_from the burnt area
# clc_filepath = os.path.join(process_path, "full", 'CLC.tif')
# glc_filepath = os.path.join(process_path, "full", 'LC100_global.tif')

# #check if clc filepath exists and calculate fire_classes, otherwise check if glc cover exists and calculate fire classes.
# if os.path.exists(clc_filepath):
#     fire_clases = calculate_land_cover_classes_clc_affected_area(clc_filepath, final_product_burned_array_path)
# elif os.path.exists(glc_filepath):
#     fire_clases = calculate_land_cover_classes_glc_affected_area(glc_filepath, final_product_burned_array_path)
# else:
#     fire_clases = {}
# print(fire_clases)    




def create_png_images(path_to_tiff_file, destination_file):
    
    RGB_SOURCE_before = gdal.Open(path_to_tiff_file)
    red_srcband_b = RGB_SOURCE_before.GetRasterBand(1)
    green_srcband_b = RGB_SOURCE_before.GetRasterBand(2)
    blue_srcband_b = RGB_SOURCE_before.GetRasterBand(3)
    rgbOutput_before = np.zeros((RGB_SOURCE_before.RasterYSize, RGB_SOURCE_before.RasterXSize, 3), 'uint8')
    red_arr = red_srcband_b.ReadAsArray(0, 0, RGB_SOURCE_before.RasterXSize, RGB_SOURCE_before.RasterYSize)
    green_arr = green_srcband_b.ReadAsArray(0, 0, RGB_SOURCE_before.RasterXSize, RGB_SOURCE_before.RasterYSize)
    blue_arr = blue_srcband_b.ReadAsArray(0, 0, RGB_SOURCE_before.RasterXSize, RGB_SOURCE_before.RasterYSize)
    rgbOutput_before[:, :, 0] = np.copy(red_arr)
    rgbOutput_before[:, :, 1] = np.copy(green_arr)
    rgbOutput_before[:, :, 2] = np.copy(blue_arr)
    temp_image = Image.fromarray(rgbOutput_before)
    temp_image.save(destination_file)

def create_pngs_affected_area(input_raster_path, tci_filepath, destination_folder, event):     
    
    affectedAreaSOURCE = gdal.Open(input_raster_path)
    affectedAreaband = affectedAreaSOURCE.GetRasterBand(1)
    affected_area = affectedAreaband.ReadAsArray(0, 0, affectedAreaSOURCE.RasterXSize, affectedAreaSOURCE.RasterYSize)
    
    
    #create the rgb png file 
    if tci_filepath == -1:
        pass
    else:
        RGB_SOURCE1 = gdal.Open(tci_filepath)
        red_srcband = RGB_SOURCE1.GetRasterBand(1)
        green_srcband = RGB_SOURCE1.GetRasterBand(2)
        blue_srcband = RGB_SOURCE1.GetRasterBand(3)
        rgbOutput = np.zeros((affectedAreaSOURCE.RasterYSize, affectedAreaSOURCE.RasterXSize, 3), 'uint8')
        red_arr = red_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        green_arr = green_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        blue_arr = blue_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        rgbOutput[:, :, 0] = np.copy(red_arr)
        rgbOutput[:, :, 1] = np.copy(green_arr)
        rgbOutput[:, :, 2] = np.copy(blue_arr)
    print('rgb initialized')    
    if event == 'fire':
        high_severity = np.where(affected_area == 4, True, False)
        medium_high_severity = np.where(affected_area == 3, True, False)
        medium_low_severity = np.where(affected_area == 2, True, False)
        low_severity = np.where(affected_area == 1, True, False)
        unburned = np.where(affected_area == 0, True, False)
        
        # initialize severity colors
        unburned_fill = (0, 255, 0)
        low_severity_fill = (255, 255, 0)
        medium_low_severity_fill = (255, 150, 10)
        medium_high_severity_fill = (230, 70, 5)
        high_fill = (170, 0, 105)
        
        # initialize severity colors - RGBA
        unburned_fill_RGBA= (0, 255, 0, 0)
        low_severity_fill_RGBA = (255, 255, 0, 255)
        medium_low_severity_fill_RGBA = (255, 150, 10, 255)
        medium_high_severity_fill_RGBA = (230, 70, 5, 255)
        high_fill_RGBA = (170, 0, 105, 255)
        print('Create output transparent files.')
        # create output files for transparent
        affectedAreaOutput = np.zeros((affectedAreaSOURCE.RasterYSize, affectedAreaSOURCE.RasterXSize, 4), 'uint8')
        affectedAreaOutput[unburned, :] = unburned_fill_RGBA
        affectedAreaOutput[low_severity, :] = low_severity_fill_RGBA
        affectedAreaOutput[medium_low_severity, :] = medium_low_severity_fill_RGBA
        affectedAreaOutput[medium_high_severity, :] = medium_high_severity_fill_RGBA
        affectedAreaOutput[high_severity, :] = high_fill_RGBA
        transparent_file_name = 'burned_area'
        print('Create output rbg files.')
        # create output files for rgb
        rgbOutput[low_severity, :] = low_severity_fill
        rgbOutput[medium_low_severity, :] = medium_low_severity_fill
        rgbOutput[medium_high_severity, :] = medium_high_severity_fill
        rgbOutput[high_severity, :] = high_fill
        rgb_file_name = 'burned_area_change'
    
    else:
        
        land = np.where(affected_area == 0, True, False)
        water = np.where(affected_area == 1, True, False)
        water_to_land_array = np.where(affected_area == 2, True, False)
        land_to_water_array = np.where(affected_area == 3, True, False)
        

        # Colors that will be used in the presentation
        land_fill = (127, 127, 127)
        water_fill = (0, 102, 102)
        land_to_water_fill = (0, 250, 250)
        water_to_land_fill = (210, 105, 30)
        
        # initialize land water transition colours  - RGBA
        land_fill_RGBA = (127, 127, 127, 0)
        water_fill_RGBA = (0, 102, 102, 0)
        land_to_water_fill_RGBA = (0, 250, 250, 255)
        water_to_land_fill_RGBA = (210, 105, 30, 255)

        # create output fles for transparent
        affectedAreaOutput = np.zeros((affectedAreaSOURCE.RasterYSize, affectedAreaSOURCE.RasterXSize, 4), 'uint8')
        affectedAreaOutput[land, :] = land_fill_RGBA
        affectedAreaOutput[water, :] = water_fill_RGBA
        affectedAreaOutput[land_to_water_array, :] = land_to_water_fill_RGBA
        affectedAreaOutput[water_to_land_array, :] = water_to_land_fill_RGBA
        transparent_file_name = 'water_change'

        # create output files for rgb
        rgbOutput[water_to_land_array, :] = water_to_land_fill
        rgbOutput[land_to_water_array,:] = land_to_water_fill
        rgb_file_name = 'water_area_change'
    temp_image_transparent = Image.fromarray(affectedAreaOutput)
    temp_image_transparent.save(os.path.join(destination_folder, transparent_file_name + '.png'))

    temp_image_rgb = Image.fromarray(rgbOutput)
    temp_image_rgb.save(os.path.join(destination_folder, rgb_file_name + '.png'))


def calculate_values_for_metadata(input_raster_path, event):
    affectedAreaSOURCE = gdal.Open(input_raster_path)
    affectedAreaband = affectedAreaSOURCE.GetRasterBand(1)
    affected_area = affectedAreaband.ReadAsArray(0, 0, affectedAreaSOURCE.RasterXSize, affectedAreaSOURCE.RasterYSize)
    if event == 'fire':
        high_severity = np.where(affected_area == 4, True, False)
        medium_high_severity = np.where(affected_area == 3, True, False)
        medium_low_severity = np.where(affected_area == 2, True, False)
        low_severity = np.where(affected_area == 1, True, False)
        unburned = np.where(affected_area == 0, True, False) 

        total_affected_area = round(((float(high_severity.sum() + medium_high_severity.sum() + medium_low_severity.sum() + low_severity.sum()) * 100) / 1000000), 2)
        high_severity_area = round(((float(high_severity.sum()) * 100) / 1000000), 2)
        medium_high_severity_area = round(((float(medium_high_severity.sum()) * 100) / 1000000), 2)
        medium_low_severity_area = round(((float(medium_low_severity.sum()) * 100) / 1000000), 2)
        low_severity_area = round(((float(low_severity.sum()) * 100) / 1000000), 2)
        return total_affected_area, high_severity_area, medium_high_severity_area, medium_low_severity_area, low_severity_area
    else:
        water_to_land_counter1 = (np.where(affected_area == 2, True, False)).sum()
        land_to_water_counter1 = (np.where(affected_area == 3, True, False)).sum()
        water_to_land_counter =  round(((float(water_to_land_counter1 ) * 100) / 1000000),2)
        land_to_water_counter =  round(((float(land_to_water_counter1) * 100) / 1000000),2)
        return water_to_land_counter, land_to_water_counter 

def create_metadata(before_date, after_date, input_raster_path, output_id, event_id, classes, destination_filepath, uncertainty_before, uncertainty_after, event):        
    affectedAreaSOURCE = gdal.Open(input_raster_path)
    affectedAreaband = affectedAreaSOURCE.GetRasterBand(1)
    affected_area = affectedAreaband.ReadAsArray(0, 0, affectedAreaSOURCE.RasterXSize, affectedAreaSOURCE.RasterYSize)
    
    export_dict = OrderedDict()
    analysis_status = OrderedDict()
    analysis_status["success"]= True
    analysis_status["message"]= ""
    export_dict["analysis_status"]=analysis_status
    task_info = OrderedDict()
    task_info["task_id"] = output_id
    task_info["event_id"] = event_id
    export_dict["task_info"] = task_info
    
    
    images = OrderedDict()
    images["before_download_link"] = '/static/' + output_id + '_before.png'
    images["after_download_link"] = '/static/' + output_id + '_after.png'
    if event == 'fire':
        images["dif_download_link"] = '/static/' + output_id + '_change.png'
        images["map_image_link"] = '/static/' + output_id + '_burned_area.png'
    else:
        images["dif_download_link"] = '/static/' + output_id + '_change.png'
        images["map_image_link"] = '/static/' + output_id + '_Water_change.png'
    images["bounds"] = GetExtent_latlon(affectedAreaSOURCE)
    export_dict["images"] = images
    
    metadata = OrderedDict()
    ds_raster = rasterio.open(input_raster_path)
    ds_raster.crs.to_epsg()
    metadata['platform'] = 'S2A, S2B'
    metadata['product_type'] = 'L2A'
    metadata['sensor_mode'] = 'MSI'
    metadata['title'] = 'Burned area change detection'
    # metadata['location_name'] = ''
    metadata['CRS'] = 'EPSG:{} - WGS 84 / UTM zone {}N'.format(ds_raster.crs.to_epsg(),
                                                                  ds_raster.crs.to_epsg() - 32600)
    metadata['pixel_size'] = [10, 10]
    metadata['Extent'] = GetExtent(affectedAreaSOURCE)
    element = datetime.datetime.strptime(before_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['start_date'] = int(time.mktime(tuple))
    element = datetime.datetime.strptime(after_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['end_date'] = int(time.mktime(tuple))
    
    metadata['uncertainty_lower'] = round(uncertainty_before, 2)
    metadata['uncertainty_upper'] = round(uncertainty_after, 2)
    if event == 'fire':

        total_affected_area, high_severity_area, medium_high_severity_area, medium_low_severity_area, low_severity_area = calculate_values_for_metadata(input_raster_path, event)
        metadata['total_affected_area'] = total_affected_area
        metadata['high_severity_area'] = high_severity_area
        metadata['medium_high_severity_area'] = medium_high_severity_area
        metadata['medium_low_severity_area'] = medium_low_severity_area
        metadata['low_severity_area'] = low_severity_area
        metadata['CLC_classes_affected_percentage_per_class'] = classes
    
    else:
        
        water_to_land_sqkm, land_to_water_sqkm = calculate_values_for_metadata(input_raster_path, event)
        
        if 'land_to_water_classes' in  classes.keys():                
            land_to_water_classes =  classes['land_to_water_classes'] 
        else:
            land_to_water_classes = {}
        if 'water_to_land_classes' in  classes.keys():                
            water_to_land_classes =  classes['water_to_land_classes'] 
        else:
            water_to_land_classes = {}
        
        metadata['water_to_land_area'] = water_to_land_sqkm 
        metadata['land_to_water_area'] = land_to_water_sqkm
        
        metadata['CLC_classes_land_to_water'] = land_to_water_classes
        metadata['CLC_classes_water_to_land'] = water_to_land_classes    
    ds_raster = 0
    #affectedAreaSOURCE = None
    export_dict['metadata'] = metadata
    metadata_path = os.path.join(destination_filepath, settings.metadata_file)
    with open(metadata_path, "w") as outfile:
        json.dump(export_dict, outfile, indent=4, sort_keys=False)       
    
    return metadata_path


#directory_for_final_pngs = '/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/final_images'
#create_png_images('/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/full_before_tci.tiff', os.path.join(directory_for_final_pngs, 'before_the_event.png'), 'fire')
#create_pngs_affected_area('/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/full_burned_area.tiff', '/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/full_before_tci.tiff', directory_for_final_pngs, 'fire')

def GetExtent_latlon(ds):
    '''
    Return list of corner coordinates from a gdal tiff file, converted from utm to degrees.   
    '''
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    crs = ds.GetProjection()
    #zone_letter = crs[28]
    #print(zone_letter)
    start = crs.find('UTM zone')
    if start:
        end = crs.find('",', start)
    #print(len(crs[start:end]))
    length = len((crs[start:end]))
    if length == 12: 
        zone_letter = crs[start + 11:end]
        zone_number = int(crs[start + 9:end -1])
    else:    
        zone_letter = crs[start + 10:end]
        zone_number = int(crs[start + 9:end -1])
    if zone_letter != 'N' and zone_letter != 'S': 
        zone_letter = 'N'  
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel
    #zone = utm.latlon_to_zone_number(lat, lon)
    if zone_letter == 'S':
        ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone_number, northern=False)
        ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone_number,  northern=False)
    else:
        ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone_number, zone_letter)
        ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone_number, zone_letter)
    return (ymax_conv, xmin_conv),  (ymin_conv, xmax_conv)



# get extent of the bounding box of a GeoTIFF raster file
def GetExtent(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel 
    return (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin) 

# find_tiles_extent(path_list)
#create_metadata('2022-08-12', '2022-09-12', '/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/full_affected_area.tiff', 'new_output',32, {}, '/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/final_images', 15, 23)    

# path_list = ['/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-04-03_2022-04-18_T34JBL/2022-04-03', '/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-04-03_2022-04-18_T34JBL/2022-04-18']
# products_id_list_safe = ['S2B_MSIL2A_20220403T082559_N0400_R021_T34JBL_20220403T123625.SAFE', 'S2A_MSIL2A_20220418T082611_N0400_R021_T34JBL_20220418T112354.SAFE']
# box_extent = 262782.7685868184780702, 339211.6153815748402849, 6581086.6067097093909979, 6619363.7795707946643233
# dates = ['2022-04-03', '2022-04-18'] 
# expand_and_download_tiles.box_belongs_to_tile(path_list, box_extent, dates, products_id_list_safe)   

#returned from algorithm: 18.5186452181213 -30.547366977344296, 19.32373566228174 -30.547366977344296, 19.32373566228174 -30.879756182844684, 18.5186452181213 -30.879756182844684, 18.5186452181213 -30.547366977344296)
#QGIS: 18.5272662528634768,-30.8892207982641693 : 19.3178102209830449,-30.5426008933626001


#calculate_land_cover_classes_glc_affected_area('/home/lefkats/snapearth_api/snapearth_api/output/California/full/LC100_global.tif', '/home/lefkats/snapearth_api/snapearth_api/output/California/full/full_burned_area.tiff', 'fire')
# water_dict = calculate_land_cover_classes_glc_affected_area('/home/lefkats/snapearth_api/snapearth_api/output/test_metadata/LC100_global.tif', '/home/lefkats/snapearth_api/snapearth_api/output/1NJ25RWYIC63CFE/water_change_2022-08-01_and_2022-08-31/water_change.tif', 'waterchange')
# print(water_dict)


# classes_w = calculate_land_cover_classes_glc_affected_area('/home/lefkats/snapearth_api/snapearth_api/output/KUVL5M125MKBR9O/full/LC100_global.tif', '/home/lefkats/snapearth_api/snapearth_api/output/KUVL5M125MKBR9O/full/full_water_change_area.tiff', 'water_change')
# print(classes_w)