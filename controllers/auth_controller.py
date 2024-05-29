from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from models.user import User
from db import db
from utils.jwt import generate_token


auth_bp = Blueprint('auth', __name__)


def register_user(name, email, password):
    if User.query.filter((User.name == name) | (User.email == email)).first():
        return None
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(name, password):
    user = User.query.filter_by(name=name).first()
    if user and user.check_password(password):
        return generate_token(user.id), user
    return None


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        user = register_user(data['name'], data['email'], data['password'])
        if user:
            return redirect(url_for('auth.login'))
        return render_template('auth.html', action='register', error='User already exists')
    return render_template('auth.html', action='register')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        result = authenticate(data['name'], data['password'])
        token, user = None, None
        if result:
            token, user = result
        if token and user:
            session['token'] = token
            session['user_id'] = user.id
            return redirect(url_for('dashboard.dashboard'))
        return render_template('auth.html', action='login', error='Invalid credentials')
    return render_template('auth.html', action='login')
