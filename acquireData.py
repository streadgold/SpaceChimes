import requests
import json
from skyfield.api import Topos, load, EarthSatellite
from geopy.distance import geodesic
from credentials import USERNAME, PASSWORD # Import credentials
from datetime import datetime, timedelta
import os
import smbus
import time
import screen
import sys

start_code = datetime.now()
#set location
my_location = (29.76303, -95.362061)

ts = load.timescale()

# Create an SMBus instance
bus = smbus.SMBus(1)

# ADS1115 default address
address = 0x48

# ADS1115 registers
ADS1115_CONVERSION = 0x00
ADS1115_CONFIG = 0x01

# Configuration settings for A0 and A1
config_A0 = [0xC1, 0x83]  # A0
config_A1 = [0xD1, 0x83]  # A1

def read_potentiometer(channel_config):
    try:
        # Write configuration for the current channel
        bus.write_i2c_block_data(address, ADS1115_CONFIG, channel_config)
        
        # Wait for the conversion to complete
        time.sleep(0.1)
        
        # Read the conversion result
        data = bus.read_i2c_block_data(address, ADS1115_CONVERSION, 2)
        
        # Convert the data to a 16-bit integer
        val = (data[0] << 8) | data[1]
        
        # Check for negative values and adjust
        if val > 32767:
            val -= 65536
        
        # Invert and normalize the value (0 to 32767 becomes 1 to 0)
        normalized_val = (32767 - val) / 32767.0
        
        return normalized_val
    except Exception as e:
        print(e)
        return None

# Read and print the inverted normalized value from A0
radius = read_potentiometer(config_A0)*500 # get search radius
screen.clear_display()
screen.write_text(f"New Radius: {radius:.0f}")
print(f"Search radius: {radius:.0f} km")

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
            if distance_km > radius: #exclude satellites too far away
                return None

            return {
                'culmination_time': culmination_time.utc_strftime('%Y-%m-%d %H:%M:%S'),
                'altitude_km': altitude_km,
                'distance_km': distance_km
            }
    return None

def progress_meter(progress, total):
    percent = 100 * (progress / total)
    bar_length = 40
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\rProgress: |{bar}| {percent:.2f}% Complete', end='')
    sys.stdout.flush()


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

filename = "data.json"
need_new_data = True
need_new_debris_data = True

# Check if login was successful
if response.status_code == 200:
    print("Login successful.")

    if os.path.exists(filename):
        with open(filename, 'r') as file:
            saved_data = json.load(file)
            last_updated_str = saved_data.get("last_updated", "")
            if last_updated_str:
                last_updated = datetime.strptime(last_updated_str, '%Y-%m-%d %H:%M:%S')
                if datetime.utcnow() - last_updated < timedelta(days=1):
                    need_new_data = False
                    json_data = saved_data.get("data", [])
                    print("Using cached data.")
                else:
                    print("Cached data is older than one day.")
    else:
        print("Data file does not exist.")

    if need_new_data:
        print("Fetching data from server...")
        data_response = session.get(DATA_URL)
        if data_response.status_code == 200:
            json_data = data_response.json()
            data_to_save = {
                "last_updated": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "data": json_data
            }
            with open(filename, 'w') as file:
                json.dump(data_to_save, file, indent=4)
        else:
            print(f"Failed to retrieve data. Status Code: {data_response.status_code}")
            json_data = []  # ensure json_data is always defined

    # filter data and check for valid subpoint
    filtered_data = []
    
    index = 0
    
    filename2 = "debris_data.json"
    if os.path.exists(filename2):
        with open(filename2, 'r') as file:
            saved_data = json.load(file)
            last_updated_str2 = saved_data.get("last_updated", "")
            if last_updated_str2:
                last_updated2 = datetime.strptime(last_updated_str2, '%Y-%m-%d %H:%M:%S')
                if datetime.utcnow() - last_updated2 < timedelta(hours=2):
                    need_new_debris_data = False
                    json_data = saved_data.get("data", [])
                    print("Using cached debris data.")
                else:
                    print("Cached debris data is older than two hours so updating.")
    if need_new_debris_data:
        print("\n Checking for valid entries in the downloaded data")
        for entry in json_data:
            progress_meter(index,len(json_data))
            #print(f"{(index/len(json_data)*100):3.02f}" + "% complete")
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

        print("\n Calculating pass times:")
        for debris in filtered_data:
            progress_meter(index,len(filtered_data))
            #print(f"{(index/len(filtered_data)*100):3.02f}" + "% complete")
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
        
        debris_data_to_save = {
            "last_updated": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "data": filtered_pass_data
        }

        with open('debris_data.json', 'w') as file:
            json.dump(debris_data_to_save, file, indent=4)

        print(f"Debris data written to file successfully. {len(filtered_data)} entries saved.")

else:
    print("Login failed. Status Code:", response.status_code)

end_code = datetime.now()
print(end_code-start_code)
