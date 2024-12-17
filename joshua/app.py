from flask import Flask, jsonify, render_template
import RPi.GPIO as GPIO
import dht11
import time
import datetime
import collections
import Adafruit_ADS1x15
import threading
import numpy as np
from scipy.signal import cheby1, lfilter

# Initialize Flask app
app = Flask(__name__)

# --- GPIO and ADC Setup ---
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BCM)

# Initialize DHT11 sensor on GPIO pin 17
sensor_1 = dht11.DHT11(pin=17)

# Initialize ADS1115 ADC for soil moisture sensor
i2c_bus_number = 1
adc = Adafruit_ADS1x15.ADS1115(busnum=i2c_bus_number)
GAIN = 1  # Gain setting for ADS1115

# --- DHT11 Parameters (Window Filtering) ---
WINDOW_SIZE = 5
temperature_window = collections.deque(maxlen=WINDOW_SIZE)
last_valid_temperature = None
raw_temperature = []  # Store raw temperature readings

# --- Soil Moisture Parameters (Chebyshev Filtering) ---
SOIL_SENSOR_CHANNEL = 2
order = 4
ripple = 0.5
sampling_frequency = 1  # Hz
cutoff_frequency = 0.1  # Hz
b, a = cheby1(order, ripple, cutoff_frequency / (0.5 * sampling_frequency), btype='low')
raw_values = []  # Buffer for raw soil moisture values

# Shared data dictionary for Flask API
data = {
    "temperature": [],
    "temperature_raw": [],
    "soil_moisture": [],
    "soil_moisture_raw": [],
    "timestamps": []
}

# Function to apply Chebyshev filter
def apply_chebyshev_filter(data):
    return lfilter(b, a, data)

# Background thread for sensor readings
def read_sensors():
    global last_valid_temperature
    while True:
        # --- DHT11 Sensor Reading with Window Filtering ---
        result_1 = sensor_1.read()
        if result_1.is_valid():
            last_valid_temperature = result_1.temperature
            temperature_window.append(result_1.temperature)
            raw_temperature.append(result_1.temperature)
        else:
            if last_valid_temperature is not None:
                temperature_window.append(last_valid_temperature)
                raw_temperature.append(last_valid_temperature)
            else:
                temperature_window.append(0)
                raw_temperature.append(0)

        # Keep raw temperature manageable
        if len(raw_temperature) > 50:
            raw_temperature.pop(0)

        # Calculate smoothed temperature
        smoothed_temperature = sum(temperature_window) / len(temperature_window)

        # --- Soil Moisture Sensor Reading with Chebyshev Filtering ---
        raw_value = adc.read_adc(SOIL_SENSOR_CHANNEL, gain=GAIN)
        raw_values.append(raw_value)

        # Keep buffer manageable
        if len(raw_values) > 50:
            raw_values.pop(0)

        # Apply Chebyshev filter
        if len(raw_values) > order:
            filtered_values = apply_chebyshev_filter(raw_values)
            filtered_soil_value = filtered_values[-1]
        else:
            filtered_soil_value = raw_value  # Fallback to raw value

        # --- Store Data ---
        data["temperature"].append(smoothed_temperature)
        data["temperature_raw"].append(raw_temperature[-1])
        data["soil_moisture"].append(filtered_soil_value)
        data["soil_moisture_raw"].append(raw_value)
        data["timestamps"].append(datetime.datetime.now().strftime("%H:%M:%S"))

        # Keep data length manageable
        if len(data["temperature"]) > 50:
            data["temperature"].pop(0)
            data["temperature_raw"].pop(0)
            data["soil_moisture"].pop(0)
            data["soil_moisture_raw"].pop(0)
            data["timestamps"].pop(0)

        time.sleep(1)

# Flask Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def get_data():
    return jsonify(data)

# Start the background thread
sensor_thread = threading.Thread(target=read_sensors, daemon=True)
sensor_thread.start()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
