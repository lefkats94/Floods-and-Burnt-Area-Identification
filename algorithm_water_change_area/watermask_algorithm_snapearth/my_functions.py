import numpy as np
from osgeo import gdal
import time
import datetime
from scipy.signal import lfilter
import zipfile
import sys
import os
import pandas as pd
from matplotlib import pyplot as plt 
import distutils.dir_util
import pickle

from  algorithm_water_change_area.watermask_algorithm_snapearth import watermask_settings 
# import mysql.connector

'''
input: a monochromatic (usually gray scale) image as a numpy array (2D)
output: an 256L array (1D) with the frequency of each pixel-brightness from 0-255
'''
def visualize_image(image, title_text = "no specified title"):
	f = plt.figure()		
	plt.imshow(image)
	plt.title(title_text)
	plt.show()

'''
input: a monochromatic (usually gray scale) image as a numpy array (2D)
output: an 256L array (1D) with the frequency of each pixel-brightness from 0-255
'''

#used for R,G,B bands: filters (percentile) the extreme 1%
def range_0_255(Scaled_G):
	a=Scaled_G[Scaled_G[:,:] > 0]
	y = np.percentile(a, [1,99])
	Scaled_K=np.copy(Scaled_G)
	Scaled_K[Scaled_G < y[0]] = y[0]
	Scaled_K[Scaled_G > y[1]] = y[1]
	Scaled_K1=Scaled_K - y[0]
	Scaled_K1=Scaled_K1 / np.amax(Scaled_K1)
	return Scaled_K1	

def flat_hist_optimized(input_img_arr):
	u1,u2 = np.unique(input_img_arr,return_counts = True)
	flattened_array = np.zeros(256)
	flattened_array[u1] = u2
	return flattened_array

#find valleys that aren't too close to both of its adjacent peaks
def find_possible_valleys(peaks, valleys, distance = 5):
	possible_valleys = []
	for i,each_valley in enumerate(valleys):
		if abs(each_valley - peaks[i]) > distance or abs(each_valley-peaks[i + 1]) > distance:
			possible_valleys.append(each_valley)
	return possible_valleys

#used to find the initial threshold. The valley (initial threshold) should be close to a smoothed valley	
#returns the first element of follow_arr that is close enough to any element of the lead_arr
def findClosestFirst(lead_arr, follow_arr, distance, report_file):
	for fol in follow_arr:
		for lea in lead_arr:
			if (fol >=  lea - distance) and (lea <= lea + distance):
				report_file.write('Info - Distance of accepted threshold: '+ str(lea - fol) +'\n')
				return fol
	return None


#Smoothens a given histogram (1D array) using "moving average" calculations
def moving_average_smooth(Y, width = 5):

    n = len(Y)
    
    c = lfilter(np.ones(width)/width,1,Y)
    cbegin = np.cumsum(Y[0:width-2])
    cbegin_div = np.arange(1,(width-1),2).astype(float)
    cbegin = cbegin[::2]/cbegin_div
    cend = np.cumsum(Y[(n-1):(n-width+3-2):-1])
    cend_div = np.arange(width-2, 0, -2).astype(float)
    cend = cend[(n)::-2]/cend_div

    c = np.concatenate((cbegin, c[(width-1)::],cend))

    return c
	
#Return date_time as a string in Y_M_D-H_m_s format (i.e. 2018_03_10_17_28)	
def current_date_time_string():
	ts = time.time()
	st = datetime.datetime.fromtimestamp(ts).strftime('%Y_%m_%d-%H_%M_%S')
	return st

#Return date_time as a string in D/M/Y H:m:s format (i.e. 10/03/2018 17:28:34)	
def current_date_time_string_better_format():
	ts = time.time()
	st = datetime.datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M:%S')
	return st	
'''
Get Geo-data from GDAL image-array and transfer it to other array and then save it as tiff
input: initial image containing the Geo-data, output directory/filename, output file dimensions x-y, dtype (eg gdal.GDT_Float32, gdal.GDT_Byte, etc)
'''
def saveGeoTiff(gdal_guidance_image, output_file, rasterXSize, rasterYSize, array_image, dtype, noDataValue = ""):
	geoTrans_guidance = gdal_guidance_image.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
	wkt_guidance = gdal_guidance_image.GetProjection() # Retrieve projection system of guidance image into well known text (WKT) format and save it in wkt_guidance
	  
	format= 'GTiff'
	driver= gdal.GetDriverByName(format) #Generate an object of type Geotiff
	dst_ds = driver.Create(output_file, rasterXSize, rasterYSize, 1, dtype) #Create a raster of type Geotiff with dimension Guided_Image.RasterXSize x Guided_Image.RasterYSize, with one band and datatype of GDT_Float32
	if dst_ds is None: #Check if output_file can be saved
		print('Could not save output file %s, path does not exist.' % output_file)
		quit()
		#sys.exit(4)
	   
	dst_ds.SetGeoTransform(geoTrans_guidance) # Set the Geo-information of the output file the same as the one of the guidance image
	dst_ds.SetProjection (wkt_guidance)
	#this line sets zero to "NaN"
	if noDataValue !="":
		dst_ds.GetRasterBand(1).SetNoDataValue(noDataValue)
		print("Value to be replaced with NaN was given: "+str(noDataValue))
	dst_ds.GetRasterBand(1).WriteArray(array_image) # Save the raster into the output file 
	dst_ds.FlushCache()  # Write to disk.
	
def saveGeoTiffRGB(gdal_guidance_image, output_file, rasterXSize, rasterYSize, array_image_rgb):
	#test me
	geoTrans_guidance = gdal_guidance_image.GetGeoTransform() # Retrieve Geo-information of guidance image and save it in geoTrans_guidance
	wkt_guidance = gdal_guidance_image.GetProjection() # Retrieve projection system of guidance image into well known text (WKT) format and save it in wkt_guidance
	  
	format= 'GTiff'
	driver= gdal.GetDriverByName(format) #Generate an object of type Geotiff
	#options = ['PHOTOMETRIC=RGB', 'PROFILE=GeoTIFF']    , gdal.GDT_Float32, options=options
	dst_ds = driver.Create(output_file, rasterXSize, rasterYSize, 3, gdal.GDT_Byte) #Create a raster of type Geotiff with dimension Guided_Image.RasterXSize x Guided_Image.RasterYSize, with one band and datatype of GDT_Float32
	if dst_ds is None: #Check if output_file can be saved
		print('Could not save output file %s, path does not exist.' % outputfile)
		quit()
		#sys.exit(4)
	   
	dst_ds.SetGeoTransform(geoTrans_guidance) # Set the Geo-information of the output file the same as the one of the guidance image
	dst_ds.SetProjection (wkt_guidance)
	
	#this equals value 0 to 'NaN',!!!bug! creates NaN at the middle of the screen, cause even a single 0 at any of three bands creates NoData
	#dst_ds.GetRasterBand(1).SetNoDataValue(0)
	#dst_ds.GetRasterBand(2).SetNoDataValue(0)
	#dst_ds.GetRasterBand(3).SetNoDataValue(0)
	
	dst_ds.GetRasterBand(1).WriteArray(array_image_rgb[:,:,0])   # write r-band to the raster
	dst_ds.GetRasterBand(2).WriteArray(array_image_rgb[:,:,1])   # write g-band to the raster
	dst_ds.GetRasterBand(3).WriteArray(array_image_rgb[:,:,2])	 # write b-band to the raster
	dst_ds.FlushCache()  # Write to disk.

#takes as input the zip file with the folders(dates) with various band rasters
#checks if a valid zip file
#returns the number of critical errors that are found
#creates "input_report_YYYY_MM_DD.txt" with general information, warnings and critical errors found for each folder(date)
#returns a dictionary with the mapped filenames to actual bands to be used in the application
def check_bands_rasters(filename_bands_zip):
	
	given_input_zip = watermask_settings.data_directory + filename_bands_zip
	
	distutils.dir_util.mkpath(watermask_settings.data_directory + 'output/rasters_info/')

	top_dirs = []
	all_files_folders = []
	dates_dict = {}
		
	critical_errors_messages = []
	warnings_messages = []
	information_messages = []
		
	with zipfile.ZipFile(given_input_zip) as archive_dates_bands:	
		#check if zip file is corrupt
		try:
			ret = archive_dates_bands.testzip()
			if ret is not None:
				print ("First bad file in zip: %s" % ret)
				with open(watermask_settings.data_directory + 'output/input_report.txt','w') as f:
					f.write("First bad file in zip: %s" % ret)
					sys.exit(0)
			else:
				print("Zip file is good.")
				top_dirs = [x for x in archive_dates_bands.namelist() if x.endswith('/')]
				all_files_folders = archive_dates_bands.namelist()	
				for path_prefix in top_dirs:
				#create a dictionary
					dates_dict[path_prefix] = [f for f in all_files_folders if f.startswith(path_prefix) and not f.endswith('/')]
				for date_folder, folder_contents in dates_dict.iteritems():	
					each_folder_dict = {}
							
					min_ulx, max_ulx, min_uly, max_uly, min_lrx, max_lrx, min_lry, max_lry = [0,0,0,0,0,0,0,0]		
					
					for i, file_band in enumerate(folder_contents):
						file_info = {}				
						
						each_img_open = gdal.Open('/vsizip/' + given_input_zip + '/' + file_band)	
						srcband = each_img_open.GetRasterBand(1)
						
						img_data_type = gdal.GetDataTypeName(srcband.DataType)						
						file_info['data_type'] = img_data_type
						
						#if appears like an active area file and is of a compatible data type 
						if any(x in file_band for x in watermask_settings.active_area_raster) and img_data_type in watermask_settings.supported_active_area_data_types:
							file_info['supported_data_type'] = True
						elif any(x in file_band for x in watermask_settings.required_bands) and img_data_type in watermask_settings.supported_bands_data_types:
							file_info['supported_data_type'] = True
						else:
							file_info['supported_data_type'] = False
												
						# Retrieve Geo-information of guidance image
						ulx, xres, xskew, uly, yskew, yres  = each_img_open.GetGeoTransform()			
						lrx = ulx + (each_img_open.RasterXSize * xres)
						lry = uly + (each_img_open.RasterYSize * yres)
						file_info['coordinates'] = [ulx, uly, lrx ,lry]
						#if the first file in folder, use it as reference (coordinated)
						if  i == 0:
							min_ulx = ulx - ulx/10000
							max_ulx = ulx + ulx/10000					
							min_uly = uly - uly/10000
							max_uly = uly + uly/10000					
							min_lrx = lrx - lrx/10000
							max_lrx = lrx + lrx/10000					
							min_lry = lry - lry/10000
							max_lry = lry + lry/10000
							file_info['is_coordinated'] = True
						#for the rest files/bands compare with the first one (true or false)
						else:
							if (ulx < min_ulx or ulx > max_ulx) or (uly < min_uly or uly > max_uly) or (lrx < min_lrx or lrx > max_lrx) or (lry < min_lry or lry > max_lry):
								file_info['is_coordinated'] = False
								critical_errors_messages.append("This file has different coordinates than reference: " + str(file_band) + "\r\n")	
							else:
								file_info['is_coordinated'] = True							
						
						file_info['supported_format'] = False #initiate as false
						filename, file_extension = os.path.splitext(file_band)						
						#check if each raster's extension is within supported formats
						if (watermask_settings.supported_img_formats != ""):
							if filename != "" and file_extension != "":
								for supported_format in watermask_settings.supported_img_formats:
									if file_extension == supported_format:
										file_info['supported_format'] = True
						else:
							print("No supported extensions have been set in settings!")
						
						bands_detected = []						
						all_keyword_bands = watermask_settings.required_bands + watermask_settings.active_area_raster
						
						#detect the band in the filename
						for req_band in all_keyword_bands:
							if req_band in file_band:
								bands_detected.append(req_band)
						file_info['bands'] = bands_detected
						if len(bands_detected) > 1:
							print("Multiple bands for file " + str(file_band) + "detected: " + str(bands_detected))
							critical_errors_messages.append("Multiple bands for file " + str(file_band) + "detected: " + str(bands_detected) + "\r\n")
						elif len(bands_detected) == 0:
							#means unusable file due to bad naming
							print("No band for file " + str(file_band) + "detected.")
							critical_errors_messages.append("No band for file " + str(file_band) + "detected." + "\r\n")			
						
						each_folder_dict[file_band] = file_info 					
					dates_dict[date_folder] = each_folder_dict	
					#check if all required bands are found
					found_bands = [each_folder_dict[key]['bands'][0] for key in each_folder_dict.keys()]
					missing_bands = [item for item in watermask_settings.required_bands if item not in found_bands]
					if len(missing_bands) > 0:					
						print("The following bands are missing for folder " + str(date_folder) + ": " + str(missing_bands))
						critical_errors_messages.append("The following bands are missing for folder " + str(date_folder) + ": " + str(missing_bands))
					#now build the mapped dictionary				
		except:
			print ("Zip is corrupted!")
			with open(watermask_settings.data_directory + 'output/input_report.txt','w') as f:
				f.write("Zip is corrupted!")
				sys.exit(0)
				
	if watermask_settings.supported_img_formats == "":
		critical_errors_messages.append("Error! You must define the supported format(s) for the raster files!\r\n")
	else:
		information_messages.append("Supported raster formats: " + str(watermask_settings.supported_img_formats)+"\r\n")
		
	not_supported_format_files = [key1 for key1 in dates_dict.keys() for key2 in dates_dict[key1].keys() if dates_dict[key1][key2]['supported_format']== False]		
	if len(not_supported_format_files) == 0:
		information_messages.append("All rasters are in a supported format.\r\n")
	else:
		critical_errors_messages.append("Error! Rasters in unsupported format: " + str(not_supported_format_files) + "\r\n")

	with open(watermask_settings.data_directory + 'output/input_report.txt','a') as f:
		
		#write messages to txt file
		if len(information_messages) > 0:
			f.write("##General Information##\r\n")
			for inf in information_messages:
				f.write(inf)
		if len(warnings_messages) > 0:
			f.write("###Warnings###\r\n")
			for warn in warnings_messages:
				f.write(warn)
		if len(critical_errors_messages) > 0:
			f.write("###Critical Errors###\r\n")
			for crit in critical_errors_messages:
				f.write(crit)

	#create excel with rasters' info
	for key in dates_dict.keys():
		df = pd.DataFrame(dates_dict[key], columns = dates_dict[key].keys(), index = ['supported_format', 'bands', 'data_type', 'supported_data_type','is_coordinated', 'coordinates']).T
		df.columns = ['Supported Format', 'Bands', 'Data Type', 'Supported DType', 'Is Coordinated', 'Coordinates']
		writer = pd.ExcelWriter(watermask_settings.data_directory + 'output/rasters_info/' + key[:-1] + '.xlsx', engine = 'xlsxwriter')
		df.to_excel(writer, sheet_name='Rasters Info')
		
		writer.sheets['Rasters Info'].set_column(0, 0, 35)
		writer.sheets['Rasters Info'].set_column(1, 1, 16)
		writer.sheets['Rasters Info'].set_column(2, 2, 16)
		writer.sheets['Rasters Info'].set_column(3, 3, 9)
		writer.sheets['Rasters Info'].set_column(4, 4, 15)
		writer.sheets['Rasters Info'].set_column(5, 6, 13)
		writer.save()
	
	return len(critical_errors_messages), top_dirs, dates_dict

#compress the contents of a given directory to a zip file
def zip(src, dst):
    zf = zipfile.ZipFile(dst , "w", zipfile.ZIP_DEFLATED)
    abs_src = os.path.abspath(src)
    for dirname, subdirs, files in os.walk(src):
        for filename in files:
            absname = os.path.abspath(os.path.join(dirname, filename))
            arcname = absname[len(abs_src) + 1:]
            zf.write(absname, arcname)
    zf.close()
	
#these are the credentials for the connection (retry every 5 minutes if it fails)
def eo_db_connection():
	while True:
		try:
			cnx = mysql.connector.connect(host='160.40.50.179', port='3306', user='diaxeirisths', password='yj$qX9DSQ-GW^6?M', database='eoservices', charset='utf8mb4', use_unicode=True)			
			#cnx = mysql.connector.connect(host='localhost', port='3306', user='root', password='m3zmW5mT1oiO9vDl', database='eoservices', charset='utf8mb4', use_unicode=True)	
		except Exception as e:
			print(e)
			print("Failed to connect to database. Will try again in 5 minutes.")
			time.sleep(301)
			continue
		break	
	#http://160.40.51.218 (workstation pc)
	#host='localhost', port='3306', user='root', password='m3zmW5mT1oiO9vDl'	
	#host='160.40.50.179', port='3306', user='diaxeirisths', password='yj$qX9DSQ-GW^6?M'	  
	return cnx;

#update product watermask status (entered it here to avoid imports of previous folder level)
def update_product_watermask_status(AOI_query_id, begin_date, status_value):	
	cnx = eo_db_connection()
	
	cursor = cnx.cursor()	
	query = ("""UPDATE products_per_aoi SET calculated_watermask=%s WHERE area_of_interest_id=%s AND begin_position=%s""")
		
	try:	
		cursor.execute(query,(status_value, AOI_query_id, begin_date,))
		cnx.commit()
		print("Product watermask status updated.")
	except:
		cnx.rollback()
		print('update product watermask failed.')
	cnx.close()

