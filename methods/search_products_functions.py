"""
This module includes the functions in which the search for the products, needed for the execution, is implemented.
Two Sentinel-2 Level 2A products are needed for the execution of the affected area modules.
The function create_buffer_zone_from_point() has been written for SnapEarthDataFerching module (author: Michail Sismanis). It is being used with some modifications. 
There are two main functions: query_products_earthpress() and query_products_vqa(), which are used when the request is received by the corresponding source. The difference concerns the way the products 
are being searched. 

For the earthpress, the two products -before and after the event- are searched based on the footprint of the bounding box which is created from 
the create_buffer_zone_from_point() function.

For the vqa the image_id of the second product is provided as input, thus this product is being searched by the image_id. In case the image_id given, corresponds to L1C product (Because L1C products 
are stored in the database of the earthsignature module), the L1C product is being searched and then the corresponding L2A. 
Afterwards, the product for the first image is searched by the bbox and the dates (derived from the image_id).

The download_products() function is used in case the product cannot be copied from the ONDA ENS (which is provided in cs_group VM).
This function uses the eodag module to download the product from the catalogue. (Provider can also change)
Comments on download_products(): The extraction of the .SAFE products ca be executed by default from the eodag.download command. However, due to issues concerning the automatic extraction,
the products are extracted manually. Τo ensure that the products have been downloaded properly (because many times the downloaded products were not properly downloaded), we check if the path to a folder exists. 
If not 2 more attepts are being executed before the program exits.
"""

from eodag import EODataAccessGateway
from eodag.crunch import FilterProperty
import os
import shapely
from shapely.geometry import Point
import datetime
from eodag import setup_logging
import pandas as pd
import re
import zipfile
import glob
import tarfile
import collections
#import rarfile
#setup_logging(2)  # 3 for even more information

def create_buffer_zone_from_point(point, buffer_radius=5):
    """
    Based on the coordinates given and the buffer radius, a polygon is returned.
    """
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
    return polygon


def query_products_vqa(satellite_image_id, second_date, tile_id):
    '''
    This function is searching for the satellite products given the id of the image, the date of the second image and the tile_id. It will be used when the request is coming from the vqa.
    Returns a list with the two products
    '''
    os.environ["EODAG__ONDA__AUTH__CREDENTIALS__USERNAME"] = ""
    os.environ["EODAG__ONDA__AUTH__CREDENTIALS__PASSWORD"] = ""
    print('here')
    dag = EODataAccessGateway()
    dag.set_preferred_provider("onda")

    products = []
    
    day = int(second_date.split('-')[2])
    month = int(second_date.split('-')[1])
    year = int(second_date.split('-')[0])
    sec_date = datetime.date(year, month, day)
    
    #first we search for the second product using the image_id given.
    #In case the id is from L1C product, we need to search for the corresponding L2A.
    if re.search('L2A', satellite_image_id):

        try:
            print('Searching for the L2A product')
            second_product = dag.search(id = satellite_image_id)[0][0]
            #input_coordinate_box = second_product[0][0].geometry.bounds
            input_coordinate_box = second_product.geometry.bounds
        except:
            print(f"The given product with id {satellite_image_id} could not be found")
            return [], None, f"The given product with id {satellite_image_id} could not be found"
    elif re.search('L1C', satellite_image_id):
            #search firstly for the L1C product so as to extract the geometry, (search cannot be done by the given tile)
            try:
                second_product_L1C = dag.search(id = satellite_image_id)[0][0]
                input_coordinate_box = second_product_L1C.geometry.bounds
                datetime_ctfan = second_product_L1C.properties['completionTimeFromAscendingNode']

            except:
                print(f"The given product with id {satellite_image_id} could not be found.")
                return [], None, f"The given product with id {satellite_image_id} could not be found."
            
            end = sec_date + datetime.timedelta(days=1)
            
            search_criteria = {
                "productType": "S2_MSI_L2A",
                "start": str(sec_date),
                "end": str(end),
                "geom": input_coordinate_box
                                 }
            try:
                all_products = dag.search_all(**search_criteria)
                filtered_products = [pr for pr in all_products if re.search(tile_id, pr.properties['id'])]
                filtered_products = [pr for pr in filtered_products if datetime_ctfan == pr.properties['completionTimeFromAscendingNode']]
                if filtered_products != []:
                    second_product = filtered_products[0]
                    input_coordinate_box = second_product.geometry.bounds
            except:
                print(f"The L2A product from the corresponding  L1C with id {satellite_image_id} could not be found")
                return [], None, "The L2A product from the corresponding  L1C with id {satellite_image_id} could not be found"
    else:
        print("Check the image id. The program will exit.")
        return [], None, "Check the image id. The program will exit."           

    #Search for the product for the image before the event
    end = sec_date - datetime.timedelta(days=10)
    start = end - datetime.timedelta(days=90)
    rev = True
    search_criteria = {
        "productType": "S2_MSI_L2A",
        "start": str(start),
        "end": str(end),
        "geom": input_coordinate_box
    }

    all_products = dag.search_all(**search_criteria)
    all_products.sort(key=lambda x: x.properties['completionTimeFromAscendingNode'], reverse=rev)

    filtered_products = all_products.crunch(
        FilterProperty(dict(cloudCover=20, operator="lt")),
    )
    filtered_products = filtered_products.crunch(
        FilterProperty(dict(noDataPixelPercentage='50', operator="lt")),
    )
    filtered_products = [pr for pr in filtered_products if re.search(tile_id, pr.properties['id'])]
    if filtered_products == []:
        print(f"Product for the first date could not be found.")
        return [], f"Product for the first date could not be found."
    else:
        products.append(filtered_products[0])
        products.append(second_product)
    return products, input_coordinate_box, None




def query_products_earthpress(target_date, point):
    '''
    This function will make the queries in ONDA Catalogue for the products before and after the target date.
        Parameters:
        target_date: The date when the event happened
        point: A list [lat, lon] of the center coordinates of the region of interest
        
    '''

    #os.environ["EODAG__ONDA__AUTH__CREDENTIALS__USERNAME"] = "afroditikita@gmail.com"
    #os.environ["EODAG__ONDA__AUTH__CREDENTIALS__PASSWORD"] = "Afro1993!"
    #os.environ["EODAG__ONDA__DOWNLOAD__OUTPUTS_PREFIX"] = os.path.abspath(workspace)
    # setup_logging(3)  # 3 for even more information
    dag = EODataAccessGateway()
    dag.set_preferred_provider("onda")
    
    #Create the box from the coordinates. The function returns a shapely.geometry.Polygon object
    box1 = create_buffer_zone_from_point(point, buffer_radius=7.5)
    footprint = box1
    print(footprint)
    print(target_date)
    #Search for the  product before the event
    download = False
    day = int(target_date.split('-')[2])
    month = int(target_date.split('-')[1])
    year = int(target_date.split('-')[0])
    target = datetime.date(year, month, day)

    dates = []
    data_before = pd.DataFrame()
    data_after = pd.DataFrame()
    for i in range(0, 2):
        if i == 0:
            #search the product before the target date
            end = target - datetime.timedelta(days=10)
            start = end - datetime.timedelta(days=60)
            
            print(start)
            # start = datetime.date(2022, 10, 5)
            # end = datetime.date(2022, 10, 10)
            rev = True
        else:
            #search the product after the target date

            #start = target + datetime.timedelta(days=2)
            start = target
            today = datetime.date.today()
            if abs(target - today) > datetime.timedelta(days=10):
                rev = False
                start = target + datetime.timedelta(days=2)
            else:
                start = target - datetime.timedelta(days=8)
                rev = True
            end = start + datetime.timedelta(days=60)

        search_criteria = {
            "productType": "S2_MSI_L2A",
            "start": str(start),
            "end": str(end),
            "geom": footprint
        }
        dates_products = []
        tiles_pr = []
        check_double = False
        while not check_double:
            all_products = dag.search_all(**search_criteria)
            #check if same products exist so as to run again the search
            ids_check  = []
            for pr in all_products:    
                ids_check.append(pr.properties['id'])
            doubles_list = [item for item, count in collections.Counter(ids_check).items() if count > 1]    
            if doubles_list == []:
                check_double = True
                break

        
        all_products.sort(key=lambda x: x.properties['completionTimeFromAscendingNode'], reverse=rev)
        
        #check if all_products for a specific date do not exist, return empty lists and a related message.
        if all_products == []:
            if i == 0:
                message = 'No available products for the first date.'
            else:  
                message = 'No available products for the second date.'
            return [[],[]], [], [[],[]], [nt_initial, nt_initial], message  

        #calculate the tiles needed. This can be achieved by finding the maximum number of images for the same date without having remove products with higher cloud coverage
        for el in all_products:
            try:
                el.properties['cloudCover']
            except:
                problem_pr = el.properties['id']  
                el.properties['cloudCover'] = 0
            dates_products.append(el.properties['completionTimeFromAscendingNode'])
            
        #create a dictonary which shows the number of tiles (values) that exist for a specific date (key)
        if i == 0:
            set_dates = sorted(list(set(dates_products)))
            counts = dict((x, dates_products.count(x)) for x in set_dates)
            counts_max_tiles = dict((x, list(counts.values()).count(x)) for x in set(counts.values()))
            nt_initial = list(counts_max_tiles.keys())[list(counts_max_tiles.values()).index(max(counts_max_tiles.values()))]
        print(f"Number of tiles with same date returned by the first search {nt_initial}")
        if nt_initial >= 3:
            cloud_cover = 40
        elif nt_initial >= 2:
            cloud_cover = 35
        else:
            cloud_cover = 30

        #print(dates_products)
        #print(len(all_products))
        
        all_products = all_products.crunch(FilterProperty(dict(cloudCover=cloud_cover, operator="lt")))
        
        
        if all_products == []:
            if i == 0:
                message = 'For the date before the event, there are available products with datatake sensing time:'
                for date in dates_products:
                    message = message + ' ' + date + ','

                message = message + f' but the cloud coverage of each product is greater than {cloud_cover}%'
            else:  
                message = 'For the date after the event, there are available products with datatake sensing time:'
                for date in dates_products:
                    message = message + ' ' + date  + ','

                message = message + f' but the cloud coverage of each product is greater than {cloud_cover}%.'
            return [[],[]], [], [[],[]], [nt_initial, nt_initial], message
        
        #we need to avoid downloading one that for a specific date has many nodata values and send a related message if no products remain after the filtering
        all_products = all_products.crunch(FilterProperty(dict(noDataPixelPercentage='50', operator="lt")))
        #Rodopi
        all_products = [el for el in all_products if el.properties['id']!= 'S2A_MSIL2A_20221017T090941_N0400_R050_T35TLF_20221017T134756']
        all_products = [el for el in all_products if el.properties['id']!= 'S2A_MSIL2A_20221007T090851_N0400_R050_T35TLF_20221007T134600']
        #PORTUGAL
        all_products = [el for el in all_products if el.properties['id']!= 'S2B_MSIL2A_20220610T110619_N0400_R137_T29SPD_20220610T141507']
        #Africa
        all_products = [el for el in all_products if el.properties['id']!= 'S2B_MSIL2A_20220809T074619_N0400_R135_T36NXG_20220809T101635']
        #new_event
        all_products = [el for el in all_products if el.properties['id']!= 'S2A_MSIL2A_20220405T081601_N0400_R121_T36RXV_20220405T112446']
        # tile_id = 'T29TQE'
        # all_products = [pr for pr in all_products if re.search(tile_id, pr.properties['id'])]
        if all_products == []:
            if i == 0:
                message = f'For the date before the event there are not products without cloud coverage less than the {cloud_cover}% and noDataPixelPercentage less than 50%.'
            else:
                message = f'For the date after the event there are not products without cloud coverage less than the {cloud_cover}% and noDataPixelPercentage less than 50%.'
            return [[],[]], [], [[],[]], [nt_initial, nt_initial], message

        all_products.sort(key=lambda x: x.properties['completionTimeFromAscendingNode'], reverse=rev)
         
        
        


        dates_products = []
        #Create the same variables as before but after having filtered the products.
        for el in all_products:
            dates_products.append(el.properties['completionTimeFromAscendingNode'])
        #create a dictonary which shows the number of tiles (values) that exist for a specific date (key)
        set_dates = sorted(list(set(dates_products)), reverse = rev)
        counts = dict((x, dates_products.count(x)) for x in set_dates)
        tiles_per_date = [[] for x in range(0, len(set_dates))]
        cloudCover_per_tile = [[] for x in range(0, len(set_dates))]
        cloud_cover = [] #boolean True if for all tiles the cloud cover is permitted
        products = [[] for x in range(0, len(set_dates))]
        # Apart from the maximum number of tiles for one date it's important to find the dominant number of tiles -for more than one date-)
        counts_max_tiles = dict((x, list(counts.values()).count(x)) for x in set(counts.values()))

        #Create a dataset (one before, one after) with features: each date, the number of tiles for this date, the name of the tiles (list), the cloud cover per tile (list) and the object products in a list.
        for el in all_products:
            index = set_dates.index(el.properties['completionTimeFromAscendingNode'])
            tiles_per_date[index].append(el.properties['id'][38:44])
            cloudCover_per_tile[index].append(el.properties['cloudCover'])
            products[index].append(el)


        #filtered_products = all_products.crunch(FilterProperty(dict(cloudCover=35, operator="lt")))
        #filtered_products.sort(key=lambda x: x.properties['completionTimeFromAscendingNode'], reverse=rev)

        if i==0:
            data_before['dates'] = counts.keys()
            data_before['number_of_tiles'] = counts.values()
            data_before['tiles'] = tiles_per_date
            data_before['cloudCover'] = cloudCover_per_tile
            data_before['products'] = products
            counts_max_tiles_before = counts_max_tiles
           
        else:
            data_after['dates'] = counts.keys()
            data_after['number_of_tiles'] = counts.values()
            data_after['tiles'] = tiles_per_date
            data_after['cloudCover'] = cloudCover_per_tile
            data_after['products'] = products
            counts_max_tiles_after = counts_max_tiles

    
    nt_current_before = nt_initial
    nt_current_after = nt_initial
    flag_stop = False
    flag_before = False
    flag_after = False
    while not flag_stop:
        if not flag_before:
            df_selected = data_before.where(data_before['number_of_tiles'] >= nt_current_before)
            rows_select = df_selected[~df_selected.isnull().any(axis=1)]
            if rows_select.shape[0] !=0:
                dates_before = data_before[~data_before['dates'].where(data_before['number_of_tiles'] == nt_current_before).isnull()]
                filtered_products_list_before = list(dates_before['products'])[0]
                flag_before = True
            else:
                nt_current_before -= 1
                if nt_initial <= 3 or (nt_initial - nt_current_before)  > 1:
                    print("Products for the date before are not available.")
                    break

        if not flag_after:
            df_selected = data_after.where(data_after['number_of_tiles'] >= nt_current_after)
            rows_select = df_selected[~df_selected.isnull().any(axis=1)]
            if  rows_select.shape[0] !=0:
                dates_after = data_after[~data_after['dates'].where(data_after['number_of_tiles'] ==  nt_current_after).isnull()]
                filtered_products_list_after = list(dates_after['products'])[0]
                flag_after = True
            else:
                nt_current_after -= 1
                if nt_initial <= 3 or (nt_initial - nt_current_after) > 1:
                    print("Products for the date after are not available.")
                    break
            if flag_after and flag_before:
                flag_stop = True
                break

    if flag_stop:
        if nt_current_before > nt_current_after:
            tiles_list = dates_after['tiles'][0]
            filtered_products_list_before = [el for el in filtered_products_list_before if el.properties['id'][38:44] in tiles_list]
    
    if flag_stop:
        filter_by_date_list = [filtered_products_list_before, filtered_products_list_after]
        for filter_by_date in filter_by_date_list:
            product_list = []
            products = []
            for pr in filter_by_date:
                product_list.append(pr.properties['id'])
                products.append(pr)
            if filter_by_date_list.index(filter_by_date) == 0:
                before_date = return_date(filter_by_date[0])
                product_list_before = product_list
                products_before = products
                number_of_tiles_before = len(product_list_before)
            else:
                after_date = return_date(filter_by_date[0])
                product_list_after = product_list
                products_after = products
                number_of_tiles_after = len(product_list_after)
        if not(number_of_tiles_after == number_of_tiles_before):
            message = f"The number of different tiles needed for the construction of the image is {nt_initial}. Same number of products for the first image and the second could not be found."
            print("Products have not been found")
            return [[],[]], [], [[],[]], [nt_initial, nt_initial], message
    else:
        print(f"The number of different tiles needed for the construction of the image is {nt_initial}. Same number of products for the first image and the second could not be found.")
        message = f"The number of different tiles needed for the construction of the image is {nt_initial}. Same number of products for the first image and the second could not be found."
        return [[],[]], [], [[],[]], [nt_initial, nt_initial], message
    message = 'Products found.'
    return [product_list_before, product_list_after], [before_date, after_date], [products_before, products_after], [number_of_tiles_before, number_of_tiles_after], message

def return_filter_by_date_list(product_list):
    '''
    This function filters a list of products based on their date. If the products have the same date with the first product
    then the are kept in the list.
    '''
    filtered_product_list = []
    date = product_list[0].properties['completionTimeFromAscendingNode'][:10]
    for el in product_list:
        if el.properties['completionTimeFromAscendingNode'][:10] == date:
            filtered_product_list.append(el)
    return filtered_product_list

def return_date(product):
    date = product.properties['completionTimeFromAscendingNode'][:10]
    return date        


def download_products(pr, dest):
    flag = False
    if dest != None:
        workspace = dest
        try:
            os.mkdir(workspace)
        except:
            pass
        os.environ["EODAG__ONDA__AUTH__CREDENTIALS__USERNAME"] = "afroditikita@gmail.com"
        os.environ["EODAG__ONDA__AUTH__CREDENTIALS__PASSWORD"] = "Afro1993!"
        os.environ["EODAG__ONDA__DOWNLOAD__OUTPUTS_PREFIX"] = os.path.abspath(workspace)
    
        attempts_to_download = 0
        while not flag and attempts_to_download <= 2:

            try:
                dag = EODataAccessGateway()
                dag.set_preferred_provider("onda")
                
                dag.download(pr, delete_archive = True, outputs_prefix = os.path.abspath(workspace), extract = False)
                download = True
                print('Eodag message: The product downloaded successfully but the extraction needs to be confirmed')
                
            
            except:
                print('Problem occured during product download from onda catalogue.')
                download = False
                attempts_to_download +=1
            
            if download:
                
                if os.path.exists(os.path.join(dest, pr.properties['id'] + '.zip')):
                    filepath = os.path.join(dest, pr.properties['id'] + '.zip')
                    print(filepath)
                elif os.path.exists(os.path.join(dest, pr.properties['id'] + '.SAFE.zip')):    
                    filepath = os.path.join(dest, pr.properties['id'] + '.SAFE.zip')
                    print(filepath)
                
                else: 
                    if glob.glob(dest + '/' + pr.properties['id'] + '*') != []:
                        filepath = glob.glob(dest + '/' + pr.properties['id'] + '*')[0] 
                        print(filepath)
                if zipfile.is_zipfile(os.path.basename(filepath)):
                    print('Yes, it is a zipfile')
                elif tarfile.is_tarfile(filepath):
                    print('It is a tarfile')
                else:
                    print('unknown file type.')         
                
                try:
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(dest)    
                        zip_ref.close()
               
                
                    if os.path.exists(os.path.join(dest, pr.properties['id'] + '.SAFE', 'GRANULE')):
                        print('Eodag message: The product downloaded and extracted successfully from onda dias using eodag')
                        flag = True
                        if filepath:
                            os.remove(filepath)
                        
                        break
                except:
                        attempts_to_download +=1
                        download = False
                        if filepath:
                                os.remove(filepath)
                        if attempts_to_download == 3:
                            break
                        print(f"Cannot unzip the downloaded product. Attempt number: {attempts_to_download}")
    return flag        

def download_products_test(pr, dest):
    flag = False
    if dest != None:
        workspace = dest
        try:
            os.mkdir(workspace)
        except:
            pass
        os.environ["EODAG__ONDA__AUTH__CREDENTIALS__USERNAME"] = "afroditikita@gmail.com"
        os.environ["EODAG__ONDA__AUTH__CREDENTIALS__PASSWORD"] = "Afro1993!"
        attempts_to_download = 0
        while not flag and attempts_to_download <= 2:

            try:
                dag = EODataAccessGateway()
                dag.set_preferred_provider("onda")
                dag.download(pr, delete_archive = True, outputs_prefix = os.path.abspath(workspace), extract = False)
                download = True
                print('Eodag message: The product downloaded successfully but the extraction needs to be confirmed')
                
            
            except:
                print('Problem occured during product download from onda catalogue.')
                download = False
                attempts_to_download +=1
            
            
            
            
            if download:
                if glob.glob(os.path.join(dest, pr.properties['id'] + '*.zip' )) != []:
                    filepath = glob.glob(os.path.join(dest, pr.properties['id'] + '*.zip' ))[0]
                    print(filepath)
                elif glob.glob(dest + '/' + pr.properties['id'] + '*')!= []: 
                    filepath = glob.glob(dest + '/' + pr.properties['id'] + '*')[0]
                    print(filepath)
               
                if os.path.exists(filepath):
                    if zipfile.is_zipfile(filepath):
                        print('Yes, it is a zipfile')
                        with zipfile.ZipFile(filepath, 'r') as zip_ref:
                            zip_ref.extractall(dest)    
                            #zip_ref.close()
                    elif tarfile.is_tarfile(filepath):
                        print('It is a tarfile')
                        tar = tarfile.open(filepath, "r:gz")
                        tar.extractall(dest)
                        tar.close()
                
                    else:
                        print('unknown file type.') 
                        try:        
                            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                                zip_ref.extractall(dest)  
                                print('Product extracted.')
                        except:
                            print('unknown file type. could not be extracted.') 

            if os.path.exists(os.path.join(dest, pr.properties['id'] + '.SAFE', 'GRANULE')):
                print('Eodag message: The product downloaded and extracted successfully from onda dias using eodag')
                if filepath:
                        os.remove(filepath)
                flag = True
                break
                
            else:
                attempts_to_download +=1
                if attempts_to_download == 3:
                    break
                if filepath:
                        os.remove(filepath)
                print(f"Cannot unzip the downloaded product. Attempt number: {attempts_to_download}")
        
    return flag

