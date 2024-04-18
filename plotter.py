import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json

# Assuming you've already loaded your culmination times into `culmination_times`
# If not, load them from your JSON file
with open('debris_data.json', 'r') as file:
    debris_data = json.load(file)
culmination_times = [datetime.strptime(debris['culmination_time'], '%Y-%m-%d %H:%M:%S') for debris in debris_data]

# Prepare the plot
fig, ax = plt.subplots()

# Plotting each culmination time against a range to spread them out visually
ax.plot(culmination_times, range(len(culmination_times)), marker='o', linestyle='')

# Formatting the x-axis to show dates and times
ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))  # Locate every hour
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))  # Format including hours, minutes, seconds

plt.gcf().autofmt_xdate()  # Auto-rotate date labels to fit

# Adding labels and title for context
plt.xlabel('Culmination Time')
plt.ylabel('Number of Culminations')
plt.title('Distribution of Culmination Times')

# Show plot
plt.show()

