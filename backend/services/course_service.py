from typing import List, Optional, Dict, Any
from datetime import datetime
from core.schemas.course_schema import CourseSearchParams, CourseUpdate, CourseResponse
from database.repositories.course_repository import CourseRepository
from services.sis_api_service import SISAPIService
from core.models.course import Course, Meeting
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CourseService:
    """Service layer for course-related business logic"""
    
    def __init__(self):
        self.course_repo = CourseRepository()
        self.sis_api = SISAPIService()
    
    async def search_courses(
        self, 
        params: CourseSearchParams, 
        limit: int, 
        offset: int
    ) -> List[CourseResponse]:
        """Search courses with given parameters"""
        search_dict = params.dict(exclude_none=True)
        
        # First try to get from database
        courses = self.course_repo.search_courses(search_dict)
        
        # Apply pagination
        paginated_courses = courses[offset:offset + limit]
        
        # Convert to response schema
        return [CourseResponse.from_db(course) for course in paginated_courses]
    
    async def get_course_by_class_nbr(self, class_nbr: int) -> Optional[CourseResponse]:
        """Get a course by its class number"""
        course = self.course_repo.find_by_class_nbr(class_nbr)
        if course:
            return CourseResponse.from_db(course)
        return None
    
    async def get_courses_by_code(self, subject: str, catalog_nbr: str) -> List[CourseResponse]:
        """Get all sections of a course by subject and catalog number"""
        courses = self.course_repo.find_by_subject_and_catalog(subject, catalog_nbr)
        return [CourseResponse.from_db(course) for course in courses]
    
    async def sync_courses_from_sis(
        self, 
        term: str, 
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync courses from SIS API to database"""
        try:
            logger.info(f"Starting course sync for term {term}, subject: {subject or 'all'}")
            
            # Get courses from SIS
            if subject:
                raw_courses = self.sis_api.search_courses(term=term, subject=subject)
            else:
                raw_courses = self.sis_api.get_all_courses_for_term(term)
            
            logger.info(f"Retrieved {len(raw_courses)} courses from SIS")
            
            # Parse and prepare courses for insertion
            courses_to_save = []
            for raw_course in raw_courses:
                parsed = self.sis_api.parse_course_data(raw_course)
                
                # Create Course entity
                meetings = []
                for meeting_data in parsed.get('meetings', []):
                    meetings.append(Meeting(
                        days=meeting_data['days'],
                        start_time=meeting_data['start_time'],
                        end_time=meeting_data['end_time'],
                        location=meeting_data['location']
                    ))
                
                course = Course(
                    course_id=parsed['course_id'],
                    course_offer_nbr=parsed['course_offer_nbr'],
                    strm=parsed['strm'],
                    session_code=parsed['session_code'],
                    subject=parsed['subject'],
                    catalog_nbr=parsed['catalog_nbr'],
                    title=parsed['descr'],
                    description=parsed['descr'],
                    class_section=parsed['class_section'],
                    class_nbr=parsed['class_nbr'],
                    units=parsed['units'],
                    enrollment_total=parsed['enrollment_total'],
                    enrollment_available=parsed['enrollment_available'],
                    class_capacity=parsed['class_capacity'],
                    waitlist_total=parsed['waitlist_total'],
                    waitlist_capacity=parsed['waitlist_capacity'],
                    meetings=meetings,
                    instructor=parsed['instructor'],
                    instruction_mode=parsed['instruction_mode'],
                    location=parsed['location'],
                    enrollment_status=parsed['enrollment_status'],
                    class_type=parsed['class_type'],
                    ge_attributes=parsed['ge_attributes'],
                    semester=self._term_to_semester(term)
                )
                
                courses_to_save.append(course)
            
            # Save to database
            saved_courses = self.course_repo.create_many(courses_to_save)
            
            logger.info(f"Successfully saved {len(saved_courses)} courses to database")
            
            return {
                "status": "success",
                "courses_retrieved": len(raw_courses),
                "courses_saved": len(saved_courses),
                "term": term,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"Error syncing courses: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "courses_retrieved": 0,
                "courses_saved": 0
            }
    
    async def update_course(
        self, 
        class_nbr: int, 
        course_update: CourseUpdate
    ) -> Optional[CourseResponse]:
        """Update course information"""
        # Get existing course
        existing_course = self.course_repo.find_by_class_nbr(class_nbr)
        if not existing_course:
            return None
        
        # Apply updates
        update_dict = course_update.dict(exclude_none=True)
        for field, value in update_dict.items():
            if hasattr(existing_course, field):
                setattr(existing_course, field, value)
        
        # Save changes
        updated_course = self.course_repo.update(existing_course.id, existing_course)
        if updated_course:
            return CourseResponse.from_db(updated_course)
        return None
    
    async def refresh_enrollment(self, class_nbr: int) -> bool:
        """Refresh enrollment information for a course from SIS"""
        try:
            # Get current course info
            course = self.course_repo.find_by_class_nbr(class_nbr)
            if not course:
                return False
            
            # Search for the course in SIS
            raw_courses = self.sis_api.search_courses(
                term=course.strm,
                class_number=class_nbr
            )
            
            if not raw_courses:
                logger.warning(f"Course {class_nbr} not found in SIS")
                return False
            
            # Update enrollment info
            raw_course = raw_courses[0]
            enrollment_data = {
                'enrollment_total': raw_course.get('enrollment_total', 0),
                'available_seats': raw_course.get('enrollment_available', 0),
                'waitlist_total': raw_course.get('waitlist_total', 0)
            }
            
            return self.course_repo.update_enrollment_info(class_nbr, enrollment_data)
            
        except Exception as e:
            logger.error(f"Error refreshing enrollment for course {class_nbr}: {str(e)}")
            return False
    
    def _term_to_semester(self, term: str) -> str:
        """Convert term code to semester string"""
        # Term codes: 1258 = Fall 2025, 1252 = Spring 2025, etc.
        year = "20" + term[1:3]
        term_digit = term[3]
        
        if term_digit == "2":
            return f"Spring {year}"
        elif term_digit == "8":
            return f"Fall {year}"
        elif term_digit == "6":
            return f"Summer {year}"
        elif term_digit == "1":
            return f"J-Term {year}"
        else:
            return f"Term {term}"