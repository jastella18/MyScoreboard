import requests
import time

api_url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

class API:
    def fetch_nfl_scores():
        response = requests.get(api_url)
        scores_data = response.json()
        return scores_data

    def process_event(event):
        status_details = event["competitions"][0]["status"]
        status = status_details["type"]["description"]
        clock = status_details.get("displayClock", "")
        quart = status_details.get("period", "")
        home_info = event["competitions"][0]["competitors"][0]
        away_info = event["competitions"][0]["competitors"][1]
        leaders_info=event["competitions"][0]["leaders"]
        home_team = {
            "name": home_info["team"]["abbreviation"],
            "score": home_info["score"]
        }
        away_team = {
            "name": away_info["team"]["abbreviation"],
            "score": away_info["score"]
        }
        
        leaders = {
            "qb": leaders_info[0]["leaders"][0]["athlete"]["shortName"],
            "pyds": leaders_info[0]["leaders"][0]["displayValue"],
            "rb": leaders_info[1]["leaders"][0]["athlete"]["shortName"],
            "ruyds": leaders_info[1]["leaders"][0]["displayValue"],
            "wr": leaders_info[2]["leaders"][0]["athlete"]["shortName"],
            "reyds": leaders_info[2]["leaders"][0]["displayValue"]
        }
        
        return {
            "status": status,
            "clock": clock,
            "quarter": quart,
            "home_team": home_team,
            "away_team": away_team,
            "leaders": leaders
            # Add more fields as needed
        }

    def get_all_events_data():
        scores_data = API.fetch_nfl_scores()
        events = scores_data.get('events', [])
        all_events_data = [API.process_event(event) for event in events]
        return all_events_data
    
#TESTING PURPOSES

def main():
    while True:
        try:

            # Extract relevant information from the API response
            all_events_data = API.get_all_events_data()

            time.sleep(10)  # Update scores every 60 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Retry after 60 seconds if an error occurs

if __name__ == "__main__":
    main()
