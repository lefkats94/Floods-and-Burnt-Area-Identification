import json
from osgeo import gdal
import numpy as np
import input_parameters
def is_uncertainty_greater_than(path_for_metadata, threshold):
    flag = False
    with open(path_for_metadata, 'r') as json_file:
        my_json = json.load(json_file)
        #Check if uncertainty for both images is greater than the threshold.
        for uncertainty_value in [my_json['metadata']['uncertainty_lower'], my_json['metadata']['uncertainty_upper'] ]:
            if uncertainty_value > threshold:
                flag = True
    return flag

def affected_area_detected(path_for_final_pr, path_for_metadata):
    """
    Checks if the percentage of the burnt area detected is greater than a value so as to avoid return results with noise
    Parameters:
        path_for_final_pr (str): destination path for the final tiff file 
        path_for_metadata (str): destination path for the final metadata.json file
    
    Return: True if burnt area has been detected 
    """
    event = input_parameters.event
    with open(path_for_metadata, 'r') as json_file:
        my_json = json.load(json_file)
        if event == "fire":
            total_burned_area = my_json['metadata']['total_affected_area']
            high_severity_area = my_json['metadata']['high_severity_area']
            medium_high_severity_area = my_json['metadata']['medium_high_severity_area']
            percentage_of_burned = total_burned_area/calculate_raster_area(path_for_final_pr) * 100
            if percentage_of_burned < 0.5 or (high_severity_area == 0 and medium_high_severity_area < 0.02 and percentage_of_burned < 1) :
                return False
        else:
            total_water_change_area = my_json['metadata']['land_to_water_area']
            percentage_of_water_change = total_water_change_area / calculate_raster_area(path_for_final_pr) * 100
            if percentage_of_water_change < 0.1:
                return False
    return True

def calculate_raster_area(path_to_final_pr):
    final_pr = gdal.Open(path_to_final_pr)
    srcband = final_pr.GetRasterBand(1)
    final_array = srcband.ReadAsArray(0, 0, final_pr.RasterXSize, final_pr.RasterYSize).astype(np.float)
    #taking into account the pixel's size, and convert to km2
    size = final_array.size
    area = final_array.size * 100 / 1000000
    return area

def find_center_of_geotiff(geotiff):
    """
    Given a tiff file returns the coordinates of the center of the map in meters.
    Parameters:
        geotiff (str): destination path for input tiff file 
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

def is_uncertainty_greater_than_for_each_box(path_for_metadata, threshold):
    flag = False
    with open(path_for_metadata, 'r') as json_file:
        my_json = json.load(json_file)
        #Check if uncertainty for both images is greater than the threshold.
        for uncertainty_value in [my_json['uncertainty_lower'], my_json['uncertainty_upper'] ]:
            if uncertainty_value > threshold:
                flag = True
    return flag