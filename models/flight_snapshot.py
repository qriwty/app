from db import db


class FlightSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)

    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    point_id = db.Column(db.Integer, db.ForeignKey('point.id'), nullable=False)

    roll = db.Column(db.Float, nullable=False)
    pitch = db.Column(db.Float, nullable=False)
    yaw = db.Column(db.Float, nullable=False)

    gimbal_roll = db.Column(db.Float, nullable=False)
    gimbal_pitch = db.Column(db.Float, nullable=False)
    gimbal_yaw = db.Column(db.Float, nullable=False)

    flight = db.relationship('Flight', backref=db.backref('flight_snapshots', lazy=True))
    point = db.relationship('Point', backref=db.backref('flight_snapshots', lazy=True))
