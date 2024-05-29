from flask import Blueprint, render_template, session, request, redirect, url_for
from utils.jwt import token_required
from models.user import User
from db import db


profile_bp = Blueprint('profile_bp', __name__)


@profile_bp.route('/')
@token_required
def profile(user_id):
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)


@profile_bp.route('/update', methods=['POST'])
@token_required
def update(user_id):
    user = User.query.get(user_id)
    if user:
        user.username = request.form['name']
        user.email = request.form['email']
        password = request.form['password']
        if password:
            user.set_password(password)
            db.session.commit()
    return redirect(url_for('profile_bp.profile'))
