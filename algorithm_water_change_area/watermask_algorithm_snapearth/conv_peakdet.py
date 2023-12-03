#the matlab's peakdet conversion

#@mfunction("maxtab, mintab")
import numpy as np

def peakdet(v=None, delta=None, x=None):
    
    '''
    PEAKDET Detect peaks in a vector
            [MAXTAB, MINTAB] = PEAKDET(V, DELTA) finds the local
            maxima and minima ("peaks") in the vector V.
            MAXTAB and MINTAB consists of two columns. Column 1
            contains indices in V, and column 2 the found values.
          
            With [MAXTAB, MINTAB] = PEAKDET(V, DELTA, X) the indices
            in MAXTAB and MINTAB are replaced with the corresponding
            X-values.
    
            A point is considered a maximum peak if it has the maximal
            value, and was preceded (to the left) by a value lower by
            DELTA.
    '''
    maxtab = []
    mintab = []

    v = np.array(v)
       
    #if args < 3 actually
    if x is None:
        x = range(0, len(v))
        x = np.array(x)
    else:
        if len(v) != len(x):
            print('Input vectors v and x must have same length')
            quit()
    delta = np.array(delta)
    
    if (delta.size)>1:
        print('Input argument DELTA must be a scalar')
        quit()
    if delta <= 0:
        print("Input argument DELTA must be positive")
        quit()
    
    mn = float('Inf')
    mx = -float('Inf')

    mnpos = float('NaN')
    mxpos = float('NaN')

    lookformax = 1

    for i in range (1,len(v)+1):
      temp = v[i-1];
      if temp > mx:
        mx = temp
        mxpos = x[i-1]
      if temp < mn:
        mn = temp
        mnpos = x[i-1]

      
      if lookformax:
        if temp < mx - delta:
            temp_maxtab = []
            temp_maxtab.append(mxpos)
            temp_maxtab.append(mx)
            maxtab.append(temp_maxtab)
            mn = temp
            mnpos = x[i-1]
            lookformax = 0
          
      else:
          if temp > mn + delta:
            temp_mintab = []
            temp_mintab.append(mnpos)
            temp_mintab.append(mn)
            mintab.append(temp_mintab)  
            mx = temp
            mxpos = x[i-1]
            lookformax = 1

    return maxtab, mintab
