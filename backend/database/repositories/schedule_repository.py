from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from database.repositories.base_repository import BaseRepository
from database.models.schedule import Schedule
from database.models.course import Course
from core.models.schedule import Schedule as ScheduleEntity
from core.models.course import Course as CourseEntity
from database.repositories.course_repository import CourseRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ScheduleRepository(BaseRepository[Schedule]):
    """Repository for schedule database operations using SQLAlchemy"""
    
    def __init__(self):
        super().__init__(Schedule)
        self.course_repo = CourseRepository()
    
    def to_entity(self, db_schedule: Schedule) -> ScheduleEntity:
        """Convert SQLAlchemy model to domain entity"""
        courses = []
        if db_schedule.courses:
            for db_course in db_schedule.courses:
                courses.append(self.course_repo.to_entity(db_course))
        
        return ScheduleEntity(
            id=db_schedule.id,
            user_id=db_schedule.user_id,
            name=db_schedule.name,
            semester=db_schedule.semester,
            courses=courses,
            total_credits=db_schedule.total_credits,
            is_valid=db_schedule.is_valid,
            validation_errors=db_schedule.validation_errors or [],
            created_at=db_schedule.created_at,
            updated_at=db_schedule.updated_at
        )
    
    def from_entity(self, entity: ScheduleEntity) -> Dict[str, Any]:
        """Convert domain entity to database model data"""
        return {
            'user_id': entity.user_id,
            'name': entity.name,
            'semester': entity.semester,
            'total_credits': entity.total_credits,
            'is_valid': entity.is_valid,
            'validation_errors': entity.validation_errors
        }
    
    async def find_by_user(
        self, 
        session: AsyncSession, 
        user_id: str,
        semester: Optional[str] = None
    ) -> List[ScheduleEntity]:
        """Find schedules by user ID with optional semester filter"""
        try:
            filters = {'user_id': user_id}
            if semester:
                filters['semester'] = semester
            
            query = select(Schedule).options(selectinload(Schedule.courses))
            
            # Apply filters
            conditions = []
            for field_name, value in filters.items():
                field = getattr(Schedule, field_name)
                conditions.append(field == value)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await session.execute(query)
            db_schedules = result.scalars().all()
            
            return [self.to_entity(schedule) for schedule in db_schedules]
        except Exception as e:
            logger.error(f"Error finding schedules by user: {str(e)}")
            return []
    
    async def find_by_id_with_courses(
        self, 
        session: AsyncSession, 
        schedule_id: int
    ) -> Optional[ScheduleEntity]:
        """Find a schedule by ID with courses loaded"""
        try:
            query = (
                select(Schedule)
                .options(selectinload(Schedule.courses))
                .where(Schedule.id == schedule_id)
            )
            
            result = await session.execute(query)
            db_schedule = result.scalar_one_or_none()
            
            if db_schedule:
                return self.to_entity(db_schedule)
            return None
        except Exception as e:
            logger.error(f"Error finding schedule by ID with courses: {str(e)}")
            return None
    
    async def create_schedule(
        self, 
        session: AsyncSession, 
        schedule_entity: ScheduleEntity
    ) -> ScheduleEntity:
        """Create a new schedule from entity"""
        try:
            schedule_data = self.from_entity(schedule_entity)
            db_schedule = await self.create(session, **schedule_data)
            
            # Add courses to the schedule if provided
            if schedule_entity.courses:
                await self._add_courses_to_schedule(
                    session, 
                    db_schedule, 
                    [course.class_nbr for course in schedule_entity.courses]
                )
            
            # Refresh to get the updated schedule with courses
            await session.refresh(db_schedule, ['courses'])
            return self.to_entity(db_schedule)
        except Exception as e:
            logger.error(f"Error creating schedule: {str(e)}")
            raise
    
    async def add_course_to_schedule(
        self, 
        session: AsyncSession, 
        schedule_id: int, 
        class_nbr: int
    ) -> Optional[ScheduleEntity]:
        """Add a course to a schedule"""
        try:
            # Get the schedule
            db_schedule = await self.find_by_id(session, schedule_id)
            if not db_schedule:
                return None
            
            # Get the course
            course_query = select(Course).where(Course.class_nbr == class_nbr)
            course_result = await session.execute(course_query)
            db_course = course_result.scalar_one_or_none()
            
            if not db_course:
                logger.warning(f"Course with class_nbr {class_nbr} not found")
                return None
            
            # Check if course is already in the schedule
            if db_course not in db_schedule.courses:
                db_schedule.courses.append(db_course)
                
                # Update total credits and validation
                await self._update_schedule_metadata(session, db_schedule)
                await session.commit()
            
            # Refresh and return
            await session.refresh(db_schedule, ['courses'])
            return self.to_entity(db_schedule)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error adding course to schedule: {str(e)}")
            return None
    
    async def remove_course_from_schedule(
        self, 
        session: AsyncSession, 
        schedule_id: int, 
        class_nbr: int
    ) -> Optional[ScheduleEntity]:
        """Remove a course from a schedule"""
        try:
            # Get the schedule with courses
            query = (
                select(Schedule)
                .options(selectinload(Schedule.courses))
                .where(Schedule.id == schedule_id)
            )
            result = await session.execute(query)
            db_schedule = result.scalar_one_or_none()
            
            if not db_schedule:
                return None
            
            # Find and remove the course
            course_to_remove = None
            for course in db_schedule.courses:
                if course.class_nbr == class_nbr:
                    course_to_remove = course
                    break
            
            if course_to_remove:
                db_schedule.courses.remove(course_to_remove)
                
                # Update total credits and validation
                await self._update_schedule_metadata(session, db_schedule)
                await session.commit()
            
            # Refresh and return
            await session.refresh(db_schedule, ['courses'])
            return self.to_entity(db_schedule)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error removing course from schedule: {str(e)}")
            return None
    
    async def duplicate_schedule(
        self, 
        session: AsyncSession, 
        schedule_id: int, 
        new_name: str,
        user_id: Optional[str] = None
    ) -> Optional[ScheduleEntity]:
        """Create a copy of an existing schedule"""
        try:
            # Get the original schedule with courses
            original = await self.find_by_id_with_courses(session, schedule_id)
            if not original:
                return None
            
            # Create new schedule data
            new_schedule_data = {
                'user_id': user_id or original.user_id,
                'name': new_name,
                'semester': original.semester,
                'total_credits': 0,  # Will be recalculated
                'is_valid': True,
                'validation_errors': []
            }
            
            # Create the new schedule
            db_schedule = await self.create(session, **new_schedule_data)
            
            # Add courses from original schedule
            if original.courses:
                course_class_nbrs = [course.class_nbr for course in original.courses]
                await self._add_courses_to_schedule(session, db_schedule, course_class_nbrs)
            
            # Refresh and return
            await session.refresh(db_schedule, ['courses'])
            return self.to_entity(db_schedule)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error duplicating schedule: {str(e)}")
            return None
    
    async def get_schedules_by_semester(
        self, 
        session: AsyncSession, 
        semester: str,
        limit: Optional[int] = None
    ) -> List[ScheduleEntity]:
        """Get all schedules for a specific semester"""
        try:
            query = (
                select(Schedule)
                .options(selectinload(Schedule.courses))
                .where(Schedule.semester == semester)
            )
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            db_schedules = result.scalars().all()
            
            return [self.to_entity(schedule) for schedule in db_schedules]
        except Exception as e:
            logger.error(f"Error getting schedules by semester: {str(e)}")
            return []
    
    async def _add_courses_to_schedule(
        self, 
        session: AsyncSession, 
        db_schedule: Schedule, 
        class_nbrs: List[int]
    ) -> None:
        """Helper method to add multiple courses to a schedule"""
        try:
            # Get all courses by class numbers
            course_query = select(Course).where(Course.class_nbr.in_(class_nbrs))
            course_result = await session.execute(course_query)
            courses = course_result.scalars().all()
            
            # Add courses to schedule
            for course in courses:
                if course not in db_schedule.courses:
                    db_schedule.courses.append(course)
            
            # Update metadata
            await self._update_schedule_metadata(session, db_schedule)
        except Exception as e:
            logger.error(f"Error adding courses to schedule: {str(e)}")
            raise
    
    async def _update_schedule_metadata(
        self, 
        session: AsyncSession, 
        db_schedule: Schedule
    ) -> None:
        """Update schedule metadata like total credits and validation"""
        try:
            # Calculate total credits
            total_credits = 0
            for course in db_schedule.courses:
                if course.units:
                    # Handle units like "3", "3-4", etc.
                    units_str = course.units.split('-')[0]
                    if units_str.isdigit():
                        total_credits += int(units_str)
            
            db_schedule.total_credits = total_credits
            db_schedule.updated_at = datetime.now()
            
            # Basic validation (can be expanded)
            validation_errors = []
            if total_credits > 18:
                validation_errors.append("Schedule exceeds maximum credit limit (18)")
            if total_credits < 12:
                validation_errors.append("Schedule below minimum full-time credits (12)")
            
            db_schedule.validation_errors = validation_errors
            db_schedule.is_valid = len(validation_errors) == 0
            
        except Exception as e:
            logger.error(f"Error updating schedule metadata: {str(e)}")
            raise