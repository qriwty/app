from datetime import datetime

from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify

from app import core_service
from db import db
from models import Task, Object, Detection, Point
from utils.jwt import token_required
from utils.helpers import flight_active_required

navigation_bp = Blueprint('navigation_bp', __name__)


@navigation_bp.route('/')
@token_required
@flight_active_required
def navigation(user_id):
    flight_id = session.get('flight_id')

    tasks = Task.query.filter_by(flight_id=flight_id).all()

    return render_template('navigation.html', tasks=tasks)


@navigation_bp.route('/tasks')
@token_required
@flight_active_required
def get_tasks(user_id):
    flight_id = session.get('flight_id')

    tasks = Task.query.filter_by(flight_id=flight_id).all()
    tasks_data = [{'id': task.id, 'command': task.command, 'status': task.status} for task in tasks]
    return jsonify({'tasks': tasks_data})


@navigation_bp.route('/add', methods=['POST'])
@token_required
@flight_active_required
def add_task(user_id):
    flight_id = session.get('flight_id')

    command = request.form['command']

    command_dictionary = {
        "COMMAND": command,
        "ARGUMENTS": None
    }

    arguments = {}

    if 'height' in request.form:
        arguments['HEIGHT'] = request.form['height']
    if 'roll' in request.form and 'pitch' in request.form and 'yaw' in request.form:
        arguments['ROLL'] = request.form['roll']
        arguments['PITCH'] = request.form['pitch']
        arguments['YAW'] = request.form['yaw']
    if 'object_id' in request.form:
        arguments['OBJECT_ID'] = request.form['object_id']
    if 'lat' in request.form and 'lon' in request.form and 'alt' in request.form:
        arguments['LATITUDE'] = request.form['lat']
        arguments['LONGITUDE'] = request.form['lon']
        arguments['ALTITUDE'] = request.form['alt']
    if 'direction' in request.form:
        arguments['DIRECTION'] = request.form['direction']
    if 'distance' in request.form:
        arguments['DISTANCE'] = request.form['distance']

    command_dictionary["ARGUMENTS"] = arguments
    command_string = str(command_dictionary)

    new_task = Task(flight_id=flight_id, command=command_string, created=datetime.now(), status=0)
    db.session.add(new_task)
    db.session.commit()

    return redirect(url_for('navigation_bp.navigation'))


@navigation_bp.route('/update/<int:task_id>', methods=['POST'])
@token_required
@flight_active_required
def update_task(user_id, task_id):
    task = Task.query.get(task_id)
    if task:
        task.status = request.form['status']
        db.session.commit()

    return redirect(url_for('navigation_bp.navigation'))


@navigation_bp.route('/run/<int:task_id>', methods=['POST'])
@token_required
@flight_active_required
def run_task(user_id, task_id):
    task = Task.query.get(task_id)
    if task:
        task.status = 1
        db.session.commit()

        command_string = task.command
        command_dictionary = eval(command_string)

        if "OBJECT_ID" in command_dictionary["ARGUMENTS"]:
            object_id = command_dictionary["ARGUMENTS"]['OBJECT_ID']
            object = Object.query.get(object_id)
            if object:
                latest_detection = db.session.query(Detection).filter_by(object_id=object.id).order_by(Detection.id.desc()).first()
                if latest_detection:
                    point = Point.query.get(latest_detection.point_id)
                    if point:
                        command_dictionary["ARGUMENTS"]['LATITUDE'] = point.latitude
                        command_dictionary["ARGUMENTS"]['LONGITUDE'] = point.longitude
                        command_dictionary["ARGUMENTS"]['ALTITUDE'] = point.altitude
            if command_dictionary["COMMAND"] == "SET_CAMERA_ROI_OBJECT":
                command_dictionary["COMMAND"] = "SET_ROI"
            elif command_dictionary["COMMAND"] == "GO_TO_OBJECT":
                command_dictionary["COMMAND"] = "GO_TO"
            elif command_dictionary["CIRCLE_AROUND_OBJECT"]:
                command_dictionary["COMMAND"] = "CIRCLE_AROUND"
            elif command_dictionary["POINT_DRONE_OBJECT"]:
                command_dictionary["COMMAND"] = "POINT_DRONE"

        core_service.execute_command(command_dictionary)

        task.status = 2
        db.session.commit()

    return redirect(url_for('navigation_bp.navigation'))
