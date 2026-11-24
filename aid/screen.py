"""Screenshot of the primary monitor, returned as a data URI for the vision model."""
import base64
import io

import mss
from PIL import Image

MAX_SIDE = 1568  # keep small text readable without exploding image tokens


def capture_data_uri() -> str:
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
