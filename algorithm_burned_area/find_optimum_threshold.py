import numpy as np
import math
from skimage.measure import regionprops
from algorithm_burned_area.adaptive_thresholding import adaptive_thresholding 
# import watermask_settings

import pickle
import time

#some image, the mask, the segmented image, colorRGB
def find_optimum_threshold(SWIR_SCALED, SWIR_MASK, labels, ACTIVE_AREA_MASK):
	
	ACTIVE_AREA_MASK_copy_cloud = None
	SWIR_SCALED_copy_cloud = None
	#assuming that SCL band is provided as active_area_mask, then exclude the shadows of the clouds (value 3) from calculation of centroids
	if ACTIVE_AREA_MASK is not None:
		print("Cloud shadows are filtered from active_area_mask in find_optimum_threshold")
		SWIR_SCALED_copy_cloud = np.copy(SWIR_SCALED)
		ACTIVE_AREA_MASK_copy_cloud = np.copy(ACTIVE_AREA_MASK)
		#SWIR_SCALED_copy_cloud[ACTIVE_AREA_MASK == 3] = 0		
		#ACTIVE_AREA_MASK_copy_cloud[np.logical_or(ACTIVE_AREA_MASK == 3, ACTIVE_AREA_MASK == 2)] = 0
		
		SWIR_SCALED_copy_cloud = np.nan_to_num(SWIR_SCALED)


	#convert to 1D: sized
	SWIR_MASK_reshaped = SWIR_MASK.flatten();
	print ("Number_of_labels: " + str(int(np.amax(labels))))
	
	labels_reshaped = labels.flatten().astype(int);
			
	good_labels = []

	#if temp_calculate_labels == 1:		
	#selection of segments with high percentage inundated pixels
	#Start calculation of Good Labels	
	print("Start calculating good labels")
	labels_start_time = time.time()
	
	print ("Number_of_labels: " + str(int(np.amax(labels))))
	for i in range(1, int(np.amax(labels))):	
		a2 = np.where(labels_reshaped==i)   
		#the height dimension size of the a2 array	
		threshold = np.sum(SWIR_MASK_reshaped[a2[0]])// len(a2[0])
		#print(threshold)
		if threshold != 0 and threshold != 1:
			print('to brika')
		# if threshold < 0.5:
		if threshold < 0.3:
			good_labels.append(i)
			#print("Good Label Found")
	# watermask_settings.exec_time_good_labels = time.time() - labels_start_time
	# print("--- Good labels calculated in %s seconds ---" % watermask_settings.exec_time_good_labels)
		#End of calculation of good labels
		
	#	with open(temp_good_labels_filename+'.bin', 'wb') as f:
	#		pickle.dump(good_labels, f)
	#		print("Good  labels saved as: " + temp_good_labels_filename+'.bin')
	#else:
	#	with open(temp_good_labels_filename+'.bin', 'rb') as f:
	#		good_labels = pickle.load(f)
	#	print("Good labels were loaded from file: " + temp_good_labels_filename+'.bin')
		
	start_time_thresholds = time.time()
	
	all_mode = []
	#start enumeration from 1
	for my_count,k_each_good_label in enumerate(good_labels, 1):
		#this contains the centroid #its always zero index
		measurements = regionprops((labels==k_each_good_label).astype(int))	
			
		if len(measurements) == 1:
			#if active area mask is provided, then find thresholds only for centroids that are on active area		
			if ACTIVE_AREA_MASK_copy_cloud is not None:
				#print("Good Labels1")
				if ACTIVE_AREA_MASK_copy_cloud[int(math.floor(measurements[0].centroid[0])), int(math.floor(measurements[0].centroid[1]))] > 0:
					#here returns the threshold of the patch(es) for the specific centroid				
					thresholds = adaptive_thresholding(SWIR_SCALED_copy_cloud, np.floor(measurements[0].centroid), 10)
							
					all_mode_sublist = []
					if (len(thresholds) > 0 and thresholds[0] != 500):
				
						#0: thresholds
						all_mode_sublist.append(np.median(thresholds))									
						#1: x
						all_mode_sublist.append(math.floor(measurements[0].centroid[1]))
						#2: y							
						all_mode_sublist.append(math.floor(measurements[0].centroid[0]))
						#append all in a single row
						all_mode.append(all_mode_sublist)
			#else find thresholds for all the centroids			
			else:
				#print("Good Labels2")
				#here returns the threshold of the patch(es) for the specific centroid				
				thresholds = adaptive_thresholding(SWIR_SCALED, np.floor(measurements[0].centroid), 10)
						
				all_mode_sublist = []
				if (len(thresholds) > 0 and thresholds[0] != 500):
			
					#0: thresholds
					all_mode_sublist.append(np.median(thresholds))									
					#1: x
					all_mode_sublist.append(math.floor(measurements[0].centroid[1]))
					#2: y							
					all_mode_sublist.append(math.floor(measurements[0].centroid[0]))
					#append all in a single row
					all_mode.append(all_mode_sublist)
				
	# watermask_settings.exec_time_threasholds = time.time() - start_time_thresholds
	# print("--- Inside Thresholds calculated in %s seconds ---" % (watermask_settings.exec_time_threasholds))
	
	np_thresholds = np.array(all_mode)
	print(len(np_thresholds))
	
	#check if optimum threashold can be calculated
	#print(np_thresholds[:,0])
	if (len(np_thresholds) > 0):
		optimum_threshold = np.median(np_thresholds[:,0])
	else:
		optimum_threshold = -1
			
	return optimum_threshold
