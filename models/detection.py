from app import db


class Detection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    point_id = db.Column(db.Integer, db.ForeignKey('point.id'), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    object_id = db.Column(db.Integer, db.ForeignKey('object.id'), nullable=False)
    class_name = db.Column(db.String(64), nullable=False)
    frame = db.Column(db.Text, nullable=False)
    point = db.relationship('Point', backref=db.backref('detections', lazy=True))
    image = db.relationship('Image', backref=db.backref('detections', lazy=True))
    object = db.relationship('Object', backref=db.backref('detections', lazy=True))
