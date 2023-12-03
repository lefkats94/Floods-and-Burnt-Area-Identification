
import os
import sys

import settings

import affected_area_api 
import tasks
import input_parameters
from tasks.earthpress_tasks import search_earthpress_products, preprocess_earthpress
from tasks.vqa_tasks import search_vqa_products, preprocess_vqa


def main_earthpress_task(input_dict):
    """Execute all tasks related to earthpress service

    Args:
        input_dict (dict): The dictionary contains all the user input parameters 

    Returns:
        _type_: _description_
    """
    input_parameters.init(input_dict)
    #search for available products
    products_id_list, dates, products = search_earthpress_products()
    print("The search of the products has been completed")

    #create directories to store the downloaded products
    path_list = tasks.shared_tasks.create_directories(products_id_list, dates)
    print("Directories have been created")

    #download products
    products_id_list_safe = tasks.shared_tasks.download_sentinel2_products(path_list, products_id_list, products)
    print("Products have been downloaded")

    #preprocess products
    main_process_path = preprocess_earthpress(path_list, products_id_list_safe, dates)
    print("Products have been preprocessed")
    
    #execute affected area algorithm for the initial box
    path_for_results, output_tif_name = tasks.shared_tasks.execute_affected_area_algorithm(main_process_path, dates)
    results_folder = os.path.basename(path_for_results)
    print("algorithm has been executed for the first box")

    #expand aoi if needed
    path_metadata = tasks.shared_tasks.expand_area(path_for_results, output_tif_name, main_process_path, results_folder, path_list, dates, products_id_list_safe)
    print("algorithm has been executed the expanded area. Final files (pngs and json) have been produced.")

    #post results
    tasks.shared_tasks.post_results(path_metadata, settings.earthpress_response_url)  
    print("Results have been posted.")
    return f"Main earthpress for {input_parameters.output_id} has been executed."

def main_vqa_task(input_dict):
    """Execute all tasks related to vqa service

    Args:
        input_dict (_type_): The dictionary contains all the user input parameters 

    Returns:
        _type_: _description_
    """
    print(input_dict)
    input_parameters.init(input_dict)
    
    #search for available products
    products_id_list, dates, products, tile_extend_box = search_vqa_products()
    print("The search of the products has been completed")
    print(products_id_list)
    
    #create directories to store the downloaded products
    path_list = tasks.shared_tasks.create_directories(products_id_list, dates)
    print("Directories have been created")
    path_list = ['/home/lefkats/snapearth_api/snapearth_api_new/input/Input_2022-07-11_2022-07-31_T35SMD/2022-07-11', '/home/lefkats/snapearth_api/snapearth_api_new/input/Input_2022-07-11_2022-07-31_T35SMD/2022-07-31']
    products_id_list = ['S2B_MSIL2A_20220711T085559_N0400_R007_T35SMD_20220711T105045', 'S2B_MSIL2A_20220731T085559_N0400_R007_T35SMD_20220731T103425']
    
    
    
    #download products
    products_id_list_safe = tasks.shared_tasks.download_sentinel2_products(path_list, products_id_list, products)
    print("Products have been downloaded")
    
    #preprocess products
    main_process_path = preprocess_vqa(path_list, products_id_list_safe, dates, tile_extend_box)
    print("Products have been preprocessed")
    
    #execute affected area algorithm for the initial box
    path_for_results, output_tif_name = tasks.shared_tasks.execute_affected_area_algorithm(main_process_path, dates)
    results_folder = os.path.basename(path_for_results)
    print("algorithm has been executed for the first box")

    #expand aoi if needed For vqa we need to limit the expansion to the first tile that the product_id declares
    #path_metadata = tasks.shared_tasks.expand_area(path_for_results, output_tif_name, main_process_path, results_folder, path_list, dates, products_id_list_safe)
    print("algorithm has been executed the expanded area. Final files (pngs and json) have been produced.")

    #post results
    #tasks.shared_tasks.post_results(path_metadata, settings.vqa_response_url)  
    print("Results have been posted.")
    return f"Main vqa for {input_parameters.output_id} has been executed."


  