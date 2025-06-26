from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from core.models.course import Course


@dataclass
class TimeSlot:
    """Represents a time slot in a schedule"""
    day: str
    start_time: str
    end_time: str
    course_code: str
    course_title: str
    location: str
    instructor: str
    class_nbr: int


@dataclass
class Schedule:
    """Schedule entity model"""
    id: Optional[int] = None
    user_id: Optional[str] = None
    name: str = "My Schedule"
    semester: Optional[str] = None
    courses: List[Course] = None
    total_credits: int = 0
    is_valid: bool = True
    validation_errors: List[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.courses is None:
            self.courses = []
        if self.validation_errors is None:
            self.validation_errors = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def add_course(self, course: Course) -> bool:
        """Add a course to the schedule"""
        # Check for conflicts before adding
        if self._has_time_conflict(course):
            self.validation_errors.append(f"Time conflict with {course.course_code}")
            self.is_valid = False
            return False
        
        self.courses.append(course)
        self._update_total_credits()
        self.updated_at = datetime.now()
        return True
    
    def remove_course(self, class_nbr: int) -> bool:
        """Remove a course from the schedule by class number"""
        original_length = len(self.courses)
        self.courses = [c for c in self.courses if c.class_nbr != class_nbr]
        
        if len(self.courses) < original_length:
            self._update_total_credits()
            self._validate_schedule()
            self.updated_at = datetime.now()
            return True
        return False
    
    def _has_time_conflict(self, new_course: Course) -> bool:
        """Check if a course conflicts with existing courses"""
        for existing_course in self.courses:
            if self._courses_conflict(existing_course, new_course):
                return True
        return False
    
    def _courses_conflict(self, course1: Course, course2: Course) -> bool:
        """Check if two courses have overlapping meeting times"""
        for meeting1 in course1.meetings:
            for meeting2 in course2.meetings:
                if self._meetings_overlap(meeting1, meeting2):
                    return True
        return False
    
    def _meetings_overlap(self, meeting1, meeting2) -> bool:
        """Check if two meetings overlap"""
        # Check if any days overlap
        days1 = set(meeting1.days)
        days2 = set(meeting2.days)
        
        if not days1.intersection(days2):
            return False
        
        # Convert times to minutes for comparison
        start1 = self._time_to_minutes(meeting1.start_time)
        end1 = self._time_to_minutes(meeting1.end_time)
        start2 = self._time_to_minutes(meeting2.start_time)
        end2 = self._time_to_minutes(meeting2.end_time)
        
        # Check for time overlap
        return not (end1 <= start2 or end2 <= start1)
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string to minutes since midnight"""
        try:
            # Assuming time format is "HH:MM AM/PM" or "HH:MM"
            if 'AM' in time_str or 'PM' in time_str:
                time_obj = datetime.strptime(time_str, "%I:%M %p")
            else:
                time_obj = datetime.strptime(time_str, "%H:%M")
            
            return time_obj.hour * 60 + time_obj.minute
        except:
            return 0
    
    def _update_total_credits(self):
        """Update total credits based on courses"""
        self.total_credits = sum(
            int(course.units.split('-')[0]) if course.units and '-' in course.units 
            else int(course.units) if course.units and course.units.isdigit() 
            else 0 
            for course in self.courses
        )
    
    def _validate_schedule(self):
        """Validate the entire schedule"""
        self.validation_errors = []
        self.is_valid = True
        
        # Check for time conflicts
        for i, course1 in enumerate(self.courses):
            for course2 in self.courses[i+1:]:
                if self._courses_conflict(course1, course2):
                    self.validation_errors.append(
                        f"Time conflict between {course1.course_code} and {course2.course_code}"
                    )
                    self.is_valid = False
        
        # Check credit limits (example: max 18 credits)
        if self.total_credits > 18:
            self.validation_errors.append("Schedule exceeds maximum credit limit (18)")
            self.is_valid = False
        
        # Check minimum credits (example: min 12 credits for full-time)
        if self.total_credits < 12:
            self.validation_errors.append("Schedule below minimum full-time credits (12)")
    
    def get_time_slots(self) -> List[TimeSlot]:
        """Get all time slots for the schedule"""
        time_slots = []
        
        for course in self.courses:
            for meeting in course.meetings:
                for day in meeting.days:
                    time_slot = TimeSlot(
                        day=day,
                        start_time=meeting.start_time,
                        end_time=meeting.end_time,
                        course_code=course.course_code,
                        course_title=course.title or course.description,
                        location=meeting.location,
                        instructor=course.instructor,
                        class_nbr=course.class_nbr
                    )
                    time_slots.append(time_slot)
        
        return sorted(time_slots, key=lambda x: (x.day, self._time_to_minutes(x.start_time)))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'semester': self.semester,
            'courses': [course.to_dict() for course in self.courses],
            'total_credits': self.total_credits,
            'is_valid': self.is_valid,
            'validation_errors': self.validation_errors,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }