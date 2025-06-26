from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    """SQLAlchemy model for courses"""
    __tablename__ = "courses"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Course identification
    course_id = Column(String(50), index=True)
    course_offer_nbr = Column(Integer)
    strm = Column(String(10), index=True)  # Term
    session_code = Column(String(10))
    
    # Course details
    subject = Column(String(10), index=True)  # Department code
    catalog_nbr = Column(String(10), index=True)  # Course number
    title = Column(String(255))
    description = Column(Text)
    class_section = Column(String(10))
    class_nbr = Column(Integer, unique=True, index=True)  # Unique class number
    
    # Academic info
    units = Column(String(10))
    instruction_mode = Column(String(50))
    class_type = Column(String(50))
    
    # Enrollment info
    enrollment_total = Column(Integer, default=0)
    enrollment_available = Column(Integer, default=0)
    class_capacity = Column(Integer, default=0)
    waitlist_total = Column(Integer, default=0)
    waitlist_capacity = Column(Integer, default=0)
    enrollment_status = Column(String(20))
    
    # Meeting times and location (stored as JSON)
    meetings = Column(JSON)  # List of meeting time objects
    location = Column(String(255))
    
    # Instructor and academic details
    instructor = Column(String(255), default="TBA")
    prerequisites = Column(Text)
    ge_attributes = Column(JSON)  # List of general education attributes
    
    # Metadata
    semester = Column(String(20), index=True)
    last_updated = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Course {self.subject} {self.catalog_nbr} - {self.class_nbr}>"