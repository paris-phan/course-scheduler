import requests
from typing import List, Dict, Any, Optional
from app.config import settings
from utils.logger import setup_logger
from utils.exceptions import SISAPIException

logger = setup_logger(__name__)


class SISAPIService:
    """Service for interacting with UVA's SIS API"""
    
    def __init__(self):
        self.base_url = settings.UVA_API_BASE_URL
        self.default_term = settings.UVA_API_TERM
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_courses(
        self,
        term: Optional[str] = None,
        subject: Optional[str] = None,
        catalog_number: Optional[str] = None,
        keyword: Optional[str] = None,
        instructor: Optional[str] = None,
        class_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for courses in the SIS API
        
        Args:
            term: Term code (e.g., "1258" for Fall 2025)
            subject: Subject/department code (e.g., "CS")
            catalog_number: Course number (e.g., "1110")
            keyword: Search keyword
            instructor: Instructor name
            class_number: Specific class number
            
        Returns:
            List of course dictionaries
        """
        try:
            params = {
                'page': 1,
                'start': 0,
                'limit': 200,
                'sortColumn': 'SUBJECT',
                'sortDirection': 'ASC',
                'strm': term or self.default_term
            }
            
            # Add optional search parameters
            if subject:
                params['subject'] = subject
            if catalog_number:
                params['catalog_nbr'] = catalog_number
            if keyword:
                params['keyword'] = keyword
            if instructor:
                params['instructor'] = instructor
            if class_number:
                params['class_nbr'] = class_number
            
            logger.info(f"Searching courses with params: {params}")
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            courses = data.get('data', [])
            
            logger.info(f"Found {len(courses)} courses")
            return courses
            
        except requests.RequestException as e:
            logger.error(f"SIS API request failed: {str(e)}")
            raise SISAPIException(f"Failed to search courses: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in course search: {str(e)}")
            raise SISAPIException(f"Course search failed: {str(e)}")
    
    def get_all_courses_for_term(self, term: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all courses for a given term
        
        Args:
            term: Term code (defaults to configured term)
            
        Returns:
            List of all courses in the term
        """
        all_courses = []
        page = 1
        
        try:
            while True:
                params = {
                    'page': page,
                    'start': (page - 1) * 200,
                    'limit': 200,
                    'sortColumn': 'SUBJECT',
                    'sortDirection': 'ASC',
                    'strm': term or self.default_term
                }
                
                response = self.session.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                courses = data.get('data', [])
                
                if not courses:
                    break
                
                all_courses.extend(courses)
                logger.info(f"Retrieved page {page} with {len(courses)} courses")
                
                # Check if we've reached the last page
                if len(courses) < 200:
                    break
                
                page += 1
            
            logger.info(f"Retrieved total of {len(all_courses)} courses for term {term or self.default_term}")
            return all_courses
            
        except Exception as e:
            logger.error(f"Failed to retrieve all courses: {str(e)}")
            raise SISAPIException(f"Failed to retrieve courses: {str(e)}")
    
    def parse_course_data(self, raw_course: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw course data from SIS API into a standardized format
        
        Args:
            raw_course: Raw course data from SIS API
            
        Returns:
            Parsed course dictionary
        """
        try:
            # Extract meeting information
            meetings = []
            if raw_course.get('meetings'):
                for meeting in raw_course['meetings']:
                    meetings.append({
                        'days': meeting.get('days', ''),
                        'start_time': meeting.get('start_time', ''),
                        'end_time': meeting.get('end_time', ''),
                        'location': meeting.get('location', '')
                    })
            
            # Extract general education attributes
            ge_attributes = []
            for key, value in raw_course.items():
                if key.startswith('ge_') and value:
                    ge_attributes.append(key.replace('ge_', '').upper())
            
            parsed_course = {
                'course_id': raw_course.get('crse_id'),
                'course_offer_nbr': raw_course.get('crse_offer_nbr'),
                'strm': raw_course.get('strm'),
                'session_code': raw_course.get('session_code'),
                'subject': raw_course.get('subject'),
                'catalog_nbr': raw_course.get('catalog_nbr'),
                'class_section': raw_course.get('class_section'),
                'class_nbr': raw_course.get('class_nbr'),
                'descr': raw_course.get('descr'),
                'units': raw_course.get('units'),
                'enrollment_total': raw_course.get('enrollment_total', 0),
                'enrollment_available': raw_course.get('enrollment_available', 0),
                'class_capacity': raw_course.get('class_capacity', 0),
                'waitlist_total': raw_course.get('waitlist_total', 0),
                'waitlist_capacity': raw_course.get('waitlist_capacity', 0),
                'meetings': meetings,
                'ge_attributes': ge_attributes,
                'instruction_mode': raw_course.get('instruction_mode'),
                'location': raw_course.get('location'),
                'instructor': self._parse_instructor(raw_course),
                'enrollment_status': raw_course.get('enrl_stat'),
                'class_type': raw_course.get('class_type')
            }
            
            return parsed_course
            
        except Exception as e:
            logger.error(f"Failed to parse course data: {str(e)}")
            raise SISAPIException(f"Course data parsing failed: {str(e)}")
    
    def _parse_instructor(self, course: Dict[str, Any]) -> str:
        """Extract instructor name from course data"""
        # Try different possible instructor fields
        instructor_fields = ['instructor', 'instructors', 'faculty']
        
        for field in instructor_fields:
            if field in course and course[field]:
                if isinstance(course[field], list):
                    return ', '.join(course[field])
                return str(course[field])
        
        return "TBA"
    
    def close(self):
        """Close the session"""
        self.session.close()