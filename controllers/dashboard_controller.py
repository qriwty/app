import base64
from datetime import datetime, timedelta

import cv2
from flask import Blueprint, render_template, jsonify, session
from app import core_service
from db import db
from models import Flight, Image, Detection, Point, Setting, FlightSnapshot, Object
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


@dashboard_bp.route('/get-flight-info', methods=['GET'])
@token_required
@flight_active_required
def get_flight_info(user_id):
    flight_id = session.get('flight_id')

    all_snapshots = db.session.query(FlightSnapshot).filter_by(flight_id=flight_id).order_by(
        FlightSnapshot.timestamp.asc()).all()
    filtered_snapshots = []
    last_timestamp = None

    for snapshot in all_snapshots:
        if last_timestamp is None or (snapshot.timestamp - last_timestamp >= timedelta(minutes=1)):
            filtered_snapshots.append(snapshot)
            last_timestamp = snapshot.timestamp

    snapshots_data = []
    for snapshot in filtered_snapshots:
        point = db.session.query(Point).get(snapshot.point_id)
        if not point:
            continue

        snapshots_data.append({
            'timestamp': snapshot.timestamp.isoformat(),
            'latitude': point.latitude,
            'longitude': point.longitude,
            'altitude': point.altitude
        })

    return jsonify({'snapshots': snapshots_data})


@dashboard_bp.route('/get-analysis', methods=['GET'])
@token_required
@flight_active_required
def get_analysis(user_id):
    flight_id = session.get('flight_id')

    analysis = core_service.get_analysis()

    if analysis:
        store_analysis(flight_id, analysis)

        _, compressed_image = cv2.imencode('.jpg', analysis["analysis"]["frame"], [cv2.IMWRITE_JPEG_QUALITY, 70])
        image = base64.b64encode(compressed_image).decode('utf-8')

        return jsonify({
            "timestamp": analysis["timestamp"].isoformat(),
            "image": image,
            "tracks": [{
                "track_id": str(track["track_id"]),
                "class_name": str(core_service.analysis_service.model.names[track["class_id"]]),
                "latitude": str(track["location"]["latitude"]),
                "longitude": str(track["location"]["longitude"]),
                "altitude": str(track["location"]["altitude"])
            } for track in analysis["analysis"]["tracks"]]
        })

    return jsonify({"error": "No data"})


def store_analysis(flight_id, analysis):
    analysis_timestamp = analysis["timestamp"]

    existing_analysis = db.session.query(FlightSnapshot).filter_by(
        flight_id=flight_id, timestamp=analysis_timestamp
    ).first()

    if existing_analysis:
        return

    location = analysis["drone"]["location"]

    drone_location = save_point(
        latitude=location["latitude"],
        longitude=location["longitude"],
        altitude=location["altitude"]
    )

    drone_attitude = analysis["drone"]["attitude"]
    gimbal_attitude = analysis["drone"]["gimbal"]
    drone_snapshot = save_flight_snapshot(
        flight_id=flight_id,
        point_id=drone_location.id,
        timestamp=analysis["timestamp"],
        drone_attitude=[
            drone_attitude["roll"],
            drone_attitude["pitch"],
            drone_attitude["yaw"]
        ],
        gimbal_attitude=[
            gimbal_attitude["roll"],
            gimbal_attitude["pitch"],
            gimbal_attitude["yaw"]
        ]
    )

    camera = analysis["drone"]["camera"]
    _, compressed_image = cv2.imencode('.jpg', camera["frame"], [cv2.IMWRITE_JPEG_QUALITY, 70])
    image_bytes = compressed_image.tobytes()
    image = save_image(
        flight_snapshot_id=drone_snapshot.id,
        image_bytes=image_bytes,
        width=camera["width"],
        height=camera["height"],
        fov_horizontal=camera["fov_horizontal"],
        fov_vertical=camera["fov_vertical"]
    )

    for detection in analysis["analysis"]["tracks"]:
        point = save_point(
            latitude=detection["location"]["latitude"],
            longitude=detection["location"]["longitude"],
            altitude=detection["location"]["altitude"]
        )

        object = save_object(detection["track_id"], flight_id)

        x1, y1, x2, y2 = (
            detection["frame"]["x1"],
            detection["frame"]["y1"],
            detection["frame"]["x2"],
            detection["frame"]["y2"]
        )
        save_detection(
            point_id=point.id,
            image_id=image.id,
            object_id=object.id,
            class_name=detection["class_id"],
            frame=f'{x1}, {y1}, {x2}, {y2}'
        )


def save_flight_snapshot(flight_id, point_id, timestamp, drone_attitude, gimbal_attitude):
    drone_roll, drone_pitch, drone_yaw = drone_attitude
    gimbal_roll, gimbal_pitch, gimbal_yaw = gimbal_attitude
    new_snapshot = FlightSnapshot(
        flight_id=flight_id,
        timestamp=timestamp,
        point_id=point_id,
        roll=drone_roll,
        pitch=drone_pitch,
        yaw=drone_yaw,
        gimbal_roll=gimbal_roll,
        gimbal_pitch=gimbal_pitch,
        gimbal_yaw=gimbal_yaw
    )

    db.session.add(new_snapshot)
    db.session.commit()

    return new_snapshot


def save_image(flight_snapshot_id, image_bytes, width, height, fov_horizontal, fov_vertical):
    new_image = Image(
        flight_snapshot_id=flight_snapshot_id,
        image=image_bytes,
        width=width,
        height=height,
        fov_horizontal=fov_horizontal,
        fov_vertical=fov_vertical
    )

    db.session.add(new_image)
    db.session.commit()

    return new_image


def save_detection(point_id, image_id, object_id, class_name, frame):
    new_detection = Detection(
        point_id=point_id,
        image_id=image_id,
        object_id=object_id,
        class_name=class_name,
        frame=frame
    )

    db.session.add(new_detection)
    db.session.commit()

    return new_detection


def save_point(latitude, longitude, altitude):
    new_point = Point(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude
    )

    db.session.add(new_point)
    db.session.commit()

    return new_point


def save_object(track_id, flight_id):
    existing_object = Object.query.filter_by(track_id=track_id, flight_id=flight_id).first()

    if existing_object:
        return existing_object

    new_object = Object(track_id=track_id, flight_id=flight_id)

    db.session.add(new_object)
    db.session.commit()

    return new_object
