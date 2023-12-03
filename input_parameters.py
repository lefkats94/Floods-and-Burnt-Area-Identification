def init(params_dict={}):
    
    if params_dict['source'] =='earthpress':
        init_earthpress(params_dict)
    else:
        init_vqa(params_dict)

def init_earthpress(params_dict={}):
    global lat
    global lon
    global date
    global event
    global event_id
    global source
    global output_id
     
    lat = params_dict['lat']
    lon = params_dict['lon'] 
    date = params_dict['date']
    event = params_dict['event']
    event_id = params_dict['event_id'] 
    source = params_dict['source'] 
    output_id = params_dict['output_id'] 
    

def init_vqa(params_dict={}):
    global event
    global source
    global output_id
    global product_id
    
    event = params_dict['event']
    product_id = params_dict['product_id'] 
    source = params_dict['source'] 
    output_id = params_dict['output_id'] 
    

    
       