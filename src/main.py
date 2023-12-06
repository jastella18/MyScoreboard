import requests
import time
from rgbmatrix import graphics,RGBMatrix, RGBMatrixOptions
from PTL import Image
from io import BytesIO


def fetch_nfl_scores(api_url):
    response = requests.get(api_url)
    return response.json()

def get_logo(url):
    response = requests.get(url)
    image = BytesIO(response.content)
    return Image.open(image)

def display_scores(matrix, events):
    offscreen_canvas= matrix.CreateFrameCanvas()
    font = graphics.Font()
    font.LoadFont('/home/jastella/sportsdisplay/MyNflScoreboard/rpi-rgb-led-matrix/rpi-rgb-led-matrix/fonts/4x6.bdf')
    color = graphics.Color(255,0,0)

    matrix.Clear()
    graphics.DrawText(offscreen_canvas, font, 10, 16, color , "NFL Scores")
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    time.sleep(2)

    matrix.Clear()
    y_position = 32
    for event in events:
        offscreen_canvas = matrix.CreateFrameCanvas()
        matrix.Clear()

        home_info = event["competitions"][0]["competitors"][0]
        hteam_name = home_info["team"]["abbreviation"]
        hteam_logo = home_info["team"]["logo"]

        away_info = event["competitions"][0]["competitors"][1]
        ateam_name = away_info["team"]["abbreviation"]
        ateam_logo = away_info["team"]["logo"]

        home_score = home_info["score"]
        away_score = away_info["score"]


        hlogo = get_logo(hteam_logo)
        rgbhlogo = graphics.Image()
        rgbhlogo.SetImage(hlogo)

        alogo = get_logo(ateam_logo)
        rgbalogo = graphics.Image()
        rgbalogo.SetImage(alogo)

        score_text = f"{hteam_name}{home_score} - {away_score} {ateam_name}"
        print(score_text)

        graphics.DrawImage(offscreen_canvas,rgbhlogo,5,16)
        graphics.DrawImage(offscreen_canvas,rgbalogo,37,16)
        graphics.DrawText(offscreen_canvas, font, 3, 0, color, score_text)
        
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
        time.sleep(3)


def main():
    # Configure RGB Matrix
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
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

            time.sleep(60)  # Update scores every 60 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Retry after 60 seconds if an error occurs

if __name__ == "__main__":
    main()