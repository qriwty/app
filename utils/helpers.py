from functools import wraps

import numpy as np
import random
import base64
from io import BytesIO
from PIL import Image
from flask import session, jsonify


def convert_image_to_base64(img_array):
    img = Image.fromarray(img_array.astype('uint8'))
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str


def create_blank_image(width, height):
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    img_array[:, :] = [
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    ]

    return img_array


def flight_active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        flight_id = session.get('flight_id')
        if not flight_id:
            return jsonify({'error': 'No active flight. Start a flight first.'}), 403
        return f(*args, **kwargs)
    return decorated_function
