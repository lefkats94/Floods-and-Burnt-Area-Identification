from math import log
import numpy as np

'''
 MinCE is a function for thresholding using Minimum Cross Entropy
 The code calculates:

input = I ==> Image in gray level 
 output =
           I1 ==> binary image
           threshold ==> the threshold choosen by MinCE
'''
def minCE(img_arr, h_flat):

        m,n = img_arr.shape
        
        hn=(h_flat)/float(n*m)
                
        imEntropy=0.0
        for i in range (1,257):
                imEntropy = imEntropy+(i*hn[i-1]*log(i))
        CE = []
        
        for t in range (1,257):
                #moyenne de Low range image
                lowValue = 0
                lowSum = 0
                for i in range (1,t+1):
                        lowValue=lowValue+(i*hn[i-1])
                        lowSum=lowSum + hn[i-1]
                if lowSum > 0:
                        lowValue = lowValue / float(lowSum)
                        
                else:
                        lowValue=1
                #moyenne de High range image
                highValue = 0;
                highSum = 0;
                for i in range (t+1,257):
                        highValue=highValue+(i*hn[i-1])
                        highSum=highSum+hn[i-1]
                if highSum>0:
                        highValue=highValue/float(highSum)
                else:
                        highValue=1;
				#Entropy of low range 
                lowEntropy=0;
                for i in range (1,t+1):
                        lowEntropy=lowEntropy+(i*hn[i-1]*log(lowValue))
                #Entropy of high range 
                highEntropy=0;
                for i in range (t+1,257):
                        highEntropy=highEntropy+(i*hn[i-1]*log(highValue))
                #Cross Entropy 
                CE.append(imEntropy - lowEntropy - highEntropy)
        
        #choose the best threshold
        D_min = CE[0]
        entropie = []
        entropie.append(D_min)
        threshold = 0
	
        for t in range (2,257):
                entropie.append(CE[t-1])
                if entropie[t-1] < D_min:
                        D_min=entropie[t-1]
                        threshold = t-1
               
        I1 = np.zeros((n,m)) 
        I1[img_arr<threshold] = 0;
        I1[img_arr>threshold] = 255;
        
        return threshold, I1