import os
import time
import pika
import json
import fastf1
import pandas as pd
from datetime import datetime
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv()

print("Connecting to RabbitMQ...")
params = pika.ConnectionParameters(host="f1livebot1-rabbitmq-1")  # Use service name from docker-compose
connection = pika.BlockingConnection(params)
channel = connection.channel()
channel.queue_declare(queue='f1_timetable_queue')
channel.exchange_declare(exchange='f1_timetable', exchange_type='direct')
channel.queue_bind(exchange='f1_timetable', queue="f1_timetable_queue")
print("Connected to RabbitMQ")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 90))
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
TEST_YEAR = int(os.getenv("TEST_YEAR", 2024))
TEST_RACE = os.getenv("TEST_RACE", "Italian")
SIMULATE_LIVE = os.getenv("SIMULATE_LIVE", "False").lower() == "true"
CURRENT_LAP = int(os.getenv("CURRENT_LAP", 1))
TOTAL_LAPS = None

def fetch_current_session():
    global TOTAL_LAPS
    if TEST_MODE:
        schedule = fastf1.get_event_schedule(TEST_YEAR)
        test_event = schedule[schedule['EventName'].str.contains(TEST_RACE, case=False)]
        if not test_event.empty:
            session = fastf1.get_session(TEST_YEAR, int(test_event.iloc[0]['RoundNumber']), 'R')
            session.load()
            TOTAL_LAPS = session.total_laps if hasattr(session, 'total_laps') else None
            return test_event.iloc[0]
        return None
    now = datetime.now()
    schedule = fastf1.get_event_schedule(now.year)
    schedule['Session1Date'] = pd.to_datetime(schedule['Session1Date'], errors='coerce')
    upcoming = schedule[schedule['Session1Date'] > now].sort_values(by='Session1Date')
    if not upcoming.empty:
        session = fastf1.get_session(now.year, int(upcoming.iloc[0]['RoundNumber']), 'R')
        session.load()
        TOTAL_LAPS = session.total_laps if hasattr(session, 'total_laps') else None
        return upcoming.iloc[0]
    return None

def clean_time(time_str):
    if pd.isna(time_str) or time_str == "N/A":
        return "N/A"
    try:
        return str(pd.to_timedelta(time_str)).replace("0 days ", "") if "0 days " in str(pd.to_timedelta(time_str)) else str(pd.to_timedelta(time_str))
    except:
        return "N/A"

def fetch_lap_times(event, current_lap=None):
    year = TEST_YEAR if TEST_MODE else event.get('EventDate', datetime.now()).year
    round_number = int(event.get('RoundNumber', 0))
    session = fastf1.get_session(year, round_number, 'R')
    session.load()
    total_laps = session.total_laps if hasattr(session, 'total_laps') else "N/A"
    
    if SIMULATE_LIVE and current_lap is not None:
        laps_until_now = session.laps[session.laps['LapNumber'] <= current_lap]
        latest_positions = laps_until_now[laps_until_now['LapNumber'] == current_lap]
        standings = []
        
        all_drivers = session.results['DriverNumber'].tolist() if hasattr(session, 'results') else []
        for driver_number in all_drivers:
            lap = latest_positions[latest_positions['DriverNumber'] == driver_number] if driver_number in latest_positions['DriverNumber'].values else None
            driver_info = session.get_driver(driver_number)
            driver_code = driver_info['Abbreviation'] if 'Abbreviation' in driver_info else "UNK"
            driver_name = f"{driver_info['FirstName']} {driver_info['LastName']}" if 'FirstName' in driver_info else "Unknown Driver"
            team_name = driver_info['TeamName'] if 'TeamName' in driver_info else "Unknown Team"
            
            lap_time = clean_time(lap['LapTime'].values[0]) if lap is not None and 'LapTime' in lap else "N/A"
            pit_stops = len(laps_until_now[(laps_until_now['DriverNumber'] == driver_number) & laps_until_now['PitInTime'].notna()])
            
            position = lap['Position'].values[0] if lap is not None else "N/A"
            
            standings.append({
                "pos": position,
                "num": driver_number,
                "code": driver_code,
                "name": driver_name,
                "team": team_name,
                "lap_time": lap_time,
                "lap": int(lap['LapNumber'].values[0]) if lap is not None else "N/A",
                "pits": pit_stops
            })
        
        # Sort standings by position (numerical first, then "N/A" at the end)
        def sort_key(item):
            pos = item["pos"]
            if pos == "N/A":
                return float('inf')  # Place N/A at the end
            try:
                return float(pos)    # Convert numeric positions for proper sorting
            except (ValueError, TypeError):
                return float('inf')  # If conversion fails, place at the end
        
        standings.sort(key=sort_key)
        
        return standings, total_laps
    return [], "N/A"

def create_timetable(event, standings, total_laps, current_lap=None):
    if not standings:
        return "No data available for the current session."
    
    table_data = [[s["pos"], s["num"], s["code"], s["name"], s["team"], s["lap_time"], s["lap"], s["pits"]] for s in standings]
    headers = ["Pos", "№", "Code", "Driver", "Team", "Time", "Lap", "Pits"]
    table = tabulate(table_data, headers=headers, tablefmt="pipe")
    
    return (
        f"🏎️ *{event['EventName']} - Race* 🏁\n"
        f"📍 {event['EventName']}\n"
        f"🏎️ Race In Progress - Lap {current_lap}/{total_laps}\n"
        f"⏱️ Last Updated: {datetime.now().strftime('%H:%M:%S')} ETC\n\n"
        f"```{table}```"
    )

def main():
    global CURRENT_LAP
    event = fetch_current_session()
    if event is not None and TOTAL_LAPS is not None:
        while CURRENT_LAP <= TOTAL_LAPS:
            standings, total_laps = fetch_lap_times(event, CURRENT_LAP)
            timetable = create_timetable(event, standings, total_laps, CURRENT_LAP)
            # Send message to RabbitMQ
            print(f"Sending update for lap {CURRENT_LAP}/{TOTAL_LAPS}")
            channel.basic_publish(
                exchange='f1_timetable',
                routing_key='f1_timetable_queue',
                body=json.dumps(timetable)
            )
            CURRENT_LAP += 1
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()