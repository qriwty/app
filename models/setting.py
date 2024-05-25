from app import db


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    parameter = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(64), nullable=False)
    flight = db.relationship('Flight', backref=db.backref('settings', lazy=True))
