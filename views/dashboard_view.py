import base64
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, session
from app import core_service
from db import db
from models import Flight, Image, Detection, Point, Setting, FlightSnapshot
from utils.jwt import token_required
from utils.helpers import flight_active_required

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

    default_settings = [
        {'parameter': 'confidence', 'value': '0.5'},
        {'parameter': 'jaccard_index', 'value': '0.5'},
        {'parameter': 'detection_limit', 'value': '100'},
        {'parameter': 'exclude_classes', 'value': '-1'}
    ]

    for setting in default_settings:
        new_setting = Setting(
            flight_id=new_flight.id,
            parameter=setting['parameter'],
            value=setting['value']
        )
        db.session.add(new_setting)

    db.session.commit()

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


@dashboard_bp.route('/get-analysis', methods=['GET'])
@token_required
@flight_active_required
def get_analysis(user_id):
    flight_id = session.get('flight_id')

    core_service.run_analysis(flight_id)

    latest_snapshot = db.session.query(FlightSnapshot).filter_by(flight_id=flight_id).order_by(
        FlightSnapshot.timestamp.desc()).first()
    if not latest_snapshot:
        return jsonify({'message': 'No flight snapshot data available'}), 400

    latest_image_record = db.session.query(Image).filter_by(flight_snapshot_id=latest_snapshot.id).first()
    if not latest_image_record:
        return jsonify({'message': 'No image data available'}), 400

    latest_image = base64.b64encode(latest_image_record.image).decode('utf-8')

    detections = db.session.query(Detection).filter_by(image_id=latest_image_record.id).all()
    image_detections = []
    for detection in detections:
        point = db.session.query(Point).filter_by(id=detection.point_id).first()
        if point:
            image_detections.append({
                'track_id': detection.object_id,
                'class_id': detection.class_name,
                'location': (point.latitude, point.longitude, point.altitude)
            })

    all_snapshots = db.session.query(FlightSnapshot).filter_by(flight_id=flight_id).order_by(
        FlightSnapshot.timestamp.asc()).all()
    filtered_snapshots = []
    last_timestamp = None

    for snapshot in all_snapshots:
        if last_timestamp is None or (snapshot.timestamp - last_timestamp >= timedelta(minutes=1)):
            filtered_snapshots.append(snapshot)
            last_timestamp = snapshot.timestamp

    snapshot_data = []
    for snapshot in filtered_snapshots:
        point = db.session.query(Point).filter_by(id=snapshot.point_id).first()
        if point:
            snapshot_data.append({
                'timestamp': snapshot.timestamp,
                'latitude': point.latitude,
                'longitude': point.longitude,
                'altitude': point.altitude
            })

    return jsonify({
        'image_data': latest_image,
        'detections': image_detections,
        'snapshots': snapshot_data
    })
