from skyfield.api import load, EarthSatellite
import json
from geopy.distance import geodesic
import time
from datetime import datetime, timedelta

# G6 = 1567.98
# A#6 = 1864.66
# C7 = 2093.00
# D7 = 2349.32
# F7 = 2793.83
# G7 = 3135.96
# A#7 = 3729.31
# C8 = 4186.01

# Function to classify altitude into pitch bins
def altitude_to_pitch_bin(altitude):
    bins = [0, 400, 800, 1200, 1600, 2000, 10000, 30000]  # km
    pitches = [1567.98, 1864.66, 2093.00, 2349.32, 2793.83, 3135.96, 3729.31, 4186.01]  # chime notes

    for i, bin_edge in enumerate(bins):
        if altitude <= bin_edge:
            return pitches[i]
    return pitches[-1]  # For altitudes > 30000km


# Function to classify RCS into duration bins
def rcs_to_duration_bin(rcs_size):
    # Assuming RCS values are classified into none (0), small (1), medium (2), large (3)
    # Adjust the thresholds as per your definitions
    if rcs_size == 'null':
        return 1  # Duration in seconds (example)
    elif rcs_size == 'SMALL':
        return 2
    elif rcs_size == 'MEDIUM':
        return 3
    elif rcs_size == 'LARGE':
        return 6
    else:
        return 0  # Default or error case


# Your location
start = (29.76303, -95.362061)

# Initialize a Skyfield timescale
ts = load.timescale()


# Load the JSON file initially
def load_debris_data():
    with open('debris_data.json', 'r') as file:
        return json.load(file)


debris_data = load_debris_data()

# Set the next reload time to 24 hours from now
next_reload_time = datetime.now() + timedelta(days=1)

# Main loop
while True:
    current_time = datetime.now()

    # Reload the debris data if a day has passed
    if current_time >= next_reload_time:
        debris_data = load_debris_data()
        next_reload_time = current_time + timedelta(days=1)
        print("Reloaded debris data.")

    t = ts.now()

    for debris in debris_data:
        tle_line1 = debris.get('TLE_LINE1')
        tle_line2 = debris.get('TLE_LINE2')

        if tle_line1 and tle_line2:
            satellite = EarthSatellite(tle_line1, tle_line2)
            geocentric = satellite.at(t)
            subpoint = geocentric.subpoint()
            end = (subpoint.latitude.degrees, subpoint.longitude.degrees)

            distance = geodesic(start, end).km

            if distance < 200:
                altitude_km = subpoint.elevation.km
                rcs = debris.get('RCS_SIZE', 'null')  # Default to 'null'
                pitch = altitude_to_pitch_bin(altitude_km)
                duration = rcs_to_duration_bin(rcs)

                # Placeholder for sound generation based on pitch and duration
                print(f"Play sound for {debris.get('OBJECT_ID')} {debris.get('OBJECT_NAME')} with pitch {pitch} and "
                      f"duration {duration} seconds. {rcs} RCS {altitude_km:.0f} km altitude {distance:.0f} km away")

    print()
    time.sleep(60)  # Wait 60 seconds before the next update
