from osgeo import gdal
import numpy as np
import datetime
import time
import os
from PIL import Image
import time
import rasterio
from collections import OrderedDict
import json
import sys
cwd = os.getcwd()
sys.path.append(os.path.join(cwd, 'watermask_algorithm_snapearth'))
import utm
import datetime

def land_water_change_detection_simple(before_folder, after_folder, rgb_filepath, destination_file):


    # initialization
    before_date = os.path.split(before_folder)[1]
    after_date = os.path.split(after_folder)[1]

    watermask_before_filepath = os.path.join(before_folder, 'water_mask_' + before_date + '.tif')
    watermask_after_filepath = os.path.join(after_folder, 'water_mask_' + after_date + '.tif')
    print(os.path.exists(watermask_after_filepath))
    print(os.path.exists(watermask_before_filepath))
   
    
    ndvi_after_filepath = os.path.join(after_folder, 'NDVI.tif')


    # report
    f = open(os.path.join(destination_file, 'water_change_detection_report.txt'), 'w')
    # f.write('Watermasks for: ' + product_begin_date + '\n')

    # check about a CLC tif file in the before and after folders
    if os.path.exists(os.path.join(before_folder, 'CLC.tif')):
        clc_filepath = os.path.join(before_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'CLC.tif')):
        clc_filepath = os.path.join(after_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        print('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.')
        f.write('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead. \n')
        clc_filepath = -1

    # initialize global land cover - check about LC_global in the tif file in the before and after folder
    if os.path.exists(os.path.join(before_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(before_folder, 'LC100_global.tif')
    elif os.path.exists(os.path.join(after_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(after_folder, 'LC100_global.tif')
    else:
        print('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder')
        f.write('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder\n')
        lc_gl_filepath = -1

    print('Water change detection between %s and %s ' % (before_date, after_date))
    f.write('Water change detection between %s and %s \n' % (before_date, after_date))

    # read rasters and create the respective arrays
    t0 = time.time()

    raster_x_size = 0
    raster_y_size = 0

    # load waterMasks as numpy arrays for processing
    
    SOURCE = gdal.Open(watermask_before_filepath)
    guidance = SOURCE
    srcband = SOURCE.GetRasterBand(1)
    raster_x_size = SOURCE.RasterXSize
    raster_y_size = SOURCE.RasterYSize
    # geoTrans_guidance1 = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    # wkt_guidance1 = SOURCE.GetProjection()
    SOURCE1_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)

    SOURCE = gdal.Open(watermask_after_filepath)
    srcband = SOURCE.GetRasterBand(1)
    # geoTrans_guidance2 = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    # wkt_guidance2 = SOURCE.GetProjection()
    if raster_x_size != SOURCE.RasterXSize or raster_y_size != SOURCE.RasterYSize:
        print('Input waterMasks have different dimensions. Using the dimension of the previous WaterMask as the basis.')
        SOURCE2_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize, raster_x_size, raster_y_size)
    else:
        SOURCE2_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)

    # if CLC 2018 initialize the respective numpy array  else use the Global LC 100m if file is provided
    if clc_filepath != -1:
        # Extract Land use - Land cover from the provided CLC2018 GeoTIFF file. If a file isn't present, no LULC percentages are calculated.
        CLC_SOURCE = gdal.Open(clc_filepath)
        srcband = CLC_SOURCE.GetRasterBand(1)
        # geoTrans_guidance_clc = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
        # wkt_guidance_clc = SOURCE.GetProjection()
        CLC_arr = srcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize)
        CLC_arr_resized = srcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize, SOURCE.RasterXSize, SOURCE.RasterYSize)
        # save_geo_tiff(SOURCE, clc_filepath_resized, 'GTiff', SOURCE.RasterXSize, SOURCE.RasterYSize, CLC_arr_resized,gdal.GDT_Float32)
        CLC_SOURCE = 0
        CLC_arr = 0
    #use the global land cover instead
    elif lc_gl_filepath != -1:
        # Extract Land use - Land cover from the provided LC100_global.tiff file which has been calculated for each band
        LC100_global_SOURCE = gdal.Open(lc_gl_filepath)
        srcband = LC100_global_SOURCE.GetRasterBand(1)
        
        LC100_gl_arr_resized = srcband.ReadAsArray(0, 0, LC100_global_SOURCE.RasterXSize,
                                                   LC100_global_SOURCE.RasterYSize, SOURCE.RasterXSize,
                                                   SOURCE.RasterYSize)
    else:
        print("No CLC or LC global file provided.")

    # Create a mask where NDVI > 0.8. This is to filter out noise that may be induced.
    SOURCE = gdal.Open(ndvi_after_filepath)
    srcband = SOURCE.GetRasterBand(1)
    ndvi_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
    ndvi_mask = np.where(ndvi_arr < 0.8, True, False)


    # final outputs initialization
    rgbOutput = np.zeros((raster_y_size, raster_x_size, 3), 'uint8')
    watermaskOutput = np.zeros((raster_y_size, raster_x_size, 4), 'uint8')
    waterMaskOutputTIF = np.zeros((raster_y_size, raster_x_size), 'uint8')

    # in a RGB image is provided, initialize the output array
    if rgb_filepath == -1:
        pass
    else:
        SOURCE = gdal.Open(rgb_filepath)
        red_srcband = SOURCE.GetRasterBand(1)
        green_srcband = SOURCE.GetRasterBand(2)
        blue_srcband = SOURCE.GetRasterBand(3)
        red_arr = red_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        green_arr = green_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        blue_arr = blue_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        rgbOutput[:, :, 0] = np.copy(red_arr)
        rgbOutput[:, :, 1] = np.copy(green_arr)
        rgbOutput[:, :, 2] = np.copy(blue_arr)
        SOURCE = 0
        red_srcband = 0
        green_srcband = 0
        blue_srcband = 0

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

    # load SCL files and calculate uncertainty
    if os.path.exists(os.path.join(before_folder, 'SCL.tif')):
        SCL_before = gdal.Open(os.path.join(before_folder, 'SCL.tif'))
        srcband = SCL_before.GetRasterBand(1)
        SCL_before_array = srcband.ReadAsArray(0, 0, SCL_before.RasterXSize, SCL_before.RasterYSize)
        SCL_before_array_resized = srcband.ReadAsArray(0, 0, SCL_before.RasterXSize, SCL_before.RasterYSize, raster_x_size,
                                                      raster_y_size)
        uncertainty_before = np.zeros((SCL_before.RasterXSize, SCL_before.RasterYSize))
        uncertainty_before = np.where(SCL_before_array == 2, True, False)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 3, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 8, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 9, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 1, True, False), uncertainty_before)
    else:
        print("SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated")
        f.write(
            'SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated\n')
        uncertainty_before = -1
    if os.path.exists(os.path.join(after_folder, 'SCL.tif')):
        SCL_after = gdal.Open(os.path.join(after_folder, 'SCL.tif'))
        srcband = SCL_after.GetRasterBand(1)
        SCL_after_array = srcband.ReadAsArray(0, 0, SCL_after.RasterXSize, SCL_after.RasterYSize)
        SCL_after_array_resized = srcband.ReadAsArray(0, 0, SCL_after.RasterXSize, SCL_after.RasterYSize, raster_x_size,
                                      raster_y_size)
        uncertainty_after = np.zeros((SCL_after.RasterXSize, SCL_after.RasterYSize))
        uncertainty_after = np.where(SCL_after_array == 2, True, False)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 3, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 8, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 9, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 1, True, False), uncertainty_after)
    else:
        print("SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated")
        f.write(
            'SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated\n')

        uncertainty_after = -1

    # detection of the land-to-water and water-to-land changes
    land_to_water_array = np.logical_and(SOURCE2_arr.astype('bool'), np.invert(SOURCE1_arr.astype('bool')))
    #use SCL layers so as to exclude clouds or shadows that might have been predicted erroneously 
    try:
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 3, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 8, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 9, False, True), land_to_water_array)
    except:
        print('The SCL array for the image before could not be used as a the mask for the clouds of the land_to_water_array.')
    try:
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 3, False, True),  land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 8, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 9, False, True), land_to_water_array)
    except:
        print('The SCL array for the image after could not be used as a mask for the clouds of the land_to_water_array.')
    
    land_to_water_array = np.logical_and(land_to_water_array, ndvi_mask)

    # water to land changes are not calculated by default.
    # If they are needed with the context of SnapEarth, then comment the first 3 lines and uncomment the following 3

    # dummy array logic. will always return zero array
    #water_to_land_array = np.logical_and(SOURCE1_arr.astype('bool'), np.invert(SOURCE1_arr.astype('bool')))
    #water_to_land_array = np.logical_and(water_to_land_array, ndvi_mask)
    #water_to_land_calc = 0

    # correct calculation of water to land changes. to calculate uncomment the following lines
    water_to_land_array = np.logical_and(SOURCE1_arr.astype('bool'), np.invert(SOURCE2_arr.astype('bool')))
    #use SCL layers so as to exclude clouds or shadows that might have been predicted erroneously 
    try:
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 3, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 8, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 9, False, True), water_to_land_array)
    except:
        print('The SCL array for the image before could not be used as a the mask for the clouds of the water_to_land_array.')
    try:
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 3, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 8, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 9, False, True), water_to_land_array)
    except:
        print('The SCL array for the image after could not be used as a the mask for the clouds of the water_to_land_array.')
    water_to_land_array = np.logical_and(water_to_land_array, ndvi_mask)
    water_to_land_calc = 1




    # outputs as numpy arrays
    watermaskOutput[np.invert(np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool'))), :] = land_fill_RGBA
    watermaskOutput[np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool')), :] = water_fill_RGBA
    watermaskOutput[water_to_land_array, :] = water_to_land_fill_RGBA
    watermaskOutput[land_to_water_array, :] = land_to_water_fill_RGBA

    rgbOutput[water_to_land_array, :] = water_to_land_fill
    rgbOutput[land_to_water_array,:] = land_to_water_fill

    waterMaskOutputTIF [np.invert(np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool')))] = 0
    waterMaskOutputTIF [np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool'))] = 1
    waterMaskOutputTIF [water_to_land_array] = 2
    waterMaskOutputTIF [land_to_water_array] = 3

    # calculate the total number of pixel of the land-to-water and water-to-land classes
    water_to_land_counter = (np.where(waterMaskOutputTIF == 2, True, False)).sum()
    land_to_water_counter = (np.where(waterMaskOutputTIF == 3, True, False)).sum()


    t1 = time.time()
    f.write('Result extraction required {:.2f} sec\n\n'.format(t1 - t0))
    f.write('The size of the land-to-water area is {:.2f} km^2\n'.format((float(land_to_water_counter) * 100) / 1000000))
    if water_to_land_calc == 1:
        f.write('The size of the water-to-land area is {:.2f} km^2\n\n'.format((float(water_to_land_counter) * 100) / 1000000))

    # calculated uncertainty for before/after images
    if isinstance(uncertainty_before, int) or isinstance(uncertainty_after, int):
        if isinstance(uncertainty_before, int):
            uncertainty_after = float(uncertainty_after.sum()) / (uncertainty_after.shape[0] * uncertainty_after.shape[1]) * 100
            f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,uncertainty_after))
        else:
            uncertainty_before = float(uncertainty_before.sum()) / (uncertainty_before.shape[0] * uncertainty_before.shape[1]) * 100
            f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,uncertainty_after))
    else:
        uncertainty_before = float(uncertainty_before.sum()) / (uncertainty_before.shape[0] * uncertainty_before.shape[1]) * 100
        uncertainty_after = float(uncertainty_after.sum()) / (uncertainty_after.shape[0] * uncertainty_after.shape[1]) * 100
        f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before, uncertainty_after))

    
    # calculated CLC classes affected for the water to land changes if CLC exists, otherwise calculate global lanad cover classes form the global layer
    if clc_filepath !=-1:

        temp_array = np.multiply(CLC_arr_resized, land_to_water_array)
        clc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(CLC_arr_resized, water_to_land_array)
        clc_water_to_land = temp_array[np.nonzero(temp_array)]

        clc_land_to_water_classes = get_percentage_for_all_classes_of_CLC_array(clc_land_to_water)
        clc_water_to_land_classes = get_percentage_for_all_classes_of_CLC_array(clc_water_to_land)

        # {k: v for k, v in sorted(clc_land_to_water_classes.items(), key=lambda item: item[1])}
        f.write('The CLC classes with their percentages affected from the floods are:\n')
        land_to_water_classes = {}
        for i in clc_land_to_water_classes.keys():
            if clc_land_to_water_classes[i][1] > 2:
                f.write(clc_land_to_water_classes[i][0] + ' ' + str(clc_land_to_water_classes[i][1]) + '%\n')
                land_to_water_classes.update(dict({clc_land_to_water_classes[i]}))


        if water_to_land_calc == 1 :
            water_to_land_classes = {}
            f.write('\nThe CLC classes with their percentages affected water to land change are:\n')
            for i in clc_water_to_land_classes.keys():
                if clc_water_to_land_classes[i][1] > 2:
                    f.write(clc_land_to_water_classes[i][0] + ' ' + str(clc_land_to_water_classes[i][1]) + '%\n')
                    water_to_land_classes.update(dict({clc_water_to_land_classes[i]}))
    
    elif lc_gl_filepath !=-1:
        temp_array = np.multiply(LC100_gl_arr_resized, land_to_water_array)
        glc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(LC100_gl_arr_resized, water_to_land_array)
        glc_water_to_land = temp_array[np.nonzero(temp_array)]

        glc_land_to_water_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_land_to_water)
        glc_water_to_land_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_water_to_land)

        f.write('The LC classes with their percentages affected from the floods are:\n')
        land_to_water_classes = {}
        for i in glc_land_to_water_classes.keys():
            if glc_land_to_water_classes[i][1] > 2:
                f.write(glc_land_to_water_classes[i][0] + ' ' + str(glc_land_to_water_classes[i][1]) + '%\n')
                land_to_water_classes.update(dict({glc_land_to_water_classes[i]}))

        if water_to_land_calc == 1:
            water_to_land_classes = {}
            f.write('\nThe LC classes with their percentages affected water to land change are:\n')
            for i in glc_water_to_land_classes.keys():
                if glc_water_to_land_classes[i][1] > 2:
                    f.write(glc_land_to_water_classes[i][0] + ' ' + str(glc_land_to_water_classes[i][1]) + '%\n')
                    water_to_land_classes.update(dict({glc_water_to_land_classes[i]}))
    else:
        land_to_water_classes = {}
        water_to_land_classes = {}
    
    # save Outputs to disk
    im1 = Image.fromarray(watermaskOutput)
    im2 = Image.fromarray(rgbOutput)
    im1.save(os.path.join(destination_file, 'water_change.png'))
    im2.save(os.path.join(destination_file, 'water_area_change.png'))
    save_geo_tiff(guidance, os.path.join(destination_file,'water_change.tif' ), 'GTiff',raster_x_size, raster_y_size, waterMaskOutputTIF , gdal.GDT_Float32)
    f.close()
    #save as png TCI.tiff before
    rgb_filepath_bef = os.path.join(before_folder, 'TCI.tif')
    if os.path.exists(rgb_filepath_bef):
        RGB_SOURCE_before = gdal.Open(rgb_filepath_bef)
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
        temp_image.save(os.path.join(destination_file, 'before_the_event.png'))


    #Save as png TCI.tiff after
    rgb_filepath_af = os.path.join(after_folder, 'TCI.tif')
    if os.path.exists(rgb_filepath_af):
        RGB_SOURCE_after = gdal.Open(rgb_filepath_af)
        red_srcband_a = RGB_SOURCE_after.GetRasterBand(1)
        green_srcband_a = RGB_SOURCE_after.GetRasterBand(2)
        blue_srcband_a = RGB_SOURCE_after.GetRasterBand(3)
        rgbOutput_after = np.zeros((RGB_SOURCE_after.RasterYSize, RGB_SOURCE_after.RasterXSize, 3), 'uint8')
        red_arr = red_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        green_arr = green_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        blue_arr = blue_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        rgbOutput_after[:, :, 0] = np.copy(red_arr)
        rgbOutput_after[:, :, 1] = np.copy(green_arr)
        rgbOutput_after[:, :, 2] = np.copy(blue_arr)
        temp_image = Image.fromarray(rgbOutput_after)
        temp_image.save(os.path.join(destination_file, 'after_the_event.png'))


def land_water_change_detection(before_folder, after_folder, rgb_filepath, destination_file, output_id, event_id):


    # initialization
    before_date = os.path.split(before_folder)[1]
    after_date = os.path.split(after_folder)[1]

    watermask_before_filepath = os.path.join(before_folder, 'water_mask_' + before_date + '.tif')
    watermask_after_filepath = os.path.join(after_folder, 'water_mask_' + after_date + '.tif')
    print(os.path.exists(watermask_after_filepath))
    print(os.path.exists(watermask_before_filepath))
   
    
    ndvi_after_filepath = os.path.join(after_folder, 'NDVI.tif')


    # report
    f = open(os.path.join(destination_file, 'water_change_detection_report.txt'), 'w')
    # f.write('Watermasks for: ' + product_begin_date + '\n')

    # check about a CLC tif file in the before and after folders
    if os.path.exists(os.path.join(before_folder, 'CLC.tif')):
        clc_filepath = os.path.join(before_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'CLC.tif')):
        clc_filepath = os.path.join(after_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        print('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.')
        f.write('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead. \n')
        clc_filepath = -1

    # initialize global land cover - check about LC_global in the tif file in the before and after folder
    if os.path.exists(os.path.join(before_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(before_folder, 'LC100_global.tif')
    elif os.path.exists(os.path.join(after_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(after_folder, 'LC100_global.tif')
    else:
        print('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder')
        f.write('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder\n')
        lc_gl_filepath = -1

    print('Water change detection between %s and %s ' % (before_date, after_date))
    f.write('Water change detection between %s and %s \n' % (before_date, after_date))

    # read rasters and create the respective arrays
    t0 = time.time()

    raster_x_size = 0
    raster_y_size = 0

    # load waterMasks as numpy arrays for processing
    
    SOURCE = gdal.Open(watermask_before_filepath)
    guidance = SOURCE
    srcband = SOURCE.GetRasterBand(1)
    raster_x_size = SOURCE.RasterXSize
    raster_y_size = SOURCE.RasterYSize
    # geoTrans_guidance1 = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    # wkt_guidance1 = SOURCE.GetProjection()
    SOURCE1_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)

    SOURCE = gdal.Open(watermask_after_filepath)
    srcband = SOURCE.GetRasterBand(1)
    # geoTrans_guidance2 = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    # wkt_guidance2 = SOURCE.GetProjection()
    if raster_x_size != SOURCE.RasterXSize or raster_y_size != SOURCE.RasterYSize:
        print('Input waterMasks have different dimensions. Using the dimension of the previous WaterMask as the basis.')
        SOURCE2_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize, raster_x_size, raster_y_size)
    else:
        SOURCE2_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)

    # if CLC 2018 initialize the respective numpy array  else use the Global LC 100m if file is provided
    if clc_filepath != -1:
        # Extract Land use - Land cover from the provided CLC2018 GeoTIFF file. If a file isn't present, no LULC percentages are calculated.
        CLC_SOURCE = gdal.Open(clc_filepath)
        srcband = CLC_SOURCE.GetRasterBand(1)
        # geoTrans_guidance_clc = SOURCE.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
        # wkt_guidance_clc = SOURCE.GetProjection()
        CLC_arr = srcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize)
        CLC_arr_resized = srcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize, SOURCE.RasterXSize, SOURCE.RasterYSize)
        # save_geo_tiff(SOURCE, clc_filepath_resized, 'GTiff', SOURCE.RasterXSize, SOURCE.RasterYSize, CLC_arr_resized,gdal.GDT_Float32)
        CLC_SOURCE = 0
        CLC_arr = 0
    #use the global land cover instead
    elif lc_gl_filepath != -1:
        # Extract Land use - Land cover from the provided LC100_global.tiff file which has been calculated for each band
        LC100_global_SOURCE = gdal.Open(lc_gl_filepath)
        srcband = LC100_global_SOURCE.GetRasterBand(1)
        
        LC100_gl_arr_resized = srcband.ReadAsArray(0, 0, LC100_global_SOURCE.RasterXSize,
                                                   LC100_global_SOURCE.RasterYSize, SOURCE.RasterXSize,
                                                   SOURCE.RasterYSize)
    else:
        print("No CLC or LC global file provided.")

    # Create a mask where NDVI > 0.8. This is to filter out noise that may be induced.
    SOURCE = gdal.Open(ndvi_after_filepath)
    srcband = SOURCE.GetRasterBand(1)
    ndvi_arr = srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
    ndvi_mask = np.where(ndvi_arr < 0.8, True, False)


    # final outputs initialization
    rgbOutput = np.zeros((raster_y_size, raster_x_size, 3), 'uint8')
    watermaskOutput = np.zeros((raster_y_size, raster_x_size, 4), 'uint8')
    waterMaskOutputTIF = np.zeros((raster_y_size, raster_x_size), 'uint8')

    # in a RGB image is provided, initialize the output array
    if rgb_filepath == -1:
        pass
    else:
        SOURCE = gdal.Open(rgb_filepath)
        red_srcband = SOURCE.GetRasterBand(1)
        green_srcband = SOURCE.GetRasterBand(2)
        blue_srcband = SOURCE.GetRasterBand(3)
        red_arr = red_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        green_arr = green_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        blue_arr = blue_srcband.ReadAsArray(0, 0, SOURCE.RasterXSize, SOURCE.RasterYSize)
        rgbOutput[:, :, 0] = np.copy(red_arr)
        rgbOutput[:, :, 1] = np.copy(green_arr)
        rgbOutput[:, :, 2] = np.copy(blue_arr)
        SOURCE = 0
        red_srcband = 0
        green_srcband = 0
        blue_srcband = 0

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

    # load SCL files and calculate uncertainty
    if os.path.exists(os.path.join(before_folder, 'SCL.tif')):
        SCL_before = gdal.Open(os.path.join(before_folder, 'SCL.tif'))
        srcband = SCL_before.GetRasterBand(1)
        SCL_before_array = srcband.ReadAsArray(0, 0, SCL_before.RasterXSize, SCL_before.RasterYSize)
        SCL_before_array_resized = srcband.ReadAsArray(0, 0, SCL_before.RasterXSize, SCL_before.RasterYSize, raster_x_size,
                                                      raster_y_size)
        uncertainty_before = np.zeros((SCL_before.RasterXSize, SCL_before.RasterYSize))
        uncertainty_before = np.where(SCL_before_array == 2, True, False)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 3, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 8, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 9, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 1, True, False), uncertainty_before)
    else:
        print("SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated")
        f.write(
            'SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated\n')
        uncertainty_before = -1
    if os.path.exists(os.path.join(after_folder, 'SCL.tif')):
        SCL_after = gdal.Open(os.path.join(after_folder, 'SCL.tif'))
        srcband = SCL_after.GetRasterBand(1)
        SCL_after_array = srcband.ReadAsArray(0, 0, SCL_after.RasterXSize, SCL_after.RasterYSize)
        SCL_after_array_resized = srcband.ReadAsArray(0, 0, SCL_after.RasterXSize, SCL_after.RasterYSize, raster_x_size,
                                      raster_y_size)
        uncertainty_after = np.zeros((SCL_after.RasterXSize, SCL_after.RasterYSize))
        uncertainty_after = np.where(SCL_after_array == 2, True, False)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 3, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 8, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 9, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 1, True, False), uncertainty_after)
    else:
        print("SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated")
        f.write(
            'SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated\n')

        uncertainty_after = -1

    # detection of the land-to-water and water-to-land changes
    land_to_water_array = np.logical_and(SOURCE2_arr.astype('bool'), np.invert(SOURCE1_arr.astype('bool')))
    #use SCL layers so as to exclude clouds or shadows that might have been predicted erroneously 
    try:
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 3, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 8, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_before_array_resized == 9, False, True), land_to_water_array)
    except:
        print('The SCL array for the image before could not be used as a the mask for the clouds of the land_to_water_array.')
    try:
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 3, False, True),  land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 8, False, True), land_to_water_array)
        land_to_water_array = np.logical_and(np.where(SCL_after_array_resized == 9, False, True), land_to_water_array)
    except:
        print('The SCL array for the image after could not be used as a mask for the clouds of the land_to_water_array.')
    
    land_to_water_array = np.logical_and(land_to_water_array, ndvi_mask)

    # water to land changes are not calculated by default.
    # If they are needed with the context of SnapEarth, then comment the first 3 lines and uncomment the following 3

    # dummy array logic. will always return zero array
    #water_to_land_array = np.logical_and(SOURCE1_arr.astype('bool'), np.invert(SOURCE1_arr.astype('bool')))
    #water_to_land_array = np.logical_and(water_to_land_array, ndvi_mask)
    #water_to_land_calc = 0

    # correct calculation of water to land changes. to calculate uncomment the following lines
    water_to_land_array = np.logical_and(SOURCE1_arr.astype('bool'), np.invert(SOURCE2_arr.astype('bool')))
    #use SCL layers so as to exclude clouds or shadows that might have been predicted erroneously 
    try:
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 3, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 8, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_before_array_resized == 9, False, True), water_to_land_array)
    except:
        print('The SCL array for the image before could not be used as a the mask for the clouds of the water_to_land_array.')
    try:
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 3, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 8, False, True), water_to_land_array)
        water_to_land_array = np.logical_and(np.where(SCL_after_array_resized == 9, False, True), water_to_land_array)
    except:
        print('The SCL array for the image after could not be used as a the mask for the clouds of the water_to_land_array.')
    water_to_land_array = np.logical_and(water_to_land_array, ndvi_mask)
    water_to_land_calc = 1




    # outputs as numpy arrays
    watermaskOutput[np.invert(np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool'))), :] = land_fill_RGBA
    watermaskOutput[np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool')), :] = water_fill_RGBA
    watermaskOutput[water_to_land_array, :] = water_to_land_fill_RGBA
    watermaskOutput[land_to_water_array, :] = land_to_water_fill_RGBA

    rgbOutput[water_to_land_array, :] = water_to_land_fill
    rgbOutput[land_to_water_array,:] = land_to_water_fill

    waterMaskOutputTIF [np.invert(np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool')))] = 0
    waterMaskOutputTIF [np.logical_and(SOURCE2_arr.astype('bool'), SOURCE1_arr.astype('bool'))] = 1
    waterMaskOutputTIF [water_to_land_array] = 2
    waterMaskOutputTIF [land_to_water_array] = 3


    # calculate the total number of pixel of the land-to-water and water-to-land classes
    water_to_land_counter = (np.where(waterMaskOutputTIF == 2, True, False)).sum()
    land_to_water_counter = (np.where(waterMaskOutputTIF == 3, True, False)).sum()


    t1 = time.time()
    f.write('Result extraction required {:.2f} sec\n\n'.format(t1 - t0))
    f.write('The size of the land-to-water area is {:.2f} km^2\n'.format((float(land_to_water_counter) * 100) / 1000000))
    if water_to_land_calc == 1:
        f.write('The size of the water-to-land area is {:.2f} km^2\n\n'.format((float(water_to_land_counter) * 100) / 1000000))

    # calculated uncertainty for before/after images
    if isinstance(uncertainty_before, int) or isinstance(uncertainty_after, int):
        if isinstance(uncertainty_before, int):
            uncertainty_after = float(uncertainty_after.sum()) / (uncertainty_after.shape[0] * uncertainty_after.shape[1]) * 100
            f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,uncertainty_after))
        else:
            uncertainty_before = float(uncertainty_before.sum()) / (uncertainty_before.shape[0] * uncertainty_before.shape[1]) * 100
            f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,uncertainty_after))
    else:
        uncertainty_before = float(uncertainty_before.sum()) / (uncertainty_before.shape[0] * uncertainty_before.shape[1]) * 100
        uncertainty_after = float(uncertainty_after.sum()) / (uncertainty_after.shape[0] * uncertainty_after.shape[1]) * 100
        f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before, uncertainty_after))

    
    # calculated CLC classes affected for the water to land changes if CLC exists, otherwise calculate global lanad cover classes form the global layer
    if clc_filepath !=-1:

        temp_array = np.multiply(CLC_arr_resized, land_to_water_array)
        clc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(CLC_arr_resized, water_to_land_array)
        clc_water_to_land = temp_array[np.nonzero(temp_array)]

        clc_land_to_water_classes = get_percentage_for_all_classes_of_CLC_array(clc_land_to_water)
        clc_water_to_land_classes = get_percentage_for_all_classes_of_CLC_array(clc_water_to_land)

        # {k: v for k, v in sorted(clc_land_to_water_classes.items(), key=lambda item: item[1])}
        f.write('The CLC classes with their percentages affected from the floods are:\n')
        land_to_water_classes = {}
        for i in clc_land_to_water_classes.keys():
            if clc_land_to_water_classes[i][1] > 2:
                f.write(clc_land_to_water_classes[i][0] + ' ' + str(clc_land_to_water_classes[i][1]) + '%\n')
                land_to_water_classes.update(dict({clc_land_to_water_classes[i]}))


        if water_to_land_calc == 1 :
            water_to_land_classes = {}
            f.write('\nThe CLC classes with their percentages affected water to land change are:\n')
            for i in clc_water_to_land_classes.keys():
                if clc_water_to_land_classes[i][1] > 2:
                    f.write(clc_land_to_water_classes[i][0] + ' ' + str(clc_land_to_water_classes[i][1]) + '%\n')
                    water_to_land_classes.update(dict({clc_water_to_land_classes[i]}))
    
    elif lc_gl_filepath !=-1:
        temp_array = np.multiply(LC100_gl_arr_resized, land_to_water_array)
        glc_land_to_water = temp_array[np.nonzero(temp_array)]

        temp_array = np.multiply(LC100_gl_arr_resized, water_to_land_array)
        glc_water_to_land = temp_array[np.nonzero(temp_array)]

        glc_land_to_water_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_land_to_water)
        glc_water_to_land_classes = get_percentage_for_all_classes_of_LC_gl_array(glc_water_to_land)

        f.write('The LC classes with their percentages affected from the floods are:\n')
        land_to_water_classes = {}
        for i in glc_land_to_water_classes.keys():
            if glc_land_to_water_classes[i][1] > 2:
                f.write(glc_land_to_water_classes[i][0] + ' ' + str(glc_land_to_water_classes[i][1]) + '%\n')
                land_to_water_classes.update(dict({glc_land_to_water_classes[i]}))

        if water_to_land_calc == 1:
            water_to_land_classes = {}
            f.write('\nThe LC classes with their percentages affected water to land change are:\n')
            for i in glc_water_to_land_classes.keys():
                if glc_water_to_land_classes[i][1] > 2:
                    f.write(glc_land_to_water_classes[i][0] + ' ' + str(glc_land_to_water_classes[i][1]) + '%\n')
                    water_to_land_classes.update(dict({glc_water_to_land_classes[i]}))
    else:
        land_to_water_classes = {}
        water_to_land_classes = {}
    
    # save Outputs to disk
    im1 = Image.fromarray(watermaskOutput)
    im2 = Image.fromarray(rgbOutput)
    im1.save(os.path.join(destination_file, 'water_change.png'))
    im2.save(os.path.join(destination_file, 'water_area_change.png'))
    save_geo_tiff(guidance, os.path.join(destination_file,'water_change.tif' ), 'GTiff',raster_x_size, raster_y_size, waterMaskOutputTIF , gdal.GDT_Float32)
    f.close()
    #save as png TCI.tiff before
    rgb_filepath_bef = os.path.join(before_folder, 'TCI.tif')
    if os.path.exists(rgb_filepath_bef):
        RGB_SOURCE_before = gdal.Open(rgb_filepath_bef)
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
        temp_image.save(os.path.join(destination_file, 'before_the_event.png'))


    #Save as png TCI.tiff after
    rgb_filepath_af = os.path.join(after_folder, 'TCI.tif')
    if os.path.exists(rgb_filepath_af):
        RGB_SOURCE_after = gdal.Open(rgb_filepath_af)
        red_srcband_a = RGB_SOURCE_after.GetRasterBand(1)
        green_srcband_a = RGB_SOURCE_after.GetRasterBand(2)
        blue_srcband_a = RGB_SOURCE_after.GetRasterBand(3)
        rgbOutput_after = np.zeros((RGB_SOURCE_after.RasterYSize, RGB_SOURCE_after.RasterXSize, 3), 'uint8')
        red_arr = red_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        green_arr = green_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        blue_arr = blue_srcband_a.ReadAsArray(0, 0, RGB_SOURCE_after.RasterXSize, RGB_SOURCE_after.RasterYSize)
        rgbOutput_after[:, :, 0] = np.copy(red_arr)
        rgbOutput_after[:, :, 1] = np.copy(green_arr)
        rgbOutput_after[:, :, 2] = np.copy(blue_arr)
        temp_image = Image.fromarray(rgbOutput_after)
        temp_image.save(os.path.join(destination_file, 'after_the_event.png'))
    
    
    
    
	

    # # test code block for creating an RGB overlayed image with legend.
    # feel free to experiment

    # test = plt.imread(os.path.join(destination_file, 'RGB_%s_%s.png' %(before_date, after_date)))
    # fig = plt.figure( figsize=(19.20, 10.80), dpi = 300)
    # # plt.imshow(test)
    # string_patch = mpatches.Patch(color='white', label='Land-Water Transition Zone Change Detection between %s and %s' %(before_date, after_date), visible = False)
    # # string_patch = mpatches.Patch(color='white', label=' ', visible= False)
    # land_to_water_patch = mpatches.Patch(color='darkturquoise', label='Land to water change. Total area is {:.2f} km2'.format((float(land_to_water_counter) * 100) / 1000000))
    # water_to_land_patch = mpatches.Patch(color='darkorange', label='Water to land change. Total area is {:.2f} km2'.format((float(water_to_land_counter) * 100) / 1000000))
    # # land_to_water_patch = mpatches.Patch(color='darkturquoise', label='Land to water change')
    # # water_to_land_patch = mpatches.Patch(color='darkorange', label='Water to land change')
    # string_patch2 = mpatches.Patch(color='white', label='Uncertainty: [-{:.2f}%,+{:.2f}%]'.format(uncertainty_before, uncertainty_after), visible= False)
    # plt.legend(handles=[string_patch, land_to_water_patch, water_to_land_patch, string_patch2], loc = 3, prop={'size':12})
    # plt.gca().set_axis_off()
    # plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    # plt.margins(0, 0)
    # plt.gca().yaxis.set_major_locator(plt.NullLocator())
    # plt.savefig(os.path.join(destination_file, 'Change detection map %s_%s.png' %(before_date, after_date)), bbox_inches='tight', pad_inches=0)


    # metadata creation as a json file
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
    images["dif_download_link"] = '/static/' + output_id + '_change.png'
    images["map_image_link"] = '/static/' + output_id + '_Water_change.png'
    images['bounds'] = GetExtent_latlon(guidance)
    export_dict["images"] = images
    
    

    metadata = OrderedDict()

    ds_raster = rasterio.open(watermask_after_filepath)
    ds_raster.crs.to_epsg()
    metadata['platform'] = 'S2A, S2B'
    metadata['product_type'] = 'L2A'
    metadata['sensor_mode'] = 'MSI'
    metadata['title'] = 'Water change detection (floods)'
    # metadata['location_name'] = ''
    metadata['CRS'] = 'EPSG:{} - WGS 84 / UTM zone {}N'.format(ds_raster.crs.to_epsg(),
                                                               ds_raster.crs.to_epsg() - 32600)
    metadata['pixel_size'] = [10, 10]



    metadata['Extent'] = GetExtent(guidance)
    element = datetime.datetime.strptime(before_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['start_date'] = int(time.mktime(tuple))
    element = datetime.datetime.strptime(after_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['end_date'] = int(time.mktime(tuple))
    metadata['land_to_water_area'] = round(((float(land_to_water_counter) * 100) / 1000000),2)
    metadata['water_to_land_area'] = round(((float(water_to_land_counter) * 100) / 1000000),2)
    metadata['uncertainty_lower'] = round(uncertainty_before,2)
    metadata['uncertainty_upper'] = round(uncertainty_after,2)
    # if clc_filepath!=-1:
    #     metadata['CLC_classes_land_to_water'] = land_to_water_classes
    #     if water_to_land_calc == 1:
    #         metadata['CLC_classes_water_to_land'] = water_to_land_classes
    # else:
    #     metadata['CLC_classes_land_to_water'] = {}
    #     metadata['CLC_classes_water_to_land'] = {}
    #the following key needs to be changed because we use classes from LC100_global layer.
    metadata['CLC_classes_land_to_water'] = land_to_water_classes
    metadata['CLC_classes_water_to_land'] = water_to_land_classes
    export_dict['metadata'] = metadata
    ds_raster = 0

    with open(destination_file+'/metadata.json', "w") as outfile:
        json.dump(export_dict, outfile, indent=4, sort_keys=False)

    print('Water change detection between dates %s and %s has finished successfully' % (before_date, after_date))

# save a numpy array as a GeoTIFF file
def save_geo_tiff(gdal_guidance_image, output_file, out_format, rasterXSize, rasterYSize, array_image, dtype,noDataValue=""):
    geoTrans_guidance = gdal_guidance_image.GetGeoTransform()  # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    wkt_guidance = gdal_guidance_image.GetProjection()  # Retrieve projection system of guidance image into well known text (WKT) format and save it in wkt_guidance

    # format = 'GTiff'
    driver = gdal.GetDriverByName(out_format)  # Generate an object of type GeoTIFF / KEA
    dst_ds = driver.Create(output_file, rasterXSize, rasterYSize, 1, dtype)  # Create a raster of type Geotiff / KEA with dimension Guided_Image.RasterXSize x Guided_Image.RasterYSize, with one band and datatype of GDT_Float32
    if dst_ds is None:  # Check if output_file can be saved
        print ("Could not save output file %s, path does not exist." % output_file)
        quit()

    dst_ds.SetGeoTransform(
        geoTrans_guidance)  # Set the Geo-information of the output file the same as the one of the guidance image
    dst_ds.SetProjection(wkt_guidance)
    # this line sets zero to "NaN"
    if noDataValue != "":
        dst_ds.GetRasterBand(1).SetNoDataValue(noDataValue)
        # print("Value to be replaced with NaN was given: " + str(noDataValue))
    dst_ds.GetRasterBand(1).WriteArray(array_image)  # Save the raster into the output file
    dst_ds.FlushCache()  # Write to disk.

# Find the percentage of all CLC classes an array containing the CLC values
def get_percentage_for_all_classes_of_CLC_array(clc_array):
    class_dict_percentage = {}
    class_ids_list = range(1,46)
    class_names = []
    class_names.append(' ')

    with open(os.path.join(os.getcwd(), 'CLC2018', 'CLC2018_CLC2018_V2018_20_QGIS.txt'), 'r') as reader:
    # with open('/home/sismanism/PycharmProjects/snapearth_source/server/snapearth_products/CLC_2018/u2018_clc2018_v2020_20u1_raster100m/Legend/CLC2018_CLC2018_V2018_20_QGIS.txt', 'r') as reader:
        line = reader.readline()
        while line != '':  # The EOF char is an empty string
            class_names.append(line[-2::-1].partition(',')[0][-1::-1])
            line = reader.readline()

    for each_class_id in class_ids_list:
        desired_class = (clc_array == each_class_id).sum()
        total_area = np.size(clc_array)
        print(total_area)
        percentage = (desired_class / float(total_area)) * 100.0
        class_dict_percentage[each_class_id] = (class_names[each_class_id],round(percentage,4))
    class_dict_percentage.pop(45)
    class_dict_percentage[48] = (class_names[45], round(percentage, 4))
    return class_dict_percentage

#function save as above but using global land cover
def get_percentage_for_all_classes_of_LC_gl_array(lc_array):
    class_dict_percentage = {}
    class_ids_list = []
    class_names = []
    # class_names.append(' ')

    with open(os.path.join(os.getcwd(),'LC100_GLOBAL', 'Global_land_cover_classes.txt'),'r') as reader:
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

# Band 02 (BLUE), Band 03 (Green) and Band 04 (RED)are used to calculate NRGB
def createNRGBraster(BLUE_filepath, GREEN_filepath, RED_filepath, save_result_directory):
    GREEN = gdal.Open(GREEN_filepath)
    srcband = GREEN.GetRasterBand(1)
    GREEN_original = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)

    BLUE = gdal.Open(BLUE_filepath)
    srcband = BLUE.GetRasterBand(1)
    BLUE_original = srcband.ReadAsArray(0, 0, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

    RED = gdal.Open(RED_filepath)
    srcband = RED.GetRasterBand(1)
    RED_original = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    NRGB = np.multiply(BLUE_original, GREEN_original)
    NRGB = np.multiply(NRGB, RED_original)
    NRGB = NRGB / 1000000
    save_geo_tiff(GREEN, save_result_directory + '/NRGB.tif', 'GTiff', GREEN.RasterXSize, GREEN.RasterYSize, NRGB, gdal.GDT_Float32)

# Band 04 (RED) and 08 (NIR) are used to calculate NDVI
def createNDVIraster(RED_filepath, NIR_filepath, save_result_directory):
    RED = gdal.Open(RED_filepath)
    srcband = RED.GetRasterBand(1)
    RED_original = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    NIR = gdal.Open(NIR_filepath)
    srcband = NIR.GetRasterBand(1)
    NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDVI = np.divide((NIR_original - RED_original), ((NIR_original + RED_original)))
    save_geo_tiff(RED, save_result_directory + '/NDVI.tif', 'GTiff', RED.RasterXSize, RED.RasterYSize, NDVI, gdal.GDT_Float32)

    print('NDVI:')
    print(np.amin(NDVI))
    print(np.amax(NDVI))

# Band 8A (Narrow NIR) and 11 (SWIR) are used to calculate NDMI (Normalized Difference Moisture Index)
def createNDMIraster(NIR_filepath, SWIR_filepath, save_result_directory):
    NIR = gdal.Open(NIR_filepath)
    srcband = NIR.GetRasterBand(1)
    NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    SWIR = gdal.Open(SWIR_filepath)
    srcband = SWIR.GetRasterBand(1)
    SWIR_original = srcband.ReadAsArray(0, 0, SWIR.RasterXSize, SWIR.RasterYSize).astype(np.float)

    NDMI = np.divide((NIR_original - SWIR_original), ((NIR_original + SWIR_original)))
    save_geo_tiff(NIR, save_result_directory + '/NDMI.tif', 'GTiff', NIR.RasterXSize, NIR.RasterYSize, NDMI,
                  gdal.GDT_Float32)

    print('NDMI:')
    print(np.amin(NDMI))
    print(np.amax(NDMI))

# Band 03 (Green) and 08 (NIR) are used to calculate NDWI (Normalized Difference Water Index)
def createNDWIraster_green(GREEN_filepath, NIR_filepath, save_result_directory):


    GREEN = gdal.Open(GREEN_filepath)
    srcband = GREEN.GetRasterBand(1)
    GREEN_original = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)

    NIR = gdal.Open(NIR_filepath)
    srcband = NIR.GetRasterBand(1)
    NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDWI = np.divide((GREEN_original - NIR_original), ((GREEN_original + NIR_original)))
    save_geo_tiff(NIR, save_result_directory + '/NDWI.tif', 'GTiff', NIR.RasterXSize, NIR.RasterYSize, NDWI,
                  gdal.GDT_Float32)

    print('NDWI:')
    print(np.amin(NDWI))
    print(np.amax(NDWI))


def apply_mask_to_watermask(mask_filepath, watermask_filepath, watermask_filepath_new):
    SOURCE2 = gdal.Open(watermask_filepath)
    srcband2 = SOURCE2.GetRasterBand(1)
    watermask = srcband2.ReadAsArray(0, 0, SOURCE2.RasterXSize, SOURCE2.RasterYSize)

    SOURCE1 = gdal.Open(mask_filepath)
    srcband1 = SOURCE1.GetRasterBand(1)
    mask = srcband1.ReadAsArray(0, 0, SOURCE1.RasterXSize, SOURCE1.RasterYSize, SOURCE2.RasterXSize,
                                SOURCE2.RasterYSize)
    result = np.multiply(watermask, mask)

    save_geo_tiff(SOURCE2, watermask_filepath_new, 'GTiff', SOURCE2.RasterXSize, SOURCE2.RasterYSize, result,
                  gdal.GDT_Byte)

def apply_mask_to_hydromap(mask_filepath, hydromap_filepath, hydromap_filepath_new):
    SOURCE2 = gdal.Open(hydromap_filepath)
    srcband2 = SOURCE2.GetRasterBand(1)
    watermask = srcband2.ReadAsArray(0, 0, SOURCE2.RasterXSize, SOURCE2.RasterYSize)

    SOURCE1 = gdal.Open(mask_filepath)
    srcband1 = SOURCE1.GetRasterBand(1)
    mask = srcband1.ReadAsArray(0, 0, SOURCE1.RasterXSize, SOURCE1.RasterYSize, SOURCE2.RasterXSize,
                                SOURCE2.RasterYSize)
    result = np.multiply(watermask, mask)

    save_geo_tiff(SOURCE2, hydromap_filepath_new, 'GTiff', SOURCE2.RasterXSize, SOURCE2.RasterYSize, result,
                  gdal.GDT_UInt16)

# get extent of the bounding box of a GeoTIFF raster file
def GetExtent(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel

    return (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)
    
def GetExtent_latlon_old(ds, lat, lon):
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    #print(ds.GetGeoTransform())
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel
    zone = utm.latlon_to_zone_number(lat, lon)
    ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone, 'N')
    ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone, 'N')
    return (xmin_conv, ymax_conv), (xmax_conv, ymax_conv), (xmax_conv, ymin_conv), (xmin_conv, ymin_conv)

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
    
    if zone_letter == 'S':
        ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone_number, northern=False)
        ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone_number,  northern=False)
    else:
        ymax_conv, xmax_conv, = utm.to_latlon(xmax, ymax, zone_number, zone_letter)
        ymin_conv, xmin_conv = utm.to_latlon(xmin, ymin, zone_number, zone_letter)
    return (ymax_conv, xmin_conv),  (ymin_conv, xmax_conv)

#land_water_change_detection('/home/lefkats/snapearth_api/snapearth_api/output/new_output/2022-07-11', '/home/lefkats/snapearth_api/snapearth_api/output/new_output/2022-07-26', '/home/lefkats/snapearth_api/snapearth_api/output/new_output/2022-07-11/TCI.tif', '/home/lefkats/snapearth_api/snapearth_api/output/new_output/water_change_2022-07-11_2022-07-26_new', 'test', 123,   24, 45)    
