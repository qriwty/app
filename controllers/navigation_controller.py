from datetime import datetime

from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify

from app import db
from models import Task
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
    new_task = Task(flight_id=flight_id, command=command, created=datetime.now(), status=0)
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
