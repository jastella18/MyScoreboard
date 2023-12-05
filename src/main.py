import requests
import time
from rgbmatrix import graphics,RGBMatrix, RGBMatrixOptions

COLOR = (255,0,0)
FONT = ImageFont.load_default()
image = Image.new("RGB", (options.cols, options.rows), color=(0, 0, 0))
draw = ImageDraw.Draw(image)

#to test on regular pc
def display_example(matrix):
    matrix.Fill(255, 0, 0)  # Fill the matrix with red
    matrix.SwapOnVSync()     # Update the display

def fetch_nfl_scores(api_url):
    response = requests.get(api_url)
    return response.json()

def display_scores(matrix, events):
    matrix.Clear()
    matrix.Fill(255, 255, 255)  # Set background color (white)
    matrix.DrawText(10, 16, (255, 0, 0), "NFL Scores")

    y_position = 32
    image = Image.new("RGB", (options.cols, options.rows), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)

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


        draw.text((10,0),score_text,font=font,fill=color)
        rgb_data=image.convert("RGB")
        pixel_data = rgb_data.getdata()

        y_position += 16
	
        matrix.SetImage(pixel_data,0,0)

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

            display_example(matrix)

            time.sleep(1)  # Update scores every 60 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Retry after 60 seconds if an error occurs

if __name__ == "__main__":
    main()