import os
import watermasks_new

# declare a  filepath a run WaterMasks module for all folder/dates included in the filepath
#
filepath = "/media/sismanism/My Passport/EOS/NewLife4Drylands/test_floating"

folder_list = os.listdir(filepath)
try:
    folder_list.pop(folder_list.index('clouds'))
except:
    pass

for each_folder in folder_list:
    try:
        watermasks_new.main(["-i", os.path.join(filepath, each_folder)+"/"])
    except:
        pass