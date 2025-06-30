import requests
from bs4 import BeautifulSoup
import time
import os
from supabase import create_client, Client 
from dotenv import load_dotenv
import re
from pathlib import Path

def scrape_all_courses(client, term = 1258):

    #get all the courses from the database
    base_url = f"https://louslist.org/search.php?Semester={term}"
    # Navigate to the search page
    url = base_url
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Clicking the search button 
    search_button = soup.find('input', {'type': 'submit', 'value': 'Search for Classes'})
    if search_button:
        print("Search button found")
        
        # DEBUG: Print the form's HTML and all input fields
        form = soup.find('form')
        if form:
            print('Form HTML:', form.prettify())
            for inp in form.find_all('input'):
                print(f"Input: name={inp.get('name')}, value={inp.get('value')}, type={inp.get('type')}")
        else:
            print('No form found!')
        
        # DEBUG: Print all <a> tags' text and href
        for a in soup.find_all('a'):
            print(f"A tag: text='{a.text.strip()}', href='{a.get('href', '')}'")
        
        # Find all <a> tags that contain a 5-digit number as text
        links = soup.find_all("a", string=re.compile(r"^\d{5}$"))

        # Extract and print the full URLs
        base_url = "https://louslist.org/sectiontip.php?Semester=1258&ClassNumber="

        for link in links:
            class_number = link.text.strip()
            url = base_url + class_number
            print(url)
    else:
        print("Search button not found")
        return
    
    class_regex = r'[A-Z]{3,4}\d{4}'
    # unique_classes = set()
    
    results = {}  # Changed to dictionary to store class_id -> five_digit_numbers mapping
    for tag in soup.find_all(class_=True):
        class_str = ' '.join(tag.get('class'))
        match = re.search(r'\b([A-Z]{2,}\d{4})\b', class_str)
        if match:
            class_id = match.group(1)
            print(class_id)
            if class_id in results:
                continue
            
            five_digit_numbers = []
            for a in tag.find_all('a'):
                numbers = re.findall(r'\b\d{5}\b', a.text)
                five_digit_numbers.extend(numbers)
            if five_digit_numbers:
                results[class_id] = five_digit_numbers  # Store as key-value pair
                print(f"{class_id}: {five_digit_numbers}")
            else:
                print(f"No five-digit numbers found for {class_id}")
        else:
            continue
    
    return results

if __name__ == "__main__":
    # Load .env from the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    load_dotenv(project_root / ".env")
    
    # Temporarily comment out Supabase client to test URL printing
    # supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    course_data = scrape_all_courses(None)  # Pass None instead of supabase client

