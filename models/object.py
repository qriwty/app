from app import db


class Object(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detection.id'), nullable=False)
    detection = db.relationship('Detection', backref=db.backref('objects', lazy=True))
