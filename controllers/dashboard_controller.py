from datetime import datetime
from flask import Blueprint, render_template, jsonify, session
from app import db
from models import Flight
from utils.jwt import token_required
from utils.helpers import convert_image_to_base64, create_blank_image, flight_active_required
from functools import wraps

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@token_required
def dashboard(user_id):
    return render_template('dashboard.html')


@dashboard_bp.route('/start-flight', methods=['POST'])
@token_required
def start_flight(user_id):
    if 'flight_id' in session:
        return jsonify({'error': 'End the current flight before starting a new one'}), 400

    new_flight = Flight(user_id=user_id, start_time=datetime.now())
    db.session.add(new_flight)
    db.session.commit()

    session['flight_id'] = new_flight.id

    return jsonify({'flight_id': new_flight.id})


@dashboard_bp.route('/stop-flight', methods=['POST'])
@token_required
def stop_flight(user_id):
    flight_id = session.get('flight_id')
    if not flight_id:
        return jsonify({'error': 'No active flight to stop'}), 400

    current_flight = Flight.query.get(flight_id)
    if current_flight.end_time is not None:
        return jsonify({'error': 'This flight has already been stopped'}), 400

    current_flight.end_time = datetime.now()
    db.session.commit()

    session.pop('flight_id', None)

    return jsonify({'message': 'Flight stopped successfully'})


@dashboard_bp.route('/image')
@token_required
@flight_active_required
def dashboard_image(user_id):
    image = create_blank_image(640, 480)
    converted_image = convert_image_to_base64(image)

    return jsonify({'image_data': converted_image})
