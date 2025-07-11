#!/usr/bin/env python3

import os
import time
import re
import requests
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver

load_dotenv()

USERNAME = os.getenv("KIDSNOTE_USERNAME")
PASSWORD = os.getenv("KIDSNOTE_PASSWORD")

if not USERNAME or not PASSWORD:
    print("Error: KIDSNOTE_USERNAME and/or KIDSNOTE_PASSWORD is not set.")
    sys.exit(1)

login_url = "https://www.kidsnote.com/en/login"

def extract_child_id_from_requests(requests) -> str | None:
    """Extract the first child_id found in request URLs."""
    for request in requests:
        if match := re.search(r'/children/(\d+)/reports', request.url):
            return match.group(1)
    return None

# Use headless browser if you don't need to see it
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=chrome_options)
driver.get(login_url)

# Wait for page to load
time.sleep(2)

# Fill in login form
driver.find_element(By.NAME, "username").send_keys(USERNAME)
driver.find_element(By.NAME, "password").send_keys(PASSWORD)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Wait for login to process (adjust if needed)
time.sleep(3)

child_id = extract_child_id_from_requests(driver.requests)
report_url = f"https://www.kidsnote.com/api/v1_2/children/{child_id}/reports/?page_size=5000"

# Extract cookies
cookies = driver.get_cookies()
driver.quit()

with requests.Session() as session:
    # Convert cookies for requests
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache, no-store",
        "Connection": "keep-alive",
        "DNT": "1",
        "Host": "www.kidsnote.com",
        "Pragma": "no-cache",
        "Referer": "https://www.kidsnote.com/service/report",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0",
        "X-ENROLLMENT": "16417613",
    }

    report_response = session.get(report_url, headers=headers)
    if report_response.ok:
        with open("report.json", "w", encoding="utf-8") as f:
            f.write(report_response.text)
    else:
        print("Failed to get report:", report_response.status_code)

