import time
from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
from PIL import Image,ImageDraw
from io import BytesIO

def fetch_nfl_scores(api_url):
    response = requests.get(api_url)
    return response.json()

def get_logo(abv):
    abvlow = abv.lower()
    img_ad = '/home/jastella/sportsdisplay/MyNflScoreboard/assets/Logos/' + abv + '/' + abvlow + '.png'
    return img_ad

def canvaslogo(canvas, image, start_x, start_y):
    # Convert the image to RGB mode if it's not already
    if image.mode != 'RGB':
        image = image.convert('RGB')
	

    image.thumbnail((22,22),Image.ANTIALIAS)

    canvas.SetImage(image,start_x,start_y)

def getstatus(event):
    status_details = event["competitions"][0]["status"]
    return status_details
    


def display_scores(matrix, events):
    offscreen_canvas = matrix.CreateFrameCanvas()
    font = graphics.Font()
    font.LoadFont('/home/jastella/sportsdisplay/MyNflScoreboard/rpi-rgb-led-matrix/rpi-rgb-led-matrix/fonts/4x6.bdf')
    color = graphics.Color(255, 255, 255)

    matrix.Clear()
    graphics.DrawText(offscreen_canvas, font, 10, 16, color, "NFL Scores")
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    time.sleep(2)

    matrix.Clear()
    y_position = 32

    for event in events:
        status_details = getstatus(event)
        status = status_details["type"]["description"]
        if (status ==  "In Progress" or status ==  "Halftime"):
            clock = status_details["displayClock"]
            quart =status_details["period"]
            #down =  event["competitions"][0]["situation"]["downDistanceText"]
            play = event["competitions"][0]["situation"]["lastPlay"]["text"]
            passer=event["competitions"][0]["leaders"][0]["leaders"]["athlete"]["shortName"]
            pyds= event["competitions"][0]["leaders"][0]["leaders"][0]["displayValue"]
            rusher= event["competitions"][0]["leaders"][1]["leaders"]["athlete"]["shortName"]
            ryds=event["competitions"][0]["leaders"][1]["leaders"][0]["displayValue"]
            reciever=event["competitions"][0]["leaders"][2]["leaders"]["athlete"]["shortName"]
            reyds=event["competitions"][0]["leaders"][2]["leaders"][0]["displayValue"]


        home_info = event["competitions"][0]["competitors"][0]
        hteam_name = home_info["team"]["abbreviation"]
        hteam_logo = get_logo(hteam_name)

        away_info = event["competitions"][0]["competitors"][1]
        ateam_name = away_info["team"]["abbreviation"]
        ateam_logo = get_logo(ateam_name)

        home_score = home_info["score"]
        away_score = away_info["score"]

        hlogo = Image.open(hteam_logo)
        alogo = Image.open(ateam_logo)

        score_text = f"{hteam_name} {home_score} - {away_score} {ateam_name}"
        print(score_text)

        status_text = f"{quart} {clock}"
        play_text = f"{play}"

  

        canvaslogo(offscreen_canvas, hlogo, 5,12)
        canvaslogo(offscreen_canvas, alogo,37, 12)
        graphics.DrawText(offscreen_canvas, font, 5, 5, color, score_text)
        if (status ==  "In Progress"):
            graphics.DrawText(offscreen_canvas, font, 18, 10, color, status_text)



        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
        time.sleep(3)
        matrix.Clear()

        if (status ==  "In Progress"):
            graphics.DrawText(offscreen_canvas, font, 1, 5, color,"{passer}: {pyds}")
            graphics.DrawText(offscreen_canvas, font, 1, 15, color, "{rusher}: {ryds}")
            graphics.DrawText(offscreen_canvas, font, 1, 25, color, "{reciever}: {reyds}")

            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            time.sleep(3)
            matrix.Clear()


def main():
    # Configure RGB Matrix
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.hardware_mapping = 'adafruit-hat'
    options.chain_length = 1
    matrix = RGBMatrix(options=options)
    # API endpoint for real-time NFL scores (replace with your API URL)
    api_url = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

    while True:
        try:
            # Fetch NFL scores from the API
            scores_data = fetch_nfl_scores(api_url)

            # Extract relevant information from the API response
            events = scores_data.get('events', [])

            # Display scores on the LED matrix
            display_scores(matrix, events)

            time.sleep(10)  # Update scores every 60 seconds

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)  # Retry after 60 seconds if an error occurs

if __name__ == "__main__":
    main()