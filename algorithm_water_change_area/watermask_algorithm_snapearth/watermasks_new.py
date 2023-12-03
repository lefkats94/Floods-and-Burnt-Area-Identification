import masks_calculation_new as masks_calculation_new
import watermask_settings as watermask_settings
import zipfile
import sys
import os
import my_functions as myfun
import getopt

def main(argv):

	product_bands_directory = ''
	product_begin_date = ''
	
	try:
		opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
	except getopt.GetoptError:
		print('watermasks_new.py -i <product_bands_directory> -o <product_begin_date>')
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print('watermasks_new.py -i <product_bands_directory> -o <product_begin_date>')
			sys.exit()
		elif opt in ("-i", "--ifile"):
			product_bands_directory = arg
		elif opt in ("-o", "--ofile"):
			product_begin_date = arg
	print('Input file is "', product_bands_directory)
	print('Output file is "', product_begin_date)
	
	#critical_errors, top_dirs, dates_dict = myfun.check_bands_rasters(zip_input_filename)
	watermask_settings.init()

	#if critical_errors > 0:
	#		print(str(critical_errors) + " critical errors detected! Please check the file \"input_report.txt\" at:\n" + watermask_settings.data_directory + "output/")
	#		sys.exit(0)

	watermask_settings.exec_time_mean_shift_segmentation = 0
	watermask_settings.exec_time_good_labels = 0
	watermask_settings.exec_time_threasholds = 0
	masks_calculation_new.calculate_watermasks(product_bands_directory, product_begin_date)

	#compress results into a single zip
	data_directory_output =  product_bands_directory + 'output-watermask2/'
	myfun.zip(data_directory_output, product_bands_directory + "output_watermask.zip")
	
if __name__ == "__main__":
   main(sys.argv[1:])