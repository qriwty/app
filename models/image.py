from app import db


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    flight = db.relationship('Flight', backref=db.backref('images', lazy=True))
