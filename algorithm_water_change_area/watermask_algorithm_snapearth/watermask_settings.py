def init(running_modes={}):
	
	##Declare global variables
	#the main working directory that contains the folders-dates
	global processed_data_directory
	
	#set water and earth values for the output output tiff	
	global water_value
	global earth_value
	global MCET_or_OTSU_or_Avg
	global Alt1_or_Alt2_or_Alt3
	global Rice_Paddies_Estimation
	
	#measures the execution times of each major phase
	global exec_time_mean_shift_segmentation
	global exec_time_good_labels
	global exec_time_threasholds
	
	#the supported raster extensions
	global supported_img_formats	
		
	#the supported raster-bands data types 
	global supported_bands_data_types
	#the supported raster-active area data types 
	global supported_active_area_data_types
	
	#the required bands for each date folder (used at dictionary as identifiers for filenames)
	global required_bands
	
	#optional raster to be used to exclude areas of the calculations
	global active_area_raster
	
	##Initial values:
	
	#to be completed
	#processed_data_directory = 'data/'
	
	#output water mask values
	water_value = 1
	earth_value = 0

	#if MCET then MCET_or_OTSU_or_Avg = 1, if Otsu then MCET then MCET_or_OTSU_or_Avg = 2, if Average then MCET then MCET_or_OTSU_or_Avg = 3
	if 'thresholding' in running_modes:
		if running_modes['thresholding'] > 0 and running_modes['thresholding'] < 4:
			MCET_or_OTSU_or_Avg = running_modes['thresholding']
		else:
			MCET_or_OTSU_or_Avg = 1
	else:
		MCET_or_OTSU_or_Avg = 1

	# MCET_or_OTSU_or_Avg = 1

	#if Alt1 then Alt1_or_Alt2_or_Alt3 = 1, if Alt2 then Alt1_or_Alt2_or_Alt3 = 2, if Alt3 then Alt1_or_Alt2_or_Alt3 = 3

	if 'alt' in running_modes:
		if running_modes['alt'] > 0 and running_modes['alt'] < 4:
			Alt1_or_Alt2_or_Alt3 = running_modes['alt']
		else:
			Alt1_or_Alt2_or_Alt3 = 1
	else:
		Alt1_or_Alt2_or_Alt3 = 1

	Alt1_or_Alt2_or_Alt3 = 1
	
	#Rice_Paddies_Estimation = 1
	Rice_Paddies_Estimation = 0
	supported_img_formats = [".tif", ".tiff"]
	
	required_bands = ["B02", "B03", "B04", "B05", "B07","B11","B06","B08","B8A","B09","B12","SCL"]
	supported_bands_data_types = ["UInt16", "UInt32"]		
	
	active_area_raster = ["active_area_mask"]
	supported_active_area_data_types = ["Byte"]
