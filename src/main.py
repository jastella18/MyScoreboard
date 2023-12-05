import requests
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def fetch_nfl_scores(api_url):
    response = requests.get(api_url)
    return response.json()

def display_scores(matrix, events):
    offscreen_canvas= matrix.CreateFrameCanvas()
    font = graphics.Font()
    color = graphics.Color(255,0,0)

    matrix.Clear()
    matrix.Fill(255, 255, 255)  # Set background color (white)
    matrix.DrawText(offscreen_canvas, font, 10, 16, (255, 0, 0), "NFL Scores")


    y_position = 32
    for event in events:
        home_info = event["competitions"][0]["competitors"][0]
        hteam_name = home_info["team"]["abbreviation"]
        away_info = event["competitions"][0]["competitors"][1]
        ateam_name = away_info["team"]["abbreviation"]

        home_score = home_info["score"]
        away_score = away_info["score"]

        score_text = f"{hteam_name} {home_score} - {away_score} {ateam_name}"
        print(score_text)

        time.sleep(.5)
        matrix.DrawText(offscreen_canvas, font, 10, y_position, (255, 255, 255), score_text)
        y_position += 16

def main():
    # Configure RGB Matrix
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    matrix = RGBMatrix(options=options)
    #API endpoint for real-time NFL scores (replace with your API URL)
    api_url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

    while True:
        try:
            # Fetch NFL scores from the API
            scores_data = fetch_nfl_scores(api_url)

            # Extract relevant information from the API response
            events = scores_data.get('events', [])

            # Display scores on the LED matrix
            display_scores(matrix,events)

            time.sleep(1)  # Update scores every 60 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Retry after 60 seconds if an error occurs

if __name__ == "__main__":
    main()