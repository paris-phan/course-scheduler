from typing import List, Optional, Dict, Any
from datetime import datetime
from database.repositories.base_repository import BaseRepository
from core.models.course import Course, Meeting
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CourseRepository(BaseRepository[Course]):
    """Repository for course database operations"""
    
    def __init__(self):
        super().__init__("courses")
    
    def to_entity(self, data: Dict[str, Any]) -> Course:
        """Convert database row to Course entity"""
        meetings = []
        if data.get('meeting_days_and_times'):
            for meeting_data in data['meeting_days_and_times']:
                meetings.append(Meeting(
                    days=meeting_data.get('days', ''),
                    start_time=meeting_data.get('start_time', ''),
                    end_time=meeting_data.get('end_time', ''),
                    location=meeting_data.get('location', '')
                ))
        
        return Course(
            id=data.get('id'),
            course_id=data.get('course_id'),
            course_offer_nbr=data.get('course_offer_nbr'),
            strm=data.get('strm'),
            session_code=data.get('session_code'),
            subject=data.get('dept_name'),  # Note: mapped from dept_name
            catalog_nbr=data.get('course_number'),  # Note: mapped from course_number
            title=data.get('course_title'),
            description=data.get('course_description'),
            class_section=data.get('class_section'),
            class_nbr=data.get('class_nbr'),
            units=data.get('units'),
            enrollment_total=data.get('enrollment_total', 0),
            enrollment_available=data.get('available_seats', 0),  # Note: mapped from available_seats
            class_capacity=data.get('total_seats', 0),  # Note: mapped from total_seats
            waitlist_total=data.get('waitlist_total', 0),
            waitlist_capacity=data.get('waitlist_capacity', 0),
            meetings=meetings,
            instructor=data.get('instructor', 'TBA'),
            instruction_mode=data.get('instruction_mode'),
            location=data.get('location'),
            enrollment_status=data.get('enrollment_status'),
            class_type=data.get('class_type'),
            ge_attributes=data.get('gened_attributes', []),
            prerequisites=data.get('prerequisites'),
            semester=data.get('semester'),
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else None
        )
    
    def to_dict(self, entity: Course) -> Dict[str, Any]:
        """Convert Course entity to dictionary for database operations"""
        return {
            'course_id': entity.course_id,
            'course_offer_nbr': entity.course_offer_nbr,
            'strm': entity.strm,
            'session_code': entity.session_code,
            'dept_name': entity.subject,  # Note: mapped to dept_name
            'course_number': entity.catalog_nbr,  # Note: mapped to course_number
            'course_title': entity.title,
            'course_description': entity.description,
            'class_section': entity.class_section,
            'class_nbr': entity.class_nbr,
            'units': entity.units,
            'enrollment_total': entity.enrollment_total,
            'available_seats': entity.enrollment_available,  # Note: mapped to available_seats
            'total_seats': entity.class_capacity,  # Note: mapped to total_seats
            'waitlist_total': entity.waitlist_total,
            'waitlist_capacity': entity.waitlist_capacity,
            'meeting_days_and_times': [
                {
                    'days': m.days,
                    'start_time': m.start_time,
                    'end_time': m.end_time,
                    'location': m.location
                } for m in entity.meetings
            ],
            'instructor': entity.instructor,
            'instruction_mode': entity.instruction_mode,
            'location': entity.location,
            'enrollment_status': entity.enrollment_status,
            'class_type': entity.class_type,
            'gened_attributes': entity.ge_attributes,
            'prerequisites': entity.prerequisites,
            'semester': entity.semester,
            'last_updated': datetime.now().isoformat()
        }
    
    def find_by_class_nbr(self, class_nbr: int) -> Optional[Course]:
        """Find a course by class number"""
        try:
            response = self.db.get_table(self.table_name).select("*").eq("class_nbr", class_nbr).execute()
            
            if response.data:
                return self.to_entity(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error finding course by class number: {str(e)}")
            return None
    
    def find_by_subject_and_catalog(self, subject: str, catalog_nbr: str) -> List[Course]:
        """Find courses by subject and catalog number"""
        try:
            response = (
                self.db.get_table(self.table_name)
                .select("*")
                .eq("dept_name", subject)
                .eq("course_number", catalog_nbr)
                .execute()
            )
            
            return [self.to_entity(row) for row in response.data]
        except Exception as e:
            logger.error(f"Error finding courses by subject and catalog: {str(e)}")
            return []
    
    def search_courses(self, params: Dict[str, Any]) -> List[Course]:
        """Search courses with various filters"""
        try:
            query = self.db.get_table(self.table_name).select("*")
            
            # Apply filters
            if params.get('semester'):
                query = query.eq('semester', params['semester'])
            
            if params.get('subject'):
                query = query.eq('dept_name', params['subject'])
            
            if params.get('catalog_number'):
                query = query.eq('course_number', params['catalog_number'])
            
            if params.get('instructor'):
                query = query.ilike('instructor', f"%{params['instructor']}%")
            
            if params.get('has_seats'):
                query = query.gt('available_seats', 0)
            
            if params.get('instruction_mode'):
                query = query.eq('instruction_mode', params['instruction_mode'])
            
            if params.get('ge_attribute'):
                query = query.contains('gened_attributes', [params['ge_attribute']])
            
            # Execute query
            response = query.execute()
            
            courses = [self.to_entity(row) for row in response.data]
            
            # Additional filtering for keyword search (done in memory)
            if params.get('keyword'):
                keyword = params['keyword'].lower()
                courses = [
                    c for c in courses
                    if keyword in (c.title or '').lower() 
                    or keyword in (c.description or '').lower()
                ]
            
            return courses
            
        except Exception as e:
            logger.error(f"Error searching courses: {str(e)}")
            return []
    
    def get_courses_by_class_numbers(self, class_numbers: List[int]) -> List[Course]:
        """Get multiple courses by their class numbers"""
        try:
            response = (
                self.db.get_table(self.table_name)
                .select("*")
                .in_('class_nbr', class_numbers)
                .execute()
            )
            
            return [self.to_entity(row) for row in response.data]
        except Exception as e:
            logger.error(f"Error getting courses by class numbers: {str(e)}")
            return []
    
    def update_enrollment_info(self, class_nbr: int, enrollment_data: Dict[str, int]) -> bool:
        """Update enrollment information for a course"""
        try:
            update_data = {
                'enrollment_total': enrollment_data.get('enrollment_total'),
                'available_seats': enrollment_data.get('available_seats'),
                'waitlist_total': enrollment_data.get('waitlist_total'),
                'last_updated': datetime.now().isoformat()
            }
            
            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}
            
            response = (
                self.db.get_table(self.table_name)
                .update(update_data)
                .eq('class_nbr', class_nbr)
                .execute()
            )
            
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error updating enrollment info: {str(e)}")
            return False