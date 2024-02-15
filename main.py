from skyfield.api import load, EarthSatellite
import json
import random
from geopy.distance import geodesic
import numpy as np
import pyaudio
import time
from datetime import datetime, timedelta
import contextlib
import os
import sys
import time
import board
import runpy
import serial

arduino_port = '/dev/ttyACM0'  # Serial port for Arduino
baud_rate = 9600  # Common baud rate for Arduino
serial_conn = serial.Serial(arduino_port, baud_rate, timeout=1)

my_location = (29.76303, -95.362061)

note_frequencies = {
    "C0": 16.35, "C#0/Db0": 17.32, "D0": 18.35, "D#0/Eb0": 19.45, "E0": 20.60, "F0": 21.83, "F#0/Gb0": 23.12, "G0": 24.50, "G#0/Ab0": 25.96, "A0": 27.50, "A#0/Bb0": 29.14, "B0": 30.87,
    "C1": 32.70, "C#1/Db1": 34.65, "D1": 36.71, "D#1/Eb1": 38.89, "E1": 41.20, "F1": 43.65, "F#1/Gb1": 46.25, "G1": 49.00, "G#1/Ab1": 51.91, "A1": 55.00, "A#1/Bb1": 58.27, "B1": 61.74,
    "C2": 65.41, "C#2/Db2": 69.30, "D2": 73.42, "D#2/Eb2": 77.78, "E2": 82.41, "F2": 87.31, "F#2/Gb2": 92.50, "G2": 98.00, "G#2/Ab2": 103.83, "A2": 110.00, "A#2/Bb2": 116.54, "B2": 123.47,
    "C3": 130.81, "C#3/Db3": 138.59, "D3": 146.83, "D#3/Eb3": 155.56, "E3": 164.81, "F3": 174.61, "F#3/Gb3": 185.00, "G3": 196.00, "G#3/Ab3": 207.65, "A3": 220.00, "A#3/Bb3": 233.08, "B3": 246.94,
    "C4": 261.63, "C#4/Db4": 277.18, "D4": 293.66, "D#4/Eb4": 311.13, "E4": 329.63, "F4": 349.23, "F#4/Gb4": 369.99, "G4": 392.00, "G#4/Ab4": 415.30, "A4": 440.00, "A#4/Bb4": 466.16, "B4": 493.88,
    "C5": 523.25, "C#5/Db5": 554.37, "D5": 587.33, "D#5/Eb5": 622.25, "E5": 659.25, "F5": 698.46, "F#5/Gb5": 739.99, "G5": 783.99, "G#5/Ab5": 830.61, "A5": 880.00, "A#5/Bb5": 932.33, "B5": 987.77,
    "C6": 1046.50, "C#6/Db6": 1108.73, "D6": 1174.66, "D#6/Eb6": 1244.51, "E6": 1318.51, "F6": 1396.91, "F#6/Gb6": 1479.98, "G6": 1567.98, "G#6/Ab6": 1661.22, "A6": 1760.00, "A#6/Bb6": 1864.66, "B6": 1975.53,
    "C7": 2093.00, "C#7/Db7": 2217.46, "D7": 2349.32, "D#7/Eb7": 2489.02, "E7": 2637.02, "F7": 2793.83, "F#7/Gb7": 2959.96, "G7": 3135.96, "G#7/Ab7": 3322.44, "A7": 3520.00, "A#7/Bb7": 3729.31, "B7": 3951.07,
    "C8": 4186.01, "C#8/Db8": 4434.92, "D8": 4698.63, "D#8/Eb8": 4978.03, "E8": 5274.04, "F8": 5587.65, "F#8/Gb8": 5919.91, "G8": 6271.93, "G#8/Ab8": 6644.88, "A8": 7040.00, "A#8/Bb8": 7458.62, "B8": 7902.13,
}

@contextlib.contextmanager
def ignore_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


# Sound synthesis functions
def generate_tone(frequency, duration, decay_rate, volume=0.5, rate=44100):
    length = int(duration * rate)
    t = np.linspace(0, duration, length)
    decay = np.exp(decay_rate * t)  # Exponential decay
    waveform = (volume * np.sin(2 * np.pi * frequency * t) * decay).astype(np.float32)
    return waveform


def generate_tone_with_reverb(frequency, duration, decay_rate, volume=0.5, rate=44100, reverb_delay=0.05, reverb_decay=0.3):
    length = int(duration * rate)
    t = np.linspace(0, duration, length)
    decay = np.exp(decay_rate * t)
    waveform = volume * np.sin(2 * np.pi * frequency * t) * decay

    # Calculate the number of samples for the reverb delay
    delay_samples = int(reverb_delay * rate)

    # Create a reverb effect by adding delayed and attenuated copies of the waveform
    reverb_waveform = np.zeros_like(waveform)
    for i in range(1, 5):  # Create multiple echoes for a more complex reverb effect
        echo_delay = i * delay_samples
        echo_volume = volume * (reverb_decay ** i)
        if echo_delay < length:
            reverb_waveform[:-echo_delay] += waveform[echo_delay:] * echo_volume

    # Mix the original waveform with the reverb waveform
    mixed_waveform = waveform + reverb_waveform
    # Ensure the waveform doesn't exceed the original volume
    mixed_waveform = np.clip(mixed_waveform, -volume, volume)

    return mixed_waveform.astype(np.float32)


def play_combined_sounds(tone_list, rate=44100):
    """
    Mixes and plays a list of tones with specified offsets.
    Each element in tone_list is a tuple (waveform, offset_in_seconds).
    """
    # Calculate the total length needed for the combined waveform, considering offsets
    total_length = max(len(waveform) + int(offset * rate) for waveform, offset in tone_list)
    combined_waveform = np.zeros(total_length, dtype=np.float32)
    
    for waveform, offset in tone_list:
        start_index = int(offset * rate)
        end_index = start_index + len(waveform)
        combined_waveform[start_index:end_index] += waveform[:end_index-start_index]
    
    # Normalize to prevent clipping
    max_val = np.max(np.abs(combined_waveform))
    if max_val > 1:
        combined_waveform /= max_val
    
    play_sound(combined_waveform)


def play_sound(waveform, rate=44100):
    with ignore_stderr():
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32, channels=1, rate=rate, output=True)
        stream.write(waveform.tostring())
        stream.stop_stream()
        stream.close()
        p.terminate()


# Function to classify altitude into pitch bins
def altitude_to_pitch_bin(altitude):
    bins = [0, 400, 800, 1200, 1600, 2000, 10000, 30000]  # km
    #notes = ["G6", "A#6/Bb6", "C7", "D7", "F7", "G7", "A#7/Bb7", "C8"]  # Note names
    notes = ["G4", "A#5/Bb5", "C6", "D6", "F6", "G6", "A#6/Bb6", "C7"]  # Note names
    #notes = ["G3", "A4", "C5", "D5", "E5", "F#5/Gb5", "D6", "F6"]  # Note names

    for i, bin_edge in enumerate(bins):
        if altitude <= bin_edge:
            return note_frequencies[notes[i]],i-1
    return note_frequencies[notes[-1]] , 7  # For altitudes > 30000km


# Function to classify RCS into duration bins
def rcs_to_duration_bin(rcs_size):
    if rcs_size == 'null':
        duration=2
        decay_rate=-2
    elif rcs_size == 'None':
        duration=2
        decay_rate=-2
    elif rcs_size is None:
        duration=2
        decay_rate=-2
    elif rcs_size == 'SMALL':
        duration=2
        decay_rate=-2
    elif rcs_size == 'MEDIUM':
        duration=4
        decay_rate=-1
    elif rcs_size == 'LARGE':
        duration=8
        decay_rate=-0.5
    else:
        duration=2
        decay_rate=2
    return duration,decay_rate

ts = load.timescale()

def load_debris_data():
    with open('debris_data.json', 'r') as file:
        return json.load(file)

runpy.run_path(path_name='getData.py')
debris_data = load_debris_data()
next_reload_time = datetime.now() + timedelta(days=1)

#main loop
while True:
    tone_list = []  # List to store tone data (waveform, offset)
    if datetime.now() >= next_reload_time:
        debris_data = load_debris_data()
        next_reload_time = datetime.now() + timedelta(days=1)
        print("Reloaded debris data.")
    
    serial_conn.write(str(999).encode())
    time.sleep(0.1)
     
    for debris in debris_data:
        tle_line1, tle_line2 = debris.get('TLE_LINE1'), debris.get('TLE_LINE2')
        if tle_line1 and tle_line2 and (debris.get('DECAY_DATE') is None or debris.get('DECAY_DATE') == "None"):
            satellite = EarthSatellite(tle_line1, tle_line2)

            distance = 1000
            # Need this to handle problem when a satellite has decayed but data set hasn't updated - which causes a NaN result for the lat/long
            try:
                geocentric = satellite.at(ts.now())
            except Exception as e:
                print("Error encountered " + str(e))
                print(debris.get('DECAY_DATE'))
            else:
                try:
                    distance = geodesic(my_location, (geocentric.subpoint().latitude.degrees, geocentric.subpoint().longitude.degrees)).km
                except Exception as e:
                    print(debris.get('OBJECT_ID'))
                    print(debris.get('DECAY_DATE'))
                    print(geocentric.subpoint())
                    print("Error encountered " + str(e))
                    
            
            if distance < 200: #add all objects within 200km of my location
                altitude_km = geocentric.subpoint().elevation.km
                frequency, pixelbin = altitude_to_pitch_bin(altitude_km)
                duration, decay_rate = rcs_to_duration_bin(debris.get('RCS_SIZE', 'null'))
                waveform = generate_tone_with_reverb(frequency, duration, decay_rate)
                offset_by_distance = (distance/200) * 2
                tone_list.append((waveform, offset_by_distance))  # Add tone with a random offset
                print(f"{debris.get('OBJECT_ID')} {debris.get('OBJECT_NAME')} - (RCS: {debris.get('RCS_SIZE')} , Altitude: {altitude_km:.0f} km , Distance: {distance:.0f} km)")
                serial_conn.write(str(pixelbin).encode())
                time.sleep(0.1)

    if tone_list:
        play_combined_sounds(tone_list)
    
    print()
    time.sleep(5)

serial_conn.close()
