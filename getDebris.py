import requests
import json
from credentials import USERNAME, PASSWORD  # Import credentials

# URL for the login action
LOGIN_URL = 'https://www.space-track.org/ajaxauth/login'

# URL for the data query
DATA_URL = 'https://www.space-track.org/basicspacedata/query/class/gp/decay_date/null-val/epoch/%3Enow-30/orderby/norad_cat_id/format/json'

# Create a session object
session = requests.Session()

# Payload for login, using imported credentials
payload = {
    'identity': USERNAME,
    'password': PASSWORD,
}

# Perform login
response = session.post(LOGIN_URL, data=payload)

# Check if login was successful
if response.status_code == 200:
    print("Login successful.")

    # Retrieve the data
    data_response = session.get(DATA_URL)

    if data_response.status_code == 200:
        # Load the JSON data
        json_data = data_response.json()

        # Open a file to write the filtered data
        with open('debris_data.json', 'w') as file:
            # Filter and write entries where OBJECT_TYPE is DEBRIS
            debris_data = [entry for entry in json_data if entry.get("OBJECT_TYPE") == "DEBRIS" or entry.get("OBJECT_TYPE") == "ROCKET BODY" or entry.get("OBJECT_TYPE") == "UNKNOWN" and entry.get('DECAY_DATE') is None]
            print(len(debris_data))
            # Write the filtered data to the file in JSON format
            json.dump(debris_data, file, indent=4)

        print("Debris data written to file successfully.")
    else:
        print("Failed to retrieve data. Status Code:", data_response.status_code)
else:
    print("Login failed. Status Code:", response.status_code)
