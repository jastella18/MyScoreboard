import requests
from api.nfl_api import nfl_api as API
from datetime import datetime

all_events_data = API.get_all_events_data()
now = datetime.now()
current_day = now.strftime("%A").lower()

def displayDay(){
    
}
            
                    