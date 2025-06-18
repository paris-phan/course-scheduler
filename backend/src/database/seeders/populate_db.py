import os 
from supabase import create_client, Client 
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime
'''
Script for populating the the database from the coures from the SIS api.
'''

def establish_connection():
    #All Classes url 
    term = 1258
    all_classes_url = f"https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term={term}"

    print("Attempting to establish a connection")
    response = requests.get(all_classes_url)

    data = None
    if response.status_code ==200:
        data = response.json()
    else:
        logging.ERROR(response.status_code)

    return data

""" establishing connectiion and geting all the classe"""
def insert_into_db(client,response):

    all_inserts = []
    for i, course in enumerate(response["classes"]):
        
        course_query = {
            "id": i,
            "sis_id": course["crse_id"],
            "course_name": course["descr"],
            "dept_name": course["subject"],
            "semester": "Fall 2025",
            "available_seats": course["enrollment_total"],
            "total_seats": course["class_capacity"],
            "last_updated": datetime.now().isoformat(),
            "units": course["units"],
            "Meeting Days and Times": course["meetings"] 
        }

        all_inserts.append(course_query)
        

    response = (
        client
        .table("courses")
        .insert(all_inserts )
        .execute()
    )




def main():
    load_dotenv()

    # Creating a Supabase Client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url,key)
    
    all_classes = establish_connection()
    insert_into_db(supabase, all_classes)

    

if __name__ == '__main__':
    main()

    


