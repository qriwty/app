from db import db


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    command = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    flight = db.relationship('Flight', backref=db.backref('tasks', lazy=True))
