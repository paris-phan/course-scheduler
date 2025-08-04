#!/usr/bin/env python3
"""
Database Schema Setup Script for Cloud SQL PostgreSQL
This script creates the required database schema for the course scheduler application.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the database directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'database'))
from postgresql_client import PostgreSQLClient

def read_schema_file():
    """Read the clean schema.sql file"""
    schema_file = Path(__file__).parent / 'schema.sql'
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return None
    
    with open(schema_file, 'r') as f:
        content = f.read()
    
    return content

def create_database_schema():
    """Create the database schema using the PostgreSQL client"""
    print("=== Database Schema Setup ===\n")
    
    # Load environment
    load_dotenv('backend/.env')
    
    try:
        # Initialize database client
        client = PostgreSQLClient()
        
        # Test connection
        if not client.test_connection():
            print("❌ Database connection failed")
            return False
        
        print("✅ Database connection successful")
        
        # Check if schema already exists
        result = client.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = :table_name",
            {'table_name': 'terms'},
            fetch=True
        )
        
        if result[0]['count'] > 0:
            print("⚠️  Schema already exists. Do you want to continue? (y/N): ", end='')
            response = input().strip().lower()
            if response != 'y':
                print("Schema setup cancelled.")
                return False
        
        # Read schema SQL
        schema_sql = read_schema_file()
        if not schema_sql:
            return False
        
        print("📄 Schema file loaded successfully")
        
        # Split SQL into individual statements
        statements = []
        current_statement = []
        
        for line in schema_sql.split('\n'):
            stripped_line = line.strip()
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('--'):
                continue
            
            # Add line to current statement
            current_statement.append(line)
            
            # Check if this line ends a statement (semicolon at end)
            if stripped_line.endswith(';'):
                # Join all lines for this statement
                statement = '\n'.join(current_statement).strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = []
        
        # Add any remaining statement (shouldn't happen with well-formed SQL)
        if current_statement:
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        print(f"📋 Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        success_count = 0
        for i, statement in enumerate(statements, 1):
            try:
                print(f"⏳ Executing statement {i}/{len(statements)}...", end=' ')
                
                # Skip commented statements
                if statement.strip().startswith('--'):
                    print("⏭️  (skipped comment)")
                    continue
                
                client.execute_query(statement)
                print("✅")
                success_count += 1
                
            except Exception as e:
                print(f"❌ Error: {e}")
                
                # Check if it's a harmless error (like table already exists)
                error_str = str(e).lower()
                if 'already exists' in error_str or 'duplicate' in error_str:
                    print("   (continuing - table already exists)")
                    success_count += 1
                    continue
                else:
                    print(f"   Statement: {statement[:100]}...")
                    response = input("   Continue with remaining statements? (y/N): ").strip().lower()
                    if response != 'y':
                        break
        
        print(f"\n🎉 Schema setup completed!")
        print(f"✅ Successfully executed {success_count}/{len(statements)} statements")
        
        # Verify schema creation
        print("\n🔍 Verifying schema creation...")
        
        required_tables = [
            'terms', 'course_catalog', 'course_offerings', 'sections',
            'meeting_patterns', 'section_snapshots'
        ]
        
        existing_tables = []
        for table in required_tables:
            try:
                result = client.execute_query(
                    "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = :table_name",
                    {'table_name': table},
                    fetch=True
                )
                if result[0]['count'] > 0:
                    existing_tables.append(table)
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} - not found")
            except Exception as e:
                print(f"   ❌ {table} - error checking: {e}")
        
        if len(existing_tables) == len(required_tables):
            print(f"\n🎉 All required tables created successfully!")
            print("You can now run the migration script:")
            print("python backend/database/migrations/migrate_to_postgresql.py --data-dir backend/database/course-data-backup/data --semester 1228")
            return True
        else:
            print(f"\n⚠️  Only {len(existing_tables)}/{len(required_tables)} tables were created successfully")
            return False
        
    except Exception as e:
        print(f"❌ Schema setup failed: {e}")
        return False
    
    finally:
        if hasattr(client, 'close'):
            client.close()

def main():
    """Main entry point"""
    if not create_database_schema():
        sys.exit(1)
    else:
        print("\n✅ Database schema setup completed successfully!")

if __name__ == '__main__':
    main()