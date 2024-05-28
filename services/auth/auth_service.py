from models.user import User
from db import db
from utils.jwt import generate_token


class AuthService:
    def register_user(self, name, email, password):
        if User.query.filter((User.name == name) | (User.email == email)).first():
            return None
        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def authenticate(self, name, password):
        user = User.query.filter_by(name=name).first()
        if user and user.check_password(password):
            return generate_token(user.id), user
        return None
