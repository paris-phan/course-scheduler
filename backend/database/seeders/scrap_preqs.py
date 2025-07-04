import requests
from bs4 import BeautifulSoup
import time
import os
from supabase import create_client, Client 
from dotenv import load_dotenv
import re
from pathlib import Path
import postgrest

def validate_course_number(class_number_str):
    """
    Validate and convert course number string to integer
    
    Args:
        class_number_str: String containing the course number
        
    Returns:
        int: Valid course number integer
        
    Raises:
        ValueError: If the course number is not a valid 5-digit integer
    """
    # Check if it's exactly 5 digits
    if not re.match(r'^\d{5}$', class_number_str):
        raise ValueError(f"Course number must be exactly 5 digits, got: {class_number_str}")
    
    # Convert to integer
    course_number = int(class_number_str)
    
    # Additional validation if needed (e.g., range checks)
    if course_number < 10000 or course_number > 99999:
        raise ValueError(f"Course number must be between 10000 and 99999, got: {course_number}")
    
    return course_number

def scrap_course_links(client, term=1258):
    # Use the direct search URL to get all classes for the semester
    url = f"https://louslist.org/pagex.php?Type=Search&Semester={term}&iGroup=&iMnemonic=&iNumber=&iStatus=&iType=&iInstructor=&iBuilding=&iRoom=&iMode=&iDays=&iTime=&iDates=&iUnits=&iTitle=&iTopic=&iDescription=&iDiscipline=&iMinPosEnroll=&iMaxPosEnroll=&iMinCurEnroll=&iMaxCurEnroll=&iMinCurWaitlist=&iMaxCurWaitlist=&Submit=Search+for+Classes"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all <a> tags that contain a 5-digit number as text
    links = soup.find_all("a", string=re.compile(r"^\d{5}$"))

    # Extract and print the full URLs
    base_url = f"https://louslist.org/sectiontip.php?Semester={term}&ClassNumber="
    course_urls = []
    for link in links:
        class_number = link.text.strip()
        url = base_url + class_number
        course_urls.append(url)


    return course_urls



def scrape_prereqs(client, course_urls):
    batch_size = 50
    
    # Process URLs in batches
    for batch_start in range(0, len(course_urls), batch_size):
        batch_end = min(batch_start + batch_size, len(course_urls))
        batch_urls = course_urls[batch_start:batch_end]
        
        print(f"Processing batch {batch_start // batch_size + 1}: URLs {batch_start + 1}-{batch_end}")
        
        # Create a list of dictionaries for this batch
        batch_records = []
        
        # Process each URL in the current batch
        for i, url in enumerate(batch_urls):
            try:
                print(f"  Processing URL {batch_start + i + 1}: {url}")
                
                classNumber_regex = r"(?<=ClassNumber=)\d{5}"
                classNumber_match = re.search(classNumber_regex, url)
                
                if classNumber_match:
                    classNumber = classNumber_match.group(0)
                    classNumber_int = validate_course_number(classNumber)
                else:
                    print(f"Warning: Could not extract class number from URL: {url}")
                    continue

                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                html = str(soup)

                enroll_match = re.search(r'Enrollment Requirements:</td>\s*<td>\s*(.*?)\s*</td>', html, re.DOTALL)
                components_match = re.search(r'Class Components:</td>\s*<td>\s*(.*?)\s*</td>', html, re.DOTALL)
                sis_desc_match = re.search(r'<em>SIS Description:\s*</em>\s*(.*?)\s*</td>', html, re.DOTALL)
                
                #Join record regex
                subject = None
                catalog_nbr = None
                class_section = None

                join_match = re.search(r"<title>\s*([A-Z]{2,4})\s+(\d{4})\s+(\d{2,3})\s+-.*?", html )
                if join_match:
                    subject = join_match.group(1) # example : "AAS" , "MATH", "CS"
                    catalog_nbr = join_match.group(2) # example : "3140" , "4501"
                    class_section = join_match.group(3) # example : "1000" , "02"

                    # Query the database to get the id where subject, catalog_nbr, and class_section match
                    primary_id = None
                    try:
                        result = client.table("courses").select("id").eq("subject", subject).eq("catalog_nbr", catalog_nbr).eq("class_section", class_section).limit(1).execute()
                        if result.data and len(result.data) > 0:
                            primary_id = result.data[0]["id"]

                    except Exception as e:
                        print(f"Error fetching id from database for {subject} {catalog_nbr} {class_section}: {e}")

                # Create a record for this course
                if subject and catalog_nbr and class_section and primary_id is not None:
                    course_record = {
                        "id": primary_id, 
                        "sis_id": classNumber_int,
                        "description_link": url,
                        "enrollment_requirements": enroll_match.group(1).strip() if enroll_match else None,
                        "class_components": components_match.group(1).strip() if components_match else None,
                        "sis_description": sis_desc_match.group(1).strip() if sis_desc_match else None
                    }
                    batch_records.append(course_record)
                else:
                    print(f"Skipping course {subject} {catalog_nbr} {class_section} due to missing id")
                
                
            except ValueError as e:
                print(f"Error: Invalid class number format in URL {url}: {e}")
                continue
            except Exception as e:
                print(f"Error processing URL {url}: {e}")
                continue
        
        # Insert the batch of records
        max_retries = 3
        retry_delay = 3  # seconds

        if batch_records:
            for attempt in range(1, max_retries + 1):
                try:
                    response = client.table("courses").upsert(
                        batch_records, 
                        on_conflict = ["id"]
                    ).execute()
                    print(f"  Successfully inserted batch {batch_start // batch_size + 1}")
                    break  # Success, exit the retry loop
                except postgrest.APIError as e:
                    print(f"Database error (attempt {attempt}): {e}")
                    if attempt == max_retries:
                        print(f"Failed after {max_retries} attempts. Batch records preview: {batch_records[:2]}")
                        return
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

        # Add delay between batches
        if batch_end < len(course_urls):
            print("  Waiting 2 seconds before next batch...")
            time.sleep(2)
    
    print(f"Completed processing all {len(course_urls)} URLs")






if __name__ == "__main__":
    # Load .env from the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    load_dotenv(project_root / ".env")

    # Temporarily comment out Supabase client to test URL printing
    # supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    urls = scrap_course_links(supabase, 1258)
    scrape_prereqs(supabase, urls)
