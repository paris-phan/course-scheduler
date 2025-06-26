import requests
from bs4 import BeautifulSoup
import time

SEARCH_URL = "https://louslist.org/page.php?Semester=1242&Type=Search"

def get_course_links():
    response = requests.get(GROUP_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    course_links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if 'Course' in href and href not in course_links:
            course_links.append(BASE_URL + href)
    return course_links

def get_course_details(course_url):
    response = requests.get(course_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for prerequisites and corequisites (likely in <p>, <div>, or <td> tags)
    text = soup.get_text()
    prereq = coreq = None

    for line in text.splitlines():
        line = line.strip()
        if "Prerequisite" in line:
            prereq = line
        elif "Corequisite" in line:
            coreq = line

    return {
        "url": course_url,
        "prerequisite": prereq,
        "corequisite": coreq
    }

def scrape_all_courses():
    all_data = []
    links = get_course_links()

    for link in links:
        details = get_course_details(link)
        all_data.append(details)
        time.sleep(0.5)  # Be nice to the server

    return all_data

# Run the scraper
if __name__ == "__main__":
    course_data = scrape_all_courses()
    for course in course_data:
        print(course)
