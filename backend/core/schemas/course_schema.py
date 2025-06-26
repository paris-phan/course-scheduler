from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MeetingSchema(BaseModel):
    """Schema for course meeting times"""
    days: str
    start_time: str
    end_time: str
    location: str


class CourseBase(BaseModel):
    """Base course schema"""
    course_id: Optional[str] = None
    subject: str
    catalog_nbr: str
    title: Optional[str] = None
    description: Optional[str] = None
    units: Optional[str] = None
    instructor: str = "TBA"
    instruction_mode: Optional[str] = None
    prerequisites: Optional[str] = None


class CourseCreate(CourseBase):
    """Schema for creating a course"""
    course_offer_nbr: Optional[int] = None
    strm: str
    session_code: Optional[str] = None
    class_section: str
    class_nbr: int
    enrollment_total: int = 0
    enrollment_available: int = 0
    class_capacity: int = 0
    waitlist_total: int = 0
    waitlist_capacity: int = 0
    meetings: List[MeetingSchema] = []
    location: Optional[str] = None
    enrollment_status: Optional[str] = None
    class_type: Optional[str] = None
    ge_attributes: List[str] = []
    semester: str


class CourseUpdate(BaseModel):
    """Schema for updating a course"""
    title: Optional[str] = None
    description: Optional[str] = None
    enrollment_total: Optional[int] = None
    enrollment_available: Optional[int] = None
    waitlist_total: Optional[int] = None
    instructor: Optional[str] = None
    meetings: Optional[List[MeetingSchema]] = None
    prerequisites: Optional[str] = None


class CourseInDB(CourseBase):
    """Schema for course in database"""
    id: int
    course_offer_nbr: Optional[int] = None
    strm: str
    session_code: Optional[str] = None
    class_section: str
    class_nbr: int
    enrollment_total: int
    enrollment_available: int
    class_capacity: int
    waitlist_total: int
    waitlist_capacity: int
    meetings: List[MeetingSchema]
    location: Optional[str] = None
    enrollment_status: Optional[str] = None
    class_type: Optional[str] = None
    ge_attributes: List[str]
    semester: str
    last_updated: datetime
    
    class Config:
        from_attributes = True


class CourseResponse(CourseInDB):
    """Schema for course API response"""
    course_code: str = Field(description="Course code (e.g., CS 1110)")
    is_open: bool = Field(description="Whether the course has available seats")
    occupancy_rate: float = Field(description="Percentage of seats filled")
    
    @classmethod
    def from_db(cls, course: CourseInDB):
        course_dict = course.dict()
        course_dict['course_code'] = f"{course.subject} {course.catalog_nbr}"
        course_dict['is_open'] = course.enrollment_available > 0
        course_dict['occupancy_rate'] = (
            (course.enrollment_total / course.class_capacity * 100) 
            if course.class_capacity > 0 else 0
        )
        return cls(**course_dict)


class CourseSearchParams(BaseModel):
    """Schema for course search parameters"""
    term: Optional[str] = None
    subject: Optional[str] = None
    catalog_number: Optional[str] = None
    keyword: Optional[str] = None
    instructor: Optional[str] = None
    class_number: Optional[int] = None
    ge_attribute: Optional[str] = None
    has_seats: Optional[bool] = None
    instruction_mode: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "term": "1258",
                "subject": "CS",
                "catalog_number": "1110",
                "has_seats": True
            }
        }