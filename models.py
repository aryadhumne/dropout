from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    roll_no = db.Column(db.String(20))
    division = db.Column(db.String(10))
    attendance = db.Column(db.Integer)
    marks = db.Column(db.Integer)
    behavior = db.Column(db.Integer)
    risk_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    added_by = db.Column(db.String(50))  # teacher email
