from db import db


class Object(db.Model):
    id = db.Column(db.Integer, primary_key=True)
