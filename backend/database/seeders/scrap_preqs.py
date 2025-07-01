import requests
from bs4 import BeautifulSoup
import time
import os
from supabase import create_client, Client 
from dotenv import load_dotenv
import re
from pathlib import Path

def scrap_course_links(client, term=1258):
    # Use the direct search URL to get all classes for the semester
    url = f"https://louslist.org/pagex.php?Type=Search&Semester={term}&iGroup=&iMnemonic=&iNumber=&iStatus=&iType=&iInstructor=&iBuilding=&iRoom=&iMode=&iDays=&iTime=&iDates=&iUnits=&iTitle=&iTopic=&iDescription=&iDiscipline=&iMinPosEnroll=&iMaxPosEnroll=&iMinCurEnroll=&iMaxCurEnroll=&iMinCurWaitlist=&iMaxCurWaitlist=&Submit=Search+for+Classes"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    print(f"Fetched Lou's List all-classes page for semester {term}")
    print(f"Response URL: {response.url}")
    print(f"Response status: {response.status_code}")

    # Find all <a> tags that contain a 5-digit number as text
    links = soup.find_all("a", string=re.compile(r"^\d{5}$"))
    print(f"Found {len(links)} course links with 5-digit numbers")

    # Extract and print the full URLs
    base_url = f"https://louslist.org/sectiontip.php?Semester={term}&ClassNumber="
    course_urls = []
    for link in links:
        class_number = link.text.strip()
        url = base_url + class_number
        course_urls.append(url)
        print(f"Course URL: {url}")

    # Optionally, save a sample of the HTML for debugging
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("Saved page HTML to debug_page.html for inspection")

    return course_urls



def scrape_prereqs(client, course_urls):

    #to insert into the table called "courses"
    sis_ids_and_likks = {
        
        "sis_id":
    }

    #get the course number from the urlsupabase
    for url in course_urls:
        regex = r"^(\d{5})"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        print(soup.prettify())



if __name__ == "__main__":
    # Load .env from the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    load_dotenv(project_root / ".env")

    # Temporarily comment out Supabase client to test URL printing
    # supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    urls = scrap_course_links(None)
    print(f"\nTotal course URLs found: {len(urls)}")

