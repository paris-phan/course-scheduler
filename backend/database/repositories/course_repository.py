from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from datetime import datetime
from database.repositories.base_repository import BaseRepository
from database.models.course import Course
from core.models.course import Course as CourseEntity, Meeting
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CourseRepository(BaseRepository[Course]):
    """Repository for course database operations using SQLAlchemy"""
    
    def __init__(self):
        super().__init__(Course)
    
    def to_entity(self, db_course: Course) -> CourseEntity:
        """Convert SQLAlchemy model to domain entity"""
        meetings = []
        if db_course.meetings:
            for meeting_data in db_course.meetings:
                meetings.append(Meeting(
                    days=meeting_data.get('days', ''),
                    start_time=meeting_data.get('start_time', ''),
                    end_time=meeting_data.get('end_time', ''),
                    location=meeting_data.get('location', '')
                ))
        
        return CourseEntity(
            id=db_course.id,
            course_id=db_course.course_id,
            course_offer_nbr=db_course.course_offer_nbr,
            strm=db_course.strm,
            session_code=db_course.session_code,
            subject=db_course.subject,
            catalog_nbr=db_course.catalog_nbr,
            title=db_course.title,
            description=db_course.description,
            class_section=db_course.class_section,
            class_nbr=db_course.class_nbr,
            units=db_course.units,
            enrollment_total=db_course.enrollment_total,
            enrollment_available=db_course.enrollment_available,
            class_capacity=db_course.class_capacity,
            waitlist_total=db_course.waitlist_total,
            waitlist_capacity=db_course.waitlist_capacity,
            meetings=meetings,
            instructor=db_course.instructor,
            instruction_mode=db_course.instruction_mode,
            location=db_course.location,
            enrollment_status=db_course.enrollment_status,
            class_type=db_course.class_type,
            ge_attributes=db_course.ge_attributes or [],
            prerequisites=db_course.prerequisites,
            semester=db_course.semester,
            last_updated=db_course.last_updated
        )
    
    def from_entity(self, entity: CourseEntity) -> Dict[str, Any]:
        """Convert domain entity to database model data"""
        meetings_data = []
        if entity.meetings:
            for meeting in entity.meetings:
                meetings_data.append({
                    'days': meeting.days,
                    'start_time': meeting.start_time,
                    'end_time': meeting.end_time,
                    'location': meeting.location
                })
        
        return {
            'course_id': entity.course_id,
            'course_offer_nbr': entity.course_offer_nbr,
            'strm': entity.strm,
            'session_code': entity.session_code,
            'subject': entity.subject,
            'catalog_nbr': entity.catalog_nbr,
            'title': entity.title,
            'description': entity.description,
            'class_section': entity.class_section,
            'class_nbr': entity.class_nbr,
            'units': entity.units,
            'enrollment_total': entity.enrollment_total,
            'enrollment_available': entity.enrollment_available,
            'class_capacity': entity.class_capacity,
            'waitlist_total': entity.waitlist_total,
            'waitlist_capacity': entity.waitlist_capacity,
            'meetings': meetings_data,
            'instructor': entity.instructor,
            'instruction_mode': entity.instruction_mode,
            'location': entity.location,
            'enrollment_status': entity.enrollment_status,
            'class_type': entity.class_type,
            'ge_attributes': entity.ge_attributes,
            'prerequisites': entity.prerequisites,
            'semester': entity.semester,
            'last_updated': entity.last_updated or datetime.now()
        }
    
    async def find_by_class_nbr(self, session: AsyncSession, class_nbr: int) -> Optional[CourseEntity]:
        """Find a course by class number"""
        try:
            db_course = await self.find_by_field(session, 'class_nbr', class_nbr)
            if db_course:
                return self.to_entity(db_course[0])
            return None
        except Exception as e:
            logger.error(f"Error finding course by class number: {str(e)}")
            return None
    
    async def find_by_subject_and_catalog(
        self, 
        session: AsyncSession, 
        subject: str, 
        catalog_nbr: str
    ) -> List[CourseEntity]:
        """Find courses by subject and catalog number"""
        try:
            db_courses = await self.find_by_fields(session, {
                'subject': subject,
                'catalog_nbr': catalog_nbr
            })
            return [self.to_entity(course) for course in db_courses]
        except Exception as e:
            logger.error(f"Error finding courses by subject and catalog: {str(e)}")
            return []
    
    async def search_courses(
        self, 
        session: AsyncSession, 
        params: Dict[str, Any],
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[CourseEntity]:
        """Search courses with various filters"""
        try:
            query = select(Course)
            
            # Apply filters
            conditions = []
            
            if params.get('semester'):
                conditions.append(Course.semester == params['semester'])
            
            if params.get('subject'):
                conditions.append(Course.subject == params['subject'])
            
            if params.get('catalog_number'):
                conditions.append(Course.catalog_nbr == params['catalog_number'])
            
            if params.get('instructor'):
                conditions.append(Course.instructor.ilike(f"%{params['instructor']}%"))
            
            if params.get('has_seats'):
                conditions.append(Course.enrollment_available > 0)
            
            if params.get('instruction_mode'):
                conditions.append(Course.instruction_mode == params['instruction_mode'])
            
            if params.get('ge_attribute'):
                # Search in JSON array for general education attribute
                conditions.append(
                    Course.ge_attributes.op('@>')([params['ge_attribute']])
                )
            
            if params.get('keyword'):
                keyword = f"%{params['keyword']}%"
                conditions.append(
                    or_(
                        Course.title.ilike(keyword),
                        Course.description.ilike(keyword)
                    )
                )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            db_courses = result.scalars().all()
            
            return [self.to_entity(course) for course in db_courses]
            
        except Exception as e:
            logger.error(f"Error searching courses: {str(e)}")
            return []
    
    async def get_courses_by_class_numbers(
        self, 
        session: AsyncSession, 
        class_numbers: List[int]
    ) -> List[CourseEntity]:
        """Get multiple courses by their class numbers"""
        try:
            db_courses = await self.find_by_fields(session, {
                'class_nbr': class_numbers
            })
            return [self.to_entity(course) for course in db_courses]
        except Exception as e:
            logger.error(f"Error getting courses by class numbers: {str(e)}")
            return []
    
    async def update_enrollment_info(
        self, 
        session: AsyncSession, 
        class_nbr: int, 
        enrollment_data: Dict[str, int]
    ) -> bool:
        """Update enrollment information for a course"""
        try:
            # Find the course by class_nbr
            query = select(Course).where(Course.class_nbr == class_nbr)
            result = await session.execute(query)
            course = result.scalar_one_or_none()
            
            if not course:
                return False
            
            # Update enrollment fields
            if 'enrollment_total' in enrollment_data:
                course.enrollment_total = enrollment_data['enrollment_total']
            if 'enrollment_available' in enrollment_data:
                course.enrollment_available = enrollment_data['enrollment_available']
            if 'waitlist_total' in enrollment_data:
                course.waitlist_total = enrollment_data['waitlist_total']
            
            course.last_updated = datetime.now()
            
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating enrollment info: {str(e)}")
            return False
    
    async def create_course(self, session: AsyncSession, course_entity: CourseEntity) -> CourseEntity:
        """Create a new course from entity"""
        try:
            course_data = self.from_entity(course_entity)
            db_course = await self.create(session, **course_data)
            return self.to_entity(db_course)
        except Exception as e:
            logger.error(f"Error creating course: {str(e)}")
            raise
    
    async def create_courses_bulk(
        self, 
        session: AsyncSession, 
        course_entities: List[CourseEntity]
    ) -> List[CourseEntity]:
        """Create multiple courses in bulk"""
        try:
            courses_data = [self.from_entity(entity) for entity in course_entities]
            db_courses = await self.create_many(session, courses_data)
            return [self.to_entity(course) for course in db_courses]
        except Exception as e:
            logger.error(f"Error creating courses in bulk: {str(e)}")
            raise
    
    async def get_distinct_subjects(self, session: AsyncSession) -> List[str]:
        """Get all distinct subjects/departments"""
        try:
            query = select(Course.subject).distinct().where(Course.subject.isnot(None))
            result = await session.execute(query)
            return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Error getting distinct subjects: {str(e)}")
            return []
    
    async def get_courses_by_semester(
        self, 
        session: AsyncSession, 
        semester: str,
        limit: Optional[int] = None
    ) -> List[CourseEntity]:
        """Get all courses for a specific semester"""
        try:
            db_courses = await self.find_by_field(session, 'semester', semester, limit)
            return [self.to_entity(course) for course in db_courses]
        except Exception as e:
            logger.error(f"Error getting courses by semester: {str(e)}")
            return []