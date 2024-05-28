from db import db


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_snapshot_id = db.Column(db.Integer, db.ForeignKey('flight_snapshot.id'), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)

    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)

    fov_horizontal = db.Column(db.Float, nullable=False)
    fov_vertical = db.Column(db.Float, nullable=False)

    flight_snapshot = db.relationship('FlightSnapshot', backref=db.backref('images', lazy=True))
