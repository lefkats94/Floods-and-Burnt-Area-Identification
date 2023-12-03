from osgeo import gdal
import numpy as np
import time
import os
import pymeanshift as pms
from PIL import Image
from scipy.signal import lfilter
from algorithm_burned_area import conv_peakdet
import rasterio
from collections import OrderedDict
import json
import algorithm_burned_area.my_functions as myfun
from algorithm_burned_area.find_optimum_threshold import find_optimum_threshold
import datetime
import utm

def burned_area_change_detection(before_folder, after_folder, rgb_filepath, destination_filepath, output_id, event_id):


    # initialization
    before_date = os.path.split(before_folder)[1]
    after_date = os.path.split(after_folder)[1]

    f = open(os.path.join(destination_filepath, 'comparison_report.txt'), 'w')

    print('Burned area change detection between %s and %s' % (before_date, after_date))
    f.write('Burned area change detection between %s and %s \n' % (before_date, after_date))

    t0 = time.time()

    # check if a CLC.tif file exists in the before/after folders
    if os.path.exists(os.path.join(before_folder, 'CLC.tif')):
        clc_filepath = os.path.join(before_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'CLC.tif')):
        clc_filepath = os.path.join(after_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        print('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.')
        f.write('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.\n')
        clc_filepath = -1

    # initialize global land cover - check about LC_global in the tif file in the before and after folder
    if os.path.exists(os.path.join(before_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(before_folder, 'LC100_global.tif')
        # lc_gl_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(after_folder, 'LC100_global.tif')
        # lc_gl_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        print('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder')
        f.write('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder\n')
        lc_gl_filepath = -1

    # load the GeoTIFF bands of the after date into numpy arrays

    ###10m bands###
    BLUE = gdal.Open(os.path.join(after_folder, 'B02.tif'))
    srcband = BLUE.GetRasterBand(1)
    blue_array_after = srcband.ReadAsArray(0, 0, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

    ###10m bands###

    RED = gdal.Open(os.path.join(after_folder, 'B04.tif'))
    srcband = RED.GetRasterBand(1)
    red_array_after = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    GREEN = gdal.Open(os.path.join(after_folder, 'B03.tif'))
    srcband = GREEN.GetRasterBand(1)
    green_array_after = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)
    #
    # NIR = gdal.Open(os.path.join(after_folder, 'B08.tif'))
    # srcband = NIR.GetRasterBand(1)
    # nir_array_after = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)
    #
    # SWIR2 = gdal.Open(os.path.join(after_folder, 'B12.tif'))
    # srcband = SWIR2.GetRasterBand(1)
    # swir2_array_after = srcband.ReadAsArray(0, 0, SWIR2.RasterXSize, SWIR2.RasterYSize, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    # testing about deleting variables and impact on resources. May have no effect
    del RED
    del GREEN
    # del NIR


    # calculate NBR and dNBR rasters and save them in the disk
    createNBRraster(os.path.join(before_folder, 'B08.tif'), os.path.join(before_folder, 'B12.tif'), before_folder)
    createNBRraster(os.path.join(after_folder, 'B08.tif'), os.path.join(after_folder, 'B12.tif'), after_folder )
    createDNBRrraster(os.path.join(before_folder, 'NBR.tif'), os.path.join(after_folder, 'NBR.tif'), destination_filepath)
    createNDMIraster(os.path.join(after_folder, 'B8A.tif'), os.path.join(after_folder, 'B11.tif'), after_folder)
    createNDWIraster(os.path.join(after_folder, 'B03.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
    
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

    # load SCL files if available and calculate uncertainty
    if os.path.exists(os.path.join(before_folder, 'SCL.tif')):
        SCL_before = gdal.Open(os.path.join(before_folder, 'SCL.tif'))
        srcband = SCL_before.GetRasterBand(1)
        SCL_before_array = srcband.ReadAsArray(0,0, SCL_before.RasterXSize, SCL_before.RasterYSize)
        uncertainty_before = np.zeros((SCL_before.RasterXSize, SCL_before.RasterYSize))
        uncertainty_before = np.where(SCL_before_array == 2, True, False)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 3, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 8, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 9, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 1, True, False), uncertainty_before)
    else:
        print("SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated")
        f.write('SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated\n')
        uncertainty_before = -1

    if os.path.exists(os.path.join(after_folder, 'SCL.tif')):
        SCL_after = gdal.Open(os.path.join(after_folder, 'SCL.tif'))
        srcband = SCL_after.GetRasterBand(1)
        SCL_after_array = srcband.ReadAsArray(0,0, SCL_after.RasterXSize, SCL_after.RasterYSize)
        uncertainty_after = np.zeros((SCL_after.RasterXSize, SCL_after.RasterYSize))
        uncertainty_after = np.where(SCL_after_array == 2, True, False)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 3, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 8, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 9, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 1, True, False), uncertainty_after)
    else:
        print("SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated")
        f.write('SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated\n')
        uncertainty_after = -1

     # if SCL layers are present, then calculate uncertainty
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
        f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,
                                                                                                 uncertainty_after))
    print(uncertainty_before)
    

    # initialize rasters for processing

    # difference Normalized Burned Ratio
    dNBR_SOURCE = gdal.Open(os.path.join(destination_filepath, 'dNBR.tif'))
    srcband = dNBR_SOURCE.GetRasterBand(1)
    burned_area_array = srcband.ReadAsArray(0, 0, dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize)
    burned_area_array = np.nan_to_num(burned_area_array)

    burnedAreaOutput = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, 4), 'uint8')
    burnedAreaOutputTIF = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize), 'uint8')

    # if an TCI image is present then initialize arrays for respective outputs
    if rgb_filepath == -1:
        pass
    else:
        RGB_SOURCE1 = gdal.Open(rgb_filepath)
        red_srcband = RGB_SOURCE1.GetRasterBand(1)
        green_srcband = RGB_SOURCE1.GetRasterBand(2)
        blue_srcband = RGB_SOURCE1.GetRasterBand(3)
        rgbOutput = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, 3), 'uint8')
        red_arr = red_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        green_arr = green_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        blue_arr = blue_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        rgbOutput[:, :, 0] = np.copy(red_arr)
        rgbOutput[:, :, 1] = np.copy(green_arr)
        rgbOutput[:, :, 2] = np.copy(blue_arr)

    # if a CLC layer is present then initialize arrays for respective outputs
    if clc_filepath != -1:
        # clc cover
        CLC_SOURCE = gdal.Open(clc_filepath)
        clcband = CLC_SOURCE.GetRasterBand(1)
        CLC_array_resized = clcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize)
        # geoTrans_guidance_clc = CLC_SOURCE.GetGeoTransform()  # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
        # wkt_guidance_clc = CLC_SOURCE.GetProjection()
        # epsg = int(gdal.Info(CLC_SOURCE, format='json')['coordinateSystem']['wkt'].rsplit('"EPSG","', 1)[-1].split('"')[0])
     #use the global land cover instead
    elif lc_gl_filepath != -1:
        # Extract Land use - Land cover from the provided LC100_global.tiff file which has been calculated for each band
        LC100_global_SOURCE = gdal.Open(lc_gl_filepath)
        srcband = LC100_global_SOURCE.GetRasterBand(1)
        LC100_gl_arr_resized = srcband.ReadAsArray(0, 0, LC100_global_SOURCE.RasterXSize,
                                                   LC100_global_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize,
                                                   dNBR_SOURCE.RasterYSize)
    else:
        print("No CLC or LC global file provided.")
    #  --------------------  indices and masks  -----------------------------

    # mask of clouds, smoke and very bright formations
    NRGB_mask_before = create_NRGB_index_mask(before_folder)
    NRGB_mask_after = create_NRGB_index_mask(after_folder)
    NRGB_mask = np.logical_xor(NRGB_mask_before, NRGB_mask_after)
    NRGB_mask = np.invert(NRGB_mask)

    # mask about everything that appears as water
    # can be replaced with watermask module
    sea_mask = create_NDWI_mask(before_folder)

    non_vegetation_mask_final = create_vegetation_mask(before_folder, after_folder)

    NBR_after_filepath = (os.path.join(after_folder, 'NBR.tif'))
    NBR_after = gdal.Open(NBR_after_filepath)
    srcband = NBR_after.GetRasterBand(1)
    NBR_after_original = srcband.ReadAsArray(0, 0, NBR_after.RasterXSize, NBR_after.RasterYSize).astype(np.float)

    NBR_after_original = np.multiply(sea_mask, NBR_after_original)
    NBR_after_original = np.multiply(np.invert(non_vegetation_mask_final), NBR_after_original)
    #NBR_after_original = np.multiply(NRGB_mask, NBR_after_original)
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NBR_after_original.tif'), 'GTiff',
                  dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NBR_after_original, gdal.GDT_Byte)
    #  --------------------  NBR after fire initial threshold -----------------------------


    # initial NBR threshold and mask
    NBR_after_mask, NBR_threshold = histogram_and_mask_for_NBR(NBR_after_original, -0.20)
    print(NBR_threshold)
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NBR_after_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NBR_after_mask, gdal.GDT_Byte)


    print('Initial NBR threshold has been calculated successfully')


    #  -------------------- segmentation and NBR optimal threshold  -----------------------------

    print('Starting segmentation of the RBG image after the event')

    RED_normalized = myfun.range_0_255(red_array_after);
    BLUE_normalized = myfun.range_0_255(blue_array_after);
    GREEN_normalized = myfun.range_0_255(green_array_after);

    rgbArray = np.zeros((BLUE.RasterYSize, BLUE.RasterXSize, 3), 'uint8')
    rgbArray[..., 0] = RED_normalized * 255
    rgbArray[..., 1] = GREEN_normalized * 255
    rgbArray[..., 2] = BLUE_normalized * 255

    # segmentation of the RBG images into non-overlapping segments using pymeanshift
    regions_number = -1
    print("LABELS image is being created using PyMeanShift based on RGB")
    (segmented_image, labels_image, number_regions) = pms.segment(rgbArray, spatial_radius=3, range_radius=3, min_density=500)

    LABELS_original = labels_image
    regions_number = number_regions
    myfun.saveGeoTiff(BLUE, os.path.join(destination_filepath, 'labels.tif'),BLUE.RasterXSize, BLUE.RasterYSize, labels_image, gdal.GDT_UInt32)

    # find the optimum threshold
    optimum_threshold = find_optimum_threshold((NBR_after_original+1)*120,np.invert(NBR_after_mask), LABELS_original,None)
    print(optimum_threshold)
    optimum_threshold = optimum_threshold/120-1
    

    #  -------------------- segmentation and NBR optimal threshold  -----------------------------

    # testing and creating tif files for validation with QGIS
    # change_detection_functions.save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NRGB_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NRGB_mask, gdal.GDT_Byte)
    # save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'sea_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, sea_mask, gdal.GDT_Byte)
    # change_detection_functions.save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'dNBR_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, burned_area_array, gdal.GDT_Float32)


    # apply masks
    print('Optimal threshold has been calculated successfully. Now proceeding with output generation')
    NBR_optimum_threshold_mask = np.where(NBR_after_original < optimum_threshold, True, False)
    burned_area_array = np.multiply(burned_area_array, sea_mask)
    burned_area_array = np.multiply(burned_area_array, np.invert(non_vegetation_mask_final))
    burned_area_array = np.multiply(burned_area_array, NRGB_mask)


     #  --------------------------------------------------------  calculations for burned area outputs  ---------------------------------------


    f.write('\n')

    # estimate the different grade of damage severity based on dNBR
    burned_area_array_mask_clip = np.multiply(burned_area_array, NBR_optimum_threshold_mask)
    # burned_area_array_mask_clip = burned_area_array
    high_severity = np.where(burned_area_array_mask_clip > 0.66, True, False)
    medium_high_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.66, burned_area_array_mask_clip > 0.44), True, False)
    medium_low_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.44, burned_area_array_mask_clip > 0.27), True, False)
    low_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.27, burned_area_array_mask_clip > 0.1), True, False)
    unburned = np.where(burned_area_array_mask_clip <= 0.1, True, False)

    f.write('The size of the high severity area is {:.2f} km^2\n'.format((float(high_severity.sum()) * 100) / 1000000))
    f.write('The size of the medium-high severity area is {:.2f} km^2\n'.format((float(medium_high_severity.sum()) * 100) / 1000000))
    f.write('The size of the medium-low severity area is {:.2f} km^2\n'.format((float(medium_low_severity.sum()) * 100) / 1000000))
    f.write('The size of the low severity is {:.2f} km^2\n'.format((float(low_severity.sum()) * 100) / 1000000))
    f.write('The total area affected is {:.2f} km^2\n'.format((float(high_severity.sum() + medium_high_severity.sum() + medium_low_severity.sum() + low_severity.sum()) * 100) / 1000000))

    # create output files
    burnedAreaOutput[unburned, :] = unburned_fill_RGBA
    burnedAreaOutput[low_severity, :] = low_severity_fill_RGBA
    burnedAreaOutput[medium_low_severity, :] = medium_low_severity_fill_RGBA
    burnedAreaOutput[medium_high_severity, :] = medium_high_severity_fill_RGBA
    burnedAreaOutput[high_severity, :] = high_fill_RGBA

    burnedAreaOutputTIF[unburned] = 0
    burnedAreaOutputTIF[low_severity] = 1
    burnedAreaOutputTIF[medium_low_severity] = 2
    burnedAreaOutputTIF[medium_high_severity] = 3
    burnedAreaOutputTIF[high_severity] = 4

    temp_image = Image.fromarray(burnedAreaOutput)
    temp_image.save(os.path.join(destination_filepath, 'burned_area.png'))
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'burned_area.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, burnedAreaOutputTIF, gdal.GDT_Byte)
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
        temp_image.save(os.path.join(destination_filepath, 'before_the_event.png'))


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
        temp_image.save(os.path.join(destination_filepath, 'after_the_event.png'))

    # if RGB iage is present the create an RGB overlay with the disaster
    if rgb_filepath != -1:
        rgbOutput[low_severity, :] = low_severity_fill
        rgbOutput[medium_low_severity, :] = medium_low_severity_fill
        rgbOutput[medium_high_severity, :] = medium_high_severity_fill
        rgbOutput[high_severity, :] = high_fill
        temp_image = Image.fromarray(rgbOutput)
        temp_image.save(os.path.join(destination_filepath, 'burned_area_change.png'))


   
    
    # if CLC thematic layer is available, then calculate the land cover affected
    if clc_filepath != -1:
        temp_array_1 = np.multiply(CLC_array_resized, low_severity)
        temp_array_2 = np.multiply(CLC_array_resized, medium_low_severity)
        temp_array_3 = np.multiply(CLC_array_resized, medium_high_severity)
        temp_array_4 = np.multiply(CLC_array_resized, high_severity)
        clc_low = temp_array_1[np.nonzero(temp_array_1)]
        clc_medium_low = temp_array_2[np.nonzero(temp_array_2)]
        clc_medium_high = temp_array_3[np.nonzero(temp_array_3)]
        clc_high = temp_array_4[np.nonzero(temp_array_4)]

        clc_classes = get_percentage_for_all_classes_of_CLC_array(np.concatenate((clc_low, clc_medium_low, clc_medium_high, clc_high)))

        fire_clases = {}
        f.write('The CLC classes with their percentages affected from the fires are:\n')
        for i in clc_classes.keys():
            if clc_classes[i][1] > 2:
                f.write(clc_classes[i][0] + ': ' + str(clc_classes[i][1]) + '%\n')
                fire_clases.update(dict({clc_classes[i]}))
    
    elif lc_gl_filepath != -1:
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

        fire_clases = {}
        f.write('The CLC classes with their percentages affected from the fires are:\n')
        for i in glc_classes.keys():
            if glc_classes[i][1] > 2:
                f.write(glc_classes[i][0] + ': ' + str(glc_classes[i][1]) + '%\n')
                fire_clases.update(dict({glc_classes[i]}))
    else:
        fire_clases = {}            



    # ------------------------------- end calculations for burned area outputs -------------------------------------------------

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
    images["map_image_link"] = '/static/' + output_id + '_burned_area.png'
    images["bounds"] = GetExtent_latlon(dNBR_SOURCE)
    export_dict["images"] = images
    
    metadata = OrderedDict()
    ds_raster = rasterio.open(os.path.join(destination_filepath, 'dNBR.tif'))
    ds_raster.crs.to_epsg()
    metadata['platform'] = 'S2A, S2B'
    metadata['product_type'] = 'L2A'
    metadata['sensor_mode'] = 'MSI'
    metadata['title'] = 'Burned area change detection'
    # metadata['location_name'] = ''
    metadata['CRS'] = 'EPSG:{} - WGS 84 / UTM zone {}N'.format(ds_raster.crs.to_epsg(),
                                                                  ds_raster.crs.to_epsg() - 32600)
    metadata['pixel_size'] = [10, 10]
    metadata['Extent'] = GetExtent(dNBR_SOURCE)
    element = datetime.datetime.strptime(before_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['start_date'] = int(time.mktime(tuple))
    element = datetime.datetime.strptime(after_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['end_date'] = int(time.mktime(tuple))
    metadata['total_affected_area'] = round(((float(high_severity.sum() + medium_high_severity.sum() + medium_low_severity.sum() + low_severity.sum()) * 100) / 1000000), 2)
    metadata['high_severity_area'] = round(((float(high_severity.sum()) * 100) / 1000000), 2)
    metadata['medium_high_severity_area'] = round(((float(medium_high_severity.sum()) * 100) / 1000000), 2)
    metadata['medium_low_severity_area'] = round(((float(medium_low_severity.sum()) * 100) / 1000000), 2)
    metadata['low_severity_area'] = round(((float(low_severity.sum()) * 100) / 1000000), 2)
    metadata['uncertainty_lower'] = round(uncertainty_before, 2)
    metadata['uncertainty_upper'] = round(uncertainty_after, 2)
    #if clc_filepath != -1:
    #    metadata['CLC_classes_affected_percentage_per_class'] = fire_clases
    #else:
    #    metadata['CLC_classes_affected_percentage_per_class'] = {}                
    #the following key needs to be changed because we use classes from LC100_global layer.
    metadata['CLC_classes_affected_percentage_per_class'] = fire_clases
    ds_raster = 0
    export_dict['metadata'] = metadata

    with open(destination_filepath + '/metadata.json', "w") as outfile:
        json.dump(export_dict, outfile, indent=4, sort_keys=False)

    print('Burned area change detection between %s and %s has finished successfully' % (before_date, after_date))
    t1 = time.time()
    print('Time required: %.2f seconds' % (t1-t0))


def burned_area_change_detection_min(before_folder, after_folder, rgb_filepath, destination_filepath):
    """
    This function is being used, instead of the previous "burned_area_change_detection()", when detection of the burnt area is expanded and the burned area change detection will be executed for the bbox.
    """
    # initialization
    before_date = os.path.split(before_folder)[1]
    after_date = os.path.split(after_folder)[1]

    f = open(os.path.join(destination_filepath, 'comparison_report.txt'), 'w')

    print('Burned area change detection between %s and %s' % (before_date, after_date))
    f.write('Burned area change detection between %s and %s \n' % (before_date, after_date))

    t0 = time.time()

    # check if a CLC.tif file exists in the before/after folders
    if os.path.exists(os.path.join(before_folder, 'CLC.tif')):
        clc_filepath = os.path.join(before_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'CLC.tif')):
        clc_filepath = os.path.join(after_folder, 'CLC.tif')
        clc_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        #print('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.')
        f.write('No CLC geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder. Global land cover will be used instead.\n')
        clc_filepath = -1

    # initialize global land cover - check about LC_global in the tif file in the before and after folder
    if os.path.exists(os.path.join(before_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(before_folder, 'LC100_global.tif')
        # lc_gl_filepath_resized = os.path.join(before_folder, 'CLC_resized.tif')
    elif os.path.exists(os.path.join(after_folder, 'LC100_global.tif')):
        lc_gl_filepath = os.path.join(after_folder, 'LC100_global.tif')
        # lc_gl_filepath_resized = os.path.join(after_folder, 'CLC_resized.tif')
    else:
        #print('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder')
        f.write('No global geoTIFF file found to visualize the result. Please make sure there is a CLC.tiff in either the pre or after date folder\n')
        lc_gl_filepath = -1

    # load the GeoTIFF bands of the after date into numpy arrays

    ###10m bands###
    BLUE = gdal.Open(os.path.join(after_folder, 'B02.tif'))
    srcband = BLUE.GetRasterBand(1)
    blue_array_after = srcband.ReadAsArray(0, 0, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

    ###10m bands###

    RED = gdal.Open(os.path.join(after_folder, 'B04.tif'))
    srcband = RED.GetRasterBand(1)
    red_array_after = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    GREEN = gdal.Open(os.path.join(after_folder, 'B03.tif'))
    srcband = GREEN.GetRasterBand(1)
    green_array_after = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)
    #
    # NIR = gdal.Open(os.path.join(after_folder, 'B08.tif'))
    # srcband = NIR.GetRasterBand(1)
    # nir_array_after = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)
    #
    # SWIR2 = gdal.Open(os.path.join(after_folder, 'B12.tif'))
    # srcband = SWIR2.GetRasterBand(1)
    # swir2_array_after = srcband.ReadAsArray(0, 0, SWIR2.RasterXSize, SWIR2.RasterYSize, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    # testing about deleting variables and impact on resources. May have no effect
    del RED
    del GREEN
    # del NIR


    # calculate NBR and dNBR rasters and save them in the disk
    createNBRraster(os.path.join(before_folder, 'B08.tif'), os.path.join(before_folder, 'B12.tif'), before_folder)
    createNBRraster(os.path.join(after_folder, 'B08.tif'), os.path.join(after_folder, 'B12.tif'), after_folder )
    createDNBRrraster(os.path.join(before_folder, 'NBR.tif'), os.path.join(after_folder, 'NBR.tif'), destination_filepath)
    createNDMIraster(os.path.join(after_folder, 'B8A.tif'), os.path.join(after_folder, 'B11.tif'), after_folder)
    createNDWIraster(os.path.join(after_folder, 'B03.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
    
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

    # load SCL files if available and calculate uncertainty
    if os.path.exists(os.path.join(before_folder, 'SCL.tif')):
        SCL_before = gdal.Open(os.path.join(before_folder, 'SCL.tif'))
        srcband = SCL_before.GetRasterBand(1)
        SCL_before_array = srcband.ReadAsArray(0,0, SCL_before.RasterXSize, SCL_before.RasterYSize)
        uncertainty_before = np.zeros((SCL_before.RasterXSize, SCL_before.RasterYSize))
        uncertainty_before = np.where(SCL_before_array == 2, True, False)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 3, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 8, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 9, True, False), uncertainty_before)
        uncertainty_before = np.logical_or(np.where(SCL_before_array == 1, True, False), uncertainty_before)
    else:
        print("SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated")
        f.write('SCL.tif file for the previous date cannot be access. Uncertainty for the previous image will not be calculated\n')
        uncertainty_before = -1

    if os.path.exists(os.path.join(after_folder, 'SCL.tif')):
        SCL_after = gdal.Open(os.path.join(after_folder, 'SCL.tif'))
        srcband = SCL_after.GetRasterBand(1)
        SCL_after_array = srcband.ReadAsArray(0,0, SCL_after.RasterXSize, SCL_after.RasterYSize)
        uncertainty_after = np.zeros((SCL_after.RasterXSize, SCL_after.RasterYSize))
        uncertainty_after = np.where(SCL_after_array == 2, True, False)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 3, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 8, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 9, True, False), uncertainty_after)
        uncertainty_after = np.logical_or(np.where(SCL_after_array == 1, True, False), uncertainty_after)
    else:
        print("SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated")
        f.write('SCL.tif file for the following date cannot be access. Uncertainty for the after image will not be calculated\n')
        uncertainty_after = -1

     # if SCL layers are present, then calculate uncertainty
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
        f.write('\nThe uncertainty (error) of the calculations is: [-{:2f}%,+{:2f}%]\n\n'.format(uncertainty_before,
                                                                                                 uncertainty_after))
    print(uncertainty_before)
    

    # initialize rasters for processing

    # difference Normalized Burned Ratio
    dNBR_SOURCE = gdal.Open(os.path.join(destination_filepath, 'dNBR.tif'))
    srcband = dNBR_SOURCE.GetRasterBand(1)
    burned_area_array = srcband.ReadAsArray(0, 0, dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize)
    burned_area_array = np.nan_to_num(burned_area_array)

    burnedAreaOutput = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, 4), 'uint8')
    burnedAreaOutputTIF = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize), 'uint8')

    # if an TCI image is present then initialize arrays for respective outputs
    if rgb_filepath == -1:
        pass
    else:
        RGB_SOURCE1 = gdal.Open(rgb_filepath)
        red_srcband = RGB_SOURCE1.GetRasterBand(1)
        green_srcband = RGB_SOURCE1.GetRasterBand(2)
        blue_srcband = RGB_SOURCE1.GetRasterBand(3)
        rgbOutput = np.zeros((dNBR_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, 3), 'uint8')
        red_arr = red_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        green_arr = green_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        blue_arr = blue_srcband.ReadAsArray(0, 0, RGB_SOURCE1.RasterXSize, RGB_SOURCE1.RasterYSize)
        rgbOutput[:, :, 0] = np.copy(red_arr)
        rgbOutput[:, :, 1] = np.copy(green_arr)
        rgbOutput[:, :, 2] = np.copy(blue_arr)

    # if a CLC layer is present then initialize arrays for respective outputs
    if clc_filepath != -1:
        # clc cover
        CLC_SOURCE = gdal.Open(clc_filepath)
        clcband = CLC_SOURCE.GetRasterBand(1)
        CLC_array_resized = clcband.ReadAsArray(0, 0, CLC_SOURCE.RasterXSize, CLC_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize)
        # geoTrans_guidance_clc = CLC_SOURCE.GetGeoTransform()  # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
        # wkt_guidance_clc = CLC_SOURCE.GetProjection()
        # epsg = int(gdal.Info(CLC_SOURCE, format='json')['coordinateSystem']['wkt'].rsplit('"EPSG","', 1)[-1].split('"')[0])
     #use the global land cover instead
    elif lc_gl_filepath != -1:
        # Extract Land use - Land cover from the provided LC100_global.tiff file which has been calculated for each band
        LC100_global_SOURCE = gdal.Open(lc_gl_filepath)
        srcband = LC100_global_SOURCE.GetRasterBand(1)
        LC100_gl_arr_resized = srcband.ReadAsArray(0, 0, LC100_global_SOURCE.RasterXSize,
                                                   LC100_global_SOURCE.RasterYSize, dNBR_SOURCE.RasterXSize,
                                                   dNBR_SOURCE.RasterYSize)
    else:
        print("No CLC or LC global file provided.")
    #  --------------------  indices and masks  -----------------------------

    # mask of clouds, smoke and very bright formations
    NRGB_mask_before = create_NRGB_index_mask(before_folder)
    NRGB_mask_after = create_NRGB_index_mask(after_folder)
    NRGB_mask = np.logical_xor(NRGB_mask_before, NRGB_mask_after)
    NRGB_mask = np.invert(NRGB_mask)

    # mask about everything that appears as water
    # can be replaced with watermask module
    sea_mask = create_NDWI_mask(before_folder)

    non_vegetation_mask_final = create_vegetation_mask(before_folder, after_folder)

    NBR_after_filepath = (os.path.join(after_folder, 'NBR.tif'))
    NBR_after = gdal.Open(NBR_after_filepath)
    srcband = NBR_after.GetRasterBand(1)
    NBR_after_original = srcband.ReadAsArray(0, 0, NBR_after.RasterXSize, NBR_after.RasterYSize).astype(np.float)

    NBR_after_original = np.multiply(sea_mask, NBR_after_original)
    NBR_after_original = np.multiply(np.invert(non_vegetation_mask_final), NBR_after_original)
    #NBR_after_original = np.multiply(NRGB_mask, NBR_after_original)
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NBR_after_original.tif'), 'GTiff',
                  dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NBR_after_original, gdal.GDT_Byte)
    #  --------------------  NBR after fire initial threshold -----------------------------


    # initial NBR threshold and mask
    NBR_after_mask, NBR_threshold = histogram_and_mask_for_NBR(NBR_after_original, -0.20)
    print(NBR_threshold)
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NBR_after_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NBR_after_mask, gdal.GDT_Byte)


    print('Initial NBR threshold has been calculated successfully')


    #  -------------------- segmentation and NBR optimal threshold  -----------------------------

    print('Starting segmentation of the RBG image after the event')

    RED_normalized = myfun.range_0_255(red_array_after);
    BLUE_normalized = myfun.range_0_255(blue_array_after);
    GREEN_normalized = myfun.range_0_255(green_array_after);

    rgbArray = np.zeros((BLUE.RasterYSize, BLUE.RasterXSize, 3), 'uint8')
    rgbArray[..., 0] = RED_normalized * 255
    rgbArray[..., 1] = GREEN_normalized * 255
    rgbArray[..., 2] = BLUE_normalized * 255

    # segmentation of the RBG images into non-overlapping segments using pymeanshift
    regions_number = -1
    print("LABELS image is being created using PyMeanShift based on RGB")
    (segmented_image, labels_image, number_regions) = pms.segment(rgbArray, spatial_radius=3, range_radius=3, min_density=500)

    LABELS_original = labels_image
    regions_number = number_regions
    myfun.saveGeoTiff(BLUE, os.path.join(destination_filepath, 'labels.tif'),BLUE.RasterXSize, BLUE.RasterYSize, labels_image, gdal.GDT_UInt32)

    # find the optimum threshold
    optimum_threshold = find_optimum_threshold((NBR_after_original+1)*120,np.invert(NBR_after_mask), LABELS_original,None)
    print(optimum_threshold)
    optimum_threshold = optimum_threshold/120-1
    

    #  -------------------- segmentation and NBR optimal threshold  -----------------------------

    # testing and creating tif files for validation with QGIS
    # change_detection_functions.save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'NRGB_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, NRGB_mask, gdal.GDT_Byte)
    # save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'sea_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, sea_mask, gdal.GDT_Byte)
    # change_detection_functions.save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'dNBR_mask.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, burned_area_array, gdal.GDT_Float32)


    # apply masks
    print('Optimal threshold has been calculated successfully. Now proceeding with output generation')
    NBR_optimum_threshold_mask = np.where(NBR_after_original < optimum_threshold, True, False)
    burned_area_array = np.multiply(burned_area_array, sea_mask)
    burned_area_array = np.multiply(burned_area_array, np.invert(non_vegetation_mask_final))
    burned_area_array = np.multiply(burned_area_array, NRGB_mask)


     #  --------------------------------------------------------  calculations for burned area outputs  ---------------------------------------


    f.write('\n')

    # estimate the different grade of damage severity based on dNBR
    burned_area_array_mask_clip = np.multiply(burned_area_array, NBR_optimum_threshold_mask)
    # burned_area_array_mask_clip = burned_area_array
    high_severity = np.where(burned_area_array_mask_clip > 0.66, True, False)
    medium_high_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.66, burned_area_array_mask_clip > 0.44), True, False)
    medium_low_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.44, burned_area_array_mask_clip > 0.27), True, False)
    low_severity = np.where(np.logical_and(burned_area_array_mask_clip <= 0.27, burned_area_array_mask_clip > 0.1), True, False)
    unburned = np.where(burned_area_array_mask_clip <= 0.1, True, False)

    f.write('The size of the high severity area is {:.2f} km^2\n'.format((float(high_severity.sum()) * 100) / 1000000))
    f.write('The size of the medium-high severity area is {:.2f} km^2\n'.format((float(medium_high_severity.sum()) * 100) / 1000000))
    f.write('The size of the medium-low severity area is {:.2f} km^2\n'.format((float(medium_low_severity.sum()) * 100) / 1000000))
    f.write('The size of the low severity is {:.2f} km^2\n'.format((float(low_severity.sum()) * 100) / 1000000))
    f.write('The total area affected is {:.2f} km^2\n'.format((float(high_severity.sum() + medium_high_severity.sum() + medium_low_severity.sum() + low_severity.sum()) * 100) / 1000000))

    # create output files
    burnedAreaOutput[unburned, :] = unburned_fill_RGBA
    burnedAreaOutput[low_severity, :] = low_severity_fill_RGBA
    burnedAreaOutput[medium_low_severity, :] = medium_low_severity_fill_RGBA
    burnedAreaOutput[medium_high_severity, :] = medium_high_severity_fill_RGBA
    burnedAreaOutput[high_severity, :] = high_fill_RGBA

    burnedAreaOutputTIF[unburned] = 0
    burnedAreaOutputTIF[low_severity] = 1
    burnedAreaOutputTIF[medium_low_severity] = 2
    burnedAreaOutputTIF[medium_high_severity] = 3
    burnedAreaOutputTIF[high_severity] = 4

    temp_image = Image.fromarray(burnedAreaOutput)
    temp_image.save(os.path.join(destination_filepath, 'burned_area.png'))
    save_geo_tiff(dNBR_SOURCE, os.path.join(destination_filepath, 'burned_area.tif'), 'GTiff', dNBR_SOURCE.RasterXSize, dNBR_SOURCE.RasterYSize, burnedAreaOutputTIF, gdal.GDT_Byte)
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
        temp_image.save(os.path.join(destination_filepath, 'before_the_event.png'))


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
        temp_image.save(os.path.join(destination_filepath, 'after_the_event.png'))

    # if RGB iage is present the create an RGB overlay with the disaster
    if rgb_filepath != -1:
        rgbOutput[low_severity, :] = low_severity_fill
        rgbOutput[medium_low_severity, :] = medium_low_severity_fill
        rgbOutput[medium_high_severity, :] = medium_high_severity_fill
        rgbOutput[high_severity, :] = high_fill
        temp_image = Image.fromarray(rgbOutput)
        temp_image.save(os.path.join(destination_filepath, 'burned_area_change.png'))


   
    
    # if CLC thematic layer is available, then calculate the land cover affected
    if clc_filepath != -1:
        temp_array_1 = np.multiply(CLC_array_resized, low_severity)
        temp_array_2 = np.multiply(CLC_array_resized, medium_low_severity)
        temp_array_3 = np.multiply(CLC_array_resized, medium_high_severity)
        temp_array_4 = np.multiply(CLC_array_resized, high_severity)
        clc_low = temp_array_1[np.nonzero(temp_array_1)]
        clc_medium_low = temp_array_2[np.nonzero(temp_array_2)]
        clc_medium_high = temp_array_3[np.nonzero(temp_array_3)]
        clc_high = temp_array_4[np.nonzero(temp_array_4)]

        clc_classes = get_percentage_for_all_classes_of_CLC_array(np.concatenate((clc_low, clc_medium_low, clc_medium_high, clc_high)))

        fire_clases = {}
        f.write('The CLC classes with their percentages affected from the fires are:\n')
        for i in clc_classes.keys():
            if clc_classes[i][1] > 2:
                f.write(clc_classes[i][0] + ': ' + str(clc_classes[i][1]) + '%\n')
                fire_clases.update(dict({clc_classes[i]}))
    
    elif lc_gl_filepath != -1:
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

        fire_clases = {}
        f.write('The CLC classes with their percentages affected from the fires are:\n')
        for i in glc_classes.keys():
            if glc_classes[i][1] > 2:
                f.write(glc_classes[i][0] + ': ' + str(glc_classes[i][1]) + '%\n')
                fire_clases.update(dict({glc_classes[i]}))
    else:
        fire_clases = {}            


    metadata = OrderedDict()
    ds_raster = rasterio.open(os.path.join(destination_filepath, 'dNBR.tif'))
    ds_raster.crs.to_epsg()
    metadata['platform'] = 'S2A, S2B'
    metadata['product_type'] = 'L2A'
    metadata['sensor_mode'] = 'MSI'
    metadata['title'] = 'Burned area change detection'
    # metadata['location_name'] = ''
    metadata['CRS'] = 'EPSG:{} - WGS 84 / UTM zone {}N'.format(ds_raster.crs.to_epsg(),
                                                                  ds_raster.crs.to_epsg() - 32600)
    metadata['pixel_size'] = [10, 10]
    metadata['Extent'] = GetExtent(dNBR_SOURCE)
    element = datetime.datetime.strptime(before_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['start_date'] = int(time.mktime(tuple))
    element = datetime.datetime.strptime(after_date, "%Y-%m-%d")
    tuple = element.timetuple()
    metadata['end_date'] = int(time.mktime(tuple))
    metadata['total_affected_area'] = round(((float(high_severity.sum() + medium_high_severity.sum() + medium_low_severity.sum() + low_severity.sum()) * 100) / 1000000), 2)
    metadata['high_severity_area'] = round(((float(high_severity.sum()) * 100) / 1000000), 2)
    metadata['medium_high_severity_area'] = round(((float(medium_high_severity.sum()) * 100) / 1000000), 2)
    metadata['medium_low_severity_area'] = round(((float(medium_low_severity.sum()) * 100) / 1000000), 2)
    metadata['low_severity_area'] = round(((float(low_severity.sum()) * 100) / 1000000), 2)
    metadata['uncertainty_lower'] = round(uncertainty_before, 2)
    metadata['uncertainty_upper'] = round(uncertainty_after, 2)
    #if clc_filepath != -1:
    #    metadata['CLC_classes_affected_percentage_per_class'] = fire_clases
    #else:
    #    metadata['CLC_classes_affected_percentage_per_class'] = {}                
    #the following key needs to be changed because we use classes from LC100_global layer.
    metadata['CLC_classes_affected_percentage_per_class'] = fire_clases
    ds_raster = 0

    with open(destination_filepath + '/metadata.json', "w") as outfile:
        json.dump(metadata, outfile, indent=4, sort_keys=False)






'''
Water bodies may create noise and false positives when processing an area and detecting possible damages areas from
a fire. By creating a mask for all water bodies using the NDWI index, we are able to exclude those areas.
NDWI uses Band 03 (GREEN) and Band 08 (NIR).
'''
def create_NDWI_mask(input_folder, save_to_disk=True):

    GREEN = gdal.Open(os.path.join(input_folder, 'B03.tif'))
    srcband = GREEN.GetRasterBand(1)
    green_array = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)

    NIR = gdal.Open(os.path.join(input_folder, 'B08.tif'))
    srcband = NIR.GetRasterBand(1)
    nir_array = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDWI = np.divide((green_array - nir_array), ((green_array + nir_array)))
    NDWI = np.nan_to_num(NDWI)

    ndwi_mask = np.where(NDWI >= 0, False, True)  # -0.05

    if save_to_disk == True:
        createNDWIraster(os.path.join(input_folder, 'B03.tif'), os.path.join(input_folder, 'B08.tif'), input_folder)

    return ndwi_mask

''' 
Vegetation mask for the exclusion of all non-vegetated areas. Non-vegateted is
NDVI_before < 0.17 AND NDVI_after < 0.17 AND dNDVI < 0.04.
'''
def create_vegetation_mask(input_folder_before, input_folder_after, save_to_disk = True):


    # NDVI non-vegetation mask before
    RED = gdal.Open(os.path.join(input_folder_before, 'B04.tif'))
    srcband = RED.GetRasterBand(1)
    red_array = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    NIR = gdal.Open(os.path.join(input_folder_before, 'B08.tif'))
    srcband = NIR.GetRasterBand(1)
    nir_array = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDVI_before = np.divide((nir_array - red_array), ((nir_array + red_array)))
    NDVI_before = np.nan_to_num(NDVI_before)

    vegetation_mask_before = np.where(NDVI_before >= 0.17, True, False)
    non_vegetation_mask_before = np.invert(vegetation_mask_before)


    # NDVI non-vegetation mask after
    RED = gdal.Open(os.path.join(input_folder_after, 'B04.tif'))
    srcband = RED.GetRasterBand(1)
    red_array = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    NIR = gdal.Open(os.path.join(input_folder_after, 'B08.tif'))
    srcband = NIR.GetRasterBand(1)
    nir_array = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDVI_after = np.divide((nir_array - red_array), ((nir_array + red_array)))
    NDVI_after = np.nan_to_num(NDVI_after)
    
    non_vegetation_mask_after = np.where(NDVI_after <= 0.17, True, False)
    vegetation_mask_after = np.invert(non_vegetation_mask_after)

    # difference NDVI non-vegetation mask (areas that have not changed NDVI more than 0.04)
    difference_NDVI = np.subtract(NDVI_before, NDVI_after)
    non_vegetation_mask_diff = np.where(abs(difference_NDVI) < 0.04, True, False)
    vegetation_mask_diff = np.invert(non_vegetation_mask_diff)

    non_vegetation_mask_final = np.logical_and(non_vegetation_mask_before,non_vegetation_mask_after)
    non_vegetation_mask_final = np.logical_and(non_vegetation_mask_final,non_vegetation_mask_diff)

    if save_to_disk==True:
        createNDVIraster(os.path.join(input_folder_before, 'B04.tif'), os.path.join(input_folder_before, 'B08.tif'), input_folder_before)
        createNDVIraster(os.path.join(input_folder_after, 'B04.tif'), os.path.join(input_folder_after, 'B08.tif'), input_folder_after)
        # raster_diffetence(os.path.join(input_folder_before, 'NDVI.tif'), os.path.join(input_folder_after, 'NDVI.tif'), os.path.join(destination_file, 'indexes_and_bands'), 'NDVI')

    return non_vegetation_mask_final

'''
New index of the RGR Bands for the exclusion of very bright area and rock formations, clouds and smoke. It relies of the RGB bands
and has not been validated extensively yet.
'''
def create_NRGB_index_mask(input_folder, save_to_disk=True):

    ###10m bands###
    BLUE = gdal.Open(os.path.join(input_folder, 'B02.tif'))
    srcband = BLUE.GetRasterBand(1)
    blue_array = srcband.ReadAsArray(0, 0, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

    RED = gdal.Open(os.path.join(input_folder, 'B04.tif'))
    srcband = RED.GetRasterBand(1)
    red_array = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    GREEN = gdal.Open(os.path.join(input_folder, 'B03.tif'))
    srcband = GREEN.GetRasterBand(1)
    green_array = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)

    if save_to_disk == True:
        createNRGBraster(os.path.join(input_folder, 'B02.tif'), os.path.join(input_folder, 'B03.tif'),os.path.join(input_folder, 'B04.tif'), input_folder)


    NRGB_index_array = np.multiply(blue_array, green_array)
    NRGB_index_array = np.multiply(NRGB_index_array, red_array)
    NRGB_index_array = NRGB_index_array/1000000

    index_hist = np.histogram(NRGB_index_array.flatten(), bins=255, range=(0, 20000))
    first_gradient = np.gradient(index_hist[0], index_hist[1][:-1])
    for i, value in enumerate(first_gradient):
        if abs(value) < 3 and index_hist[1][i] > 2000:
            NRGB_threshold = index_hist[1][i]
            break
    NRGB_index_mask = np.where(NRGB_index_array > NRGB_threshold, False, True)


    return NRGB_index_mask

# Smoothens a given histogram (1D array) using "moving average" calculations
def moving_average_smooth(Y, width=5):
    n = len(Y)

    c = lfilter(np.ones(width) / width, 1, Y)
    cbegin = np.cumsum(Y[0:width - 2])
    cbegin_div = np.arange(1, (width - 1), 2).astype(float)
    cbegin = cbegin[::2] / cbegin_div
    cend = np.cumsum(Y[(n - 1):(n - width + 3 - 2):-1])
    cend_div = np.arange(width - 2, 0, -2).astype(float)
    cend = cend[(n)::-2] / cend_div

    c = np.concatenate((cbegin, c[(width - 1)::], cend))

    return c

#find valleys that aren't too close to both of its adjacent peaks
def find_possible_valleys(peaks, valleys, distance = 5):
	possible_valleys = []
	for i,each_valley in enumerate(valleys):
		if i+1>=len(peaks):
			continue
		elif abs(each_valley - peaks[i]) > distance or abs(each_valley-peaks[i + 1]) > distance:
			possible_valleys.append(each_valley)
	return possible_valleys

def save_geo_tiff(gdal_guidance_image, output_file, out_format, rasterXSize, rasterYSize, array_image, dtype,noDataValue=""):
    # test me
    geoTrans_guidance = gdal_guidance_image.GetGeoTransform()  # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
    wkt_guidance = gdal_guidance_image.GetProjection()  # Retrieve projection system of guidance image into well known text (WKT) format and save it in wkt_guidance

    # format = 'GTiff'
    driver = gdal.GetDriverByName(out_format)  # Generate an object of type GeoTIFF / KEA
    dst_ds = driver.Create(output_file, rasterXSize, rasterYSize, 1,
                           dtype)  # Create a raster of type Geotiff / KEA with dimension Guided_Image.RasterXSize x Guided_Image.RasterYSize, with one band and datatype of GDT_Float32
    if dst_ds is None:  # Check if output_file can be saved
        print ("Could not save output file %s, path does not exist." % output_file)
        quit()
    # sys.exit(4)

    dst_ds.SetGeoTransform(
        geoTrans_guidance)  # Set the Geo-information of the output file the same as the one of the guidance image
    dst_ds.SetProjection(wkt_guidance)
    # this line sets zero to "NaN"
    if noDataValue != "":
        dst_ds.GetRasterBand(1).SetNoDataValue(noDataValue)
        print("Value to be replaced with NaN was given: " + str(noDataValue))
    dst_ds.GetRasterBand(1).WriteArray(array_image)  # Save the raster into the output file
    dst_ds.FlushCache()  # Write to disk.

# Find the percentage of all CLC classes an array containing the CLC values
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

'''
Calculation of the histogram for a NBR raster, find a valley (if present) and use it for thresholding.
If no valleys are present a hard threshold will be used, found empirically that may provide adequate results most of
the time.
'''
def histogram_and_mask_for_NBR(ind_array,  hard_threshold = -0.2):

    ind_array_hist, _ = np.histogram(ind_array[ind_array != 0], bins=201, range=[-1.0, 1.0])
    peaks, valleys = conv_peakdet.peakdet(ind_array_hist, np.mean(ind_array_hist) / 10)
    ind_array_hist_smoothed = moving_average_smooth(ind_array_hist)
    valleys_only = [x[0] for x in valleys]
    valleys_only_ranged = [(x - 100) / 100.0 for x in valleys_only]
    peaks_only = [x[0] for x in peaks]
    peaks_only_ranged = [(x - 100) / 100.0 for x in peaks_only]
    if len(valleys_only_ranged) > 0 and len(peaks_only_ranged) > 1:
        if valleys_only_ranged[0] > hard_threshold:
            threshold = hard_threshold
        else:
            threshold = valleys_only_ranged[0]
    else:
        threshold = hard_threshold
    ind_array_hist_ranged = [(x - 100) / 100.0 for x in ind_array_hist]
    ind_array_mask = np.where(ind_array < threshold, True, False)
    # ind_array_mask_image = (ind_array_mask * 255)
    # temp_image = Image.fromarray(ind_array_mask_image.astype('uint8'))
    # temp_image.save((os.path.join(destination, 'NBR_mask.png')))

    return ind_array_mask, threshold

#Band 08 (NIR) and band 12(SWIR) are used to calculate NBR (Normalized Burn Ratio)
def createNBRraster(NIR_filepath, SWIR_filepath, save_result_directory):

    NIR = gdal.Open(NIR_filepath)
    srcband = NIR.GetRasterBand(1)
    NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    SWIR = gdal.Open(SWIR_filepath)
    srcband = SWIR.GetRasterBand(1)
    SWIR_original = srcband.ReadAsArray(0, 0, SWIR.RasterXSize, SWIR.RasterYSize).astype(np.float)
    SWIR_resized = srcband.ReadAsArray(0, 0, SWIR.RasterXSize, SWIR.RasterYSize, NIR.RasterXSize,NIR.RasterYSize).astype(np.float)

    NBR = np.divide((NIR_original - SWIR_resized),((NIR_original + SWIR_resized)))
    save_geo_tiff(NIR, save_result_directory + '/NBR.tif', 'GTiff', NIR.RasterXSize, NIR.RasterYSize, NBR, gdal.GDT_Float32)

    print('NBR:')
    print(np.amin(NBR))
    print(np.amax(NBR))

# NBR of image before and NBR of image after are used to calculate dNBR (Difference Normalized Burn Ratio)
def createRBRrraster(NBR_BEFORE_filepath, NBR_AFTER_filepath, save_result_directory):

    NBRB = gdal.Open(NBR_BEFORE_filepath)
    srcband = NBRB.GetRasterBand(1)
    NBRB_original = srcband.ReadAsArray(0, 0, NBRB.RasterXSize, NBRB.RasterYSize).astype(np.float)

    NBRA = gdal.Open(NBR_AFTER_filepath)
    srcband = NBRA.GetRasterBand(1)
    NBRA_original = srcband.ReadAsArray(0, 0, NBRA.RasterXSize, NBRA.RasterYSize).astype(np.float)

    RBR = np.divide(np.subtract(NBRB_original, NBRA_original), NBRB_original + 1.001)
    save_geo_tiff(NBRB, save_result_directory + '/RBR.tif', 'GTiff', NBRB.RasterXSize, NBRB.RasterYSize, RBR,
                  gdal.GDT_Float32)

    print('RBR:')
    print(np.amin(RBR))
    print(np.amax(RBR))

# Band 02 (BLUE), Band 03 (GREEN) and band 04 (RED) are used to calculate the new RGB index (partially arbitrary)
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
    NRGB = NRGB/1000000
    save_geo_tiff(GREEN, save_result_directory + '/NRGB.tif', 'GTiff', GREEN.RasterXSize, GREEN.RasterYSize, NRGB,
                  gdal.GDT_Float32)
    # slope, intercept = np.polyfit(np.log(length), np.log(time), 1)
    print('NRGB:')
    print(np.amin(NRGB))
    print(np.amax(NRGB))

# NBR of image before and NBR of image after are used to calculate dNBR (Difference Normalized Burn Ratio)
def createDNBRrraster(NBR_BEFORE_filepath, NBR_AFTER_filepath, save_result_directory):

    NBRB = gdal.Open(NBR_BEFORE_filepath)
    srcband = NBRB.GetRasterBand(1)
    NBRB_original = srcband.ReadAsArray(0, 0, NBRB.RasterXSize, NBRB.RasterYSize).astype(np.float)

    NBRA = gdal.Open(NBR_AFTER_filepath)
    srcband = NBRA.GetRasterBand(1)
    NBRA_original = srcband.ReadAsArray(0, 0, NBRA.RasterXSize, NBRA.RasterYSize).astype(np.float)

    dNBR = np.subtract(NBRB_original, NBRA_original)
    save_geo_tiff(NBRB, save_result_directory + '/dNBR.tif', 'GTiff', NBRB.RasterXSize, NBRB.RasterYSize, dNBR,
                  gdal.GDT_Float32)

    print('dNBR:')
    print(np.amin(dNBR))
    print(np.amax(dNBR))

# create a raster derived from the difference of 2 different rasters
def raster_diffetence(raster_before_filepath, raster_after_filepath, save_result_directory, index=None):

    RASTER_BEFORE = gdal.Open(raster_before_filepath)
    srcband = RASTER_BEFORE.GetRasterBand(1)
    BEFORE_ARRAY = srcband.ReadAsArray(0, 0, RASTER_BEFORE.RasterXSize, RASTER_BEFORE.RasterYSize).astype(np.float)

    RASTER_AFTER = gdal.Open(raster_after_filepath)
    srcband = RASTER_AFTER.GetRasterBand(1)
    AFTER_ARRAY = srcband.ReadAsArray(0, 0, RASTER_AFTER.RasterXSize, RASTER_AFTER.RasterYSize).astype(np.float)

    DIFF = np.subtract(BEFORE_ARRAY, AFTER_ARRAY)
    save_geo_tiff(RASTER_BEFORE, save_result_directory + '/diff_{}.tif'.format(index), 'GTiff', RASTER_BEFORE.RasterXSize, RASTER_BEFORE.RasterYSize, DIFF,
                  gdal.GDT_Float32)

    # print('dNBR:')
    # print(np.amin(dNBR))
    # print(np.amax(dNBR))

# Band 03 (Green) and 08 (NIR) are used to calculate NDWI (Normalized Difference Water Index)
def createNDWIraster(GREEN_filepath, NIR_filepath, save_result_directory):


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

# Band 04 (RED) and 08 (NIR) are used to calculate NDVI
def createNDVIraster(RED_filepath, NIR_filepath, save_result_directory):
    RED = gdal.Open(RED_filepath)
    srcband = RED.GetRasterBand(1)
    RED_original = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

    NIR = gdal.Open(NIR_filepath)
    srcband = NIR.GetRasterBand(1)
    NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)

    NDVI = np.divide((NIR_original - RED_original), ((NIR_original + RED_original)))
    save_geo_tiff(RED, save_result_directory + '/NDVI.tif', 'GTiff', RED.RasterXSize, RED.RasterYSize, NDVI,
                  gdal.GDT_Float32)

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

# get extent of the bounding box of a GeoTIFF raster file
def GetExtent(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel

    return (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)
    
def GetExtent_EPSG_4326(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel
    ds_raster = rasterio.open(ds)
    zone = ds_raster.crs.to_epsg() - 32600
    (xmax_epsg_4326, ymin_epsg_4326) = utm.to_latlon(xmax, ymin)
    (xmin_epsg_4326, ymax_epsg_4326) = utm.to_latlon(xmin, ymax)
    
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
    return (ymax_conv, xmin_conv),  (ymin_conv, xmax_conv)
    


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