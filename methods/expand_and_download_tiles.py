
import os
from osgeo import gdal
import datetime
import utm
import glob
from shapely.geometry import Point, Polygon
from eodag import EODataAccessGateway
from eodag.crunch import FilterProperty
import datetime
from eodag import setup_logging

from methods import download_products_functions
from shapely.ops import unary_union
from methods import search_products_functions
import input_parameters

def box_belongs_to_tile(path_list, box_extent, dates, products_id_list_safe):
    
    """
    box_extent: xmin_box, xmax_box, ymin_box, ymax_box
    """
    source = input_parameters.source
    tile_extent = find_tiles_extent(path_list, products_id_list_safe)
    xmin_box, xmax_box, ymin_box, ymax_box = box_extent
    
    tile_directions = []
   
    p1 = Point((xmin_box, ymax_box))
    p2 = Point((xmax_box, ymax_box))
    p3 = Point((xmax_box, ymin_box))
    p4 = Point((xmin_box, ymin_box))
    
    box_extent_poly = Polygon([p1, p2, p3, p4])
    print('Box extent:', box_extent_poly)
    print('Tile extent:', tile_extent)
    
    
    intersection = box_extent_poly.intersection(tile_extent)
    print("Check the intersection of the extent of the tiles with the extent of the new bounding box.")
    download_new_tile_vqa = True
    if intersection.equals(box_extent_poly):
        print('yes, complete intrsection')
        products_id_list_safe_new = products_id_list_safe
    else:
        print('The boundary box is extented outside the tile extent. New products will be downloaded')    
        if source == 'earthpress':
            products_id_list_safe_new = search_and_download_tile(path_list, box_extent, dates, products_id_list_safe)
        else:
            download_new_tile_vqa = False
            products_id_list_safe_new = products_id_list_safe
            
    return products_id_list_safe_new, download_new_tile_vqa
    
    

#path_list = ['/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-04-03_2022-04-18_T34JBL/2022-04-03', '/home/lefkats/snapearth_api/snapearth_api/input/Input_2022-04-03_2022-04-18_T34JBL/2022-04-18']

#get extent of the bounding box of a GeoTIFF raster file
def GetExtent(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel 
    return (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin) 

  

def find_tiles_extent(path_list, products_id_list_safe):
    all_tiles_extent = []
    all_polygons = []
    for path in path_list:
        products_list_inside_dir = os.listdir(path)
        products = [el for el in products_list_inside_dir if el in products_id_list_safe[path_list.index(path)]]
        for product in products:
            file_path = glob.glob(path + '/' + product + '/GRANULE/*/IMG_DATA/R10m/*B02_10m.jp2')
            #print(file_path)
            ds = gdal.Open(file_path[0])
            extent = GetExtent(ds)
            #print(extent)
            all_tiles_extent.append(extent)
            # creating points using Point()
            p1 = Point(extent[0])
            p2 = Point(extent[1])
            p3 = Point(extent[2])
            p4 = Point(extent[3])
            #print(p1)
            # creating polygon using Polygon()
            poly1 = Polygon([p1, p2, p3, p4])
            all_polygons.append(poly1)
            ds = None
    
    union_extent = unary_union(all_polygons) 
   
    return union_extent
   



def search_and_download_tile(path_list, box_extent, dates, products_id_list_safe):
    dag = EODataAccessGateway()
    dag.set_preferred_provider("onda")
    
    #Create the box from the coordinates. The function returns a shapely.geometry.Polygon object
    
    
    
    products = os.listdir(path_list[0])
    if products != []:
        product = products[0]
    file_path = glob.glob(path_list[0] + '/' + product + '/GRANULE/*/IMG_DATA/R10m/*B02_10m.jp2')[0]
    print(file_path)
    print(type(file_path))
    ds = gdal.Open(file_path)
    zone_letter, zone_number  = Get_zonenumber_letter(ds)
    #zone_letter = 'S'
    #zone_number = 34
    print(zone_number, zone_letter)
    print(box_extent)
    (ymax_box, xmin_box),  (ymin_box, xmax_box) = convert_box_extent(box_extent, zone_letter, zone_number)
    
    p1 = Point((xmin_box, ymax_box))
    p2 = Point((xmax_box, ymax_box))
    p3 = Point((xmax_box, ymin_box))
    p4 = Point((xmin_box, ymin_box))
    
    box_extent_poly_degrees = Polygon([p1, p2, p3, p4])
    footprint =  box_extent_poly_degrees
    print(footprint)
    
    # print(target_date)
    first_date = dates[0]
    second_date = dates[1]
    for i in range(0, 2):
        if i == 0:
            #search the product before the target date (date of the event)
            day = int(first_date.split('-')[2])
            month = int(first_date.split('-')[1])
            year = int(first_date.split('-')[0])

        else:
            #search the product after the target date
            day = int(second_date.split('-')[2])
            month = int(second_date.split('-')[1])
            year = int(second_date.split('-')[0])
        start = datetime.date(year, month, day)            
        end = start + datetime.timedelta(days=1)         
        
        search_criteria = {
            "productType": "S2_MSI_L2A",
            "start": str(start),
            "end": str(end),
            "geom": footprint
        }

        all_products = dag.search_all(**search_criteria)
        filtered_products = all_products.crunch(FilterProperty(dict(cloudCover=40, operator="lt")))
        filtered_products = filtered_products.crunch(FilterProperty(dict(noDataPixelPercentage='50', operator="lt")))
        
        print(all_products)
        if i == 0:
            products_first = all_products
            products_id_first = [pr.properties['id'] for pr in products_first]
            print(products_id_first)
        else:
            products_second = all_products
            products_id_second = [pr.properties['id'] for pr in products_second]
    print('Products for the first date:', products_first)
    print('Products for the second date:', products_second)
    products_id_list = [products_id_first, products_id_second]
    products = [products_first, products_second]
    #Download each product included in the two products lists, for the date before and after the event. Check if the product already exists.

    for path in path_list:
        if os.path.exists(path):
            p_list = os.listdir(path)
            index_path = path_list.index(path)
            for pr in products_id_list[index_path]:
                pr_safe = pr + '.SAFE'
                if pr_safe in p_list:
                    print(pr + " product is already downloaded. Preprocessing will now take place.")
                else:
                    if not download_products_functions.download_from_ENS(pr, 'afroditikita@gmail.com', 'Afro1993!', path):
                        if search_products_functions.download_products(products[index_path][products_id_list[index_path].index(pr)], path):
                            print("Product " + pr_safe + " downloaded successfully." )
                        else:
                            print("Product " + pr_safe + "could not be downloaded neither from ONDA ENS nor from onda catalogue. The program will exit.")
                            
                            return 0
                    else:
                        print(f'The product {pr} was copied and extracted successfully from ONDA ENS. Preprocessing will now take place.')
                        products_id_list_safe[index_path].append(pr_safe)
    return products_id_list_safe
  

def Get_zonenumber_letter(ds):
    '''
    Return list of corner coordinates from a gdal tiff file. 
    '''
    # xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    # width, height = ds.RasterXSize, ds.RasterYSize
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
    return zone_letter, zone_number
    
    
    
def convert_box_extent(boundary_box_meters, zone_letter, zone_number):  
    xmin, xmax, ymin, ymax = boundary_box_meters
    ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone_number, northern=False)
    ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone_number,  northern=False)
    return (ymax_conv, xmin_conv),  (ymin_conv, xmax_conv)


#find_tiles_extent(path_list)
# box_extent1 = 213655.5490447594202124, 242631.3319891514256597, 6556623.1746119158342481, 6584354.5987795544788241
#box_extent2 = 282628.5783847846323624, 321914.7626222731778398, 6478761.8682950828224421, 6516625.9282162822782993
#box_extent = 262782.7685868184780702, 339211.6153815748402849, 6581086.6067097093909979,6619363.7795707946643233
# box_extent3 = 125146.4600816461606883, 159574.3528332773130387, 6542355.6920539112761617, 6586020.3365193950012326
# box_belongs_to_tile(path_list, box_extent1)

# box_belongs_to_tile(path_list, box_extent3)


#xmin_box, xmax_box, ymin_box, ymax_box
# xmin_tile, xmax_tile, ymin_tile, ymax_tile = tile_extent
#xmin_box, xmax_box, ymin_box, ymax_box = box_extent

# x_center_tile = (xmin_tile + xmax_tile)/2
# y_center_tile = (ymin_tile + ymax_tile)/2

# tile_directions.append(ymax_box > ymax_tile)
# tile_directions.append(xmax_box > xmax_tile)
# tile_directions.append(ymin_box < ymin_tile)
# tile_directions.append(xmin_box < xmin_tile)

#if tile_directions[0]:
#download_tile  -> function that downloads the needed tile
#search for the product needed based on the new footproint and download the tiles needed.
#     download_tile((x_center_tile,ymax_box))
# if tile_directions[1]:
#     download_tile((xmax_box,y_center_tile))
# if tile_directions[2]:
#     download_tile((x_center_tile,ymin_box))
# if tile_directions[3]:
#     download_tile((xmin_box,y_center_tile))
#box_belongs_to_tile(path_list, box_extent2)  