import asyncio
import aiohttp
import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import random
import json
# import pickle

# currently need to make sure num_pages_in_batch is greater than number of pages in SIS, cuz SIS rate limits after one iteration leading to a request timeout
# there's probably a better way to get around this

class DataFetcher:
    def __init__(self, table_name, strm, num_pages_in_batch=150, start_page=1):
        # Load environment variables for Supabase connection
        load_dotenv()
        
        # Get Supabase credentials from environment
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        
        # Create Supabase client
        self.supabase: Client = create_client(url, key)
        self.table_name = table_name
        self.strm = strm
        self.num_pages_in_batch = num_pages_in_batch
        self.start_page = start_page
        self.courses = []


    def get_base_url(self):
        return f"https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term={self.strm}"
                           

    async def fetch_courses(self, session, page, max_retries=8):
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
                            print(f"Got results for page {page} of {self.strm}")
                            print(data)
                            return data
                        else:
                            # Got HTML instead of JSON (likely rate limited)
                            text = await response.text()
                            if 'login' in text.lower() or 'error' in text.lower():
                                print(f"Rate limited on page {page}, attempt {attempt + 1}/{max_retries}")
                                if attempt < max_retries - 1:
                                    # Wait longer before retry
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


    async def get_all_courses_in_semester(self):
        # Use a smaller batch size to avoid rate limiting
        batch_size = self.num_pages_in_batch # which is 150 
        
        async with aiohttp.ClientSession() as session:
            in_progress = True
            iteration = 0
            page_count = 0
            courses_in_batch = []
            
            while in_progress:
                start_page = self.start_page + iteration * batch_size
                end_page = batch_size + start_page
                print(f"Fetching pages {start_page} to {end_page}")
                
                # Process pages sequentially to avoid overwhelming the server
                for page in range(start_page, end_page):
                    response_data = await self.fetch_courses(session, page)
                    
                    if len(response_data.get("classes", [])) == 0 or response_data == "{'pageCount': 0, 'classes': []}":
                        in_progress = False
                        print(f"Page {page} had no results, setting in_progress= False")
                        break
                    else:
                        data = response_data["classes"]
                        for course in data:
                            courses_in_batch.append(course)
                        
                        page_count += 1
                        
                        # Insert every 5 pages processed
                        if page_count % 5 == 0:
                            print(f"Inserting batch of {len(courses_in_batch)} courses from pages {start_page} to {page}")
                            for course in courses_in_batch:
                                self.insert_course_into_supabase(course)
                            courses_in_batch = []  # Clear the batch
                
                # Add delay between batches
                if in_progress:
                    print(f"Completed batch {iteration + 1}, waiting before next batch...")
                    await asyncio.sleep(random.uniform(10, 20))
                
                iteration += 1
            
            # Insert any remaining courses
            if courses_in_batch:
                print(f"Inserting final batch of {len(courses_in_batch)} courses")
                for course in courses_in_batch:
                    self.insert_course_into_supabase(course)
            
            print("Done fetching data from SIS")


    def insert_course_into_supabase(self, course_data):
        """Insert a single course into Supabase"""
        try:
            # Extract basic course information
            course_record = {
                "strm": self.strm,
                "subject": course_data.get("subject", ""),
                "catalog_nbr": course_data.get("catalog_nbr", ""),
                "subject_descr": course_data.get("subject_descr", ""),
                "descr": course_data.get("descr", ""),
                "topic": course_data.get("topic", ""),
                "units": course_data.get("units", ""),
                "acad_group": course_data.get("acad_group", ""),
                "acad_org": course_data.get("acad_org", ""),
                "crse_attr_value": course_data.get("crse_attr_value", ""),
                "component": course_data.get("component", ""),
                "class_section": course_data.get("class_section", ""),
                "section_type": course_data.get("section_type", ""),
                "enrollment_total": course_data.get("enrollment_total", 0),
                "class_capacity": course_data.get("class_capacity", 0),
                "wait_tot": course_data.get("wait_tot", 0),
                "wait_cap": course_data.get("wait_cap", 0),
                "meetings": json.dumps(course_data.get("meetings", [])),  # Proper JSON serialization
                "instructors": json.dumps(course_data.get("instructors", [])),  # Proper JSON serialization
            }
            
            # Insert into Supabase
            self.supabase.table(self.table_name).insert(course_record).execute()
            print(f"Inserted: {course_record['subject']} {course_record['catalog_nbr']} - {course_record['class_section']}")
                                       
        except Exception as e:
            print(f"Error inserting course {course_data.get('subject', '')} {course_data.get('catalog_nbr', '')}: {e}")
                           

    def run(self):

        # fetch data from SIS and insert as we go
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_all_courses_in_semester())
        loop.close()

        print("Successfully completed data fetch and insertion")
