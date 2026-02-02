from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
import uuid

# ✅ db MUST be created BEFORE models
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)

class StudentPerformance(db.Model):
    __tablename__ = "student_performance"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    attendance = db.Column(db.Integer)
    marks = db.Column(db.Integer)
    risk_level = db.Column(db.String)

class NGOIntervention(db.Model):
    __tablename__ = "ngo_interventions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    intervention_type = db.Column(db.String)
    description = db.Column(db.String)
