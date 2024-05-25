import jwt
import datetime
from config import Config
from functools import wraps
from flask import redirect, url_for, session, jsonify


def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')


def decode_token(token):
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')

        if not token:
            return jsonify({'error': 'Unauthorized access'}), 401

        try:
            user_id = decode_token(token)
            if not user_id:
                return jsonify({'error': 'Unauthorized access'}), 401
        except Exception as error:
            return jsonify({'error': 'Unauthorized access'}), 401

        return f(user_id, *args, **kwargs)

    return decorated_function
