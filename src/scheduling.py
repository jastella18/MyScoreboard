import requests
from nfl_api import API
from datetime import datetime

all_events_data = API.get_all_events_data()
now = datetime.now()
current_day = now.strftime("%A").lower()

def displayDay(){
    
}
            
                    