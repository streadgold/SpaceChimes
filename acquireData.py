import requests
import json
from skyfield.api import Topos, load, EarthSatellite
from geopy.distance import geodesic
from credentials import USERNAME, PASSWORD # Import credentials
from datetime import datetime, timedelta
import os

start_code = datetime.now()
#set location
my_location = (29.76303, -95.362061)

ts = load.timescale()
def log_exclusion(reason, debris):
    with open('exclusion_log.txt', 'a') as log_file:
        log_message = f"Excluded {debris.get('OBJECT_ID', 'Unknown ID')}: {reason}\n"
        log_file.write(log_message)


def is_valid_subpoint(debris):
    tle_line1, tle_line2 = debris.get('TLE_LINE1'), debris.get('TLE_LINE2')
    if tle_line1 and tle_line2 and (debris.get('DECAY_DATE') is None or debris.get('DECAY_DATE') == "None"):
        satellite = EarthSatellite(tle_line1, tle_line2)
        
        #print(satellite)
        # do some checks to exclude invalid satellites
        try:
            geocentric = satellite.at(ts.now())
        except Exception as e:
            print("Error encountered " + str(e))
            print(debris.get('DECAY_DATE'))
            return False
        else:
            try:
                distance = geodesic(my_location, (geocentric.subpoint().latitude.degrees, geocentric.subpoint().longitude.degrees)).km
            except Exception as e:
                print("Error encountered " + str(e))
                return False
    return True


def next_pass_details(tle_line1, tle_line2, observer_location):
    ts = load.timescale()
    satellite = EarthSatellite(tle_line1, tle_line2)
    observer = Topos(latitude_degrees=observer_location[0], longitude_degrees=observer_location[1])

    start_time = ts.now()
    end_time = start_time + 1.0  # Look 24 hours ahead

    # Initialize variables
    pass_start = pass_end = culmination_time = None
    altitude_km = -1  # Use -1 or another sentinel value indicating "not set"

    times, events = satellite.find_events(observer, start_time, end_time, altitude_degrees=0.0)
    for time, event in zip(times, events):
        if event == 1:  # Culmination
            culmination_time = time
            geocentric = satellite.at(time)
            subpoint = geocentric.subpoint()
            altitude_km = subpoint.elevation.km  # This gives the altitude above Earth's surface in kilometers
            observer_location = (observer.latitude.degrees, observer.longitude.degrees)
            subsatellite_point = (subpoint.latitude.degrees, subpoint.longitude.degrees)
            distance_km = geodesic(observer_location, subsatellite_point).km
            if distance_km > 200: #exclude satellites too far away
                return None
            print(distance_km)

            return {
                'culmination_time': culmination_time.utc_strftime('%Y-%m-%d %H:%M:%S'),
                'altitude_km': altitude_km,
                'distance_km': distance_km
            }
    return None

# URL for the login action
LOGIN_URL = 'https://www.space-track.org/ajaxauth/login'

# URL for the data query
DATA_URL = 'https://www.space-track.org/basicspacedata/query/class/gp/decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id/format/json'

# Create a session object
session = requests.Session()

# Payload for login
payload = {
    'identity': USERNAME,
    'password': PASSWORD,
}

# Perform login
response = session.post(LOGIN_URL, data=payload)
test = True
filename = "data.json"

# Check if login was successful
if response.status_code == 200:
    print("Login successful.")

    if test and os.path.exists(filename):
        print("Loading data from local file...")
        with open(filename, 'r') as file:
            json_data = json.load(file)
    else:
        # Retrieve data from the server
        print("Fetching data from server...")
        data_response = session.get(DATA_URL)
        if data_response.status_code == 200:
            json_data = data_response.json()
            if test:  # Save for future use if in test mode
                with open(filename, 'w') as file:
                    json.dump(json_data, file, indent=4)
        else:
            print(f"Failed to retrieve data. Status Code: {data_response.status_code}")
            json_data = []  # Ensure json_data is always defined


    # Filter data and check for valid subpoint
    filtered_data = []
    
    index = 0

    for entry in json_data:
        print(f"{(index/len(json_data)*100):3.02f}" + "% complete")
        index += 1

        if entry.get('DECAY_DATE') is not None:
            log_exclusion("Already decayed", entry)
            continue

        inclination = float(entry.get('INCLINATION', 0))
        if inclination < (my_location[0]) - 4:
            log_exclusion("Inclination below threshold", entry)
            continue

        # Assuming is_valid_subpoint function checks if the satellite's pass is valid for the observer's location
        if not is_valid_subpoint(entry):
            log_exclusion("Invalid subpoint calculation", entry)
            continue

        if not (entry.get("OBJECT_TYPE") in ["DEBRIS", "ROCKET BODY", "UNKNOWN"]):
            log_exclusion("Invalid subpoint calculation", entry)
            continue
        filtered_data.append(entry)

    filtered_pass_data = []

    index = 0

    for debris in filtered_data:
        print(f"{(index/len(filtered_data)*100):3.02f}" + "% complete")
        index += 1
        tle_line1 = debris.get('TLE_LINE1')
        tle_line2 = debris.get('TLE_LINE2')
        if tle_line1 and tle_line2:
            pass_details = next_pass_details(tle_line1, tle_line2, my_location)
            if pass_details:
                filtered_pass_data.append({
                    'object_id': debris.get('OBJECT_ID'),
                    'object_name': debris.get('OBJECT_NAME'),
                    'rcs': debris.get('RCS_SIZE'),  # Assuming RCS_SIZE is the correct field for radar cross-section
                    'culmination_time': pass_details['culmination_time'],
                    'altitude_km': pass_details['altitude_km'],
                    'distance_km': pass_details['distance_km']
                })
            else:
                log_exclusion("Missing pass data", debris)
                continue
        else:
            log_exclusion("Missing TLE data", debris)
            continue

    filtered_pass_data.sort(key=lambda x: x['culmination_time'])

    with open('debris_data.json', 'w') as file:
        json.dump(filtered_pass_data, file, indent=4)

    print(f"Debris data written to file successfully. {len(filtered_data)} entries saved.")

else:
    print("Login failed. Status Code:", response.status_code)

end_code = datetime.now()
print(end_code-start_code)
