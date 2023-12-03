from osgeo import gdal
import numpy as np
from algorithm_water_change_area.watermask_algorithm_snapearth.find_optimum_threshold import find_optimum_threshold
import algorithm_water_change_area.watermask_algorithm_snapearth.my_functions as myfun
from algorithm_water_change_area.watermask_algorithm_snapearth import conv_peakdet
import distutils.dir_util
import algorithm_water_change_area.watermask_algorithm_snapearth.watermask_settings as watermask_settings
import pymeanshift as pms
import time
import matplotlib.pyplot as plt
import os


def calculate_watermasks(bands_dir, product_begin_date): ##, query_id, begin_date):

	#myfun.current_date_time_string()
	total_time = time.time()
	print("Calculating mask for " + product_begin_date)
	#start_date_time = myfun.current_date_time_string_better_format()

	#data_directory = "Z:/Validation2/"+watermask_settings.working_date+'/'
	data_directory_temp_folder = bands_dir + 'temp-watermask/'
	data_directory_output =  bands_dir
	distutils.dir_util.mkpath(data_directory_temp_folder)
	distutils.dir_util.mkpath(data_directory_output)

	#for each date re-set the output folder
	#create the output sub-folder if not already existspip 
	#distutils.dir_util.mkpath(data_directory_temp_folder+'output/')
	#in output/ create a sub-folder with the current time-stamp

	#10m resolution bands
	BLUE_STRING = bands_dir + 'B02.tif'
	GREEN_STRING = bands_dir + 'B03.tif'
	RED_STRING = bands_dir + 'B04.tif'

	#20m resolution bands
	SWIR_STRING = bands_dir + 'B11.tif'
	SWIR_STRING2 = bands_dir + 'B12.tif'
	REDEDGE1_STRING = bands_dir + 'B05.tif'
	REDEDGE3_STRING = bands_dir + 'B07.tif'

	#Added by Gio
	Narrow_NIR_STRING = bands_dir + 'B8A.tif'

	# Added by Michalis
	NIR_STRING = bands_dir + 'B08.tif'


	#active_area_raster = [key for key in file_bands.keys() if file_bands[key]['bands'] == ['active_area_mask']]
	active_area_raster = 'SCL.tif'

	try:
		active_area_raster
	except NameError:
		print("xmm, active area mask WASN'T defined!")
		ACTIVE_AREA_MASK_MASK_STRING = ''
	else:
		print("well, active aera mask was defined.")
		ACTIVE_AREA_MASK_MASK_STRING = bands_dir + active_area_raster

	#print("Segmentation maps is temporarily being calculated in ~4min with PyMeanShift (in Linux environment).")

	###10m bands###
	BLUE=gdal.Open(BLUE_STRING)
	srcband = BLUE.GetRasterBand(1)
	BLUE1 = srcband.ReadAsArray(0, 0, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	RED=gdal.Open(RED_STRING)
	srcband = RED.GetRasterBand(1)
	RED1 = srcband.ReadAsArray(0, 0, RED.RasterXSize, RED.RasterYSize).astype(np.float)

	GREEN=gdal.Open(GREEN_STRING)
	srcband = GREEN.GetRasterBand(1)
	GREEN1 = srcband.ReadAsArray(0, 0, GREEN.RasterXSize, GREEN.RasterYSize).astype(np.float)

	###these bands need upscale, in order to combine them with the better ones above (e.g. the BLUE one) ###
	RED_EDGE1 = gdal.Open(REDEDGE1_STRING)
	srcband = RED_EDGE1.GetRasterBand(1)
	RED_EDGE1_original = srcband.ReadAsArray(0, 0, RED_EDGE1.RasterXSize, RED_EDGE1.RasterYSize).astype(np.float)
	RED_EDGE1_resized = srcband.ReadAsArray(0, 0, RED_EDGE1.RasterXSize, RED_EDGE1.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	RED_EDGE3 = gdal.Open(REDEDGE3_STRING)
	srcband = RED_EDGE3.GetRasterBand(1)
	RED_EDGE3_original = srcband.ReadAsArray(0, 0, RED_EDGE3.RasterXSize, RED_EDGE3.RasterYSize).astype(np.float)
	RED_EDGE3_resized = srcband.ReadAsArray(0, 0, RED_EDGE3.RasterXSize, RED_EDGE3.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	SWIR = gdal.Open(SWIR_STRING)
	srcband = SWIR.GetRasterBand(1)
	SWIR_original = srcband.ReadAsArray(0, 0, SWIR.RasterXSize, SWIR.RasterYSize).astype(np.float)
	SWIR_resized = srcband.ReadAsArray(0, 0, SWIR.RasterXSize, SWIR.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	SWIR2 = gdal.Open(SWIR_STRING2)
	srcband = SWIR2.GetRasterBand(1)
	SWIR_original2 = srcband.ReadAsArray(0, 0, SWIR2.RasterXSize, SWIR2.RasterYSize).astype(np.float)
	SWIR_resized2 = srcband.ReadAsArray(0, 0, SWIR2.RasterXSize, SWIR2.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	#Added by Gio
	NARROW_NIR = gdal.Open(Narrow_NIR_STRING)
	srcband = NARROW_NIR.GetRasterBand(1)
	NARROW_NIR_original = srcband.ReadAsArray(0, 0, NARROW_NIR.RasterXSize, NARROW_NIR.RasterYSize).astype(np.float)
	NARROW_NIR_resized = srcband.ReadAsArray(0, 0, NARROW_NIR.RasterXSize, NARROW_NIR.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)

	# Added by Michalis
	NIR = gdal.Open(NIR_STRING)
	srcband = NIR.GetRasterBand(1)
	NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize).astype(np.float)
	NIR_original = srcband.ReadAsArray(0, 0, NIR.RasterXSize, NIR.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize).astype(np.float)


	ACTIVE_AREA_MASK1_resized = None
	if ACTIVE_AREA_MASK_MASK_STRING != "":
		ACTIVE_AREA_MASK = gdal.Open(ACTIVE_AREA_MASK_MASK_STRING)
		srcband = ACTIVE_AREA_MASK.GetRasterBand(1)
		ACTIVE_AREA_MASK1_resized = srcband.ReadAsArray(0, 0, ACTIVE_AREA_MASK.RasterXSize, ACTIVE_AREA_MASK.RasterYSize, BLUE.RasterXSize, BLUE.RasterYSize)

	#https://docs.scipy.org/doc/numpy/reference/generated/numpy.seterr.html
	np.seterr(divide='ignore', invalid='ignore')

	NDVI2 = (-1*RED_EDGE3_original + RED_EDGE1_original)/(RED_EDGE3_original+RED_EDGE1_original)
	NDVI2_resized = (-1*RED_EDGE3_resized + RED_EDGE1_resized)/(RED_EDGE3_resized+RED_EDGE1_resized)

	###clean outliers
	SWIR_resized[SWIR_resized < -1000000] = 0
	SWIR_resized[SWIR_resized > 1000000] = 0
	SWIR_resized[np.isnan(SWIR_resized)] = 0
	SWIR_resized[np.isinf(SWIR_resized)] = 0
	SWIR_resized1 = np.copy(SWIR_resized)

	SWIR_resized2[SWIR_resized2 < -1000000] = 0
	SWIR_resized2[SWIR_resized2 > 1000000] = 0
	SWIR_resized2[np.isnan(SWIR_resized2)] = 0
	SWIR_resized2[np.isinf(SWIR_resized2)] = 0

	SWIR_rescaled1 = SWIR_resized1 - np.amin(SWIR_resized1)
	SWIR_rescaled1 = SWIR_resized1 / np.amax(SWIR_resized1)
	SWIR_rescaled2 = SWIR_resized2 - np.amin(SWIR_resized2)
	SWIR_rescaled2 = SWIR_resized2 / np.amax(SWIR_resized2)

	SWIR_mult = np.multiply(SWIR_resized, SWIR_resized2) / 100000
	SWIR_mult[SWIR_mult > 250] = 0

	#Added by Gio

	if  watermask_settings.Alt1_or_Alt2_or_Alt3==0:
		aaa=11
	elif watermask_settings.Alt1_or_Alt2_or_Alt3==2:
		SWIR_resized=np.multiply(NARROW_NIR_resized,SWIR_resized2)
		SWIR_resized=myfun.range_0_255(SWIR_resized)
	elif watermask_settings.Alt1_or_Alt2_or_Alt3==3:
		SWIR_resized=np.multiply(NARROW_NIR_resized,SWIR_resized)
		SWIR_resized=myfun.range_0_255(SWIR_resized)


	#BLUE_stripped=np.copy(BLUE1)
	#BLUE_stripped[:,:] = 0
	#BLUE_stripped[BLUE1 <= 0] = 1
	##issue 5.0: SWIR_resized is still valid without black pixels at 4610, - 997


	####START CHECKS HERE##
	SWIR_resized_copy = np.copy(SWIR_resized)
	##issue 5.1: here some black pixels occur at 4610, - 997, thus commented out
	SWIR_rescaled = SWIR_resized_copy-np.amin(SWIR_resized_copy)
	SWIR_rescaled = SWIR_rescaled/np.amax(SWIR_rescaled)

	#
	# SWIR_resized_copy_mult = np.copy(SWIR_mult)
	# SWIR_rescaled2 = SWIR_resized_copy_mult-np.amin(SWIR_resized_copy_mult)
	# SWIR_rescaled2 = SWIR_resized_copy_mult/np.amax(SWIR_resized_copy_mult)


	if ACTIVE_AREA_MASK_MASK_STRING != "":
		######
		SWIR_rescaled[ACTIVE_AREA_MASK1_resized <= 0] = np.nan #originally was "NaN", should have worked: np.nan
		#if SCL is defined as active_area_mask, then filter out the shadow of the clouds (pixel value 3)
		if 'active_area_raster' in locals() and active_area_raster == 'SCL.tif':
			print("Cloud shadows will be filtered from SWIR histogram.")
			######
			# SWIR_rescaled[np.logical_or(ACTIVE_AREA_MASK1_resized == 3,  ACTIVE_AREA_MASK1_resized == 3)] = np.nan

	SWIR_rescaled_nans = np.copy (SWIR_rescaled)
	#SWIR_rescaled_nans[BLUE_stripped == 1] = np.nan
	SWIR_rescaled_flattened = SWIR_rescaled_nans.flatten()
	swir_hist,_ = np.histogram(SWIR_rescaled_flattened[~np.isnan(SWIR_rescaled_flattened)], bins = 255)


	swir_peaks, swir_valleys = conv_peakdet.peakdet(swir_hist, np.mean(swir_hist)/3)
	swir_hist_smoothed = myfun.moving_average_smooth(swir_hist)

	swir_peaks_smoothed, swir_valleys_smoothed = conv_peakdet.peakdet(swir_hist_smoothed, np.mean(swir_hist_smoothed)/3)
	swir_valleys_smoothed_only = [x[0] for x in swir_valleys_smoothed]
	swir_valleys_only = [x[0] for x in swir_valleys]
	swir_peaks_only = [x[0] for x in swir_peaks]

	plt.hist(SWIR_rescaled_flattened[~np.isnan(SWIR_rescaled_flattened)], bins = 255)
	# plt.figure()

	for x in range(0, len(swir_hist_smoothed)):
		#print (u2[x])
		plt.plot(x, swir_hist_smoothed[x], 'ro-')
		plt.plot(x, swir_hist[x], 'bo-')
	#plt.show()
	plt.title("SWIR Vs Smoothed")
	plt.savefig(data_directory_temp_folder+'swir_hist_plus_smoothed_'+product_begin_date+'.png', bbox_inches='tight')
	plt.clf()

	#some report
	f = open(data_directory_temp_folder + 'report_' + product_begin_date + '.txt','w')
	f.write('Watermasks for: '+ product_begin_date+'\n')
	f.write("Using MCET_or_OTSU_or_Avg=" + str(watermask_settings.MCET_or_OTSU_or_Avg)+'\n')
	f.write("Using Alt1_or_Alt2_or_Alt3=" + str(watermask_settings.Alt1_or_Alt2_or_Alt3)+'\n')



	initial_threshold_SWIR = -1;
	#Threshold initial is the first deep valley of the swir histogram
	if len(swir_valleys) > 0 and len(swir_valleys_smoothed) > 0:
		possible_valleys = myfun.find_possible_valleys(swir_peaks_only, swir_valleys_only)
		if len(possible_valleys) > 0:
			#initial threshold of SWIR must be close to the smoothed one (max distance 2)
			initial_threshold_SWIR = myfun.findClosestFirst(swir_valleys_smoothed_only, possible_valleys, 4, f)
			if initial_threshold_SWIR is not None:
				print ("Initial threshold found: " + str(initial_threshold_SWIR))
			else:
				print ("No valley was close to the smoothed SWIR!")
				f.write("No valley was close to the smoothed SWIR!")
				initial_threshold_SWIR = -1
		else:
			print("No possible valley was detected")
	else:
		print ("Caution! No deep valley was found. It was hard-coded to: " + str(initial_threshold_SWIR))
	f.write('initial_threshold_SWIR: ' + str(initial_threshold_SWIR)+ '\n')

	#
	# # added by Michalis
	# if the initial threshold is not detected or detected incorectly then try to substitute with NDWI index to perform the
	# rough seperation of inundated and non-inundated areas
	use_ndwi = False
	if initial_threshold_SWIR == -1 or initial_threshold_SWIR > 50:
		if initial_threshold_SWIR == -1:
			print('No initial threshold for SWIR band found. NDWI willl be used for the rough separation of water and landa, for the calculation of the optimum threshold next')
		else:
			print('Initial threshold for SWIR band was erroneously detected. NDWI willl be used for the rough separation of water and landa, for the calculation of the optimum threshold next')
		NDWI = (-1 * NIR_original + GREEN1) / (NIR_original + GREEN1)
		save_result_file_path_name = data_directory_output + 'NDWI.tif'
		myfun.saveGeoTiff(BLUE, save_result_file_path_name, BLUE.RasterXSize, BLUE.RasterYSize, NDWI, gdal.GDT_Float32)
		use_ndwi = True
		initial_threshold_SWIR = 1

	if initial_threshold_SWIR == -1:
		# this part is obsolete after the changes
		print('No initial threshold for SWIR band found. Exiting watermasks calculation, will create blank image with error.')
	else:
		#is it any different?
		#SWIR_rescaled[ACTIVE_AREA_MASK1_resized == np.nan] = 0
		SWIR_rescaled[SWIR_rescaled == np.nan] = 0

		###find the valid location for the BLUE band
		#BLUE_valid_area = np.copy(BLUE1)
		#BLUE_valid_area[:] = 0
		#This returns TRUE cause all elements were just zeroed
		#print((BLUE_proc == 0).all())
		#BLUE_valid_area[BLUE1 <= 0] = 1
		#This should return FALSE cause not all elements are zero (we must have areas to explore)
		#print((BLUE_valid_area == 0).all())

		#check value on BLUE_proc
		#if 1 in BLUE_valid_area[:]:
		#        print('ones were found in _proc')
		#scipy.misc.imsave('Z:\\BLUE_Normalized.tif', BLUE_normalized);
		RED_normalized = myfun.range_0_255(RED1);
		BLUE_normalized = myfun.range_0_255(BLUE1);
		GREEN_normalized = myfun.range_0_255(GREEN1);
		###Here we should exclude the zero pixels of the image and mark them as NaN

		#This creates the colored version of our image combining 3 Bands (r,g,b)
		rgbArray = np.zeros((BLUE.RasterYSize,BLUE.RasterXSize,3), 'uint8')
		rgbArray[..., 0] = RED_normalized*255
		rgbArray[..., 1] = GREEN_normalized*255
		rgbArray[..., 2] = BLUE_normalized*255
		#img = Image.fromarray(rgbArray)
		#img.save('Z:\\initialOut33.tif')
		myfun.saveGeoTiffRGB(BLUE, data_directory_temp_folder+'RGB_'+product_begin_date[:-1]+'.tif', BLUE.RasterXSize, BLUE.RasterYSize, rgbArray)

		init_dim_rgb_y = rgbArray.shape[0]
		init_dim_rgb_x = rgbArray.shape[1]

		dim_rgb_y = rgbArray.shape[0]
		dim_rgb_x = rgbArray.shape[1]


		total_rgb_pixels = dim_rgb_y*dim_rgb_x

		#if RGB is greater than 40 mpixel
		rgb_scale_down_times = 0
		while total_rgb_pixels > 40000000:
			dim_rgb_y = dim_rgb_y//2
			dim_rgb_x = dim_rgb_x//2
			total_rgb_pixels = dim_rgb_y*dim_rgb_x
			rgb_scale_down_times+=1

		#downscale RGB if too big
		#if rgb_scale_down_times	> 0:
		#	print("Downscaling RGB image " + str(rgb_scale_down_times) + " time(s)")
		#	rgbArray = scipy.misc.imresize(rgbArray, (dim_rgb_y, dim_rgb_x, 3), 'nearest')


		# --------------------------  segmentation and optimum threshold calculation    --------------------------------

		#Use the above RGB image-array to create the labels (segments), using PyMeanShift
		regions_number = -1
		start_segmentation_time = time.time()
		print("LABELS image is being created using PyMeanShift based on RGB")
		(segmented_image, labels_image, number_regions) = pms.segment(rgbArray, spatial_radius = 3, range_radius = 3, min_density = 500)
		print ("Number_of_labels initial: " + str(int(np.amax(labels_image))))

		#upscale Labels if RGB was previously downlscaled
		if rgb_scale_down_times	> 0:
			print("Upscaling LABELS image " + str(rgb_scale_down_times) + " time(s)")
			#labels_image = scipy.misc.imresize(labels_image,(init_dim_rgb_y, init_dim_rgb_x), 'nearest')
			labels_image = np.resize(labels_image,(init_dim_rgb_y, init_dim_rgb_x))

		print("Number_of_labels after: " + str(int(np.amax(labels_image))))

		myfun.saveGeoTiff(BLUE, data_directory_temp_folder+'labels_'+product_begin_date[:-1]+'.tiff', BLUE.RasterXSize, BLUE.RasterYSize, labels_image, gdal.GDT_UInt32)
		print("number of regions: " + str(number_regions))
		watermask_settings.exec_time_mean_shift_segmentation = (time.time() - start_segmentation_time)
		print("Segmentation map calculated in: " + str(watermask_settings.exec_time_mean_shift_segmentation) + " seconds")
		LABELS_original	= labels_image
		regions_number = number_regions

		#preload already calculated segmentation image DELETE THESE
		'''
		LABELS_STRING = data_directory_temp_folder+'labels_'+product_begin_date[:-1]+'.tiff'
		LABELS = gdal.Open(LABELS_STRING)
		srcband = LABELS.GetRasterBand(1)
		LABELS_original = srcband.ReadAsArray(0, 0, LABELS.RasterXSize, LABELS.RasterYSize).astype(np.uint32)
		print("Segmentation map was loaded")
		regions_number = np.amax(LABELS_original)
		'''

		f.write("Number of regions: " + str(regions_number) + '\n')
		f.write("Segmentation map calculated in: " + str(watermask_settings.exec_time_mean_shift_segmentation) + " seconds" + '\n')

		if use_ndwi == False:
			MASK_SWIR = np.copy(SWIR_rescaled)
			MASK_SWIR[:, :] = 0
			MASK_SWIR[SWIR_rescaled > initial_threshold_SWIR / 255.0] = 1;
		else:
			MASK_SWIR = np.copy(NDWI)
			MASK_SWIR[:, :] = 0
			MASK_SWIR[NDWI < 0] = 1;

		#MASK_SWIR_255 = np.round(MASK_SWIR*255)
		SWIR_Scaled_rounded = np.copy(SWIR_rescaled)
		SWIR_Scaled_rounded = np.round(SWIR_Scaled_rounded*255.0, 0)

		start_time_optimum = time.time()

		##This calculates the M_opt and Max(M_opt, T_init) => T_final_swir, takes 7.5min
		if watermask_settings.MCET_or_OTSU_or_Avg==1:
			print("MCET Threshold estimation")
			try:
				optimum_threshold = find_optimum_threshold(SWIR_Scaled_rounded, MASK_SWIR, LABELS_original, ACTIVE_AREA_MASK1_resized)
			except:
				optimum_threshold = initial_threshold_SWIR
		elif watermask_settings.MCET_or_OTSU_or_Avg==2:
			print("Otsu Threshold estimation")
			try:
				optimum_threshold = find_optimum_threshold(SWIR_Scaled_rounded, MASK_SWIR, LABELS_original, ACTIVE_AREA_MASK1_resized)
			except:
				optimum_threshold = initial_threshold_SWIR
		elif watermask_settings.MCET_or_OTSU_or_Avg==3:
			print("Average Threshold estimation")
			watermask_settings.MCET_or_OTSU_or_Avg=1
			optimum_threshold1 = find_optimum_threshold(SWIR_Scaled_rounded, MASK_SWIR, LABELS_original, ACTIVE_AREA_MASK1_resized)
			watermask_settings.MCET_or_OTSU_or_Avg=2
			optimum_threshold2 = find_optimum_threshold(SWIR_Scaled_rounded, MASK_SWIR, LABELS_original, ACTIVE_AREA_MASK1_resized)
			optimum_threshold=(optimum_threshold1+optimum_threshold2)/2


		if optimum_threshold == -1:
			print('No optimum threshold found. Exiting watermasks calculation')
			if use_ndwi == True:
				print('No initial or optimum threshold found. Exiting watermasks calculation')
				exit()
			else:
				print('No optimum threshold found. Will now use the initial threshold only')
				optimum_threshold = initial_threshold_SWIR
			#save blank image (but not here)
			## myfun.update_product_watermask_status(query_id, begin_date, 3)
		else:
			print("Optimum threshold: " + str(optimum_threshold))
			print("---Total Optimum threshold calculated in %s seconds ---" % (time.time() - start_time_optimum))

			f.write("Optimum threshold: " + str(optimum_threshold)  + '\n')
			#  added by michalis
			ndwi_watermask = False


			'''
			if optimum >> initial or optimum > 70, then the calculation is incorrect most of the times and the output cannot be used
			substitute the too great optimum threshold value with 2*initial_thresh
			There is also a block for handling situations where threshold is lower than 5. 
			Did not find something good so this remains as the rest. 2*init_thresh
			70 is quite high, may need to be lowered in some cases.
			'''

			if (optimum_threshold - initial_threshold_SWIR) / initial_threshold_SWIR > 3 and use_ndwi==False and optimum_threshold > 70:
				print('Optimum threshold found is more than 3 times the initial threshold or greater than 70. Possible error. WaterMask will be created using a lower threshold')

				if initial_threshold_SWIR < 5:
					T_final_swir = 2 * initial_threshold_SWIR
				else:
					T_final_swir = 2 * initial_threshold_SWIR
			else:
				T_final_swir = max(initial_threshold_SWIR, optimum_threshold)
			print("T_final_swir: " + str(T_final_swir))
			f.write('T_final_swir: ' + str(T_final_swir) + '\n')


			'''
			Below is the original methodology of picking the final threshold, without any modifications. To be used according to
			the needs of the situation
			'''


			# if optimum_threshold == -1:
			# 	print('No optimum thresholdfound. Exiting watermasks calculation, will create blank image with error.')
			# # save blank image (but not here)
			# ## myfun.update_product_watermask_status(query_id, begin_date, 3)
			# else:
			# 	print("Optimum threshold: " + str(optimum_threshold))
			# 	print("---Total Optimum threshold calculated in %s seconds ---" % (time.time() - start_time_optimum))
			#
			# 	f.write("Optimum threshold: " + str(optimum_threshold))
			#
			# 	T_final_swir = max(initial_threshold_SWIR, optimum_threshold)
			# 	print("T_final_swir: " + str(T_final_swir))

			# --------------------------  segmentation and optimum threshold calculation    ----------------------------



			# --------------------------  floating vegetation / wetlands original method detection  --------------------

			##NDVI calculation for detecting the threshold for wetlands detection
			NDVI2_resized_copy = -1 * np.copy(NDVI2_resized)
			NDVI2_nans = np.copy(NDVI2_resized_copy)
			# NDVI2_nans[BLUE_stripped == 1] = np.nan;
			NDVI2_flattened = NDVI2_nans.flatten()
			NDVI2_hist, _ = np.histogram(NDVI2_flattened[~np.isnan(NDVI2_flattened)], bins=201, range=[-1.0, 1.0])
			plt.hist(NDVI2_flattened[~np.isnan(NDVI2_flattened)], bins=201, range=[-1.0, 1.0])
			NDVI2_peaks, NDVI2_valleys = conv_peakdet.peakdet(NDVI2_hist, np.mean(NDVI2_hist) / 10)
			NDVI2_valleys_only = [x[0] for x in NDVI2_valleys]
			NDVI2_valleys_only_ranged = [(x - 100) / 100.0 for x in NDVI2_valleys_only]
			NDVI2_hist_ranged = [(x - 100) / 100.0 for x in NDVI2_hist]

			# Find T_MNDVI
			T_MNDVI = None
			if len(NDVI2_valleys_only_ranged) > 0:
				deep_valleys = NDVI2_valleys_only_ranged
				for T_MNDVI in (x for x in deep_valleys if x > 0.4): break
				print("T_MNDVI is: " + str(T_MNDVI))
				f.write("T_MNDVI is: " + str(T_MNDVI) + '\n')
			else:
				print("no valleys found at all!")
				f.write("no valleys found at all!")

			if watermask_settings.Rice_Paddies_Estimation == 1:
				aaa = 11
			else:
				T_MNDVI = None  # Gio chagne

			#T_upper is the second swir valley
			T_upper_swir = None
			if(len(swir_valleys) >= 2):
				swir_valleys_only = [x[0] for x in swir_valleys]
				for each_valley in swir_valleys_only:
					if each_valley > T_final_swir and each_valley< 100:
						T_upper_swir = each_valley
						print("T_upper_swir: " + str(T_upper_swir))
						f.write("T_upper_swir: " + str(T_upper_swir)+ '\n')
						break
					else:
						print("There is no valley after T_final")
						f.write("There is no valley after T_final" + '\n')

			else:
				print("There is no second valley at all.")
				f.write("There is no second valley at all." + '\n')

			###Half vegetation###
			SWIR_rescaled[ACTIVE_AREA_MASK1_resized <= 0] = np.nan

			do_stuff = np.copy(SWIR_rescaled)
			do_stuff[SWIR_rescaled == 0] = np.nan



			# -------------------------- end of floating vegetation / wetlands original method detection  --------------------

			# added by Michalis
			# test refining with NDVI and masking out pixels with very high NDVI
			NDVI = (-1 * RED1 + NIR_original) / (NIR_original + RED1)
			ndvi_mask = np.where(NDVI > 0.90, False, True)

			#This is mask the open water
			# NDVI mask can be aplied to exclude areas with high NDVI being regarded as inundated
			mask_open_water = (SWIR_rescaled <= (T_final_swir/255.0)) & (~np.isnan(do_stuff))
			# mask_open_water = np.logical_and(mask_open_water, ndvi_mask)
			mask_open_water[SWIR_rescaled==0]=1

			date = os.path.split(os.path.split(data_directory_output)[0])[1]
			save_result_file_path_name = data_directory_output + 'water_mask_' + date + '.tif'
			myfun.saveGeoTiff(BLUE, save_result_file_path_name, BLUE.RasterXSize, BLUE.RasterYSize,mask_open_water, gdal.GDT_Byte)
			save_result_file_path_name = data_directory_output + date + '.tif'
			myfun.saveGeoTiff(BLUE, save_result_file_path_name, BLUE.RasterXSize, BLUE.RasterYSize, mask_open_water, gdal.GDT_Byte)


			if watermask_settings.Rice_Paddies_Estimation == 1:


				###Other Half vegetation###
				# 0:earth, 1:water, 2:water+vege
				print("T_upper_swir: " + str(T_upper_swir))
				print("T_MNDVI: " + str(T_MNDVI))

				open_water_and_water_vegetation = np.copy(do_stuff)
				open_water_and_water_vegetation[~np.isnan(do_stuff)] = watermask_settings.earth_value  # Earth: change all that are not "NaN" to 0!!!!
				open_water_and_water_vegetation[mask_open_water] =  watermask_settings.water_value #1!!!! #open water to 1

				# mask_water_vegetation = np.copy(do_stuff)
				# emergent vegetation detection based on the thresholds calculated
				if T_MNDVI is not None and T_upper_swir is not None:
					# water and water vegetation
					mask_water_vegetation = (NDVI2_resized_copy > T_MNDVI) & ((T_final_swir / 255.0) < SWIR_rescaled) & (SWIR_rescaled < (T_upper_swir / 255.0)) & (~np.isnan(do_stuff))
					open_water_and_water_vegetation[mask_water_vegetation] = 2  # watermask_settings.water_value #1!!!! #water vegetation to 2
					wetlands_mask = np.copy(open_water_and_water_vegetation[mask_water_vegetation])

				save_result_file_path_name = data_directory_output + 'watermask_emergent.tif'
				np.nan_to_num(open_water_and_water_vegetation)
				myfun.saveGeoTiff(BLUE, save_result_file_path_name, BLUE.RasterXSize, BLUE.RasterYSize,open_water_and_water_vegetation, gdal.GDT_Byte)


			total_exec_time = time.time() - total_time
			print("---Total date %s calculated in %s seconds ---" % (product_begin_date, total_exec_time))

			#succesfully created watermask
	f.close()
	return
