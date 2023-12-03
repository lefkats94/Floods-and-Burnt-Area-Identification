import numpy as np
import algorithm_burned_area.my_functions as myfun
import algorithm_burned_area.conv_minCE as minc
from algorithm_burned_area import conv_peakdet


def Otsu(sub_patch):
	[hist, _] = np.histogram(sub_patch, bins=256, range=(0, 255))
	# Normalization so we have probabilities-like values (sum=1)
	hist = 1.0*hist/np.sum(hist)

	val_max = -999
	thr = -1
	for t in range(1,255):
		# Non-efficient implementation
		q1 = np.sum(hist[:t])
		q2 = np.sum(hist[t:])
		m1 = np.sum(np.array([i for i in range(t)])*hist[:t])/q1
		m2 = np.sum(np.array([i for i in range(t,256)])*hist[t:])/q2
		val = q1*(1-q1)*np.power(m1-m2,2)
		if val_max < val:
			val_max = val
			thr = t

	print("Threshold: {}".format(thr))
	
	return thr
	
def otsu3(gray):
	pixel_number = gray.shape[0] * gray.shape[1]
	mean_weigth = 1.0/pixel_number
	his, bins = np.histogram(gray, np.arange(0,257))
	final_thresh = -1
	final_value = -1
	intensity_arr = np.arange(256)
	for t in bins[1:-1]: # This goes from 1 to 254 uint8 range (Pretty sure wont be those values)
		pcb = np.sum(his[:t])
		pcf = np.sum(his[t:])
		Wb = pcb * mean_weigth
		Wf = pcf * mean_weigth

		mub = np.sum(intensity_arr[:t]*his[:t]) / float(pcb)
		muf = np.sum(intensity_arr[t:]*his[t:]) / float(pcf)
		#print mub, muf
		value = Wb * Wf * (mub - muf) ** 2

		if value > final_value:
			final_thresh = t
			final_value = value
	final_img = gray.copy()
	#print(final_thresh)
	final_img[gray > final_thresh] = 255
	final_img[gray < final_thresh] = 0
	return final_thresh

def adaptive_thresholding(VH_demek_SLC, Central_pixels, margin):
	
	thresholds = []		
	y_value=int(Central_pixels[0]) 
	x_value=int(Central_pixels[1]) 
	
	patch_i=20
	patch_x_center = patch_i*margin
	patch_y_center = patch_i*margin
	
	#####
	if ((y_value-patch_i*margin) >= 0 and (y_value+patch_i*margin) < (VH_demek_SLC.shape[0]) and (x_value-patch_i*margin) >= 0 and (x_value+patch_i*margin) < (VH_demek_SLC.shape[1])):	
		
		whole_patch = VH_demek_SLC[(y_value-patch_i*margin):(y_value+patch_i*margin+1), (x_value-patch_i*margin):(x_value+patch_i*margin+1)]
	
		for i in range (1, patch_i+1):
			
			sub_patch = whole_patch[(patch_y_center-i*margin):(patch_y_center+i*margin+1), (patch_x_center-i*margin):(patch_x_center+i*margin+1)]
			a = myfun.flat_hist_optimized(sub_patch.astype(int))	
			
			#if histogram is completely zeroed					
			if np.sum(a) == 0:			
				each_threshold = []
				each_threshold.append(500)
				thresholds.append(each_threshold)				
				return thresholds #, thresholds2
			
			maxtab, mintab = conv_peakdet.peakdet(a, np.mean(a))
			
			#if it has exactly two peaks
			if len(maxtab) == 2:			
				# if watermask_settings.MCET_or_OTSU_or_Avg==1:
				if True:
					threshold_by_minCE, someImage = minc.minCE(sub_patch, a)	
				elif watermask_settings.MCET_or_OTSU_or_Avg==2:									
					threshold_by_minCE = Otsu(sub_patch)
					#print ("Thres1: " + str(threshold_by_minCE))
					#total_pixels=sub_patch.shape[0]
					#total_pixels = sub_patch.size[0] * sub_patch.size[1]
					#bins1 = range(0,257)
					#img_histogram = np.histogram(sub_patch, bins1)
					#
					#thresh1 =  otsu2(img_histogram, total_pixels)
					#ret,thr = cv2.threshold(sub_patch, 0, 255, cv2.THRESH_OTSU)
					#thresh2=otsu3(sub_patch)
					#print ("Thre2: " + str(thresh2))
				#if calculated threshold is valid (between the two peaks)
				#if threshold_by_minCE > maxtab[0][0] and threshold_by_minCE < maxtab[1][0]:					
				thresholds.append(threshold_by_minCE)						
					
	return thresholds