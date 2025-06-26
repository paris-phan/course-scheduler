from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from core.schemas.course_schema import CourseResponse


class TimeSlotSchema(BaseModel):
    """Schema for a time slot in a schedule"""
    day: str
    start_time: str
    end_time: str
    course_code: str
    course_title: str
    location: str
    instructor: str
    class_nbr: int


class ScheduleBase(BaseModel):
    """Base schedule schema"""
    name: str = "My Schedule"
    semester: str


class ScheduleCreate(ScheduleBase):
    """Schema for creating a schedule"""
    user_id: Optional[str] = None
    course_class_numbers: List[int] = Field(
        default=[], 
        description="List of class numbers to add to the schedule"
    )


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    name: Optional[str] = None
    semester: Optional[str] = None


class ScheduleAddCourse(BaseModel):
    """Schema for adding a course to a schedule"""
    class_nbr: int = Field(description="Class number of the course to add")


class ScheduleRemoveCourse(BaseModel):
    """Schema for removing a course from a schedule"""
    class_nbr: int = Field(description="Class number of the course to remove")


class ScheduleInDB(ScheduleBase):
    """Schema for schedule in database"""
    id: int
    user_id: Optional[str]
    courses: List[CourseResponse]
    total_credits: int
    is_valid: bool
    validation_errors: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ScheduleResponse(ScheduleInDB):
    """Schema for schedule API response"""
    time_slots: List[TimeSlotSchema] = Field(
        description="List of time slots organized by day and time"
    )
    
    @classmethod
    def from_db(cls, schedule: ScheduleInDB, time_slots: List[TimeSlotSchema]):
        schedule_dict = schedule.dict()
        schedule_dict['time_slots'] = time_slots
        return cls(**schedule_dict)


class ScheduleValidationResult(BaseModel):
    """Schema for schedule validation result"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "is_valid": False,
                "errors": ["Time conflict between CS 1110 and MATH 1310"],
                "warnings": ["Schedule below minimum full-time credits (12)"]
            }
        }


class ScheduleOptimizationRequest(BaseModel):
    """Schema for schedule optimization request"""
    required_courses: List[str] = Field(
        description="List of course codes that must be included"
    )
    preferred_courses: List[str] = Field(
        description="List of course codes that should be included if possible"
    )
    avoid_times: List[Dict[str, str]] = Field(
        default=[],
        description="List of time blocks to avoid"
    )
    prefer_morning: bool = Field(
        default=False,
        description="Prefer morning classes"
    )
    prefer_afternoon: bool = Field(
        default=False,
        description="Prefer afternoon classes"
    )
    max_credits: int = Field(
        default=18,
        description="Maximum number of credits"
    )
    min_credits: int = Field(
        default=12,
        description="Minimum number of credits"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "required_courses": ["CS 2150", "CS 2110"],
                "preferred_courses": ["MATH 2310", "PHYS 1425"],
                "avoid_times": [
                    {"day": "M", "start": "08:00", "end": "09:00"},
                    {"day": "F", "start": "14:00", "end": "17:00"}
                ],
                "prefer_morning": True,
                "max_credits": 16
            }
        }