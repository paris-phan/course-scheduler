import requests
from bs4 import BeautifulSoup
import time
import os
from supabase import create_client, Client 
from dotenv import load_dotenv
import re

def scrape_all_courses(client, term = 1252):

    #get all the courses from the database
    base_url = "https://louslist.org/search.php?Semester={term}"
    # Navigate to the search page
    url = base_url.format(term=term)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Cloicking the search b utton 
    search_button = soup.find('input', {'type': 'submit', 'value': 'Search for Classes'})
    if search_button:

        # Find the parent form of the button
        form = search_button.find_parent('form')
        if form:
            # Get the form action URL, or use the current URL if not specified
            form_action = form.get('action') or url
            if not form_action.startswith('http'):
                
                from urllib.parse import urljoin
                form_action = urljoin(url, form_action)
            
            # Collect all form inputs to submit with the POST request
            form_data = {}
            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    form_data[name] = value

            # Sending a post request to the form action url with the form data
            response = requests.post(form_action, data=form_data)
            soup = BeautifulSoup(response.content, 'html.parser')


            
        else:
            print("Form containing the search button not found")
            
    else:
        print("Search button not found")
        return 
    
  


    class_regex = r'[A-Z]{3,4}\d{4}'
    # unique_classes = set()
    
    results = {}
    for tag in soup.find_all(class_=True):
        class_str = ' '.join(tag.get('class'))
        match = re.search(r'\b([A-Z]{2,}\d{4})\b', class_str)
        if match:
            class_id = match.group(1)
            print(class_id)
            if class_id in results:
                continue
            
            results.add(class_id)
            five_digit_numbers = []
            for a in tag.find_all('a'):
                numbers = re.findall(r'\b\d{5}\b', a.text)
                five_digit_numbers.extend(numbers)
            if five_digit_numbers:
                results.append(five_digit_numbers)
                print(f"{class_id}: {five_digit_numbers}")
        else:
            continue




    
        

if __name__ == "__main__":
    load_dotenv()
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    course_data = scrape_all_courses(supabase)

