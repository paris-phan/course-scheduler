import asyncio
import aiohttp
import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import random
from collections import deque
from datetime import datetime, timedelta
# import pickle

# currently need to make sure num_pages_in_batch is greater than number of pages in SIS, cuz SIS rate limits after one iteration leading to a request timeout
# there's probably a better way to get around this

class ProxyManager:
    def __init__(self, proxy_list=None):
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.proxy_failures = {}
    
    def add_proxy(self, proxy):
        """Add a proxy to the list (format: 'http://user:pass@host:port')"""
        if proxy not in self.proxy_list:
            self.proxy_list.append(proxy)
    
    def get_next_proxy(self):
        """Get the next proxy in rotation"""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def mark_proxy_failed(self, proxy):
        """Mark a proxy as failed"""
        if proxy in self.proxy_list:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            # Remove proxy if it fails too many times
            if self.proxy_failures[proxy] > 3:
                self.proxy_list.remove(proxy)
                del self.proxy_failures[proxy]
                print(f"Removed failing proxy: {proxy}")

class RateLimiter:
    def __init__(self, requests_per_minute):
        self.requests_per_minute = requests_per_minute
        self.request_times = deque()
    
    async def wait_if_needed(self):
        now = datetime.now()
        
        # Remove requests older than 1 minute
        while self.request_times and (now - self.request_times[0]) > timedelta(minutes=1):
            self.request_times.popleft()
        
        # If we've made too many requests in the last minute, wait
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                print(f"Rate limit reached, waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)

class DataFetcher:
    def __init__(self, path_to_db, table_name, strm, num_pages_in_batch=150, rate_limit_config=None):
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
        self.courses = []
        
        # Rate limiting configuration
        self.rate_limit_config = rate_limit_config or {
            "requests_per_minute": 30,
            "delay_between_requests": (1.0, 3.0),
            "delay_between_batches": (15, 30),
            "max_retries": 5,
            "backoff_multiplier": 2,
            "use_proxy_rotation": False,
            "session_timeout": 300,
        }
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(self.rate_limit_config["requests_per_minute"])
        
        # Initialize proxy manager
        self.proxy_manager = ProxyManager()
        
        # Session management
        self.session = None
        self.session_start_time = None


    def get_base_url(self):
        return f"https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term={self.strm}"


    async def create_session(self):
        """Create a new aiohttp session with appropriate headers and timeout"""
        timeout = aiohttp.ClientTimeout(total=self.rate_limit_config["session_timeout"])
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add proxy if enabled and available
        proxy = None
        if self.rate_limit_config["use_proxy_rotation"] and self.proxy_manager.proxy_list:
            proxy = self.proxy_manager.get_next_proxy()
            print(f"Using proxy: {proxy}")
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector
        )
        self.session_start_time = datetime.now()
        print("Created new session")

    async def check_session_health(self):
        """Check if session needs to be refreshed"""
        if (self.session is None or 
            self.session_start_time is None or
            (datetime.now() - self.session_start_time).total_seconds() > self.rate_limit_config["session_timeout"]):
            if self.session:
                await self.session.close()
            await self.create_session()

    async def fetch_courses(self, page, max_retries=None):
        if max_retries is None:
            max_retries = self.rate_limit_config["max_retries"]
            
        url = self.get_base_url() + f"&page={page}"
        print(f"Fetching data for page {page}")
        
        for attempt in range(max_retries):
            try:
                # Check session health
                await self.check_session_health()
                
                # Apply rate limiting
                await self.rate_limiter.wait_if_needed()
                
                # Add random delay between requests
                delay_range = self.rate_limit_config["delay_between_requests"]
                await asyncio.sleep(random.uniform(*delay_range))
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        # Check if response is JSON
                        content_type = response.headers.get('content-type', '')
                        if 'application/json' in content_type or 'text/json' in content_type:
                            data = await response.json()
                            print(f"✓ Successfully fetched page {page} of {self.strm}")
                            return data
                        else:
                            # Got HTML instead of JSON (likely rate limited)
                            text = await response.text()
                            if 'login' in text.lower() or 'error' in text.lower() or 'forbidden' in text.lower():
                                print(f"⚠️ Rate limited on page {page}, attempt {attempt + 1}/{max_retries}")
                                if attempt < max_retries - 1:
                                    # Exponential backoff
                                    backoff_time = self.rate_limit_config["backoff_multiplier"] ** attempt
                                    wait_time = random.uniform(backoff_time * 2, backoff_time * 4)
                                    print(f"⏳ Waiting {wait_time:.2f} seconds before retry...")
                                    await asyncio.sleep(wait_time)
                                    continue
                                else:
                                    print(f"❌ Failed to fetch page {page} after {max_retries} attempts")
                                    return None
                            else:
                                print(f"⚠️ Unexpected response type for page {page}: {content_type}")
                                return None
                    elif response.status == 403:
                        print(f"🚫 403 Forbidden on page {page}, attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            # Longer wait for 403 errors
                            wait_time = random.uniform(30, 60)
                            print(f"⏳ 403 error - waiting {wait_time:.2f} seconds before retry...")
                            await asyncio.sleep(wait_time)
                            # Refresh session after 403
                            await self.check_session_health()
                            continue
                        else:
                            print(f"❌ Failed to fetch page {page} after {max_retries} attempts (403)")
                            return None
                    elif response.status == 404:
                        print(f"📄 Page {page} returned 404 - likely end of data")
                        return {"classes": []}
                    else:
                        print(f"⚠️ Failed to fetch data for page {page}, status: {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(random.uniform(2, 5))
                            continue
                        return None
                        
            except asyncio.TimeoutError:
                print(f"⏰ Timeout on page {page}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(3, 8))
                    continue
                return None
            except Exception as e:
                print(f"💥 Error fetching page {page}, attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(2, 5))
                    continue
                return None
        
        return None


    async def get_all_courses_in_semester(self):
        """Fetch all courses from SIS with robust pagination handling"""
        try:
            # Create initial session
            await self.create_session()
            
            page = 1
            consecutive_empty_pages = 0
            max_consecutive_empty = 3  # Stop after 3 consecutive empty pages
            total_pages_fetched = 0
            total_courses_fetched = 0
            
            print(f"Starting to fetch all courses for semester {self.strm}")
            
            while consecutive_empty_pages < max_consecutive_empty:
                print(f"\n--- Fetching page {page} ---")
                response_data = await self.fetch_courses(page)
                
                if response_data is None:
                    print(f"Failed to fetch page {page}, retrying...")
                    await asyncio.sleep(random.uniform(5, 10))
                    continue
                
                classes = response_data.get("classes", [])
                num_classes = len(classes)
                
                if num_classes == 0:
                    consecutive_empty_pages += 1
                    print(f"Page {page} is empty (consecutive empty: {consecutive_empty_pages}/{max_consecutive_empty})")
                    
                    # If we've had too many consecutive empty pages, we might be done
                    if consecutive_empty_pages >= max_consecutive_empty:
                        print(f"Reached {max_consecutive_empty} consecutive empty pages. Assuming we've reached the end.")
                        break
                else:
                    # Reset consecutive empty counter when we get data
                    consecutive_empty_pages = 0
                    total_courses_fetched += num_classes
                    
                    # Add courses to our collection
                    for course in classes:
                        self.courses.append(course)
                    
                    print(f"Page {page}: Found {num_classes} courses (Total: {total_courses_fetched})")
                
                total_pages_fetched += 1
                page += 1
                
                # Add a small delay between pages to be respectful
                await asyncio.sleep(random.uniform(1, 3))
                
                # Every 10 pages, add a longer delay to avoid overwhelming the server
                if total_pages_fetched % 10 == 0:
                    delay_range = self.rate_limit_config["delay_between_batches"]
                    wait_time = random.uniform(*delay_range)
                    print(f"Completed {total_pages_fetched} pages, taking a {wait_time:.2f} second break...")
                    await asyncio.sleep(wait_time)
            
            print(f"\n=== Fetching Complete ===")
            print(f"Total pages fetched: {total_pages_fetched}")
            print(f"Total courses fetched: {total_courses_fetched}")
            print(f"Final consecutive empty pages: {consecutive_empty_pages}")
            
        except Exception as e:
            print(f"Error during fetching: {e}")
            raise
        finally:
            # Clean up session
            if self.session:
                await self.session.close()
                print("Session closed")
    

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
                "meetings": str(course_data.get("meetings", [])),  # Convert to string for storage
                "instructors": str(course_data.get("instructors", [])),  # Convert to string for storage
            }
            
            # Insert into Supabase
            self.supabase.table(self.table_name).insert(course_record).execute()
            print(f"Inserted: {course_record['subject']} {course_record['catalog_nbr']} - {course_record['class_section']}")
            
        except Exception as e:
            print(f"Error inserting course {course_data.get('subject', '')} {course_data.get('catalog_nbr', '')}: {e}")


    def run(self):
        # fetch data from SIS
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_all_courses_in_semester())
        loop.close()

        # with open("sis_data.pkl", "rb") as f:
        #     self.courses = pickle.load(f)
        
        print(f"Processing {len(self.courses)} courses...")
        
        # Clear existing data for this semester (optional - comment out if you want to keep existing data)
        try:
            self.supabase.table(self.table_name).delete().eq("strm", self.strm).execute()
            print(f"Cleared existing data for semester {self.strm}")
        except Exception as e:
            print(f"Warning: Could not clear existing data: {e}")
        
        # Insert each course into Supabase
        for i, course in enumerate(self.courses):
            if i % 100 == 0:  # Progress indicator
                print(f"Processing course {i+1}/{len(self.courses)}")
            self.insert_course_into_supabase(course)
        
        print(f"Successfully inserted {len(self.courses)} courses into Supabase")
