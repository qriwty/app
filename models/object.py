from db import db


class Object(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    track_id = db.Column(db.Integer, nullable=False)

    flight = db.relationship('Flight', backref=db.backref('objects', lazy=True))
