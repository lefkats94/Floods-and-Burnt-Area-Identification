"""
This module contains the functions needed for the preprocessing of the .SAFE products, so as to be in the correct format to be used for the affected area modules.
Most of the functions have been derived from SnapEarthDataFetching and preprosessing-S2 modules (author Michail Sismanis) and have been modified slightly so as to be adapted to the needs of the current work. 


The .SAFE files include the data imagery in jp2 format, thus the conversion to tiff is necessary. Additionally, each band is clipped given the extent of the bbox, which has been created 
from the create_buffer_zone_from_point_return_list_points(). The extent of the bbox that the function returns, is given as input to preprocess_product so as to clip the tile (or tiles). 

The proprocess_clc() and preprocess_clc_global() functions are used so as to create a land cover map for the area of interest and derive afterwards the classes that have been affected by the event  (flood or fire).  

The change_crs_box() function, converts the extent of the bbox from WGS84 epsg: 4087 to WGS84 UTM zone crs (Sentinel products are using the latter). Additionally, checks if the products have the same georeference. (this was implemented the 
inside the older version of preprocess_S2() function thus we kept this here. (It should be noted that changes can be made so as the conversion of the coordinates to be implemented in a separate function.))
"""

import os
import subprocess
import pandas as pd
import numpy as np
import sys
import gdal_merge as gm
import shutil
import rasterio
import fiona
import glob
import utm
import shapely
from shapely.geometry import box
from shapely.geometry import Point
from osgeo import gdal
#from decimal import Decimalconda
# keeps the higher res bands, trims to extent, converts to tif and saves them.

def pre_process_product(products_extracted_dir, products_processed_dir, product_identifier_names_list,
                        product_date, ext_x_min, ext_y_max, ext_x_max, ext_y_min):
    """
    The preprocessing of all the products contained in IMG_DATA folders is executed (author Michail Sismanis). 
    Conversion from jp2 to tiff, clip in the given extent, merge and mosaic in case of multiple tiles. 
    Some modifications have been made in the way gdal_merge is being called. (The older version is in comments).
    
    """                    
    # bands_required = ["B02", "B03", "B04", "B05", "B07", "B08", "B11", "SCL", "TCI"]
    bands_required = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12", "SCL",
                      "TCI"]

    k = []

    for each_prod_id_name in product_identifier_names_list:

        bands = []
        resolutions = []
        filepaths = []

        #product_identifier_name = each_prod_id_name + '.SAFE'
        product_identifier_name = each_prod_id_name
        sub_folder_granule = products_extracted_dir + product_identifier_name + "/GRANULE/"
        sub_product = os.listdir(sub_folder_granule)

        R10m_folder = sub_folder_granule + sub_product[0] + "/IMG_DATA/R10m/"
        listings10m = os.listdir(R10m_folder)
        for each_band_file in listings10m:
            each_band_file_proc = os.path.splitext(each_band_file)[0].split("_")
            bands.append(each_band_file_proc[-2])
            resolutions.append(each_band_file_proc[-1])
            filepaths.append(R10m_folder + each_band_file)

        R20m_folder = sub_folder_granule + sub_product[0] + "/IMG_DATA/R20m/"
        listings20m = os.listdir(R20m_folder)
        for each_band_file in listings20m:
            each_band_file_proc = os.path.splitext(each_band_file)[0].split("_")
            bands.append(each_band_file_proc[-2])
            resolutions.append(each_band_file_proc[-1])
            filepaths.append(R20m_folder + each_band_file)

        R60m_folder = sub_folder_granule + sub_product[0] + "/IMG_DATA/R60m/"
        listings60m = os.listdir(R60m_folder)
        for each_band_file in listings60m:
            each_band_file_proc = os.path.splitext(each_band_file)[0].split("_")
            bands.append(each_band_file_proc[-2])
            resolutions.append(each_band_file_proc[-1])
            filepaths.append(R60m_folder + each_band_file)

        df = pd.DataFrame({'band': bands,
                           'res': resolutions,
                           'path': filepaths})
        k.append(df.sort_values(by=['res'], ascending=True).groupby('band').first())

    save_result_file_path_name = products_processed_dir  + '/' + product_date

    if not os.path.exists(save_result_file_path_name):
        os.makedirs(save_result_file_path_name)

    df_indexes = k[0].index.values
    num_of_sub_products = len(product_identifier_names_list)

    #aoi_extent_merge = ['-ul_lr', str(ext_x_min), str(ext_y_max), str(ext_x_max), str(ext_y_min)]

    for each_band in df_indexes:
        if each_band in bands_required:
            print("Merging band: " + each_band)

            list_of_paths_for_band = []
            for each_product in range(num_of_sub_products):
                list_of_paths_for_band.append(k[each_product].loc[each_band, 'path'])
            # merge and change extent
            if os.path.isfile(each_band + '.tif'):
                os.remove(each_band + '.tif')
            print('yes')
            #sys.argv = ['-o'] + list_of_paths_for_band + aoi_extent_merge + ['-n', "0"]
            #gm.main()
            subprocess.call(['python', 'gdal_merge.py', '-ul_lr',  str(ext_x_min), str(ext_y_max), str(ext_x_max), str(ext_y_min)] +  list_of_paths_for_band)
            os.rename('out.tif', each_band + '.tif')
            shutil.move(each_band + '.tif', save_result_file_path_name + '/' + each_band + '.tif')


def process_clc(ext_x_min, ext_y_max, ext_x_max, ext_y_min, products_processed_dir,  product_date):
    """
    If the "CLC2018" corine land cover file exists for each product a CLC.tiff file is generated. 
    """
    lc_filepath = False
    if os.path.exists((os.path.join(os.getcwd(), 'CLC2018'))):
        print("yes")
        clc_filepath = glob.glob(os.path.join(os.getcwd(), 'CLC2018', '*.tif'))[0]
        save_result_file = products_processed_dir + '/' + product_date + '/' + 'CLC.tif'
        os.system(
            'gdal_translate -epo -projwin {} {} {} {} -of GTiff {} {}'.format(ext_x_min, ext_y_max, ext_x_max, ext_y_min,
                                                                         clc_filepath, save_result_file))
        #os.system('gdalwarp -t_srs EPSG:{} {} {}'.format(ds_raster.crs.to_epsg(), save_result_file, save_result_file))                                                                        
        lc_filepath = True
    return lc_filepath








def process_glc_global(ext_x_min, ext_y_max, ext_x_max, ext_y_min,  products_processed_dir,  product_date):
    """
        If the "LC100_GLOBAL.tiff" file exists for each product a LC100_global.tif file is generated This will b used in case the corine land cover does not exist or is outside of Europe. 
    """
    gl_lc_filepath = False
    global_cover_filepath = os.path.join(os.getcwd(), 'LC100_GLOBAL', 'PROBAV_LC100_global_v3.0.1_2019-nrt_Discrete-Classification-map_EPSG-4326.tif')
    if os.path.exists(global_cover_filepath):    
        save_result_file =  products_processed_dir + '/' + product_date +  '/' + 'LC100_global.tif'
        os.system('gdal_translate -epo -projwin {} {} {} {} -of GTiff {} {}'.format(ext_x_min, ext_y_max, ext_x_max, ext_y_min, global_cover_filepath, save_result_file))
        gl_lc_filepath = True
    return gl_lc_filepath

# to ensure the correct wkt_guidance of the output files we check all the wkt_guidance of the Sentinel-2 extracted raw products
def change_crs_box(input_coordinate_box, products_extracted_dir, products_list_safe):
    #bounds = box_clip.bounds
    #ext_x_min, ext_y_min, ext_x_max, ext_y_max = box(*bounds)
    current_AOI = [input_coordinate_box[0], input_coordinate_box[1], input_coordinate_box[2], input_coordinate_box[3]]
    print(current_AOI)
    # x_min, x_max, y_min, y_max of current_AOI[0][5-8]
    # convert coordinate system
    test1 = utm.latlon_to_zone_number(current_AOI[3], current_AOI[0])
    test2 = utm.latlon_to_zone_number(current_AOI[2], current_AOI[1])
    print(products_list_safe)
    print(products_extracted_dir)
    if len(os.listdir(products_extracted_dir)) > 1:
        utm_dict = {}
        #for extracted_product in os.listdir(products_extracted_dir):
        for extracted_product in products_list_safe:
            guidance_folder = products_extracted_dir + extracted_product \
                              + '/GRANULE' + '/' \
                              + os.listdir(
                products_extracted_dir + extracted_product + '/GRANULE')[0] \
                              + '/IMG_DATA/R10m'
            tif_file = os.listdir(guidance_folder)[1]
            tif_file = os.path.join(guidance_folder, tif_file)
            source = gdal.Open(tif_file)
            wkt_guidance = source.GetProjection()
            print(wkt_guidance)
            start =wkt_guidance.find('UTM zone')
            
            if start:
                end = wkt_guidance.find('",', start)
            print(len(wkt_guidance[start:end]))
            length = len((wkt_guidance[start:end]))
           
            if length == 12: 
                zone_letter = wkt_guidance[start + 11:end]
                forced_zone_number = wkt_guidance[start + 9:end -1]
            else:    
                zone_letter = wkt_guidance[start + 10: end]
                forced_zone_number = wkt_guidance[start + 9:end -1]
            print(zone_letter)
            print(forced_zone_number)
            
            # start = wkt_guidance.find('UTM')
            # if start:
            #     end = wkt_guidance.find('N', start)
            #     forced_zone_number = wkt_guidance[end - 2:end]
            if forced_zone_number in utm_dict.keys():
                utm_dict[forced_zone_number] += utm_dict[forced_zone_number] + 1
            else:
                utm_dict[forced_zone_number] = 1

        max = 0
        final_key = 0
        for k in utm_dict.keys():
            if utm_dict[k] > max:
                max = utm_dict[k]
                final_key = k
        forced_zone_number = final_key

        for k in utm_dict.keys():
            if utm_dict[k] == max and not k == final_key:
                for l in utm_dict.keys():
                    if utm_dict[l] == max and l == str(test1):
                        final_key = l
                        forced_zone_number = final_key
        print(forced_zone_number)
        utm_upper_left = utm.from_latlon(current_AOI[3], current_AOI[0], int(forced_zone_number))
        utm_lower_right = utm.from_latlon(current_AOI[2], current_AOI[1], int(forced_zone_number))

    else:
        guidance_folder = products_extracted_dir + os.listdir(products_extracted_dir)[0] \
                          + '/GRANULE' + '/' \
                          + os.listdir(
            products_extracted_dir + os.listdir(products_extracted_dir)[0] + '/GRANULE')[0] \
                          + '/IMG_DATA/R10m'
        tif_file = os.listdir(guidance_folder)[1]
        tif_file = os.path.join(guidance_folder, tif_file)
        source = gdal.Open(tif_file)
        wkt_guidance = source.GetProjection()
        print(wkt_guidance)
        start =wkt_guidance.find('UTM zone')
        if start:
            end = wkt_guidance.find('",', start)
        print(len(wkt_guidance[start:end]))
        length = len((wkt_guidance[start:end]))
        
        if length == 12: 
            zone_letter = wkt_guidance[start + 11:end]
            forced_zone_number = wkt_guidance[start + 9:end -1]
        else:    
            zone_letter = wkt_guidance[start + 10: end]
            forced_zone_number = wkt_guidance[start + 9:end -1]
        print(zone_letter)
        print(forced_zone_number)
        # start = wkt_guidance.find('UTM')
        # if start:
        #     end = wkt_guidance.find('N', start)
        #     forced_zone_number = wkt_guidance[end - 2:end]

        utm_upper_left = utm.from_latlon(current_AOI[3], current_AOI[0], int(forced_zone_number))
        utm_lower_right = utm.from_latlon(current_AOI[2], current_AOI[1], int(forced_zone_number))

    ext_y_max_utm = utm_upper_left[1]
    ext_x_min_utm = utm_upper_left[0]
    ext_y_min_utm = utm_lower_right[1]
    ext_x_max_utm = utm_lower_right[0]

    # if for some reason the extents of the area are not calculated correctly, they can be hard set here
    # ext_y_max =
    # ext_x_min =
    # ext_y_min =
    # ext_x_max =

    # check for possible errors and try to fix them
    if ext_y_max_utm < 0 or ext_x_min_utm < 0 or ext_y_min_utm < 0 or ext_x_max_utm < 0:
        utm_upper_left = utm.from_latlon(current_AOI[0][8], current_AOI[0][5])
        utm_lower_right = utm.from_latlon(current_AOI[0][7], current_AOI[0][6])
        ext_y_max_utm = utm_upper_left[1]
        ext_x_min_utm = utm_upper_left[0]
        ext_y_min_utm = utm_lower_right[1]
        ext_x_max_utm = utm_lower_right[0]
    print(ext_x_max_utm, ext_x_min_utm)
    return ext_x_min_utm, ext_x_max_utm, ext_y_min_utm, ext_y_max_utm



def create_buffer_zone_from_point(point, buffer_radius=5):
    point[0] = float(point[0])
    point[1] = float(point[1])

    offset = float(buffer_radius) / 1.853
    offset_minutes = int(offset)
    offset_seconds = round((buffer_radius - 1.853 * offset_minutes) / 0.03)
    offset_dd = float(offset_minutes) / 60 + float(offset_seconds) / 3600

    # temp1 = utm.latlon_to_zone_number(point[1], point[0])
    # temp2 = utm.latitude_to_zone_letter(point[1])
    # temp3 = utm.from_latlon(point[1],point[0])

    temp4 = (point[1] - offset_dd, point[0] - offset_dd)
    temp5 = (point[1] + offset_dd, point[0] + offset_dd)
    ext_x_min = temp4[0]
    ext_x_max = temp5[0]
    ext_y_min = temp4[1]
    ext_y_max = temp5[1]

    p1 = Point(ext_x_min, ext_y_min)
    p2 = Point(ext_x_min, ext_y_max)
    p3 = Point(ext_x_max, ext_y_max)
    p4 = Point(ext_x_max, ext_y_min)
    points = [p1, p2, p3, p4]
    polygon = shapely.geometry.Polygon(points)
    return polygon,

def create_buffer_zone_from_point_return_list_points(point, buffer_radius = 5):

    point[0] = float(point[0])
    point[1] = float(point[1])


    offset = float(buffer_radius)/1.853
    offset_minutes = int(offset)
    offset_seconds = round((buffer_radius - 1.853*offset_minutes)/0.03)
    offset_dd = float(offset_minutes) / 60 + float(offset_seconds) / 3600

    # temp1 = utm.latlon_to_zone_number(point[1], point[0])
    # temp2 = utm.latitude_to_zone_letter(point[1])
    # temp3 = utm.from_latlon(point[1],point[0])


    temp4 = (point[1]- offset_dd, point[0]- offset_dd)
    temp5 = (point[1]+ offset_dd, point[0] + offset_dd)
    ext_x_min = temp4[0]
    ext_x_max = temp5[0]
    ext_y_min = temp4[1]
    ext_y_max = temp5[1]

    return [ext_x_min, ext_x_max, ext_y_min, ext_y_max]

# keeps the higher res bands, trims to extent, converts to tif and saves them.
def process_clc_with_input_raster(path_for_input_raster, path_to_save):
    """
    If the "CLC2018" corine land cover file exists for each product a CLC.tiff file is generated. 
    The extent of the area is extracted from the box of the input raster file and the coversion also takes place.
    """
   
    if os.path.exists((os.path.join(os.getcwd(), 'CLC2018'))):
        print("yes")
        clc_filepath = glob.glob(os.path.join(os.getcwd(), 'CLC2018', '*.tif'))[0]
    save_result_file = path_to_save  + '/' + 'CLC.tif'


    ds_raster = rasterio.open(path_for_input_raster)
    bounds = ds_raster.bounds
    ext_x_min = bounds.left
    ext_y_min = bounds.bottom
    ext_x_max = bounds.right
    ext_y_max = bounds.top
    source = gdal.Open(path_for_input_raster)
    wkt_guidance = source.GetProjection()
    print(wkt_guidance)
    print(ext_x_max, ext_x_min, ext_y_max, ext_y_min)
    print(ds_raster.crs)
    # CLC processing if you want to create a CLC layer for the area
    zone_number = ds_raster.crs.to_epsg() - 32600
    print(zone_number)
    ext_y_min, ext_x_min = utm.to_latlon(ext_x_min, ext_y_min, zone_number, northern=True)
    ext_y_max, ext_x_max = utm.to_latlon(ext_x_max, ext_y_max, zone_number, northern=True)
    del ds_raster 
    os.system(
        'gdal_translate -eco -projwin {} {} {} {} -of GTiff {} {}'.format(ext_x_min, ext_y_max, ext_x_max, ext_y_min,
                                                                    clc_filepath, save_result_file))
    if os.path.exists(save_result_file):
        source_clc = gdal.Open(save_result_file)                                                                
        array_clc = source_clc.GetRasterBand(1).ReadAsArray()
        #check that the file has been created correctly
        if np.max(array_clc) == 0:
            os.remove(save_result_file)                                                         
    #os.system('gdalwarp -t_srs EPSG:{} {} {}'.format(ds_raster.crs.to_epsg(), save_result_file, save_result_file))

def process_glc_with_input_raster(path_for_input_raster, path_to_save):
    """
    If the "CLC2018" corine land cover file exists for each product a CLC.tiff file is generated. 
    The extent of the area is extracted from the box of the input raster file and the coversion also takes place.
    """
   
    if os.path.exists((os.path.join(os.getcwd(), 'LC100_GLOBAL'))):
        print("yes")
        global_cover_filepath = os.path.join(os.getcwd(), 'LC100_GLOBAL', 'PROBAV_LC100_global_v3.0.1_2019-nrt_Discrete-Classification-map_EPSG-4326.tif')
    save_result_file = path_to_save  + '/' + 'LC100_global.tif'

    print('here')
    ds_raster = rasterio.open(path_for_input_raster)
    bounds = ds_raster.bounds
    ext_x_min = bounds.left
    ext_y_min = bounds.bottom
    ext_x_max = bounds.right
    ext_y_max = bounds.top
   

    #processing if you want to create a land cover layer for the area
    zone_number = ds_raster.crs.to_epsg() - 32600
    print(zone_number)
    ext_y_min, ext_x_min = utm.to_latlon(ext_x_min, ext_y_min, zone_number, northern=True)
    ext_y_max, ext_x_max = utm.to_latlon(ext_x_max, ext_y_max, zone_number, northern=True)
   
    os.system(
        'gdal_translate -epo -projwin {} {} {} {} -of GTiff {} {}'.format(ext_x_min, ext_y_max, ext_x_max, ext_y_min,
                                                                    global_cover_filepath, save_result_file))
    if os.path.exists(save_result_file):
        source_clc = gdal.Open(save_result_file)                                                                
           
    #os.system('gdalwarp -t_srs EPSG:{} {} {}'.format(ds_raster.crs.to_epsg(), save_result_file, save_result_file))

#pre_process_product( 660644.5203585431, 668227.783235494, 4797317.555201362, 4807196.098522927)
# dates = ['2022-07-02', '2022-07-17']
# def test():
#     output_folder_name = os.path.join(os.getcwd(), 'test')
#     #os.mkdir(output_folder_name)
#     ext_x_min, ext_x_max, ext_y_min, ext_y_max  = 660644.5203585431, 668227.783235494, 4797317.555201362, 4807196.098522927
#     path_list = ['/home/lefkats/snapearth_api/snapearth_api/Input_2022-07-02_2022-07-17_T32TPN_T32TPP/2022-07-02' , '/home/lefkats/snapearth_api/snapearth_api/Input_2022-07-02_2022-07-17_T32TPN_T32TPP/2022-07-17']
#     for path in path_list:
#         print(path)
#         # print(number_tiles[path_list.index(path)])
#         # if number_tiles[path_list.index(path)] == 1:
#         #     for i in range(len(products_id_list_safe[path_list.index(path)])):
#         #         product_date = dates[path_list.index(path)]
#         #         print(product_date)
#         #         try:
#         #             preprocess_functions.pre_process_product(path + '/', output_folder_name + '/', [products_id_list_safe[path_list.index(path)][i]],
#         #             product_date, ext_x_min, ext_y_max, ext_x_max, ext_y_min)
#         #         except:
#         #             send_failure_response(f"Product {products_id_list_safe[i]} could not be processed. The program will exit.", source, event_id)
#         #             return 0
#         #else:
#             #list = os.listdir(raw_data_path)
#             #for j in range(len(list)):
#             #temp_path = os.path.join(raw_data_path, list[j])
#         temp_path = path
#         print(temp_path)
#         product_list = os.listdir(temp_path)
#         print(product_list)
#         product_date = dates[path_list.index(path)]
#         print(product_date)
#         pre_process_product(temp_path + '/', output_folder_name + '/',
#                                                     product_list, product_date, ext_x_min, ext_y_max, ext_x_max, ext_y_min)
       
# test()           

#process_clc_with_input_raster('/home/lefkats/snapearth_api/snapearth_api/output/new_output/full/full_burned_area.tiff', os.getcwd())
#process_glc_with_input_raster('/home/lefkats/snapearth_api/snapearth_api/output/California/full/full_burned_area.tiff', os.getcwd())
#process_path = '/home/lefkats/snapearth_api/snapearth_api/output/new_output'
#final_product_burned_array_path = os.path.join(process_path + "/full/full_burned_area.tiff")
# process_clc_with_input_raster(final_product_burned_array_path, process_path + "/full")
# process_glc_with_input_raster(final_product_burned_array_path, process_path + "/full")


#calculate land cover classes affected_from the burnt area
# clc_filepath = os.path.join(process_path, "full", 'CLC.tif')
# glc_filepath = os.path.join(process_path, "full", 'LC100_global.tif')

#check if clc filepath exists and calculate fire_classes, otherwise check if glc cover exists and calculate fire classes.
# if os.path.exists(clc_filepath):
#     fire_clases = expand_aoi_functions.calculate_land_cover_classes_clc_burned_area(clc_filepath, final_product_burned_array_path)
# elif os.path.exists(glc_filepath):
#     fire_clases = expand_aoi_functions.calculate_land_cover_classes_glc_burned_area(glc_filepath, final_product_burned_array_path)
# else:
#     fire_clases = {}
# print(fire_clases)  
# 
# import expand_aoi_functions
# #process_glc_with_input_raster('/home/lefkats/snapearth_api/snapearth_api/output/1NJ25RWYIC63CFE/water_change_2022-08-01_and_2022-08-31/water_change.tif', '/home/lefkats/snapearth_api/snapearth_api/output/test_metadata')  
# water_dict = expand_aoi_functions.calculate_land_cover_classes_glc_affected_area('/home/lefkats/snapearth_api/snapearth_api/output/test_metadata/LC100_global.tif', '/home/lefkats/snapearth_api/snapearth_api/output/1NJ25RWYIC63CFE/water_change_2022-08-01_and_2022-08-31/water_change.tif', 'waterchange')
# print(water_dict)


#process_clc_with_input_raster('/home/lefkats/snapearth_api/snapearth_api/output/1NJ25RWYIC63CFE/water_change_2022-08-01_and_2022-08-31/water_change.tif', os.getcwd())
#process_clc_with_input_raster('/home/lefkats/snapearth_api/snapearth_api/output/0BAJ8KNG8LBZSSI/0/fire_change_2022-07-02_and_2022-07-17/χ_y.tif', os.getcwd())