#!/usr/bin/env python3
"""
Simple connection test for Cloud SQL debugging
"""

import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import pg8000

def test_cloud_sql_connection():
    """Test Cloud SQL connection with detailed error reporting"""
    load_dotenv('backend/.env')
    
    # Get environment variables
    connection_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    db_user = os.environ.get('POSTGRES_USER') 
    db_password = os.environ.get('POSTGRES_PASSWORD')
    db_name = os.environ.get('POSTGRES_DB')
    
    print("=== Cloud SQL Connection Test ===")
    print(f"Connection Name: {connection_name}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'*' * len(db_password) if db_password else 'None'}")
    
    if not all([connection_name, db_user, db_password, db_name]):
        print("❌ Missing required environment variables!")
        return False
    
    try:
        print("\n--- Testing Cloud SQL Connector ---")
        connector = Connector()
        
        def getconn():
            conn = connector.connect(
                connection_name,
                "pg8000",
                user=db_user,
                password=db_password,
                db=db_name
            )
            return conn
        
        print("✓ Cloud SQL Connector initialized")
        
        # Test connection
        print("Attempting to connect...")
        conn = getconn()
        print("✓ Connection established")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        print(f"✓ Query successful: {result[0][:50]}...")
        
        cursor.close()
        conn.close()
        connector.close()
        
        print("\n🎉 Connection test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Additional debugging info
        if 'password authentication failed' in str(e):
            print("\n🔍 Debugging suggestions:")
            print("1. Check if the user exists in Cloud SQL")
            print("2. Verify the password is correct")
            print("3. Make sure the user has CONNECT privileges to the database")
            print("4. Check if you're using the right database name")
        elif 'does not exist' in str(e):
            print("\n🔍 The database might not exist. Create it with:")
            print(f"gcloud sql databases create {db_name} --instance=your-instance-name")
        
        return False

if __name__ == '__main__':
    test_cloud_sql_connection()