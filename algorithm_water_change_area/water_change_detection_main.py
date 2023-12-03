import os
import os.path
import algorithm_water_change_area.change_detection_functions_water_change as change_detection_functions_water_change
from algorithm_water_change_area.watermask_algorithm_snapearth import watermasks


def water_change_main(before_folder, after_folder, rgb_image, path_for_comparisons, output_id, event_id):

    print('Water change detection module (WaterMasks)')

    # set up filepaths
    date_before = os.path.split(before_folder)[1]
    date_after = os.path.split(after_folder)[1]
    product_before = os.path.join(before_folder, 'water_mask_' + date_before + '.tif')
    product_after = os.path.join(after_folder, 'water_mask_' + date_after + '.tif')

    #define values for the Watermask algorithm
    running_modes = {}
    running_modes['alt'] = 0
    running_modes['thresholding'] = 0
    # if args.alt is not None:
    #     running_modes['alt'] = args.alt
    # else:

    # if args.thresholding is not None:
    #     running_modes['thresholding'] = args.thresholding
    # else:



    # Check for WaterMasks for each date. If not present, create them using the updated waterMask module.
    if not os.path.exists(product_before):
        try:
            # change_detection_functions_water_change.createNDWIraster(os.path.join(before_folder, 'B03.tif'), os.path.join(before_folder, 'B08.tif'), before_folder)
            change_detection_functions_water_change.createNDVIraster(os.path.join(before_folder, 'B04.tif'), os.path.join(before_folder, 'B08.tif'), before_folder)
            # change_detection_functions_water_change.createNRGBraster(os.path.join(before_folder, 'B02.tif'), os.path.join(before_folder, 'B03.tif'),os.path.join(before_folder, 'B04.tif'), before_folder)
            watermasks.start_watermask(before_folder+'/', date_before, running_modes)

            # uncomment for using the original waterMasks module
            # watermasks_original.watermasks.start_watermask(before_folder+'/', date_before)
        except:
            print('WaterMask for the date before could not be created. Check the logs for more information')
            exit()
    if not os.path.exists(product_after):
        try:
            # change_detection_functions_water_change.createNDWIraster(os.path.join(after_folder, 'B03.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
            change_detection_functions_water_change.createNDVIraster(os.path.join(after_folder, 'B04.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
            # change_detection_functions_water_change.createNRGBraster(os.path.join(after_folder, 'B02.tif'), os.path.join(after_folder, 'B03.tif'),os.path.join(after_folder, 'B04.tif'), after_folder)
            watermasks.start_watermask(after_folder+'/', date_after, running_modes)

            # uncomment for using the original waterMasks module
            # watermasks_original.watermasks.start_watermask(before_folder+'/', date_before)
        except:
            print('WaterMask for the date following could not be created. Check the logs for more information')
            exit()

    print('Finished WaterMask creation. Now proceeding with water change detection')

    # apply water change for 2 dates with existing WaterMasks
    change_detection_functions_water_change.land_water_change_detection(before_folder, after_folder, rgb_image, path_for_comparisons, output_id, event_id)

def water_change_main_simple(before_folder, after_folder, rgb_image, path_for_comparisons):

    print('Water change detection module (WaterMasks)')

    # set up filepaths
    date_before = os.path.split(before_folder)[1]
    date_after = os.path.split(after_folder)[1]
    product_before = os.path.join(before_folder, 'water_mask_' + date_before + '.tif')
    product_after = os.path.join(after_folder, 'water_mask_' + date_after + '.tif')

    #define values for the Watermask algorithm
    running_modes = {}
    running_modes['alt'] = 0
    running_modes['thresholding'] = 0
    # if args.alt is not None:
    #     running_modes['alt'] = args.alt
    # else:

    # if args.thresholding is not None:
    #     running_modes['thresholding'] = args.thresholding
    # else:



    # Check for WaterMasks for each date. If not present, create them using the updated waterMask module.
    if not os.path.exists(product_before):
        try:
            # change_detection_functions_water_change.createNDWIraster(os.path.join(before_folder, 'B03.tif'), os.path.join(before_folder, 'B08.tif'), before_folder)
            change_detection_functions_water_change.createNDVIraster(os.path.join(before_folder, 'B04.tif'), os.path.join(before_folder, 'B08.tif'), before_folder)
            # chanwatermask_algorithm_snapearthge_detection_functions_water_change.createNRGBraster(os.path.join(before_folder, 'B02.tif'), os.path.join(before_folder, 'B03.tif'),os.path.join(before_folder, 'B04.tif'), before_folder)
            watermasks.start_watermask(before_folder+'/', date_before, running_modes)

            # uncomment for using the original waterMasks module
            # watermasks_original.watermasks.start_watermask(before_folder+'/', date_before)
        except:
            print('WaterMask for the date before could not be created. Check the logs for more information')
            exit()
    if not os.path.exists(product_after):
        try:
            # change_detection_functions_water_change.createNDWIraster(os.path.join(after_folder, 'B03.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
            change_detection_functions_water_change.createNDVIraster(os.path.join(after_folder, 'B04.tif'), os.path.join(after_folder, 'B08.tif'), after_folder)
            # change_detection_functions_water_change.createNRGBraster(os.path.join(after_folder, 'B02.tif'), os.path.join(after_folder, 'B03.tif'),os.path.join(after_folder, 'B04.tif'), after_folder)
            watermasks.start_watermask(after_folder+'/', date_after, running_modes)

            # uncomment for using the original waterMasks module
            # watermasks_original.watermasks.start_watermask(before_folder+'/', date_before)
        except:
            print('WaterMask for the date following could not be created. Check the logs for more information')
            exit()

    print('Finished WaterMask creation. Now proceeding with water change detection')

    # apply water change for 2 dates with existing WaterMasks
    change_detection_functions_water_change.land_water_change_detection_simple(before_folder, after_folder, rgb_image, path_for_comparisons)