from datetime import datetime
import string
import random
import json
from collections import OrderedDict
import requests
import settings
import os
from osgeo import gdal
import glob
import shutil

from methods import search_products_functions, download_products_functions, affected_area_functions, expand_and_download_tiles, expand_aoi_functions, preprocess_functions
from algorithm_burned_area.change_detection_functions import burned_area_change_detection
from algorithm_water_change_area.water_change_detection_main import water_change_main
import input_parameters
from tasks import main_tasks, shared_tasks 
import sys

def validate_parameters(event, source, lat, lon, date, product_id):
    """Validate the parameters received by the user request

    Args:
        event (int): _description_
        source (int): _description_
        lat (float): _description_
        lon (float): _description_
        date (str): _description_
        product_id (str): _description_

    Returns:
        response_data (dict):
        date_str (str) : _description_
    """
    # Initializing lists of choices
    possible_events = ['fire', 'waterchange']
    possible_services = ['earthpress','vqa']
    # Validating Parameters
    if event not in possible_events:
        return 'Wrong input: event not in possible events, possible events: "fire" or "waterchange".', 400
    if source not in possible_services:
        return 'Wrong input: source not in possible services, possible sources: "earthpress" or "vqa".', 400

    if source == 'earthpress':
        if lat<-90 or lat>90 or lon<-180 or lon>180:
            return 'Wrong input: invalid latitude or longitude values', 400
        print(type(date))
        if date//(10**9) < 1:
            return 'Wrong input: the integer part of timestamp must be at least 10 digits long', 400
        if date > datetime.timestamp(datetime.now()) or date < datetime.timestamp(datetime(2000, 1, 1, 20)):
            return 'Wrong input: invalid date value', 400
        #date_str = datetime.utcfromtimestamp(date).strftime("%Y-%m-%d")    
    else:
        if product_id == None:
            return 'Wrong input: Product id is necessary for the vqa service', 400

    output_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))	
    response_data = {'task_id': output_id, 'event': event}
    return response_data



def return_url(source):
    """Return the endpoint url to post the results based on the source of the request

    Args:
        source (str): _description_

    Returns:
        url (str): _description_
    """
    if source == "vqa":
        url = settings.vqa_response_url
    else:
        url = settings.earthpress_response_url
    return url

def create_directories(products_id_list, dates):
    """Create the directories where the satellite products will be downloaded.
        Example of a directory:
    Args:
        products_id_list (_type_): _description_
        dates (_type_): _description_

    Returns:
        _type_: _description_
    """
    localpath = os.getcwd()
    source = input_parameters.source
    if source == 'earthpress':
        tile_id = []
        for el in products_id_list[0]:
            tile_id.append(el[38:44])
        tile_id_string = tile_id[0]
        for ts in tile_id[1:]:
            tile_id_string = tile_id_string + '_' + ts
    else:   
        satellite_image_id = input_parameters.product_id
        tile_id_string = satellite_image_id[38:44] 
    
    input_folder_name = 'Input' + '_' + dates[0] + '_' + dates[1] + '_' + tile_id_string
    raw_data_path = os.path.join(localpath, 'input', input_folder_name)
    date_before_path = os.path.join(raw_data_path, dates[0])
    date_after_path = os.path.join(raw_data_path, dates[1])
    
    try:
        os.mkdir(raw_data_path)
    except:
        pass
    try:
        os.mkdir(date_before_path)
    except:
        pass
    try:
        os.mkdir(date_after_path)
    except:
        pass
    print(f'The downloaded and extracted products are stored into {raw_data_path} directory.')

    return [date_before_path, date_after_path]

def download_sentinel2_products(path_list, products_id_list, products):
    """_summary_

    Args:
        path_list (_type_): _description_
        products_id_list (_type_): _description_
        products (_type_): _description_

    Returns:
        _type_: _description_
    """
    source = input_parameters.source
    if source == 'earthpress':
        event_or_product_id = input_parameters.event_id
        products_id_list_safe = []
        temp = [pr + '.SAFE' for pr in products_id_list[0]]
        products_id_list_safe.append(temp)
        temp = [pr + '.SAFE' for pr in products_id_list[1]]
        products_id_list_safe.append(temp)
    else:
        event_or_product_id = input_parameters.product_id
        
        products_id_list_safe = [pr + '.SAFE' for pr in products_id_list]
        

    
    #Download each product included in the two products lists, for the date before and after the event. Check if the product already exists.
    for path in path_list:
        products_already_downloaded = os.listdir(path)
        index_path = path_list.index(path)
        if source == 'earthpress':
            for pr in products_id_list_safe[index_path]:
                if pr in products_already_downloaded:
                    print(pr + " product is already downloaded. Preprocessing will now take place.")
                else:
                    if not download_products_functions.download_from_ENS(pr, settings.username, settings.password, path):
                        if search_products_functions.download_products(products[index_path][products_id_list[index_path].index(pr)], path):
                            print("Product " + pr + " downloaded successfully." )
                        else:
                            print("Product " + pr + "could not be downloaded neither from ONDA ENS nor from onda catalogue. The program will exit.")
                            send_failure_response("The requested satellite products could not be downloaded neither from ONDA ENS nor from onda catalogue. The program will exit.", source, event_or_product_id)
                    else:
                        print(f'The product {pr} was copied and extracted successfully from ONDA ENS. Preprocessing will now take place.')
        else:
            pr = products_id_list_safe[index_path]
            if pr in products_already_downloaded:
                print(pr + " product is already downloaded. Preprocessing will now take place.")
            else:
                if not download_products_functions.download_from_ENS(pr, 'afroditikita@gmail.com', 'Afro1993!', path):
                    if search_products_functions.download_products(products[index_path], path):
                        print("Product " + pr + " downloaded successfully." )
                    else:
                        print("Product " + pr + "could not be downloaded neither from ONDA ENS nor from onda catalogue. The program will exit.")
                        send_failure_response("The requested satellite products could not be downloaded neither from ONDA ENS nor from onda catalogue. The program will exit.", source, event_or_product_id)
                        
                else:
                    print(f'The product {pr} was copied and extracted successfully from ONDA ENS. Preprocessing will now take place.')
    return products_id_list_safe



def execute_affected_area_algorithm(main_process_path, dates):
    """Execute the affected area module to detect the burnt or water change area.

    Args:
        main_process_path (str): The path where the processed products have been stored and the results will be save in a child directory.
        dates (list): The before and after date (yy-mm-dd) of the event.

    Returns:
        path_for_results (str): the path for the directory where the all the results will be saved 
        output_tif_name (str): the name of the final tiff product depicting the affected area.
    """
    source = input_parameters.source
    if source == 'earthpress':
        event_or_product_id = input_parameters.event_id
    else:
        event_or_product_id = input_parameters.product_id
    
    event = input_parameters.event
    output_id = input_parameters.output_id
    

    before_folder = os.path.join(main_process_path, dates[0])
    after_folder = os.path.join(main_process_path, dates[1])
   
    if not os.path.exists(before_folder) or not os.path.exists(after_folder):
        send_failure_response('No valid data folders provided. Please provide the correct filepath.', source, event_or_product_id)
        
    

    if os.path.isfile(os.path.join(before_folder, 'TCI.tif')):
        rgb_image = os.path.join(before_folder, 'TCI.tif')
    elif os.path.isfile(os.path.join(after_folder, 'TCI.tif')):
        rgb_image = os.path.join(after_folder, 'TCI.tif')
    else:
        print('No RGB image found to visualize the result. Please make sure there is a TCI.tiff in either the pre or after date folder')
        rgb_image = -1

    # creating a new folder in which the results (all the generated images and files) will be placed
    results_folder = event + '_change' + '_{}_and_{}'.format(dates[0], dates[1])
    path_for_results = os.path.join(main_process_path, results_folder)
    
    if not os.path.exists(path_for_results):
        try:
            os.mkdir(path_for_results)
        except OSError:
            print("Creation of output directory failed. All the created files will be placed on the parent folder")
            path_for_results = main_process_path
    threshold_uncertainty = settings.threshold_uncertainty
    
    if event == "fire":
        output_tif_name = "burned_area.tif"
        burned_area_change_detection(before_folder, after_folder, rgb_image, path_for_results, output_id, event_or_product_id)
    else:
        output_tif_name = "water_change.tif"
        water_change_main(before_folder, after_folder, rgb_image, path_for_results, output_id, event_or_product_id)

    path_for_first_geotiff = os.path.join(path_for_results, output_tif_name)
    path_for_metadata = os.path.join(path_for_results, settings.metadata_file)
    

    if not os.path.exists(path_for_metadata) or not os.path.exists(path_for_first_geotiff):
        
        send_failure_response("Products for the first boundary could not be generated.", source, event_or_product_id)
    else:
        
        if not affected_area_functions.is_uncertainty_greater_than(path_for_metadata, threshold_uncertainty):
            
            if affected_area_functions.affected_area_detected(path_for_first_geotiff, path_for_metadata):
                pass
                print('Affected area detected in the first bounding box.')    
            else:
                send_failure_response("Affected area not detected", source, event_or_product_id)
            
        else:
            send_failure_response(f"Uncertainty value, based on clouds and bad pixels is greater than {threshold_uncertainty}", source, event_or_product_id)
    return path_for_results, output_tif_name

def expand_area(path_for_results, output_tif_name, main_process_path, results_folder, path_list, dates, products_id_list_safe):
    
    """Checks if the detected area is possible to be expanded outside the first box. Creates new box towards the suggested direction
    and executes the algorithm. If needed downloads and preproccesses new satellite products. Creates the final products

    Args:
        path_for_results (_type_): the path for the directory where the all the results have been saved 
        output_tif_name (_type_): _description_
        main_process_path (_type_): _description_
        results_folder (_type_): _description_
        path_list (_type_): _description_
        dates (_type_): _description_
        products_id_list_safe (_type_): _description_

    Returns:
        path_for_metadata: Path of the metadata file which will be posted. Includes the urls with which the png inages are send and all the information needed. 
    """
    source = input_parameters.source
    if source == 'earthpress':
        event_or_product_id = input_parameters.event_id
    else:
        event_or_product_id = input_parameters.product_id
   
    
    event = input_parameters.event
    output_id = input_parameters.output_id
    
    metadata_path = ''
    
    path_for_first_geotiff = os.path.join(path_for_results, output_tif_name)
    initial_center_x, initial_center_y = search_products_functions.find_center_of_geotiff(path_for_first_geotiff)
    rounded_all_central_points = [(round(initial_center_x,1),round(initial_center_y,1))]
    all_central_points = [(initial_center_x, initial_center_y)]
    previous_new_points = [(initial_center_x, initial_center_y)]
    next_new_points = [0]
    

    i = 0
    #radiud in meters
    radius = settings.radius*1000
    list_i = []
    while next_new_points != [] and i<10:
        next_new_points = []
        next_list_i = []    
        for point in range(len(previous_new_points)):
            x,y = previous_new_points[point]
            if i == 0:
                geotiff_path = path_for_first_geotiff
            else:
                print(list_i[point])
                geotiff_path = os.path.join(main_process_path, str(list_i[point]), results_folder, output_tif_name)   
                #path_for_metadata_box = os.path.join(process_path, str(list_i[point]), results_folder, 'metadata.json')
                
            print("Searching the expansion in " + geotiff_path)
            directions = expand_aoi_functions.suggest_directions_of_search_area_expansion(geotiff_path)
            
            if directions[0] == True and (round(x,1),round(y+radius,1)) not in rounded_all_central_points:
                print("Search towards north direction.")
                all_central_points.append((x,y+radius))
                rounded_all_central_points.append((round(x,1),round(y+radius,1)))
                next_new_points.append((x,y+radius))
                boundary_box  = affected_area_functions.create_boundary_box((x,y+radius), radius)
                products_id_list_safe_new, download_new_tile = expand_and_download_tiles.box_belongs_to_tile(path_list, boundary_box, dates, products_id_list_safe)
                if download_new_tile: 
                    i+=1
                    next_list_i.append(i)
                    expand_aoi_functions.preprocess_and_execute_affected_area_module(path_list, boundary_box, products_id_list_safe_new, main_process_path + '/' + str(i), event) 
                    print(f"Execution completed for the new box. Results are stored in: {main_process_path + '/' + str(i)}")
            
            if directions[1] == True and (round(x+radius,1), round(y,1)) not in rounded_all_central_points:
                print("Search towards east direction.")
                all_central_points.append((x+radius,y))
                rounded_all_central_points.append((round(x+radius,1), round(y,1)))
                next_new_points.append((x+radius,y))
                boundary_box  = affected_area_functions.create_boundary_box((x+radius,y), radius)
                products_id_list_safe_new, download_new_tile = expand_and_download_tiles.box_belongs_to_tile(path_list, boundary_box, dates, products_id_list_safe)
                if download_new_tile: 
                    i+=1
                    next_list_i.append(i)
                    expand_aoi_functions.preprocess_and_execute_affected_area_module(path_list, boundary_box, products_id_list_safe_new, main_process_path + '/' + str(i), event) 
                    print(f"Execution completed for the new box. Results are stored in: {main_process_path + '/' + str(i)}")
            
            if directions[2] == True and (round(x,1), round(y-radius,1)) not in rounded_all_central_points:
                print("Search towards south direction.")
                all_central_points.append((x,y-radius))
                rounded_all_central_points.append((round(x,1), round(y-radius,1)))
                next_new_points.append((x,y-radius))
                boundary_box  = affected_area_functions.create_boundary_box((x,y-radius), radius)
                products_id_list_safe_new, download_new_tile = expand_and_download_tiles.box_belongs_to_tile(path_list, boundary_box, dates, products_id_list_safe)
                if download_new_tile: 
                    i+=1
                    next_list_i.append(i)
                    expand_aoi_functions.preprocess_and_execute_affected_area_module(path_list, boundary_box, products_id_list_safe_new, main_process_path + '/' + str(i), event) 
                    print(f"Execution completed for the new box. Results are stored in: {main_process_path + '/' + str(i)}")
            
            if directions[3] == True and (round(x-radius,1), round(y,1)) not in rounded_all_central_points:
                print("Search towards west direction.")
                all_central_points.append((x-radius,y))
                rounded_all_central_points.append((round(x-radius,1), round(y,1)))
                next_new_points.append((x-radius,y))
                boundary_box  = affected_area_functions.create_boundary_box((x-radius,y), radius)
                products_id_list_safe_new, download_new_tile = expand_and_download_tiles.box_belongs_to_tile(path_list, boundary_box, dates, products_id_list_safe)
                if download_new_tile: 
                    i+=1
                    next_list_i.append(i)
                    expand_aoi_functions.preprocess_and_execute_affected_area_module(path_list, boundary_box, products_id_list_safe_new, main_process_path + '/' + str(i), event) 
                    print(f"Execution completed for the new box. Results are stored in: {main_process_path + '/' + str(i)}")
        list_i = next_list_i
        previous_new_points = next_new_points
    
    path_for_first_before_scl = os.path.join(main_process_path, dates[0], 'SCL.tif')
    path_for_first_before_tci = os.path.join(main_process_path, dates[0], 'TCI.tif')
    
    path_for_first_after_scl = os.path.join(main_process_path, dates[1], 'SCL.tif')
    path_for_first_after_tci = os.path.join(main_process_path, dates[1], 'TCI.tif')
    
    final_path_geotiffs = [path_for_first_geotiff]
    scl_before_paths = [path_for_first_before_scl]
    scl_after_paths = [path_for_first_after_scl]
    tci_before_paths = [path_for_first_before_tci]
    tci_after_paths = [path_for_first_after_tci]
    
    for j in range(1, i+1):
        final_path_geotiffs.append(main_process_path + '/' + str(j) + '/' + results_folder + output_tif_name)
        scl_before_paths.append(main_process_path + '/' + str(j) + '/' + dates[0]  + '/SCL.tif')
        scl_after_paths.append(main_process_path + '/' + str(j) + '/' + dates[1]  + '/SCL.tif')
        tci_before_paths.append(main_process_path + '/' + str(j) + '/' + dates[0] + '/TCI.tif')
        tci_after_paths.append(main_process_path + '/' + str(j) + '/' + dates[1] + '/TCI.tif')
    
    #merge also SCL layers
    try:
        os.mkdir(main_process_path + '/full')
    except:
        pass

    merge_tiffs = gdal.Warp(main_process_path + "/full/full_" + output_tif_name, final_path_geotiffs, format="GTiff", options = ["COMPRESS=LZW", "TILED=YES"])
    merge_tiffs = None

    merge_scl_before = gdal.Warp(main_process_path + "/full/full_before_scl.tif", scl_before_paths, format="GTiff", options = ["COMPRESS=LZW", "TILED=YES"])
    merge_scl_before = None

    merge_scl_after = gdal.Warp(main_process_path + "/full/full_after_scl.tif", scl_after_paths, format="GTiff", options = ["COMPRESS=LZW", "TILED=YES"])
    merge_scl_after = None

    merge_tci_before = gdal.Warp(main_process_path + "/full/full_before_tci.tif", tci_before_paths, format="GTiff", options = ["COMPRESS=LZW", "TILED=YES"])
    merge_tci_before = None

    merge_tci_after = gdal.Warp(main_process_path + "/full/full_after_tci.tif", tci_after_paths, format="GTiff", options = ["COMPRESS=LZW", "TILED=YES"])
    merge_tci_after = None
    
    
    #clc array_creation 
    final_product_affected_area_path = os.path.join(main_process_path + "/full/full_" + output_tif_name)
    
    preprocess_functions.process_clc_with_input_raster(final_product_affected_area_path, main_process_path + "/full")
    preprocess_functions.process_glc_with_input_raster(final_product_affected_area_path, main_process_path + "/full")

    #calculate land cover classes affected_from the burnt area
    clc_filepath = os.path.join(main_process_path, "full", 'CLC.tif')
    glc_filepath = os.path.join(main_process_path, "full", 'LC100_global.tif')
    #check if clc filepath exists and calculate landcover_classes, otherwise check if glc cover exists and calculate landcover classes.
    landcover_classes = {} 
    if os.path.exists(clc_filepath):
        landcover_classes = expand_aoi_functions.calculate_land_cover_classes_clc_affected_area(clc_filepath, final_product_affected_area_path, event)
    elif os.path.exists(glc_filepath):
        landcover_classes = expand_aoi_functions.calculate_land_cover_classes_glc_affected_area(glc_filepath, final_product_affected_area_path, event)
    else:
        landcover_classes = {}

    #uncertainty calculation (This is calculated for the image before and after based on the SCL)
    scl_before_path = os.path.join(main_process_path + "/full/full_before_scl.tiff")
    scl_after_path = os.path.join(main_process_path + "/full/full_after_scl.tiff")
    uncertainty_before = expand_aoi_functions.calculate_uncertainty(scl_before_path)
    uncertainty_after = expand_aoi_functions.calculate_uncertainty(scl_after_path)
    
    #png images creation
    tci_before_filepath = os.path.join(main_process_path, 'full', 'full_before_tci.tiff')
    tci_after_filepath = os.path.join(main_process_path, 'full', 'full_after_tci.tiff')
    directory_for_final_files = os.path.join(main_process_path, 'full', 'final_images')
    try:
        os.mkdir(directory_for_final_files)
    except:
        pass
    
    tci_before = False
    tci_after = False        
    
    if os.path.exists(tci_before_filepath):
        
        expand_aoi_functions.create_png_images(tci_before_filepath, os.path.join(directory_for_final_files, 'before_the_event.png'))
        tci_before = True
        print('tci before exists')
    if os.path.exists(tci_after_filepath):
        expand_aoi_functions.create_png_images(tci_after_filepath, os.path.join(directory_for_final_files, 'after_the_event.png'))
        tci_after = True
        print('tci after exists')
    if tci_before:
        expand_aoi_functions.create_pngs_affected_area(final_product_affected_area_path, tci_before_filepath, directory_for_final_files, event)
        print('yes')
    elif tci_after:
        expand_aoi_functions.create_pngs_affected_area(final_product_affected_area_path, tci_after_filepath, directory_for_final_files, event)
    else:
        #only transparent will be created if tci does not exist
        expand_aoi_functions.create_pngs_affected_area(final_product_affected_area_path, -1, directory_for_final_files, event)
            
    #metadata_creation
    metadata_path = expand_aoi_functions.create_metadata(dates[0], dates[1], final_product_affected_area_path, output_id, event_or_product_id, landcover_classes, directory_for_final_files, uncertainty_before, uncertainty_after, event) 

    shutil.copyfile(glob.glob(directory_for_final_files + '/before_the_event.png')[0], './static/' + output_id + '_before.png')
    shutil.copyfile(glob.glob(directory_for_final_files + '/after_the_event.png')[0], './static/' + output_id + '_after.png')
    if event == 'fire':
        shutil.copyfile(glob.glob(directory_for_final_files + '/burned_area_change.png')[0], './static/' + output_id + '_change.png')
        shutil.copyfile(glob.glob(directory_for_final_files + '/burned_area.png')[0], './static/' + output_id + '_burned_area.png')
    else:
        shutil.copyfile(glob.glob(directory_for_final_files + '/water_area_change.png')[0], './static/' + output_id + '_change.png')
        shutil.copyfile(glob.glob(directory_for_final_files + '/water_change.png')[0], './static/' + output_id + '_Water_change.png')
    
    return metadata_path

def post_results(path_for_metadata, url):
    '''
    this function will post the metadata json to  earthpress or vqa endpoint
    Parameters: 
        path_for_metadata (str): destination path for the final metadata.json file
        url (str): endpoint for the post
    '''
    with open(path_for_metadata, 'r') as json_file:
        my_json = json.load(json_file)
        header = {'Content-Type': 'application/json'}
        requests.post(url, json = my_json, headers = header)
    return 0


def send_failure_response(message, source, event_id):

    """
    Receives an error message and posts it to the EarthPress/VQA API listening for outputs.

    Parameters:
            message (str): D
            source (str): D
            event_id (int): D (event id for the case of earthpress and satellite_image_id for the case of vqa)
    
    """
    response = OrderedDict()
    analysis_status = OrderedDict()

    if source == "vqa":
        #in the vqa case we send the product_id (maybe a different function would be a better solution)
        analysis_status["product_id"] = event_id
    else:
        analysis_status["event_id"] = event_id
    analysis_status["success"]= False
    analysis_status["message"]= message
    response["analysis_status"]= analysis_status
    
    try:
        requests.post(return_url(source), json = response)
    except:
        print("Response has not been posted.")
    return 0

