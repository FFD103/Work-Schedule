import requests
import re
from datetime import datetime, timedelta, time
from bs4 import BeautifulSoup
import docx
import os
import csv

# --- 1. CONFIGURATION (UPDATED FOR CLOUD) ---
LOGIN_PAGE_URL = 'https://secure13.aladtec.com/fairviewfd/index.php'
LOGIN_ACTION_URL = 'https://secure13.aladtec.com/fairviewfd/index.php?action=login'
# Securely get credentials from environment variables (GitHub Secrets)
USERNAME = os.environ.get("ALADTEC_USERNAME")
PASSWORD = os.environ.get("ALADTEC_PASSWORD")
# Look for files in the same directory as the script
ROUTINE_FILE_PATH = 'HQ and Sta2 routine.docx'
MEMBER_LIST_PATH = 'Member_List.csv'


# --- 2. DATE LOGIC ---
now = datetime.now()
cutoff_time = time(19, 0) # 7 PM cutoff
target_date = now.date() if now.time() < cutoff_time else (now + timedelta(days=1)).date()
date_for_url = target_date.strftime('%Y-%m-%d')
SCHEDULE_URL = f'https://secure13.aladtec.com/fairviewfd/index.php?action=manage_schedule_view_schedule&date={date_for_url}'
# Save the output to a 'docs' folder for GitHub Pages
output_filename = "docs/index.html"
os.makedirs("docs", exist_ok=True)


# --- 3. BIRTHDAY REMINDER PARSER ---
birthday_reminders_html = ""
try:
    if os.path.exists(MEMBER_LIST_PATH):
        found_birthdays = []
        today = now.date()
        check_dates = [today + timedelta(days=i) for i in range(3)]
        with open(MEMBER_LIST_PATH, mode='r', encoding='utf-8') as csvfile:
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
    print(f"Could not process birthday file: {e}")


# --- 4. DAILY ROUTINE PARSER ---
daily_routines_html = ""
try:
    if os.path.exists(ROUTINE_FILE_PATH):
        doc = docx.Document(ROUTINE_FILE_PATH)
        routines = {'HQ': {}, 'Station 2': {}}
        current_station, current_day = None, None
        days_of_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            if "Headquarters (HQ) Daily Routine" in text: current_station = 'HQ'; continue
            elif "Station 2 Daily Routine" in text: current_station = 'Station 2'; continue
            if current_station:
                is_day_header = False
                for day in days_of_week:
                    if text.upper().startswith(day):
                        current_day = day; routines[current_station][current_day] = []; is_day_header = True; break
                if not is_day_header and current_day and text and "Scheduled Weekly Tasks" not in text and "Important Notes" not in text:
                    routines[current_station][current_day].append(text.lstrip('-\t•_ ').strip())
        today_name = now.strftime('%A').upper()
        hq_tasks = routines.get('HQ', {}).get(today_name, ['Not found'])
        sta2_tasks = routines.get('Station 2', {}).get(today_name, ['Not found'])
        hq_routine, sta2_routine = '<br>'.join(hq_tasks), '<br>'.join(sta2_tasks)
        daily_routines_html = f"<div class=\"daily-routines\"><h3>Daily Routines for {now.strftime('%A')}</h3><div class=\"split-container\"><div class=\"split-column\"><h4>HQ</h4><p>{hq_routine or 'No tasks.'}</p></div><div class=\"split-column\"><h4>Station 2</h4><p>{sta2_routine or 'No tasks.'}</p></div></div></div>"
except Exception as e:
    print(f"Could not process routine file: {e}")


# --- 5. WEATHER FORECAST ---
weather_forecast, forecast_timeline_html = "Weather data not available.", ""
try:
    start_date_str, end_date_str = date_for_url, (target_date + timedelta(days=2)).strftime('%Y-%m-%d')
    weather_url = (f"https://api.open-meteo.com/v1/forecast?latitude=41.03&longitude=-73.76&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,windspeed_10m_max&hourly=precipitation_probability&temperature_unit=fahrenheit&windspeed_unit=mph&precipitation_unit=inch&timezone=America%2FNew_York&start_date={start_date_str}&end_date={end_date_str}")
    weather_response = requests.get(weather_url)
    if weather_response.status_code == 200:
        response_data = weather_response.json()
        daily_data, hourly_data = response_data.get('daily', {}), response_data.get('hourly', {})
        weather_codes = {0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast", 45: "Fog", 51: "Drizzle", 61: "Rain", 71: "Snow", 80: "Rain Showers", 85: "Snow Showers", 95: "Thunderstorm"}
        code, high_temp, low_temp, precip = daily_data.get('weathercode', [0])[0], round(daily_data.get('temperature_2m_max', [0])[0]), round(daily_data.get('temperature_2m_min', [0])[0]), daily_data.get('precipitation_sum', [0])[0]
        condition = weather_codes.get(code, "N/A"); weather_forecast = f"☀️ {condition} | High: {high_temp}°F | Low: {low_temp}°F | Precip: {precip:.2f} in"
        forecast_columns = []
        for i in range(len(daily_data.get('time', []))):
            day_details, day_date_obj = [], datetime.strptime(daily_data['time'][i], '%Y-%m-%d')
            day_suffix = 'th' if 11 <= day_date_obj.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day_date_obj.day % 10, 'th')
            day_details.append(f"<h4>{day_date_obj.strftime('%A, %B %d')}{day_suffix}</h4>")
            day_wind, day_rain, day_snow, day_code = daily_data['windspeed_10m_max'][i], daily_data['precipitation_sum'][i], daily_data['snowfall_sum'][i], daily_data['weathercode'][i]
            day_chance, night_chance = 0, 0
            if 'precipitation_probability' in hourly_data:
                hourly_probs = hourly_data['precipitation_probability']
                day_probs, night_probs = hourly_probs[i*24+7:i*24+19], hourly_probs[i*24+19:(i+1)*24] + hourly_probs[i*24:i*24+7]
                day_chance, night_chance = max(day_probs) if day_probs else 0, max(night_probs) if night_probs else 0
            if day_wind > 25: day_details.append(f"<p><strong>Wind Advisory:</strong> Expect winds around {day_wind:.0f} mph.</p>")
            if day_rain > 1.0: day_details.append("<p><strong>Coastal Flood Statement:</strong> Minor flooding is possible.</p>")
            if day_snow > 0.1: day_details.append(f"<p><strong>Winter Weather Advisory:</strong> Snowfall of {day_snow:.2f} inches possible.</p>")
            if day_code in [95, 96, 99]: day_details.append("<p><strong>Storm Watch:</strong> Thunderstorms are possible.</p>")
            day_details.append(f"<p><strong>Rain:</strong> Chance is {day_chance}% day / {night_chance}% night. Total: {day_rain:.2f} in.</p>")
            day_details.append(f"<p><strong>Wind:</strong> Expect winds around {day_wind:.0f} mph.</p>")
            forecast_columns.append(f"<div class='forecast-column'>{''.join(day_details)}</div>")
        forecast_timeline_html = f"<div class=\"forecast-timeline\"><h3>3-Day Forecast (White Plains, NY)</h3><div class=\"forecast-container\">{''.join(forecast_columns)}</div></div>"
except Exception as e:
    print(f"Could not fetch weather: {e}")

# --- 6. LOGIN AND FETCH SCHEDULE ---
html_content = ""
with requests.Session() as session:
    try:
        if not all([USERNAME, PASSWORD]):
             exit("ERROR: Username or password not set in GitHub Secrets.")
        login_page_response = session.get(LOGIN_PAGE_URL)
        match = re.search(r'globals\.CSRF_TOKEN = "([a-f0-9]+)"', login_page_response.text)
        if not match: exit("ERROR: Could not find CSRF token.")
        csrf_token_value = match.group(1)
        login_payload = {'username': USERNAME, 'password': PASSWORD, 'CSRF_TOKEN': csrf_token_value}
        login_response = session.post(LOGIN_ACTION_URL, data=login_payload)
        if 'logout' not in login_response.text.lower(): exit("ERROR: Login failed.")
        schedule_page_response = session.get(SCHEDULE_URL)
        if schedule_page_response.status_code == 200:
            html_content = schedule_page_response.text
    except requests.exceptions.RequestException as e:
        exit(f"An error occurred: {e}")

# --- 7. PARSE AND BUILD THE HTML REPORT ---
if html_content:
    soup = BeautifulSoup(html_content, 'html.parser')
    date_tag, schedules, trades, time_off, events = soup.find('span', id='title_date'), {}, [], [], []
    date_str = date_tag.text if date_tag else "Date Not Found"
    def get_shift(start_time_str): return 'day' if '07:45' <= start_time_str < '17:45' else 'night'
    work_schedule_header = soup.find('h2', class_='wv-summary-work-schedules-header')
    if work_schedule_header and work_schedule_header.find_next_sibling('table'):
        table = work_schedule_header.find_next_sibling('table')
        current_schedule_name = ""
        for row in table.find('tbody').find_all('tr'):
            schedule_cell = row.find('td', class_='schn_cell')
            if schedule_cell: current_schedule_name = schedule_cell.text.strip(); schedules.setdefault(current_schedule_name, [])
            cells = row.find_all('td')
            if len(cells) > 4 and current_schedule_name:
                start_time, member, time_type = cells[-6].text.strip(), cells[-3].text.strip(), cells[-1].text.strip()
                if 'Originally Scheduled:' in (trade_title := (cells[-2].find('img') or {}).get('title', '')):
                    original = trade_title.split('Originally Scheduled:')[1].split('&nbsp;')[0].strip()
                    member = f"{member} (Covering for {original})"
                if time_type and time_type.lower() != 'regular': member = f"{member} ({time_type})"
                schedules[current_schedule_name].append({'member': member, 'start': start_time})
    for section_name, data_list in [('Trades', trades), ('Time Off', time_off), ('Events', events)]:
        header = soup.find('h2', string=section_name)
        if header and (table := header.find_next_sibling('table')) and table.find('tbody'):
            for row in table.find('tbody').find_all('tr'):
                cells, start_time = row.find_all('td'), cells[1].text.strip()
                shift = get_shift(start_time)
                if section_name == 'Trades': data_list.append({'shift': shift, 'text': f"{cells[5].text.strip()} covering for {cells[4].text.strip()}"})
                elif section_name == 'Time Off': data_list.append({'shift': shift, 'text': f"{cells[4].text.strip()} ({cells[0].text.strip()})"})
                elif section_name == 'Events': data_list.append({'shift': shift, 'text': f"<strong>{cells[0].text.strip()}:</strong> {cells[4].text.strip()}"})
    
    # Process and sort all data into shifts
    def get_roster_list(key): return [item['member'] for item in schedules.get(key, [])]
    dayshift_officers, dayshift_ff = get_roster_list('Officers - Dayshift'), get_roster_list('Firefighters - Dayshift')
    nightshift_officers, nightshift_ff = get_roster_list('Officers - Nightshift'), get_roster_list('Firefighters - Nightshift')
    dayshift_overtime = [item['member'] for item in schedules.get('Non Shift Overtime / Work Detail', []) if get_shift(item['start']) == 'day']
    nightshift_overtime = [item['member'] for item in schedules.get('Non Shift Overtime / Work Detail', []) if get_shift(item['start']) == 'night']
    dayshift_trades = [item['text'] for item in trades if item['shift'] == 'day']
    nightshift_trades = [item['text'] for item in trades if item['shift'] == 'night']
    dayshift_time_off = [item['text'] for item in time_off if item['shift'] == 'day']
    nightshift_time_off = [item['text'] for item in time_off if item['shift'] == 'night']
    dayshift_events = [item['text'] for item in events if item['shift'] == 'day']
    nightshift_events = [item['text'] for item in events if item['shift'] == 'night']

    def generate_list_html(items): return '<br>'.join(items) if items else 'None'
    
    html_template = f"""
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>FD Roster</title><style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background-color: #f4f7fa; color: #333; font-size: 14px; }}
        .header {{ background-color: #c0392b; color: white; padding: 20px 40px; text-shadow: 1px 1px 1px #555; }}
        h1 {{ margin: 0; font-size: 22px; }} .header p {{ margin: 5px 0 0; opacity: 0.9; font-size: 14px; }}
        .weather-bar {{ background-color: #3498db; color: white; text-align: center; padding: 10px; font-size: 14px; font-weight: 500; }}
        .forecast-timeline, .daily-routines, .birthday-reminders {{ background-color: #ecf0f1; color: #333; padding: 15px 20px; margin: 0; border-bottom: 1px solid #dcdcdc; }}
        .forecast-timeline h3, .daily-routines h3, .birthday-reminders h3 {{ margin: 0 0 15px; text-align: center; color: #2c3e50; border-bottom: 1px solid #dcdcdc; padding-bottom: 10px; font-size: 16px; }}
        .forecast-container {{ display: flex; justify-content: space-around; flex-wrap: wrap; }}
        .forecast-column {{ flex: 1; min-width: 250px; padding: 0 10px; }}
        .forecast-timeline h4, .daily-routines h4 {{ margin: 10px 0 5px; color: #2980b9; font-size: 14px; }}
        .forecast-timeline p, .daily-routines p {{ margin: 0 0 5px; }}
        .daily-routines .split-container {{ display: flex; }} .daily-routines .split-column {{ flex: 1; padding: 0 15px; }}
        .daily-routines .split-column p {{ font-size: 13px; line-height: 1.5; }}
        .birthday-reminders ul {{ list-style-type: none; padding: 0; margin: 0; text-align: center; }}
        .container {{ display: flex; flex-wrap: wrap; padding: 10px; }}
        .column {{ flex: 1; min-width: 320px; background-color: white; margin: 10px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;}}
        .column h2 {{ background-color: #34495e; color: white; padding: 15px; margin: 0; font-size: 16px; }}
        .column ul {{ list-style-type: none; padding: 0; margin: 0; }}
        .column li {{ padding: 12px 20px; border-bottom: 1px solid #eee; }}
        .column li:last-child {{ border-bottom: none; }} .column li strong {{ color: #2980b9; }}
    </style></head><body>
        <div class="header"><h1>Fairview Fire Department Roster</h1><p>{date_str}</p></div>
        <div class="weather-bar">{weather_forecast}</div>
        {birthday_reminders_html}
        {forecast_timeline_html}
        {daily_routines_html}
        <div class="container">
            <div class="column"><h2>Dayshift (07:45 - 17:45)</h2><ul>
                <li><strong>Officers:</strong><br>{generate_list_html(dayshift_officers)}</li>
                <li><strong>Firefighters:</strong><br>{generate_list_html(dayshift_ff)}</li>
                {'<li><strong>Overtime / Work Detail:</strong><br>' + generate_list_html(dayshift_overtime) + '</li>' if dayshift_overtime else ''}
                {'<li><strong>Trades:</strong><br>' + generate_list_html(dayshift_trades) + '</li>' if dayshift_trades else ''}
                {'<li><strong>Time Off:</strong><br>' + generate_list_html(dayshift_time_off) + '</li>' if dayshift_time_off else ''}
                {'<li><strong>Events:</strong><br>' + generate_list_html(dayshift_events) + '</li>' if dayshift_events else ''}
            </ul></div>
            <div class="column"><h2>Nightshift (17:45 - 07:45)</h2><ul>
                <li><strong>Officers:</strong><br>{generate_list_html(nightshift_officers)}</li>
                <li><strong>Firefighters:</strong><br>{generate_list_html(nightshift_ff)}</li>
                {'<li><strong>Overtime / Work Detail:</strong><br>' + generate_list_html(nightshift_overtime) + '</li>' if nightshift_overtime else ''}
                {'<li><strong>Trades:</strong><br>' + generate_list_html(nightshift_trades) + '</li>' if nightshift_trades else ''}
                {'<li><strong>Time Off:</strong><br>' + generate_list_html(nightshift_time_off) + '</li>' if nightshift_time_off else ''}
                {'<li><strong>Events:</strong><br>' + generate_list_html(nightshift_events) + '</li>' if nightshift_events else ''}
            </ul></div>
        </div>
    </body></html>"""
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print("Process complete.")

