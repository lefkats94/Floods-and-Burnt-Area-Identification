from algorithm_water_change_area.watermask_algorithm_snapearth import masks_calculation_new
from  algorithm_water_change_area.watermask_algorithm_snapearth import watermask_settings
from algorithm_water_change_area.watermask_algorithm_snapearth import my_functions as myfun


def start_watermask(product_bands_directory, product_begin_date, running_modes):
	#critical_errors, top_dirs, dates_dict = myfun.check_bands_rasters(zip_input_filename)
	watermask_settings.init(running_modes)

	#if critical_errors > 0:
	#		print(str(critical_errors) + " critical errors detected! Please check the file \"input_report.txt\" at:\n" + watermask_settings.data_directory + "output/")
	#		sys.exit(0)

	watermask_settings.exec_time_mean_shift_segmentation = 0
	watermask_settings.exec_time_good_labels = 0
	watermask_settings.exec_time_threasholds = 0
	masks_calculation_new.calculate_watermasks(product_bands_directory, product_begin_date)

	#compress results into a single zip
	data_directory_output =  product_bands_directory + 'output-watermask/'
	myfun.zip(data_directory_output, product_bands_directory + "output_watermask.zip")
