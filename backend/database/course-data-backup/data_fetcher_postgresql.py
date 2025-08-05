import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv
import time
import random
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path to import postgresql_client
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from postgresql_client import PostgreSQLClient

class PostgreSQLDataFetcher:
    """
    Enhanced DataFetcher that writes directly to PostgreSQL using the normalized schema.
    This replaces the Supabase-based approach with proper relational data storage.
    """
    
    def __init__(self, strm: str, num_pages_in_batch: int = 150, start_page: int = 1):
        load_dotenv()
        
        self.strm = strm
        self.num_pages_in_batch = num_pages_in_batch
        self.start_page = start_page
        self.db_client = PostgreSQLClient()
        
        # Initialize term for this semester
        self.term_id = self._initialize_term()
        
        # Statistics tracking
        self.stats = {
            'courses_fetched': 0,
            'courses_processed': 0,
            'sections_processed': 0,
            'meetings_processed': 0,
            'errors': []
        }
        
        # Cache for catalog IDs to avoid repeated lookups
        self.catalog_cache = {}
        self.offering_cache = {}

    def _initialize_term(self) -> int:
        """Initialize or get the term record for this semester"""
        semester_name, semester_code = self.db_client.parse_semester_code(self.strm)
        
        return self.db_client.upsert_term(
            code=semester_code,
            name=semester_name,
            session='Regular'
        )

    def get_base_url(self) -> str:
        """Get the base URL for SIS API calls"""
        return f"https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term={self.strm}"

    async def fetch_courses(self, session: aiohttp.ClientSession, page: int, max_retries: int = 8) -> Dict[str, Any]:
        """Fetch course data from SIS for a specific page"""
        url = self.get_base_url() + f"&page={page}"
        print(f"Fetching data for page {page}")
        
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid rate limiting
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        # Check if response is JSON
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type or 'text/json' in content_type:
                            data = await response.json()
                            print(f"Got {len(data.get('classes', []))} results for page {page}")
                            return data
                        else:
                            # Got HTML instead of JSON (likely rate limited)
                            text = await response.text()
                            if 'login' in text.lower() or 'error' in text.lower():
                                print(f"Rate limited on page {page}, attempt {attempt + 1}/{max_retries}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(random.uniform(5, 15))
                                    continue
                                else:
                                    print(f"Failed to fetch page {page} after {max_retries} attempts")
                                    return {"classes": []}
                            else:
                                print(f"Unexpected response type for page {page}: {content_type}")
                                return {"classes": []}
                    else:
                        print(f"Failed to fetch data for page {page}, status: {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(2, 5))
                            continue
                        return {"classes": []}
                        
            except asyncio.TimeoutError:
                print(f"Timeout on page {page}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(3, 8))
                    continue
                return {"classes": []}
            except Exception as e:
                print(f"Error fetching page {page}, attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(2, 5))
                    continue
                return {"classes": []}
        
        return {"classes": []}

    def parse_units(self, units_str: str) -> tuple:
        """Parse units string to min/max credits"""
        if not units_str or units_str == '0':
            return None, None
            
        try:
            if '-' in units_str:
                min_units, max_units = units_str.split('-', 1)
                return float(min_units.strip()), float(max_units.strip())
            else:
                units = float(units_str)
                return units, units
        except (ValueError, AttributeError):
            return None, None

    def get_or_create_catalog_course(self, course_data: Dict[str, Any]) -> Optional[int]:
        """Get or create a course catalog entry"""
        subject = course_data.get('subject', '')
        catalog_nbr = course_data.get('catalog_nbr', '')
        
        if not subject or not catalog_nbr:
            return None
            
        # Check cache first
        cache_key = f"{subject}:{catalog_nbr}"
        if cache_key in self.catalog_cache:
            return self.catalog_cache[cache_key]
        
        # Check if course already exists
        catalog_id = self.db_client.get_or_create_catalog_id(subject, catalog_nbr)
        
        if not catalog_id:
            # Create new catalog entry
            title = course_data.get('descr', '')
            topic = course_data.get('topic')
            units_str = course_data.get('units', '')
            min_credits, max_credits = self.parse_units(units_str)
            
            # Build attributes from available data
            attributes = {}
            if course_data.get('acad_group'):
                attributes['academic_group'] = course_data['acad_group']
            if course_data.get('acad_org'):
                attributes['academic_organization'] = course_data['acad_org']
            if course_data.get('crse_attr_value'):
                attributes['course_attributes'] = course_data['crse_attr_value']
            
            catalog_id = self.db_client.upsert_course_catalog(
                subject=subject,
                catalog_number=catalog_nbr,
                title=title,
                description=topic,
                min_credits=min_credits,
                max_credits=max_credits,
                attributes=attributes if attributes else None
            )
        
        # Cache the result
        self.catalog_cache[cache_key] = catalog_id
        return catalog_id

    def get_or_create_offering(self, catalog_id: int, course_data: Dict[str, Any]) -> int:
        """Get or create a course offering for this term"""
        cache_key = f"{catalog_id}:{self.term_id}"
        if cache_key in self.offering_cache:
            return self.offering_cache[cache_key]
        
        topic = course_data.get('topic')
        grading_basis = 'Graded'  # Default, could be enhanced based on more data
        
        offering_id = self.db_client.upsert_course_offering(
            term_id=self.term_id,
            catalog_id=catalog_id,
            topic=topic,
            grading_basis=grading_basis
        )
        
        self.offering_cache[cache_key] = offering_id
        return offering_id

    def convert_time_format(self, time_str: str) -> Optional[str]:
        """Convert time from '05:00 PM' to '17:00:00' format"""
        if not time_str or time_str.strip() == '':
            return None
            
        try:
            time_obj = datetime.strptime(time_str.strip(), '%I:%M %p')
            return time_obj.strftime('%H:%M:%S')
        except ValueError:
            return None

    def convert_date_format(self, date_str: str) -> Optional[str]:
        """Convert date from 'MM/DD/YYYY' to 'YYYY-MM-DD' format"""
        if not date_str or date_str.strip() == '':
            return None
            
        try:
            date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None

    def process_course_data(self, course_data: Dict[str, Any]) -> bool:
        """Process a single course record from SIS"""
        try:
            # Get or create catalog course
            catalog_id = self.get_or_create_catalog_course(course_data)
            if not catalog_id:
                return False
            
            # Get or create offering
            offering_id = self.get_or_create_offering(catalog_id, course_data)
            
            # Process section data
            section_number = course_data.get('class_section', '')
            component = course_data.get('component', 'LEC')  # Default to lecture
            section_type = course_data.get('section_type', 'Lecture')
            
            if not section_number:
                print(f"Skipping course without section number: {course_data.get('subject')} {course_data.get('catalog_nbr')}")
                return False
            
            # Determine section status
            enrollment_total = course_data.get('enrollment_total', 0)
            class_capacity = course_data.get('class_capacity', 0)
            
            if enrollment_total >= class_capacity and class_capacity > 0:
                status = 'Closed'
            else:
                status = 'Open'
            
            # Create section
            section_id = self.db_client.upsert_section(
                offering_id=offering_id,
                component=component,
                section_number=section_number,
                total_seats=class_capacity if class_capacity > 0 else None,
                waitlist_capacity=course_data.get('wait_cap'),
                status=status
            )
            
            # Process meeting patterns
            meetings = course_data.get('meetings', [])
            for meeting in meetings:
                self.process_meeting_pattern(meeting, section_id)
            
            # Create enrollment snapshot
            seats_available = max(0, class_capacity - enrollment_total) if class_capacity > 0 else None
            wait_total = course_data.get('wait_tot', 0)
            wait_capacity = course_data.get('wait_cap', 0)
            waitlist_available = max(0, wait_capacity - wait_total) if wait_capacity > 0 else None
            
            self.db_client.insert_section_snapshot(
                section_id=section_id,
                seats_avail=seats_available,
                waitlist_avail=waitlist_available,
                captured_at=datetime.now()
            )
            
            self.stats['sections_processed'] += 1
            return True
            
        except Exception as e:
            error_msg = f"Error processing course {course_data.get('subject', '')} {course_data.get('catalog_nbr', '')}: {e}"
            self.stats['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False

    def process_meeting_pattern(self, meeting_data: Dict[str, Any], section_id: int):
        """Process a meeting pattern for a section"""
        try:
            days = meeting_data.get('days', '')
            day_mask = self.db_client.parse_day_mask(days)
            
            start_time = self.convert_time_format(meeting_data.get('start_time'))
            end_time = self.convert_time_format(meeting_data.get('end_time'))
            start_date = self.convert_date_format(meeting_data.get('start_dt'))
            end_date = self.convert_date_format(meeting_data.get('end_dt'))
            
            # Build location string
            building = meeting_data.get('bldg_cd', '')
            room = meeting_data.get('room', '')
            facility_descr = meeting_data.get('facility_descr', '')
            
            location = facility_descr if facility_descr else f"{building} {room}".strip()
            if not location or location == ' ':
                location = None
            
            self.db_client.insert_meeting_pattern(
                section_id=section_id,
                day_mask=day_mask,
                start_time=start_time,
                end_time=end_time,
                start_date=start_date,
                end_date=end_date,
                location=location
            )
            
            self.stats['meetings_processed'] += 1
            
        except Exception as e:
            error_msg = f"Error processing meeting pattern: {e}"
            self.stats['errors'].append(error_msg)
            print(f"Warning: {error_msg}")

    async def get_all_courses_in_semester(self):
        """Fetch all courses from SIS and store in PostgreSQL"""
        print(f"Starting data fetch for semester {self.strm}")
        print(f"Target term ID: {self.term_id}")
        
        batch_size = self.num_pages_in_batch
        
        async with aiohttp.ClientSession() as session:
            in_progress = True
            iteration = 0
            page_count = 0
            courses_in_batch = []
            
            while in_progress:
                start_page = self.start_page + iteration * batch_size
                end_page = batch_size + start_page
                print(f"\nFetching pages {start_page} to {end_page}")
                
                # Process pages sequentially to avoid overwhelming the server
                for page in range(start_page, end_page):
                    response_data = await self.fetch_courses(session, page)
                    
                    classes = response_data.get("classes", [])
                    if len(classes) == 0:
                        in_progress = False
                        print(f"Page {page} had no results, stopping fetch")
                        break
                    else:
                        courses_in_batch.extend(classes)
                        self.stats['courses_fetched'] += len(classes)
                        page_count += 1
                        
                        # Process and insert every 5 pages
                        if page_count % 5 == 0:
                            print(f"Processing batch of {len(courses_in_batch)} courses from pages {start_page} to {page}")
                            await self.process_course_batch(courses_in_batch)
                            courses_in_batch = []
                
                # Add delay between batches
                if in_progress:
                    print(f"Completed batch {iteration + 1}, waiting before next batch...")
                    await asyncio.sleep(random.uniform(10, 20))
                
                iteration += 1
            
            # Process any remaining courses
            if courses_in_batch:
                print(f"Processing final batch of {len(courses_in_batch)} courses")
                await self.process_course_batch(courses_in_batch)
            
            print("Done fetching data from SIS")

    async def process_course_batch(self, courses: List[Dict[str, Any]]):
        """Process a batch of courses"""
        for course in courses:
            if self.process_course_data(course):
                self.stats['courses_processed'] += 1
        
        print(f"Processed {len(courses)} courses. Total processed: {self.stats['courses_processed']}")

    def print_statistics(self):
        """Print final statistics"""
        print("\n=== Data Fetch Statistics ===")
        print(f"Courses fetched from SIS: {self.stats['courses_fetched']}")
        print(f"Courses successfully processed: {self.stats['courses_processed']}")
        print(f"Sections processed: {self.stats['sections_processed']}")
        print(f"Meeting patterns processed: {self.stats['meetings_processed']}")
        print(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\nRecent errors:")
            for error in self.stats['errors'][-5]:  # Show last 5 errors
                print(f"  - {error}")

    def run(self):
        """Run the complete data fetch and processing pipeline"""
        try:
            # Test database connection
            if not self.db_client.test_connection():
                print("✗ Database connection failed")
                return False
            
            print("✓ Database connection successful")
            
            # Run the async data fetching
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.get_all_courses_in_semester())
            loop.close()
            
            # Print final statistics
            self.print_statistics()
            
            print("\n✓ Successfully completed data fetch and insertion")
            return True
            
        except Exception as e:
            print(f"\n✗ Data fetch failed: {e}")
            return False
        finally:
            # Clean up database connection
            if hasattr(self.db_client, 'close'):
                self.db_client.close()

def main():
    """Main entry point for running the PostgreSQL data fetcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch UVA SIS data and store in PostgreSQL')
    parser.add_argument('--strm', required=True, help='Semester code (e.g., 1228)')
    parser.add_argument('--batch-size', type=int, default=150, help='Pages per batch')
    parser.add_argument('--start-page', type=int, default=1, help='Starting page number')
    
    args = parser.parse_args()
    
    try:
        fetcher = PostgreSQLDataFetcher(
            strm=args.strm,
            num_pages_in_batch=args.batch_size,
            start_page=args.start_page
        )
        
        success = fetcher.run()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nData fetch interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Data fetch failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()