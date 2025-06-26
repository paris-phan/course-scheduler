from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base, TimestampMixin


# Association table for many-to-many relationship between schedules and courses
schedule_courses = Table(
    'schedule_courses',
    Base.metadata,
    Column('schedule_id', Integer, ForeignKey('schedules.id'), primary_key=True),
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True)
)


class Schedule(Base, TimestampMixin):
    """SQLAlchemy model for schedules"""
    __tablename__ = "schedules"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Schedule identification
    user_id = Column(String(255), index=True)  # User identifier
    name = Column(String(255), default="My Schedule")
    semester = Column(String(20), index=True)
    
    # Schedule metadata
    total_credits = Column(Integer, default=0)
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(JSON)  # List of validation error messages
    
    # Relationships
    courses = relationship(
        "Course",
        secondary=schedule_courses,
        backref="schedules"
    )
    
    def __repr__(self):
        return f"<Schedule {self.name} ({self.semester})>"


class ScheduleTemplate(Base, TimestampMixin):
    """SQLAlchemy model for schedule templates"""
    __tablename__ = "schedule_templates"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Template identification
    name = Column(String(255), nullable=False)
    description = Column(Text)
    major = Column(String(100))
    year_level = Column(String(20))  # Freshman, Sophomore, etc.
    
    # Template data
    required_courses = Column(JSON)  # List of required course codes
    recommended_courses = Column(JSON)  # List of recommended course codes
    course_patterns = Column(JSON)  # Scheduling patterns and preferences
    
    # Metadata
    is_public = Column(Boolean, default=False)
    created_by = Column(String(255))
    usage_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<ScheduleTemplate {self.name} ({self.major})>"