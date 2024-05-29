from flask import Blueprint, render_template, request, session, redirect, url_for

from db import db
from models import Setting
from utils.jwt import token_required
from utils.helpers import flight_active_required
from app import core_service

settings_bp = Blueprint('settings_bp', __name__)


@settings_bp.route('/')
@token_required
@flight_active_required
def settings(user_id):
    flight_id = session.get('flight_id')
    if not flight_id:
        return redirect(url_for('dashboard.dashboard'))

    settings = Setting.query.filter_by(flight_id=flight_id).all()
    settings_dict = {setting.parameter: setting.value for setting in settings}

    return render_template('settings.html', settings=settings_dict)


@settings_bp.route('/update', methods=['POST'])
@token_required
@flight_active_required
def update(user_id):
    flight_id = session.get('flight_id')

    settings = [
        {'parameter': 'confidence', 'value': request.form['confidence']},
        {'parameter': 'exclude_classes', 'value': request.form['exclude_classes']},
        {'parameter': 'detection_limit', 'value': request.form['detection_limit']},
        {'parameter': 'jaccard_index', 'value': request.form['jaccard_index']}
    ]

    for setting in settings:
        setting_obj = Setting.query.filter_by(flight_id=flight_id, parameter=setting['parameter']).first()
        if setting_obj:
            setting_obj.value = setting['value']
        else:
            new_setting = Setting(flight_id=flight_id, parameter=setting['parameter'], value=setting['value'])
            db.session.add(new_setting)

    db.session.commit()

    settings_dict = {setting['parameter']: setting['value'] for setting in settings}

    detection_threshold = float(settings_dict.get('confidence', 0.5))
    iou_threshold = float(settings_dict.get('jaccard_index', 0.5))
    max_detections = int(settings_dict.get('detection_limit', 100))
    classes_excluded = list(map(int, settings_dict.get('exclude_classes', '-1').split(',')))

    core_service.update_settings(
        detection_threshold=detection_threshold,
        iou_threshold=iou_threshold,
        max_detections=max_detections,
        classes_excluded=classes_excluded
    )

    return redirect(url_for('dashboard.dashboard'))
