from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")

    recruiter_profile = relationship("RecruiterProfile", backref="user", uselist=False)
    student_profile = relationship("StudentProfile", backref="user", uselist=False)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    hr_contact = Column(String(120))
    website = Column(String(200))
    approval_status = Column(String(20), nullable=False, default="pending")

    drives = relationship("JobDrive", backref="recruiter", lazy=True)

    def __repr__(self):
        return f"<RecruiterProfile {self.company_name}>"


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False)
    cgpa = Column(Float, default=0.0)
    resume = Column(Text, default="")

    applications = relationship("DriveApplication", backref="student", lazy=True)

    def __repr__(self):
        return f"<StudentProfile {self.name}>"


class JobDrive(Base):
    __tablename__ = "job_drives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("recruiter_profiles.id"), nullable=False)
    job_title = Column(String(200), nullable=False)
    job_description = Column(Text, nullable=True)
    eligibility = Column(String(200), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="pending")

    applications = relationship("DriveApplication", backref="drive", lazy=True)

    def __repr__(self):
        return f"<JobDrive {self.job_title}>"


class DriveApplication(Base):
    __tablename__ = "drive_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("job_drives.id"), nullable=False)
    application_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="applied")

    def __repr__(self):
        return f"<DriveApplication student={self.student_id} drive={self.drive_id}>"
