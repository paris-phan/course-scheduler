#!/usr/bin/env python3
"""
Validation and testing utilities for PostgreSQL course data migration.
Provides tools to verify data integrity, compare migration results, and validate schema compliance.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter

sys.path.append(os.path.dirname(__file__))
from postgresql_client import PostgreSQLClient

class DataValidator:
    """Validates data integrity and migration results"""
    
    def __init__(self):
        self.db_client = PostgreSQLClient()
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def validate_database_schema(self) -> bool:
        """Validate that all required tables and constraints exist"""
        print("Validating database schema...")
        
        required_tables = [
            'terms', 'course_catalog', 'course_offerings', 'sections',
            'meeting_patterns', 'section_snapshots', 'requisite_groups',
            'degrees', 'academic_plans', 'requirements', 'users'
        ]
        
        try:
            # Check if all required tables exist
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            """
            
            result = self.db_client.execute_query(query, fetch=True)
            existing_tables = {row['table_name'] for row in result}
            
            missing_tables = set(required_tables) - existing_tables
            if missing_tables:
                self.validation_results['failed'].append(f"Missing tables: {missing_tables}")
                return False
            else:
                self.validation_results['passed'].append("All required tables exist")
            
            # Check foreign key constraints
            constraint_query = """
            SELECT 
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            """
            
            constraints = self.db_client.execute_query(constraint_query, fetch=True)
            if len(constraints) > 0:
                self.validation_results['passed'].append(f"Found {len(constraints)} foreign key constraints")
            else:
                self.validation_results['warnings'].append("No foreign key constraints found")
            
            return True
            
        except Exception as e:
            self.validation_results['failed'].append(f"Schema validation failed: {e}")
            return False

    def validate_data_integrity(self) -> bool:
        """Validate referential integrity and data consistency"""
        print("Validating data integrity...")
        
        integrity_checks = [
            ("Course offerings reference valid terms", 
             "SELECT COUNT(*) as count FROM course_offerings co LEFT JOIN terms t ON co.term_id = t.id WHERE t.id IS NULL"),
            
            ("Course offerings reference valid catalog entries",
             "SELECT COUNT(*) as count FROM course_offerings co LEFT JOIN course_catalog cc ON co.catalog_id = cc.id WHERE cc.id IS NULL"),
            
            ("Sections reference valid offerings",
             "SELECT COUNT(*) as count FROM sections s LEFT JOIN course_offerings co ON s.offering_id = co.id WHERE co.id IS NULL"),
            
            ("Meeting patterns reference valid sections",
             "SELECT COUNT(*) as count FROM meeting_patterns mp LEFT JOIN sections s ON mp.section_id = s.id WHERE s.id IS NULL"),
            
            ("Section snapshots reference valid sections",
             "SELECT COUNT(*) as count FROM section_snapshots ss LEFT JOIN sections s ON ss.section_id = s.id WHERE s.id IS NULL")
        ]
        
        all_passed = True
        
        try:
            for check_name, query in integrity_checks:
                result = self.db_client.execute_query(query, fetch=True)
                orphan_count = result[0]['count'] if result else 0
                
                if orphan_count == 0:
                    self.validation_results['passed'].append(f"✓ {check_name}")
                else:
                    self.validation_results['failed'].append(f"✗ {check_name}: {orphan_count} orphaned records")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.validation_results['failed'].append(f"Integrity validation failed: {e}")
            return False

    def validate_course_data_completeness(self) -> bool:
        """Validate that essential course data is complete"""
        print("Validating course data completeness...")
        
        completeness_checks = [
            ("Courses have subjects", 
             "SELECT COUNT(*) as count FROM course_catalog WHERE subject IS NULL OR subject = ''"),
            
            ("Courses have catalog numbers",
             "SELECT COUNT(*) as count FROM course_catalog WHERE catalog_number IS NULL OR catalog_number = ''"),
            
            ("Courses have titles",
             "SELECT COUNT(*) as count FROM course_catalog WHERE title IS NULL OR title = ''"),
            
            ("Sections have valid components",
             "SELECT COUNT(*) as count FROM sections WHERE component IS NULL OR component = ''"),
            
            ("Meeting patterns have day masks or times",
             "SELECT COUNT(*) as count FROM meeting_patterns WHERE (day_mask IS NULL OR day_mask = '') AND (start_time IS NULL AND end_time IS NULL)")
        ]
        
        all_passed = True
        
        try:
            for check_name, query in completeness_checks:
                result = self.db_client.execute_query(query, fetch=True)
                incomplete_count = result[0]['count'] if result else 0
                
                if incomplete_count == 0:
                    self.validation_results['passed'].append(f"✓ {check_name}")
                elif incomplete_count < 10:  # Small number might be acceptable
                    self.validation_results['warnings'].append(f"⚠ {check_name}: {incomplete_count} incomplete records")
                else:
                    self.validation_results['failed'].append(f"✗ {check_name}: {incomplete_count} incomplete records")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.validation_results['failed'].append(f"Completeness validation failed: {e}")
            return False

    def get_database_statistics(self) -> Dict[str, int]:
        """Get basic statistics about the migrated data"""
        stats = {}
        
        try:
            stat_queries = {
                'terms': "SELECT COUNT(*) as count FROM terms",
                'courses': "SELECT COUNT(*) as count FROM course_catalog",
                'offerings': "SELECT COUNT(*) as count FROM course_offerings",
                'sections': "SELECT COUNT(*) as count FROM sections",
                'meeting_patterns': "SELECT COUNT(*) as count FROM meeting_patterns",
                'snapshots': "SELECT COUNT(*) as count FROM section_snapshots"
            }
            
            for stat_name, query in stat_queries.items():
                result = self.db_client.execute_query(query, fetch=True)
                stats[stat_name] = result[0]['count'] if result else 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting database statistics: {e}")
            return {}

    def compare_with_json_data(self, json_data_dir: str) -> Dict[str, Any]:
        """Compare PostgreSQL data with original JSON files"""
        print(f"Comparing database data with JSON files in {json_data_dir}")
        
        data_dir = Path(json_data_dir)
        if not data_dir.exists():
            return {"error": f"JSON data directory {json_data_dir} does not exist"}
        
        comparison_results = {
            'json_stats': {},
            'db_stats': {},
            'discrepancies': []
        }
        
        try:
            # Count courses in JSON files
            json_course_count = 0
            json_section_count = 0
            json_meeting_count = 0
            
            semester_dirs = [d for d in data_dir.iterdir() 
                            if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
            
            for semester_dir in semester_dirs:
                json_files = list(semester_dir.glob('*.json'))
                json_files = [f for f in json_files if f.name not in ['metadata.json', 'latest_sem.json', 'departments.json']]
                
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        for department_name, courses in data.items():
                            for course in courses:
                                json_course_count += 1
                                sessions = course.get('sessions', [])
                                json_section_count += len(sessions)
                                
                                for session in sessions:
                                    meetings = session.get('meetings', [])
                                    json_meeting_count += len(meetings)
                    
                    except Exception as e:
                        comparison_results['discrepancies'].append(f"Error reading {json_file}: {e}")
            
            comparison_results['json_stats'] = {
                'courses': json_course_count,
                'sections': json_section_count,
                'meetings': json_meeting_count
            }
            
            # Get database stats
            comparison_results['db_stats'] = self.get_database_statistics()
            
            # Compare counts
            db_courses = comparison_results['db_stats'].get('offerings', 0)  # Use offerings as proxy for courses
            db_sections = comparison_results['db_stats'].get('sections', 0)
            db_meetings = comparison_results['db_stats'].get('meeting_patterns', 0)
            
            if abs(json_course_count - db_courses) > json_course_count * 0.05:  # Allow 5% difference
                comparison_results['discrepancies'].append(
                    f"Course count mismatch: JSON={json_course_count}, DB={db_courses}"
                )
            
            if abs(json_section_count - db_sections) > json_section_count * 0.05:
                comparison_results['discrepancies'].append(
                    f"Section count mismatch: JSON={json_section_count}, DB={db_sections}"
                )
            
            if abs(json_meeting_count - db_meetings) > json_meeting_count * 0.05:
                comparison_results['discrepancies'].append(
                    f"Meeting count mismatch: JSON={json_meeting_count}, DB={db_meetings}"
                )
            
            return comparison_results
            
        except Exception as e:
            return {"error": f"Comparison failed: {e}"}

    def run_all_validations(self, json_data_dir: Optional[str] = None) -> bool:
        """Run all validation checks"""
        print("=== Running Complete Data Validation ===\n")
        
        try:
            all_passed = True
            
            # Test database connection
            if not self.db_client.test_connection():
                print("✗ Database connection failed")
                return False
            
            # Run validation checks
            checks = [
                ("Database Schema", self.validate_database_schema),
                ("Data Integrity", self.validate_data_integrity),
                ("Data Completeness", self.validate_course_data_completeness)
            ]
            
            for check_name, check_function in checks:
                print(f"\n--- {check_name} ---")
                if not check_function():
                    all_passed = False
            
            # Compare with JSON data if directory provided
            if json_data_dir:
                print(f"\n--- JSON Comparison ---")
                comparison = self.compare_with_json_data(json_data_dir)
                if 'error' in comparison:
                    print(f"✗ {comparison['error']}")
                    all_passed = False
                else:
                    print(f"JSON Stats: {comparison['json_stats']}")
                    print(f"DB Stats: {comparison['db_stats']}")
                    if comparison['discrepancies']:
                        print("Discrepancies found:")
                        for discrepancy in comparison['discrepancies']:
                            print(f"  - {discrepancy}")
                        all_passed = False
                    else:
                        print("✓ Data counts match within acceptable range")
            
            # Print database statistics
            print(f"\n--- Database Statistics ---")
            stats = self.get_database_statistics()
            for stat_name, count in stats.items():
                print(f"{stat_name.capitalize()}: {count:,}")
            
            return all_passed
            
        finally:
            # Clean up database connection
            if hasattr(self.db_client, 'close'):
                self.db_client.close()

    def print_validation_summary(self):
        """Print a summary of all validation results"""
        print("\n=== Validation Summary ===")
        
        if self.validation_results['passed']:
            print(f"\n✓ Passed ({len(self.validation_results['passed'])}):")
            for result in self.validation_results['passed']:
                print(f"  {result}")
        
        if self.validation_results['warnings']:
            print(f"\n⚠ Warnings ({len(self.validation_results['warnings'])}):")
            for result in self.validation_results['warnings']:
                print(f"  {result}")
        
        if self.validation_results['failed']:
            print(f"\n✗ Failed ({len(self.validation_results['failed'])}):")
            for result in self.validation_results['failed']:
                print(f"  {result}")
        
        overall_status = "PASSED" if not self.validation_results['failed'] else "FAILED"
        print(f"\nOverall Status: {overall_status}")

def main():
    """Main entry point for validation utilities"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate PostgreSQL course data migration')
    parser.add_argument('--json-dir', help='Path to original JSON data directory for comparison')
    parser.add_argument('--stats-only', action='store_true', help='Only show database statistics')
    
    args = parser.parse_args()
    
    try:
        validator = DataValidator()
        
        if args.stats_only:
            stats = validator.get_database_statistics()
            print("=== Database Statistics ===")
            for stat_name, count in stats.items():
                print(f"{stat_name.capitalize()}: {count:,}")
        else:
            success = validator.run_all_validations(args.json_dir)
            validator.print_validation_summary()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()