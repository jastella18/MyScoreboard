# MyNflScoreboard
Code for my Adafruit LED scoreboard (NFL / MLB / Premier League).

## Running

Preferred (package-safe):

```bash
python -m src.main
```

Or use the convenience wrapper:

```bash
python run.py
```

Create a virtual environment first and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

If executed on non-Raspberry Pi platforms the rgbmatrix library is absent and
frames print to the console (development mode). On a Pi, install
`rpi-rgb-led-matrix` per that project's instructions for panel output.

Edit `config.json` to switch rotation modes (`active_mode`). The app hot-reloads
this file roughly every 30 seconds.

source /home/jas/scoreenv/bin/activate