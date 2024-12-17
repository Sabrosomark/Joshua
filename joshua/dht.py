import RPi.GPIO as GPIO
import dht11
import time
import datetime

# initialize GPIO
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BCM)

# initialize DHT11 sensor
sensor_1 = dht11.DHT11(pin=17)

# Store the last valid reading
last_valid_temperature = None

try:
    while True:
        # Read from the sensor
        result_1 = sensor_1.read()
        if result_1.is_valid():
            last_valid_temperature = result_1.temperature
            sensor_1_data = "Temperature: %-3.1f C" % result_1.temperature
        else:
            if last_valid_temperature is not None:
                sensor_1_data = "Temperature: %-3.1f C (Last Valid)" % last_valid_temperature

        # Print data
        print(f"{datetime.datetime.now()} | {sensor_1_data}")

        time.sleep(1)

except KeyboardInterrupt:
    print("Cleanup")
    GPIO.cleanup()
