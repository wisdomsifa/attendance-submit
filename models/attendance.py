from datetime import datetime
from models.models import db

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    link_code = db.Column(db.String(50), unique=True, nullable=False)
    expiry_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_name = db.Column(db.String(255), nullable=False)
    is_downloadable = db.Column(db.Boolean, default=False)
    attendances = db.relationship('Attendance', backref='lecture', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lecture.id'), nullable=False)
    student_name = db.Column(db.String(255), nullable=False)
    admission_number = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)