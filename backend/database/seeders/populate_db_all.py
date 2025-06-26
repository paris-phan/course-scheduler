import os 
from supabase import create_client, Client 
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime
import sys
import json

def insert_into_db(client, term = 1252): 
    course_query = {
        "term": term,
        "subject": "",
        "id": None,  # this is the id of the course in the database
        "enrollment_total": 0,
        "class_capacity": 0,
        "wait_tot": 0,
        "wait_cap": 0,
        "descr": "",
        "units": "",
        "topic": "",
        "section_type": "",
        "facility_id": "",
        "facility_descr": "",
        "days": [],
        "start_time": "",
        "end_time": "",
        "start_dt": "",
        "end_dt": "",
        "instructor": "",
        "catalog_number": "",
    }

    
    #directory for the term data
    try:
        term_class_dir = os.path.join(f"database/course-data/data/{term}")
    except:
        print(f"Term directory {term_class_dir} does not exist")
        return
    
    # Check if directory exists
    if not os.path.exists(term_class_dir):
        print(f"Term directory {term_class_dir} does not exist")
        return

    #iterate through each dept .json file 
    for i, dept_json_file in enumerate(os.listdir(term_class_dir)): 
        if not dept_json_file.endswith('.json'):
            continue
            
        #load the json file 
        with open(os.path.join(term_class_dir, dept_json_file), 'r') as f:
            dept_data = json.load(f)
            
        # Debug: Print the structure
        print(f"Processing {dept_json_file}")
        print(f"Keys in file: {list(dept_data.keys())}")
        
        # Iterate through each department in the file
        for dept_name, courses in dept_data.items():
            print(f"Processing department: {dept_name} with {len(courses)} courses")
            
            # Iterate through each course in the department
            for course in courses:
                # Check if course is actually a dictionary
                if not isinstance(course, dict):
                    print(f"Skipping non-dict course: {course}")
                    continue
                    
                # Reset course_query for each course
                course_query = {
                    "term": term,
                    "subject": "",
                    "id": None,
                    "enrollment_total": 0,
                    "class_capacity": 0,
                    "wait_tot": 0,
                    "wait_cap": 0,
                    "descr": "",
                    "units": "",
                    "topic": "",
                    "section_type": "",
                    "facility_id": "",
                    "facility_descr": "",
                    "days": [],
                    "start_time": "",
                    "end_time": "",
                    "start_dt": "",
                    "end_dt": "",
                    "instructor": "",
                    "catalog_number": "",
                }
                
                # Extract course data
                course_query["subject"] = course.get("subject", "")
                course_query["id"] = f"{course.get('subject', '')}-{course.get('catalog_number', '')}"  # Unique ID combining subject and catalog number
                course_query["catalog_number"] = course.get("catalog_number", "")  # Just the catalog number
                course_query["descr"] = course.get("descr", "")
                course_query["units"] = course.get("units", "")
                course_query["topic"] = course.get("topic", "")
                
                # Handle sessions data (there might be multiple sessions per course)
                if "sessions" in course and course["sessions"]:
                    session = course["sessions"][0]  # Take the first session
                    course_query["enrollment_total"] = session.get("enrollment_total", 0)
                    course_query["class_capacity"] = session.get("class_capacity", 0)
                    course_query["wait_tot"] = session.get("wait_tot", 0)
                    course_query["wait_cap"] = session.get("wait_cap", 0)
                    course_query["section_type"] = session.get("section_type", "")
                    
                    # Handle meetings data
                    if "meetings" in session and session["meetings"]:
                        meeting = session["meetings"][0]  # Take the first meeting
                        course_query["facility_id"] = meeting.get("facility_id", "")
                        course_query["facility_descr"] = meeting.get("facility_descr", "")
                        course_query["days"] = meeting.get("days", "")
                        
                        # Handle time fields - convert empty strings to None for database
                        start_time = meeting.get("start_time", "")
                        end_time = meeting.get("end_time", "")
                        course_query["start_time"] = start_time if start_time else None
                        course_query["end_time"] = end_time if end_time else None
                        
                        course_query["start_dt"] = meeting.get("start_dt", "")
                        course_query["end_dt"] = meeting.get("end_dt", "")
                        course_query["instructor"] = meeting.get("instructor", "")

                # Insert the course into the database
                try:
                    client.table("courses").insert(course_query).execute()
                    print(f"Inserted course: {course_query['subject']} {course_query['id']}")  # Use 'id' here too
                except Exception as e:
                    print(f"Error inserting course: {e}")



def main():
    load_dotenv()

    # Creating a Supabase Client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        return

    supabase: Client = create_client(url, key)
    
    # Actually call the function
    insert_into_db(supabase)

if __name__ == '__main__':
    main() 
