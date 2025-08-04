#!/usr/bin/env python3
"""
Migration script to transfer SIS course data from JSON files to PostgreSQL.
This script processes the existing JSON data structure and maps it to the normalized PostgreSQL schema.
"""

import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from postgresql_client import PostgreSQLClient

class SISDataMigrator:
    def __init__(self, data_directory: str):
        self.data_directory = Path(data_directory)
        self.db_client = PostgreSQLClient()
        self.stats = {
            'terms_processed': 0,
            'courses_processed': 0,
            'sections_processed': 0,
            'meetings_processed': 0,
            'errors': []
        }
        
    def validate_data_directory(self) -> bool:
        """Validate that the data directory exists and contains expected structure"""
        if not self.data_directory.exists():
            print(f"Error: Data directory '{self.data_directory}' does not exist")
            return False
            
        # Look for semester directories (4-digit codes)
        semester_dirs = [d for d in self.data_directory.iterdir() 
                        if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
        
        if not semester_dirs:
            print(f"Error: No semester directories found in '{self.data_directory}'")
            return False
            
        print(f"Found {len(semester_dirs)} semester directories: {[d.name for d in semester_dirs]}")
        return True

    def test_database_connection(self) -> bool:
        """Test database connection before starting migration"""
        print("Testing database connection...")
        if self.db_client.test_connection():
            print("✓ Database connection successful")
            return True
        else:
            print("✗ Database connection failed")
            return False

    def parse_units(self, units_str: str) -> tuple:
        """Parse units string to min/max credits"""
        if not units_str or units_str == '0':
            return None, None
            
        try:
            # Handle range format like "3-4" or single values like "3"
            if '-' in units_str:
                min_units, max_units = units_str.split( '-', 2)
                return float(min_units.strip()), float(max_units.strip())
            else:
                units = float(units_str)
                return units, units
        except (ValueError, AttributeError):
            return None, None

    def process_semester(self, semester_dir: Path) -> bool:
        """Process all courses in a semester directory"""
        semester_code = semester_dir.name
        semester_name, semester_abbrev = self.db_client.parse_semester_code(semester_code)
        
        print(f"\nProcessing semester: {semester_name} ({semester_code})")
        
        try:
            # Create or update term record
            term_id = self.db_client.upsert_term(
                code=semester_abbrev,
                name=semester_name,
                session='Regular'
            )
            self.stats['terms_processed'] += 1
            
            # Process each department JSON file
            json_files = list(semester_dir.glob('*.json'))
            json_files = [f for f in json_files if f.name not in ['metadata.json', 'latest_sem.json', 'departments.json']]
            
            print(f"Found {len(json_files)} department files to process")
            
            for json_file in json_files:
                if not self.process_department_file(json_file, term_id):
                    return False
                    
            return True
            
        except Exception as e:
            error_msg = f"Error processing semester {semester_code}: {e}"
            self.stats['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False

    def process_department_file(self, json_file: Path, term_id: int) -> bool:
        """Process a single department JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # The JSON structure is: {department_name: [courses]}
            for department_name, courses in data.items():
                print(f"  Processing {department_name}: {len(courses)} courses")
                
                for course_data in courses:
                    if not self.process_course(course_data, term_id):
                        continue  # Continue with next course on error
                        
            return True
            
        except Exception as e:
            error_msg = f"Error processing file {json_file}: {e}"
            self.stats['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False

    def process_course(self, course_data: Dict[str, Any], term_id: int) -> bool:
        """Process a single course and its sessions"""
        try:
            subject = course_data.get('subject', '')
            catalog_number = course_data.get('catalog_number', '')
            title = course_data.get('descr', '')
            
            if not all([subject, catalog_number, title]):
                print(f"    Skipping course with missing data: {subject} {catalog_number}")
                return False
            
            # Parse credits
            units_str = course_data.get('units', '')
            min_credits, max_credits = self.parse_units(units_str)
            
            # Create or update course catalog entry
            catalog_id = self.db_client.upsert_course_catalog(
                subject=subject,
                catalog_number=catalog_number,
                title=title,
                description=course_data.get('topic'),
                min_credits=min_credits,
                max_credits=max_credits,
                attributes={}
            )
            
            # Create course offering for this term
            offering_id = self.db_client.upsert_course_offering(
                term_id=term_id,
                catalog_id=catalog_id,
                topic=course_data.get('topic'),
                grading_basis='Graded'
            )
            
            # Process all sessions (sections) for this course
            sessions = course_data.get('sessions', [])
            for session in sessions:
                if not self.process_session(session, offering_id):
                    continue  # Continue with next session on error
                    
            self.stats['courses_processed'] += 1
            return True
            
        except Exception as e:
            error_msg = f"Error processing course {subject} {catalog_number}: {e}"
            self.stats['errors'].append(error_msg)
            print(f"    ✗ {error_msg}")
            return False

    def process_session(self, session_data: Dict[str, Any], offering_id: int) -> bool:
        """Process a course session (section)"""
        try:
            section_number = session_data.get('class_section', '')
            component = session_data.get('section_type', 'Lecture')
            
            if not section_number:
                print(f"      Skipping session with missing section number")
                return False
            
            # Determine section status based on enrollment
            enrollment_total = session_data.get('enrollment_total', 0)
            class_capacity = session_data.get('class_capacity', 0)
            
            if enrollment_total >= class_capacity:
                status = 'Closed' if class_capacity > 0 else 'Open'
            else:
                status = 'Open'
            
            # Create section
            section_id = self.db_client.upsert_section(
                offering_id=offering_id,
                component=component,
                section_number=section_number,
                total_seats=class_capacity,
                waitlist_capacity=session_data.get('wait_cap'),
                status=status
            )
            
            # Process meetings for this section
            meetings = session_data.get('meetings', [])
            for meeting in meetings:
                self.process_meeting(meeting, section_id)
            
            # Create enrollment snapshot
            seats_available = max(0, class_capacity - enrollment_total) if class_capacity else None
            waitlist_available = session_data.get('wait_cap', 0) - session_data.get('wait_tot', 0)
            waitlist_available = max(0, waitlist_available) if waitlist_available else None
            
            self.db_client.insert_section_snapshot(
                section_id=section_id,
                seats_avail=seats_available,
                waitlist_avail=waitlist_available,
                captured_at=datetime.now()
            )
            
            self.stats['sections_processed'] += 1
            return True
            
        except Exception as e:
            error_msg = f"Error processing session: {e}"
            self.stats['errors'].append(error_msg)
            print(f"      ✗ {error_msg}")
            return False

    def process_meeting(self, meeting_data: Dict[str, Any], section_id: int):
        """Process a meeting pattern for a section"""
        try:
            days = meeting_data.get('days', '')
            day_mask = self.db_client.parse_day_mask(days)
            
            start_time = meeting_data.get('start_time')
            end_time = meeting_data.get('end_time')
            start_date = meeting_data.get('start_dt')
            end_date = meeting_data.get('end_dt')
            
            # Build location string
            building = meeting_data.get('bldg_cd', '')
            room = meeting_data.get('room', '')
            facility_descr = meeting_data.get('facility_descr', '')
            
            location = facility_descr if facility_descr else f"{building} {room}".strip()
            if not location or location == ' ':
                location = None
            
            # Convert time format from "HH:MM AM/PM" to "HH:MM:SS" 24-hour format
            start_time_24 = self.convert_time_format(start_time) if start_time else None
            end_time_24 = self.convert_time_format(end_time) if end_time else None
            
            # Convert date format from "MM/DD/YYYY" to "YYYY-MM-DD"
            start_date_iso = self.convert_date_format(start_date) if start_date else None
            end_date_iso = self.convert_date_format(end_date) if end_date else None
            
            self.db_client.insert_meeting_pattern(
                section_id=section_id,
                day_mask=day_mask,
                start_time=start_time_24,
                end_time=end_time_24,
                start_date=start_date_iso,
                end_date=end_date_iso,
                location=location
            )
            
            self.stats['meetings_processed'] += 1
            
        except Exception as e:
            error_msg = f"Error processing meeting: {e}"
            self.stats['errors'].append(error_msg)
            print(f"        ✗ {error_msg}")

    def convert_time_format(self, time_str: str) -> Optional[str]:
        """Convert time from '05:00 PM' to '17:00:00' format"""
        if not time_str or time_str.strip() == '':
            return None
            
        try:
            # Parse and convert to 24-hour format
            time_obj = datetime.strptime(time_str.strip(), '%I:%M %p')
            return time_obj.strftime('%H:%M:%S')
        except ValueError:
            return None

    def convert_date_format(self, date_str: str) -> Optional[str]:
        """Convert date from 'MM/DD/YYYY' to 'YYYY-MM-DD' format"""
        if not date_str or date_str.strip() == '':
            return None
            
        try:
            # Parse and convert to ISO format
            date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None

    def run_migration(self, semester_filter: Optional[str] = None) -> bool:
        """Run the full migration process"""
        print("=== SIS Data Migration to PostgreSQL ===\n")
        
        try:
            # Validate prerequisites
            if not self.validate_data_directory():
                return False
                
            if not self.test_database_connection():
                return False
            
            # Get semester directories to process
            semester_dirs = [d for d in self.data_directory.iterdir() 
                            if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
            
            # Filter by semester if specified
            if semester_filter:
                semester_dirs = [d for d in semester_dirs if d.name == semester_filter]
                if not semester_dirs:
                    print(f"Error: Semester '{semester_filter}' not found")
                    return False
            
            # Sort semesters chronologically
            semester_dirs.sort(key=lambda x: x.name)
            
            print(f"Processing {len(semester_dirs)} semesters...")
            
            # Process each semester
            success = True
            for semester_dir in semester_dirs:
                if not self.process_semester(semester_dir):
                    success = False
                    # Continue with other semesters even if one fails
            
            # Print final statistics
            self.print_migration_stats()
            
            return success
            
        finally:
            # Clean up database connection
            if hasattr(self.db_client, 'close'):
                self.db_client.close()

    def print_migration_stats(self):
        """Print migration statistics"""
        print("\n=== Migration Statistics ===")
        print(f"Terms processed: {self.stats['terms_processed']}")
        print(f"Courses processed: {self.stats['courses_processed']}")
        print(f"Sections processed: {self.stats['sections_processed']}")
        print(f"Meeting patterns processed: {self.stats['meetings_processed']}")
        print(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print("\nErrors:")
            for error in self.stats['errors'][-10]:  # Show last 10 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more errors")

def main():
    parser = argparse.ArgumentParser(description='Migrate SIS JSON data to PostgreSQL')
    parser.add_argument('--data-dir', required=True, help='Path to data directory containing semester folders')
    parser.add_argument('--semester', help='Process only specific semester (e.g., 1228)')
    parser.add_argument('--dry-run', action='store_true', help='Validate data without inserting (not implemented)')
    
    args = parser.parse_args()
    
    try:
        migrator = SISDataMigrator(args.data_dir)
        success = migrator.run_migration(args.semester)
        
        if success:
            print("\n✓ Migration completed successfully!")
            sys.exit(0)
        else:
            print("\n✗ Migration completed with errors.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()