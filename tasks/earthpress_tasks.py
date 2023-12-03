import os
import subprocess
from osgeo import gdal
import shutil
import glob
import sys

import settings
import tasks
import affected_area_api
from methods import search_products_functions, preprocess_functions, affected_area_functions, expand_and_download_tiles, expand_aoi_functions
import input_parameters 


def search_earthpress_products():
    """Search Sentinel-2 L2A products for a date before the event and a date after the event.

    Returns:
        products_id_list (list): Includes two lists. The first contains the products_ids of the products that needed to be downloaded, 
        for the date before and the second for the date after the event.   
        dates (list of str): The before and after date (yy-mm-dd) of the event
        products (list of lists of objs): Includes two lists. For each date a list with the products -as they returned from eodag search so as to be downloaded- is returned.
    
    """
    
    lat = input_parameters.lat
    lon = input_parameters.lon
    date = input_parameters.date
    source = input_parameters.source
    event_id = input_parameters.event_id
    products_id_list = [] 
    dates = [] 
    products = []
    central_coos = [lat, lon]	
    print(f'The central_coordinates of the area of interest are {central_coos}.')
    
    try:
        print('The products\' query will start now.')
        products_id_list, dates, products, number_tiles, message = search_products_functions.query_products_earthpress(date, central_coos)
    
        #in case products have not been found, the lists are empty and the related message is being send through the tasks.shared_tasks.send_failure_response function.
        if products_id_list[0] == [] or products_id_list[1] == []:
            tasks.shared_tasks.send_failure_response(message, source, event_id)
            
    except:
        tasks.shared_tasks.send_failure_response("Unexpected error occured during quering. Program will exit.", source, event_id)
    return products_id_list, dates, products

def preprocess_earthpress(path_list, products_id_list_safe, dates):
    """Convert jp2 to tiff, 
    clip all bands based on the area of interested. 
    (aoi: the bbox is created from the lat, lon given, and a radius (defined in settings.py))

    Args:
        path_list (list): includes the paths to the folders where the raw satellite products have been downloaded. One path for each date. 
        products_id_list_safe (list): Same with the products_id_list with the .SAFE ending
        dates (list): The before and after date (yy-mm-dd) of the event

    Returns:
        main_process_path (str): The path where the processed products will be stored. 
    """
    lat = input_parameters.lat
    lon = input_parameters.lon
    event_id = input_parameters.event_id
    source = input_parameters.source
    event = input_parameters.event
    output_id = input_parameters.output_id
    main_process_path = ""
    #Create the input coordinate box from the central coos and the radius. The result (the extent) is returned in latitude, longitude. WGS84, EPSG:4326 
    try:
        input_coordinate_box = preprocess_functions.create_buffer_zone_from_point_return_list_points([lat,lon], settings.radius)
        print(input_coordinate_box)
    except:
        tasks.shared_tasks.send_failure_response("Error occured during the creation of the polygon which clips the images in the area of interest. Program will exit.", source, event_id)
        

    #The output of preprocessing for each product will be stored in the path '/output/output_folder_name' as well as the final result
    output_folder_name = str(event_id) + '_' + output_id
    #process path is the path to the output_folder_name directory. This directory includes two folders, named by the before and after dates and the results_folder.
    #The two folders include the tiff files for each date clipped by the box. The results_folder will include the results which are produced by processing the tiff files.
    main_process_path = os.path.join(os.getcwd(), 'output', event, output_folder_name)
    try:
        os.mkdir(main_process_path)
    except:
        pass
    
    for path in path_list:
        index_path = path_list.index(path)
        for pr in products_id_list_safe[index_path]:
            if os.path.exists(os.path.join(path, pr, pr)):
                subprocess.call(["timeout", str(600), "mv", os.path.join(path, pr), os.getcwd()])
                subprocess.call(["timeout", str(600), "mv", os.path.join(os.getcwd(), pr, pr), path])
                subprocess.call(["timeout", str(600), "rm", "-rf", os.path.join(os.getcwd(), pr)])
    
    #The input_coordinate_box is in lat, long, thus the change_crs_box() function is called in order to convert the coos to the crs of the satellite images.
    for path in path_list:
        index_path = path_list.index(path)    
        try:
            ext_x_min, ext_x_max, ext_y_min, ext_y_max = preprocess_functions.change_crs_box(input_coordinate_box, path + '/', products_id_list_safe[index_path])
            print(ext_x_min, ext_x_max, ext_y_min, ext_y_max)
        except:
            tasks.shared_tasks.send_failure_response("Problem occurred with the downloaded products. Please check the .SAFE files", source, event_id)
            
           
    #use the pre_process_product_() function from the module: preprocess functions, to convert the jp2 files to tiff and clip the area to the extend (ext_x_min, ext_x_max, ext_y_min, ext_y_max)
    for path in path_list:
        index_path = path_list.index(path)
        print(path)
        #extract the date from the path
        product_date = dates[index_path]
        #products_id_list_safe to check if the products are in the list 
        product_list = [el for el in os.listdir(path) if el in products_id_list_safe[index_path]]
        try:
            preprocess_functions.pre_process_product(path + '/', main_process_path,
                                                    product_list, product_date, ext_x_min, ext_y_max, ext_x_max, ext_y_min)
        except:
            tasks.shared_tasks.send_failure_response(f"Products could not be processed. The program will exit.", source, event_id)
            
        
        #use the functions process_clc() or process_glc_global() from module:preprocess functions to create a land cover classification map.                                               
        #if a LCLU thematic layer file is provided (e.x CLC2018), then another GeoTiff file with the CLC layer is generated for the AOI

        try:
            preprocess_functions.process_clc(input_coordinate_box[0], input_coordinate_box[3], input_coordinate_box[1],
                                         input_coordinate_box[2], main_process_path, product_date)
        except:
            tasks.shared_tasks.send_failure_response(f"CLC could not be created.", source, event_id)
        try:
            preprocess_functions.process_glc_global(input_coordinate_box[0], input_coordinate_box[3], input_coordinate_box[1],
                                         input_coordinate_box[2], main_process_path, product_date)
        except:
            tasks.shared_tasks.send_failure_response(f"Global land cover could not be created could not be created.", source, event_id)
    return main_process_path
