from datetime import datetime
import string
from flask import Flask, request
from flask_cors import CORS
import redis
from rq import Queue
import string
import random
import settings
import input_parameters
from tasks import shared_tasks
from tasks import main_tasks 

app = Flask(__name__)
CORS(app, supports_credentials=True)

r = redis.Redis()
q = Queue(connection=r)

@app.route("/snapearth")
def snapearth():

    """

    Parameters:
            lat (float): D
            lon (float): D
            date (float): D
            event (str): D
            event_id (str): D
            source (str): D
            product_id (str): D

    An example of an API Request is the following:

    http://ip:port/snapearth?lat=39.019400000000005&lon=26.207842&\
        date=1658572087.664&event=fire&id=58946&source=earthpress

    """
    # Reading request parameters into variables 
    lat = request.args.get('lat', type=float) # Latitude of the event location
    lon = request.args.get('lon', type=float) # Longitude of the event location
    date = request.args.get('date', type=float) # date of the event location
    event = request.args.get('event', type=str) # Event type. Can be either 'fire' or 'flood'.
    event_id = request.args.get('id', type=int) # Event id.
    source = request.args.get('source', type=str) # Source. Can be either 'earthpress' or 'VQA'
    product_id = request.args.get('product_id', type=str) # Product id
    
    response_data = shared_tasks.validate_parameters(event, source, lat, lon, date, product_id)
    output_id = response_data['task_id']
    
    
    #Generating task and adding it to the queue
    if source == 'earthpress':
        date_str = datetime.utcfromtimestamp(date).strftime("%Y-%m-%d") 
        input_params = {'lat': lat, 'lon':lon, 'date': date_str, 'event':event, 'event_id': event_id, 'source':source, 'output_id': output_id}
        job = q.enqueue(main_tasks.main_earthpress_task, input_params)
        
    else:
        input_params = {'product_id': product_id, 'event':event, 'source': source, 'output_id': output_id}
        job = q.enqueue(main_tasks.main_vqa_task, input_params)
        
    return response_data 
     
if __name__ == '__main__':
    
    app.run(host=settings.host, port=settings.port, debug=settings.debug)



