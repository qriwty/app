from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from services.auth.auth_service import AuthService


auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        user = auth_service.register_user(data['name'], data['email'], data['password'])
        if user:
            return redirect(url_for('auth.login'))
        return render_template('auth.html', action='register', error='User already exists')
    return render_template('auth.html', action='register')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        result = auth_service.authenticate(data['name'], data['password'])
        token, user = None, None
        if result:
            token, user = result
        if token and user:
            session['token'] = token
            session['user_id'] = user.id
            return redirect(url_for('dashboard.dashboard'))
        return render_template('auth.html', action='login', error='Invalid credentials')
    return render_template('auth.html', action='login')
