from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Meeting:
    """Represents a course meeting time"""
    days: str
    start_time: str
    end_time: str
    location: str


@dataclass
class Course:
    """Course entity model"""
    id: Optional[int] = None
    course_id: Optional[str] = None
    course_offer_nbr: Optional[int] = None
    strm: Optional[str] = None
    session_code: Optional[str] = None
    subject: Optional[str] = None
    catalog_nbr: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    class_section: Optional[str] = None
    class_nbr: Optional[int] = None
    units: Optional[str] = None
    enrollment_total: int = 0
    enrollment_available: int = 0
    class_capacity: int = 0
    waitlist_total: int = 0
    waitlist_capacity: int = 0
    meetings: List[Meeting] = None
    instructor: str = "TBA"
    instruction_mode: Optional[str] = None
    location: Optional[str] = None
    enrollment_status: Optional[str] = None
    class_type: Optional[str] = None
    ge_attributes: List[str] = None
    prerequisites: Optional[str] = None
    semester: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.meetings is None:
            self.meetings = []
        if self.ge_attributes is None:
            self.ge_attributes = []
    
    @property
    def course_code(self) -> str:
        """Get the course code (e.g., CS 1110)"""
        return f"{self.subject} {self.catalog_nbr}"
    
    @property
    def is_open(self) -> bool:
        """Check if the course has available seats"""
        return self.enrollment_available > 0
    
    @property
    def occupancy_rate(self) -> float:
        """Calculate the occupancy rate as a percentage"""
        if self.class_capacity == 0:
            return 0.0
        return (self.enrollment_total / self.class_capacity) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert course to dictionary"""
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course_offer_nbr': self.course_offer_nbr,
            'strm': self.strm,
            'session_code': self.session_code,
            'subject': self.subject,
            'catalog_nbr': self.catalog_nbr,
            'title': self.title,
            'description': self.description,
            'class_section': self.class_section,
            'class_nbr': self.class_nbr,
            'units': self.units,
            'enrollment_total': self.enrollment_total,
            'enrollment_available': self.enrollment_available,
            'class_capacity': self.class_capacity,
            'waitlist_total': self.waitlist_total,
            'waitlist_capacity': self.waitlist_capacity,
            'meetings': [
                {
                    'days': m.days,
                    'start_time': m.start_time,
                    'end_time': m.end_time,
                    'location': m.location
                } for m in self.meetings
            ],
            'instructor': self.instructor,
            'instruction_mode': self.instruction_mode,
            'location': self.location,
            'enrollment_status': self.enrollment_status,
            'class_type': self.class_type,
            'ge_attributes': self.ge_attributes,
            'prerequisites': self.prerequisites,
            'semester': self.semester,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }