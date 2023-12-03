import os
import subprocess
from osgeo import gdal
import shutil
import glob
import sys
import shapely

import settings
import tasks
import affected_area_api
from methods import search_products_functions, preprocess_functions, affected_area_functions, expand_and_download_tiles, expand_aoi_functions
from algorithm_burned_area.change_detection_functions import burned_area_change_detection
from algorithm_water_change_area.water_change_detection_main import water_change_main
import input_parameters

def search_vqa_products():
    """_summary_

    Returns:
        _type_: _description_
    """
    
    source = input_parameters.source
    satellite_image_id = input_parameters.product_id
    print(satellite_image_id)
    #Based on the satellite id given, the date and tile id will be extracted by the id. THe product will be downloaded by its id and the first image will be searched based on the date and tile.
    tile_id_image = satellite_image_id[38:44]
    date_id_image = satellite_image_id[11:15] + '-' + satellite_image_id[15:17] + '-' + satellite_image_id[17:19]
    dates = []
    products = []
    products_id_list = []

    try:
        print('The products\' query utilizing the image_id provided by the vqa source will start now.')
        products, tile_extend_box, message = search_products_functions.query_products_vqa(satellite_image_id, date_id_image, tile_id_image)
        if products == []:
            tasks.shared_tasks.tasks.shared_tasks.send_failure_response(message, source, satellite_image_id)
            return 0
        else:
            products_id_list.append(products[0].properties['id'])
            products_id_list.append(products[1].properties['id'])
            for el in products:
                dates.append(search_products_functions.return_date(el))
    except:
            tasks.shared_tasks.tasks.shared_tasks.send_failure_response("Error occured during quering. Products not available. Program will exit.", source, satellite_image_id)
    return products_id_list, dates,  products, tile_extend_box

def preprocess_vqa(path_list, products_id_list_safe, dates, tile_extend_box):
    """_summary_

    Args:
        path_list (list): a list with two paths. The paths in which the downloaded products are stored seperately for each date (before and after the event)
        products_id_list_safe (_type_): 
        dates (_type_): _description_
        tile_extend_box (_type_): _description_

    Returns:
        _type_: _description_
    """
    source = input_parameters.source
    satellite_image_id = input_parameters.product_id
    output_id = input_parameters.output_id
    event = input_parameters.event
 
    for path in path_list:
        index_path = path_list.index(path)
        for pr in products_id_list_safe[index_path]:
            if os.path.exists(os.path.join(path, pr, pr)):
                subprocess.call(["timeout", str(600), "mv", os.path.join(path, pr), os.getcwd()])
                subprocess.call(["timeout", str(600), "mv", os.path.join(os.getcwd(), pr, pr), path])
                subprocess.call(["timeout", str(600), "rm", "-rf", os.path.join(os.getcwd(), pr)])



    bbox = tile_extend_box
    polygon = shapely.geometry.box(*bbox, ccw=True)
    center_lat_long = polygon.centroid
    print(center_lat_long)
    type(center_lat_long)
    lat = center_lat_long.y
    long = center_lat_long.x
    
    try:
        tile_extend_box = preprocess_functions.create_buffer_zone_from_point_return_list_points([lat, long], settings.radius)
        process_complete_tile = False
    except:
        process_complete_tile = True
        #we will use the input bow returned from the product tile
        tile_extend_box = list(tile_extend_box)
        print("Input coordinate box could not be created. The whole image will be processed.")
    
    if process_complete_tile:
        current_AOI = [tile_extend_box[0], tile_extend_box[2], tile_extend_box[1],
                        tile_extend_box[3]]
    else:
        current_AOI = tile_extend_box

    for path in path_list:
        index_path = path_list.index(path)
        for pr in products_id_list_safe:
            try:
                ext_x_min, ext_x_max, ext_y_min, ext_y_max = preprocess_functions.change_crs_box(current_AOI, path + '/',
                                                                            [products_id_list_safe[index_path]])
                print(ext_x_min, ext_x_max, ext_y_min, ext_y_max)
            except:
                tasks.shared_tasks.send_failure_response("Problem occurred with the downloaded products.", source, satellite_image_id)
                return 0

    output_folder_name = satellite_image_id[38:44] + '_' + output_id
    main_process_path = os.path.join(os.getcwd(), 'output', event, output_folder_name)
    try:
        os.mkdir(main_process_path)
    except:
        pass
    
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
            tasks.shared_tasks.send_failure_response(f"Products could not be processed. The program will exit.", source, satellite_image_id)
            return 0    
    
    
        # if a LCLU thematic layer file is provided (e.x CLC2018), then another GeoTiff file with the CLC layer is generated for the AOI
        # CLC processing if you want to create a CLC layer for the area

        try:
            preprocess_functions.process_clc(current_AOI[0], current_AOI[3], current_AOI[1],
                                             current_AOI[2], main_process_path, product_date)
        except:
            tasks.shared_tasks.send_failure_response(f"CLC could not be created.", source, satellite_image_id)


        try:
            preprocess_functions.process_glc_global(current_AOI[0], current_AOI[3], current_AOI[1],
                                             current_AOI[2], main_process_path, product_date)
        except:
            tasks.shared_tasks.send_failure_response(f"Global land cover could not be created could not be created.", source, satellite_image_id)
    return main_process_path



   