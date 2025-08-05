#!/usr/bin/env python3
"""
Add missing source_hash column to terms table
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the database directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'database'))
from postgresql_client import PostgreSQLClient

def add_source_hash_column():
    """Add source_hash column to existing terms table"""
    print("=== Adding source_hash column to terms table ===\n")
    
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
        
        # Check if column already exists
        check_query = """
        SELECT COUNT(*) as count
        FROM information_schema.columns 
        WHERE table_name = 'terms' AND column_name = 'source_hash'
        """
        
        try:
            result = client.execute_query(check_query, fetch=True)
            if result[0]['count'] > 0:
                print("✅ source_hash column already exists in terms table")
                return True
        except Exception as e:
            print(f"⚠️  Could not check if column exists: {e}")
            print("Proceeding to add column...")
        
        # Add the missing column
        alter_query = "ALTER TABLE terms ADD COLUMN source_hash VARCHAR"
        
        print("⏳ Adding source_hash column to terms table...")
        client.execute_query(alter_query)
        print("✅ Successfully added source_hash column")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        return False
        
    finally:
        if hasattr(client, 'close'):
            client.close()

def main():
    """Main entry point"""
    if not add_source_hash_column():
        sys.exit(1)
    else:
        print("\n✅ Column addition completed successfully!")

if __name__ == '__main__':
    main()