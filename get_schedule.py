import requests
import re
from datetime import datetime, timedelta, time
from bs4 import BeautifulSoup
import docx
import os
import csv
import io

# --- 1. CONFIGURATION ---
LOGIN_PAGE_URL = 'https://secure13.aladtec.com/fairviewfd/index.php'
LOGIN_ACTION_URL = 'https://secure13.aladtec.com/fairviewfd/index.php?action=login'
USERNAME = os.environ.get("ALADTEC_USERNAME")
PASSWORD = os.environ.get("ALADTEC_PASSWORD")
MEMBER_DATA = os.environ.get("MEMBER_DATA") # Reads member list from Secrets
ROUTINE_FILE_PATH = 'HQ and Sta2 routine.docx'

# --- 2. DATE LOGIC ---
now = datetime.now()
cutoff_time = time(19, 0) # 7 PM cutoff
target_date = now.date() if now.time() < cutoff_time else (now + timedelta(days=1)).date()
date_for_url = target_date.strftime('%Y-%m-%d')
SCHEDULE_URL = f'https://secure13.aladtec.com/fairviewfd/index.php?action=manage_schedule_view_schedule&date={date_for_url}'
output_filename = "docs/index.html"
os.makedirs("docs", exist_ok=True)

# --- 3. BIRTHDAY REMINDER PARSER (FROM SECRET) ---
birthday_reminders_html = ""
try:
    if MEMBER_DATA:
        print("Checking for upcoming birthdays from secret data...")
        found_birthdays = []
        today = now.date()
        check_dates = [today + timedelta(days=i) for i in range(3)]

        # Use io.StringIO to treat the secret string as a file
        csvfile = io.StringIO(MEMBER_DATA)
        # Skip the first line if it's a title
        if "member list" in next(csvfile).lower():
            pass # The first line was consumed, reader will start on next line
        else:
            csvfile.seek(0) # Rewind if it was a header row
        
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            def get_val(field_name):
                for key in row:
                    if key.strip().lower() == field_name.lower(): return row[key]
                return None
            dob_str, first_name, last_name = get_val('Date of Birth'), get_val('First Name'), get_val('Last Name')
            if dob_str and first_name and last_name:
                dob = None
                for fmt in ('%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%m/%d/%y'):
                    try:
                        dob = datetime.strptime(dob_str, fmt).date()
                        break 
                    except ValueError:
                        continue 
                if dob:
                    for year_offset in [0, 1]:
                        bday_this_year = dob.replace(year=today.year + year_offset)
                        if bday_this_year in check_dates:
                            found_birthdays.append({'date': bday_this_year, 'name': f"{first_name} {last_name}"})
                            break 
        found_birthdays.sort(key=lambda x: x['date'])
        upcoming_birthdays_html_list = []
        for bday_info in found_birthdays:
            bday_date, name = bday_info['date'], bday_info['name']
            day_suffix = 'th' if 11 <= bday_date.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(bday_date.day % 10, 'th')
            bday_str = f"{bday_date.strftime('%A, %B %d')}{day_suffix}"
            upcoming_birthdays_html_list.append(f"<li>🎂 <strong>{name}</strong> - {bday_str}</li>")
        if upcoming_birthdays_html_list:
            birthday_reminders_html = f"<div class=\"birthday-reminders\"><h3>Upcoming Birthdays</h3><ul>{''.join(upcoming_birthdays_html_list)}</ul></div>"
except Exception as e:
    print(f"Could not process birthday data: {e}")


# --- DAILY ROUTINE, WEATHER, AND ROSTER LOGIC (REDACTED FOR BREVITY) ---
# ... (The rest of the script remains the same) ...


# --- 7. PARSE AND BUILD THE HTML REPORT ---
# This section remains unchanged and will use the birthday_reminders_html generated above.
# (Code redacted for brevity)

