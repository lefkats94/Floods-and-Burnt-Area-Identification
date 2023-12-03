# -*- coding: utf-8 -*-
"""
 * Data and Information access services (DIAS) ONDA - For Space data distribution. 
 *
 * This file is part of CLEOPE (Cloud Earth Observation Processing Environment) software sources.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 
@author: GCIPOLLETTA

Main module to send OData API queries for download and order instances.



Afro Kita: 
From the below functions, the download_from_ENS() function was created, so as the products to be copied from ENS node. Some functions from CLEOPE free software are used in order for the specific 
product to be activated (in case it is not in the ODATA catalogue) and the pseudopath to be created. (In case the property: STATUS of the product is OFFLINE the activation is initiated and the product becomes online after 15-20 minutes. 
(This usually concerns products that have been generated some months before the current date.) When the product is ONLINE, the pseudopath will be "visible" though ONDA ENS and the product will be copied.
The find_and_copy_tile() function (used by download_from_ENS()) copies the .SAFE product from ENS node locally. 

"""
import requests, json, glob, os, zipfile, io, shutil, tarfile
import IPython
from IPython.display import display
import pandas as pd
import numpy as np
import ipywidgets as widgets
import datetime, time
import threading
import os
import subprocess
from tqdm import tqdm_notebook
import warnings

du_thresh = 5 # GiB threshold 

def get(url):
    """Send and get the url to query products using OData API
    
    Parameters:
        url (str): OData url query
    
    Returns: query results (pandas dataframe)
    """
    res = requests.get(url)
    val = res.json()
    n = len(val["value"])
    fields = ["id","name","pseudopath","beginPosition","footprint","size","offline"]
    dataframe = pd.DataFrame(np.nan,index=range(n), columns=fields)
    for i in range(n):
        dataframe.iloc[i,0] = val["value"][i]["id"]
        dataframe.iloc[i,1] = val["value"][i]["name"]
        dataframe.iloc[i,2] = val["value"][i]["pseudopath"].split(",")[0]
        dataframe.iloc[i,3] = val["value"][i]["beginPosition"]
        dataframe.iloc[i,4] = val["value"][i]["footprint"]
        dataframe.iloc[i,5] = val["value"][i]["size"]
        dataframe.iloc[i,6] = val["value"][i]["offline"]
    return dataframe

def order_product(username, password, uuid):
    """Send POST OData API to retrieve an archived product
    
    Parameters:
        username (str): ONDA username
        password (str): ONDA user password
        uuid (str): unique product identifier (from function: get_uuid)
    
    Return: OData POST request feedback (dict)    
    """
    if username and password:
        headers = {
            'Content-Type': 'application/json',
        }
        auth = (username, password)
        response = requests.post('https://catalogue.onda-dias.eu/dias-catalogue/Products('+uuid+')/Ens.Order',
                                 headers=headers, auth=auth)
        return response.json()

def get_uuid(product):
    """Get product unique identifier from product name
    
    Parameters:
        product (str): product name with its own extension explicit
    
    Returns: product uuid (str)
    Raise exception for invalid URLs.
    
    """
    if product.startswith("LC08"):
        if product.endswith(".tar.gz"):
            product = product
        else:
            product = product+".tar.gz"
    elif product.startswith("S"):
        if product.endswith(".zip"):
            product = product
        else:
            product = product+".zip"
    url = "https://catalogue.onda-dias.eu/dias-catalogue/Products?$search=%22"+str(product)+"%22&$top=10&$format=json"
    res = requests.get(url)
    try:
        return res.json()["value"][0]["id"]
    except:
        raise Exception("Invalid URL: Invalid product name.")

def get_my_product(product):
    """Search for products given the product name
    
    Parameters:
        product (str): product name
    
    Return: query results (pandas dataframe)
    Raise exception for invalid URLs. 
    """
    if product.endswith(".tar.gz"):
        product = product.split(".")[0]
    if product.startswith("S"):
        if product.endswith(".zip"):
            product = product
        else:
            product = product+".zip"
    url = "https://catalogue.onda-dias.eu/dias-catalogue/Products?$search=%22"+str(product)+"%22&$top=10&$format=json"
    res = requests.get(url)
    val = res.json()
    fields = ["id","name","pseudopath","beginPosition","footprint","size","offline"]
    try:
        dataframe = pd.DataFrame(np.nan,index=range(1), columns=fields)
        dataframe.iloc[0,0] = val["value"][0]["id"]
        dataframe.iloc[0,1] = val["value"][0]["name"]
        dataframe.iloc[0,2] = val["value"][0]["pseudopath"].split(",")[0]
        dataframe.iloc[0,3] = val["value"][0]["beginPosition"]
        dataframe.iloc[0,4] = val["value"][0]["footprint"]
        dataframe.iloc[0,5] = val["value"][0]["size"]
        dataframe.iloc[0,6] = val["value"][0]["offline"]
        return dataframe
    except:
        raise Exception("Empty dataframe: Invalid product name.")

def check_out_product(product):
    """Check if product has been properly restored in the ENS (ONDA Advanced API)
    
    Parameters:
        product (str): product name
    
    Return: exit status (int)
    """
    pseudopath_res = get_my_product(product).iloc[0,2]
    link = "/local_path/"+pseudopath_res+"/"+product
    if os.path.exists(link):
        print("All done! Check out product:\n%s"%link)
        return 0
    else:
        print("Requested product not found.")
        return 1
    

# progress bar
def work(progress,delta):
    """Update a progress bar as a background process
    
    Parameters:
        progress (widget): tdqm notebook widget
        delta (datetime): time elapse
        
    Return: None    
    """
    total = int(delta)+1 
    for i in range(total):
        time.sleep(1) # tick upgrade in seconds
        progress.value = float(i+1)/total

# ordering API can manage thread instance 
def order(product, username, password):
    """Order an archived product in the background, displaying a progress bar updating untill complete restoration
    
    Parameters:
        product (str): product name
        username (str): ONDA username
        password (str): ONDA user password
    
    Return: product main attributes (pandas dataframe)
    """
    df = get_my_product(product)
    display(df)
    if df.iloc[0,6] == True:
        uuid = df.iloc[0,0]
        print("UUID to order: %s"%uuid)
        r = order_product(username,password,uuid)
        s = datetime.datetime.strptime(r["EstimatedTime"],'%Y-%m-%dT%H:%M:%S.%fZ')
        # removed additional 10s of waiting
        delta = datetime.datetime.timestamp(s)-datetime.datetime.timestamp(datetime.datetime.utcnow())#+600. # time elapse estimate to upgrade bar, 10 minutes added to wait for ENS refresh
        progress = widgets.FloatProgress(value=0.0, min=0.0, max=1.0, description="Ordering")
        thread = threading.Thread(target=work, args=(progress,delta,))
        tot_elaps_time = datetime.datetime.timestamp(s)#+600
        estimated_timeout = datetime.datetime.utcfromtimestamp(tot_elaps_time) 
        print("Instance is %s.\nEstimated time out %s UTC"%(r["Status"],estimated_timeout.strftime("%d-%b-%Y (%H:%M:%S.%f)")))
#         print("Instance is %s.\nEstimated time out %s UTC"%(r["Status"],datetime.datetime.strftime(s,'%H:%M:%S')))
#         print("Wait for further 10 minutes to be sure ENS is properly refreshed.")
        display(progress)
        thread.start()
    else:
        print("Warning! Products is already avaliable.\nCheck it out at:\n%s"%(os.path.join(df.iloc[0,2],product)))
    return df,delta
             
def pseudopath(dataframe):
    """Create the product pseudopath so as to access the product directly from ENS.
    
    Parameters: 
        dataframe (pandas dataframe): product main attributes queried via OData
    Return: pseudopaths list (list)
    """
    if dataframe.iloc[:,-1].values.any()==True:
        print("Warning! Some products in your dataframe are archived! Trigger an order request first. \nCheck out ORDER notebook to discover how to do it!\n") 
    pp = ["/local_path/"+os.path.join(dataframe.iloc[i,2],dataframe.iloc[i,1]) for i in range(dataframe.shape[0])]
    return pp
              

def write_list(item,filename=os.path.join(os.getcwd(),"list_local.txt")):
    """Save a list with all the downloaded product location within users own workspace. The output list is generated in the current working directory by default and named 'list_local.txt' 
    
    Parameters:
        item (str): downloaded item full path location within CLEOPE workspace
        filename (str): output file full path location; default: ./list_local.txt
        
    Return: None    
    Note: items are appended to file per each download.
    """
    with open(filename,"a+") as f:
        f.write(item+"\n")
        print("%s updated"%filename)

def make_dir(dirname):
    """Create a brand new directory in the current working directory.
    
    Parameters:
        dirname (str): directory name
    
    Return: exit status
    """
    try:
        os.mkdir(dirname)
    except FileExistsError:
        return 0      
        



def download_from_ENS(product, username, password, dest_path):
    """Main function to download products via ENS. The function "download" from CLEOPE  directory has been changed. After the order of the data, the pseudopath function runs to return te pseudopath of the product. And then the function for copying the file from ENS will be used.

    Parameters:
        product (str): product name
        username (str): ONDA user name
        password (str): ONDA user password
        dest_path (str): destination path for the final .SAFE product
    Return: exit status (int)
    Raise an exception in case of disk full.

    """
    dest = dest_path
    if not os.path.exists(dest):
        make_dir(dest)
    dataframe = get_my_product(product)
    uuid = dataframe.iloc[:, 0].values[0]
    curl = "https://catalogue.onda-dias.eu/dias-catalogue/Products(" + uuid + ")/$value"
    con = check_if_online(product, username, password)  # check if online
    if con > 0:
        print("Please wait until product restoration. Download will re-start automatically.")
        time.sleep(con + 60)  # Odata time lapse + 1 minute
        # then check if restored
        df = get_my_product(product)
        if df["offline"].values == True:
            warnings.warn(
                "Product %s is still archived. Something went wrong, retry the download in a few minutes." % product)
            return 1
    #remove_item(dest, product)  # check if products already exists in folder and delete it
    print("Product is online. The pseudopath will be created so as to be copied from ENS")
    pseudopath_res = pseudopath(dataframe=dataframe)
    print(f'The pseudopath is {pseudopath_res}')
    res = False
    try:
        res = find_copy_and_extract_tile(pseudopath_res[0], dest, product)
        #print("The product downloaded and extracted successfully from ENS.")
    except:
        print("The product will be downloaded form the ONDA catalogue through eodag.")
    return res



def find_copy_and_extract_tile(pseudopath, dest, product):
    """Given the pseudopath of the product, checks that the path exists. If no error is returned copies .value file and extracts it to the destination
        Parameters:
            pseudopath (str): product ENS pseudopath
            dest (str): destination path for the final .SAFE product
            product (str): product name
        Raise an exception in case of Remote-IO error or the path was not found

    """
    flag = False
    if os.path.exists(pseudopath):
        print(f"The path to the product {pseudopath} exists!")
    else:
        print(f'The path to the product {pseudopath} does not exist. The product will be downloaded from ONDA catalogue.')
        return False
    try:
        #cp
        fileValue = pseudopath + "/.value"
        file = os.path.join(dest, product + '.zip')
        start = time.time()
        subprocess.call(["timeout", str(600), "cp", fileValue, file])
        #runtime = time.time() - start
        size = os.path.getsize(fileValue)
        print("Product copied successfully size: %f" %size)
    except OSError as error:
        print(error + ' The product will be downloaded from ONDA catalogue.')
        return False
    except:
        print('Error occurred when trying to copy the product: %s' %product)
        return False
    #Extract zip file
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(dest)
        zip_ref.close()
        print("%s successfully copied and extracted "%product)
        flag = True

    except:
        print(f'Exception occurred when trying to extract the zip product : %s' % product)
        return False
    if flag:
        remove_zip(os.path.join(dest, product + '.zip'))
    return True


def remove_zip(item):
    """Remove a file or a directory and its related children if exists
    
    Parameters:
        item (str): full path location of file/directory to be removed
        
    Return: None    
    """
    file = glob.glob(item)
    if file:
        os.remove(file[0])
    else:
        print("%s not found"%item)

        
def check_if_online(product,username,password):
    """Call the function: order to retrieve an archived product when attempting a download it.
    
    Parameters:
        product (str): product name
        username (str): ONDA username
        password (str): ONDA user password
    
    Return: time elapse to restore product (float) if product is offline, otherwise an exit status (int)
    """
    df = get_my_product(product)
    if df["offline"].values==True:
        warnings.warn("Product %s is archived"%product)
        df,d = order(product,username,password)
        return d
    else:
        return 0
        
