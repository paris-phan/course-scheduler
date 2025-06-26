from typing import List, Optional, Dict, Any
from datetime import datetime
from core.schemas.schedule_schema import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse,
    ScheduleValidationResult, ScheduleOptimizationRequest,
    TimeSlotSchema
)
from core.models.schedule import Schedule, TimeSlot
from database.repositories.course_repository import CourseRepository
from utils.logger import setup_logger
from utils.exceptions import ResourceNotFoundException, ValidationException

logger = setup_logger(__name__)


class ScheduleService:
    """Service layer for schedule-related business logic"""
    
    def __init__(self):
        self.course_repo = CourseRepository()
        # Note: In a real app, we'd have a ScheduleRepository
        # For now, we'll simulate with in-memory storage
        self.schedules: Dict[int, Schedule] = {}
        self.next_id = 1
    
    async def get_schedules(
        self, 
        user_id: Optional[str] = None, 
        semester: Optional[str] = None
    ) -> List[ScheduleResponse]:
        """Get all schedules, optionally filtered"""
        schedules = list(self.schedules.values())
        
        # Apply filters
        if user_id:
            schedules = [s for s in schedules if s.user_id == user_id]
        if semester:
            schedules = [s for s in schedules if s.semester == semester]
        
        # Convert to response format
        return [self._to_response(schedule) for schedule in schedules]
    
    async def get_schedule(self, schedule_id: int) -> Optional[ScheduleResponse]:
        """Get a specific schedule by ID"""
        schedule = self.schedules.get(schedule_id)
        if schedule:
            return self._to_response(schedule)
        return None
    
    async def create_schedule(self, schedule_data: ScheduleCreate) -> ScheduleResponse:
        """Create a new schedule"""
        # Create new schedule
        schedule = Schedule(
            id=self.next_id,
            user_id=schedule_data.user_id,
            name=schedule_data.name,
            semester=schedule_data.semester
        )
        
        # Add initial courses if provided
        if schedule_data.course_class_numbers:
            courses = self.course_repo.get_courses_by_class_numbers(
                schedule_data.course_class_numbers
            )
            
            for course in courses:
                if not schedule.add_course(course):
                    logger.warning(f"Failed to add course {course.class_nbr} due to conflict")
        
        # Save schedule
        self.schedules[schedule.id] = schedule
        self.next_id += 1
        
        return self._to_response(schedule)
    
    async def update_schedule(
        self, 
        schedule_id: int, 
        schedule_update: ScheduleUpdate
    ) -> Optional[ScheduleResponse]:
        """Update schedule information"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        
        # Apply updates
        if schedule_update.name is not None:
            schedule.name = schedule_update.name
        if schedule_update.semester is not None:
            schedule.semester = schedule_update.semester
        
        schedule.updated_at = datetime.now()
        
        return self._to_response(schedule)
    
    async def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return True
        return False
    
    async def add_course_to_schedule(
        self, 
        schedule_id: int, 
        class_nbr: int
    ) -> ScheduleResponse:
        """Add a course to a schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            raise ResourceNotFoundException("Schedule", schedule_id)
        
        # Get the course
        course = self.course_repo.find_by_class_nbr(class_nbr)
        if not course:
            raise ResourceNotFoundException("Course", class_nbr)
        
        # Try to add the course
        if not schedule.add_course(course):
            conflicts = [err for err in schedule.validation_errors if "conflict" in err.lower()]
            if conflicts:
                raise ValueError(conflicts[0])
            else:
                raise ValueError("Failed to add course to schedule")
        
        return self._to_response(schedule)
    
    async def remove_course_from_schedule(
        self, 
        schedule_id: int, 
        class_nbr: int
    ) -> Optional[ScheduleResponse]:
        """Remove a course from a schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        
        if schedule.remove_course(class_nbr):
            return self._to_response(schedule)
        
        return self._to_response(schedule)
    
    async def validate_schedule(self, schedule_id: int) -> Optional[ScheduleValidationResult]:
        """Validate a schedule"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
        
        # Force revalidation
        schedule._validate_schedule()
        
        # Separate errors and warnings
        errors = [err for err in schedule.validation_errors if "conflict" in err.lower() or "exceeds" in err.lower()]
        warnings = [err for err in schedule.validation_errors if err not in errors]
        
        return ScheduleValidationResult(
            is_valid=schedule.is_valid,
            errors=errors,
            warnings=warnings
        )
    
    async def duplicate_schedule(self, schedule_id: int, new_name: str) -> Optional[ScheduleResponse]:
        """Create a copy of an existing schedule"""
        original = self.schedules.get(schedule_id)
        if not original:
            return None
        
        # Create new schedule
        new_schedule = Schedule(
            id=self.next_id,
            user_id=original.user_id,
            name=new_name,
            semester=original.semester
        )
        
        # Copy courses
        for course in original.courses:
            new_schedule.add_course(course)
        
        # Save new schedule
        self.schedules[new_schedule.id] = new_schedule
        self.next_id += 1
        
        return self._to_response(new_schedule)
    
    async def optimize_schedule(
        self, 
        optimization_request: ScheduleOptimizationRequest
    ) -> ScheduleResponse:
        """Generate an optimized schedule based on requirements"""
        # This is a simplified implementation
        # In a real system, this would use sophisticated algorithms
        
        # Create new schedule
        schedule = Schedule(
            id=self.next_id,
            name="Optimized Schedule",
            semester="Fall 2025"  # Should be dynamic
        )
        
        # Get all required courses
        for course_code in optimization_request.required_courses:
            parts = course_code.split()
            if len(parts) == 2:
                subject, catalog_nbr = parts
                courses = self.course_repo.find_by_subject_and_catalog(subject, catalog_nbr)
                
                # Try to add the first available section
                for course in courses:
                    if course.is_open and schedule.add_course(course):
                        break
        
        # Try to add preferred courses if we have room
        for course_code in optimization_request.preferred_courses:
            if schedule.total_credits >= optimization_request.max_credits:
                break
                
            parts = course_code.split()
            if len(parts) == 2:
                subject, catalog_nbr = parts
                courses = self.course_repo.find_by_subject_and_catalog(subject, catalog_nbr)
                
                # Try to add a section that fits preferences
                for course in courses:
                    if course.is_open and self._fits_preferences(course, optimization_request):
                        if schedule.add_course(course):
                            break
        
        # Save schedule
        self.schedules[schedule.id] = schedule
        self.next_id += 1
        
        return self._to_response(schedule)
    
    def _fits_preferences(self, course, preferences: ScheduleOptimizationRequest) -> bool:
        """Check if a course fits the user's preferences"""
        # This is a simplified check
        # In reality, we'd check against avoid_times, prefer morning/afternoon, etc.
        return True
    
    def _to_response(self, schedule: Schedule) -> ScheduleResponse:
        """Convert Schedule model to ScheduleResponse"""
        # Get time slots
        time_slots = [
            TimeSlotSchema(
                day=slot.day,
                start_time=slot.start_time,
                end_time=slot.end_time,
                course_code=slot.course_code,
                course_title=slot.course_title,
                location=slot.location,
                instructor=slot.instructor,
                class_nbr=slot.class_nbr
            )
            for slot in schedule.get_time_slots()
        ]
        
        # Create response
        return ScheduleResponse.from_db(schedule, time_slots)