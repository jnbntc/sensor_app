import Adafruit_DHT
import time
import sqlite3
from datetime import datetime
import logging
from flask import Flask, jsonify, send_from_directory, request
import RPi.GPIO as GPIO
import json

# Sensor Configuration
SENSOR = Adafruit_DHT.DHT22
PIN = 17

# Relay Configuration
RELAY1_PIN = 18
RELAY2_PIN = 19

# Database Configuration
DB_NAME = 'sensor_data.db'

# Config File
CONFIG_FILE = 'config.json'

# Logging Configuration
logging.basicConfig(filename='sensor_app.log', level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(message)s')

app = Flask(__name__, static_folder='static')

def init_gpio():
    """Initialize GPIO settings for relays"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY1_PIN, GPIO.OUT)
    GPIO.setup(RELAY2_PIN, GPIO.OUT)

    # Initially turned off (assuming active-low logic)
    GPIO.output(RELAY1_PIN, GPIO.HIGH)
    GPIO.output(RELAY2_PIN, GPIO.HIGH)
    logging.debug("GPIO relays initialized")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS readings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  temperature REAL,
                  humidity REAL,
                  timestamp TEXT)''')

    # New table for relay logs
    c.execute('''CREATE TABLE IF NOT EXISTS relay_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  relay_number INTEGER,
                  state TEXT,
                  timestamp TEXT)''')

    conn.commit()
    conn.close()
    logging.debug("Database initialized with relay logs table")

def load_config():
    """Load relay activation thresholds from the JSON configuration file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            logging.debug(f"Configuration loaded: {config}")
            return config
    except FileNotFoundError:
        logging.error("Configuration file not found. Creating default configuration.")
        default_config = {
            "temperature_threshold": 30.0,
            "temperature_hysteresis": 5.0,
            "humidity_threshold": 70.0,
            "humidity_hysteresis": 5.0
        }
        save_config(default_config)
        return default_config
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding configuration file: {e}")
        return None

def save_config(config):
    """Save default configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            logging.debug("Default configuration saved.")
    except Exception as e:
        logging.error(f"Error saving configuration file: {e}")

def read_sensor():
    humidity, temperature = Adafruit_DHT.read_retry(SENSOR, PIN)
    if humidity is not None and temperature is not None:
        logging.debug(f"Sensor read: Temperature={temperature:.1f}°C, Humidity={humidity:.1f}%")
        return temperature, humidity
    else:
        logging.error("Failed to retrieve data from DHT22 sensor")
        return None, None

def save_reading(temperature, humidity):
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO readings (temperature, humidity, timestamp) VALUES (?, ?, ?)",
                  (temperature, humidity, timestamp))
        conn.commit()
        logging.debug(f"Saved reading: Temperature={temperature:.1f}°C, Humidity={humidity:.1f}%, Timestamp={timestamp}")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def toggle_relay(relay_pin, state):
    """Toggle a specific relay on or off"""
    try:
        # Active-low logic: LOW to turn on, HIGH to turn off
        GPIO.output(relay_pin, GPIO.LOW if state else GPIO.HIGH)
        relay_number = 1 if relay_pin == RELAY1_PIN else 2
        log_relay_state(relay_number, 'ON' if state else 'OFF')
        return True
    except Exception as e:
        logging.error(f"Error toggling relay {relay_pin}: {e}")
        return False

def log_relay_state(relay_number, state):
    """Log relay state changes to database"""
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO relay_logs (relay_number, state, timestamp) VALUES (?, ?, ?)",
                  (relay_number, state, timestamp))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error logging relay state: {e}")
    finally:
        conn.close()

def activate_relays_based_on_conditions(temperature, humidity, config):
    """Check conditions and activate relays accordingly"""
    temp_threshold = config['temperature_threshold']
    temp_hysteresis = config['temperature_hysteresis']
    humid_threshold = config['humidity_threshold']
    humid_hysteresis = config['humidity_hysteresis']

    # Temperature Relay Logic
    if temperature > temp_threshold:
        toggle_relay(RELAY1_PIN, True)
    elif temperature < (temp_threshold - temp_hysteresis):
        toggle_relay(RELAY1_PIN, False)

    # Humidity Relay Logic
    if humidity > humid_threshold:
        toggle_relay(RELAY2_PIN, True)
    elif humidity < (humid_threshold - humid_hysteresis):
        toggle_relay(RELAY2_PIN, False)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/current')
def get_current_reading():
    temperature, humidity = read_sensor()
    if temperature is not None and humidity is not None:
        return jsonify({
            'temperature': temperature,
            'humidity': humidity,
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({'error': 'Failed to read sensor data'}), 500

@app.route('/api/history')
def get_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1000")
    readings = c.fetchall()
    conn.close()
    logging.debug(f"Fetched {len(readings)} readings from database")
    return jsonify([{
        'id': r[0],
        'temperature': r[1],
        'humidity': r[2],
        'timestamp': r[3]
    } for r in readings])

@app.route('/api/relay/control', methods=['POST'])
def control_relay():
    """API endpoint to control relays"""
    data = request.get_json()
    relay_number = data.get('relay', None)
    state = data.get('state', None)

    if relay_number is None or state is None:
        return jsonify({'error': 'Invalid parameters'}), 400

    relay_pin = RELAY1_PIN if relay_number == 1 else RELAY2_PIN

    if toggle_relay(relay_pin, state):
        return jsonify({
            'relay': relay_number,
            'state': 'ON' if state else 'OFF',
            'success': True
        })
    else:
        return jsonify({'error': 'Failed to toggle relay'}), 500

@app.route('/api/relay/status')
def get_relay_status():
    """Get current status of both relays"""
    return jsonify({
        'relay1': 'ON' if GPIO.input(RELAY1_PIN) == GPIO.LOW else 'OFF',
        'relay2': 'ON' if GPIO.input(RELAY2_PIN) == GPIO.LOW else 'OFF'
    })

@app.route('/api/relay/logs')
def get_relay_logs():
    """Retrieve relay state change logs"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM relay_logs ORDER BY timestamp DESC LIMIT 100")
    logs = c.fetchall()
    conn.close()

    return jsonify([{
        'id': log[0],
        'relay_number': log[1],
        'state': log[2],
        'timestamp': log[3]
    } for log in logs])

def main_loop():
    logging.debug("Starting main loop")
    config = load_config()
    while True:
        temperature, humidity = read_sensor()
        if temperature is not None and humidity is not None:
            save_reading(temperature, humidity)
            activate_relays_based_on_conditions(temperature, humidity, config)
            logging.info(f"Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
        time.sleep(60)

if __name__ == '__main__':
    try:
        init_db()
        init_gpio()
        from threading import Thread
        sensor_thread = Thread(target=main_loop)
        sensor_thread.start()
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f"Application startup error: {e}")
    finally:
        GPIO.cleanup()
else:
    init_db()
    init_gpio()
    from threading import Thread
    sensor_thread = Thread(target=main_loop)
    sensor_thread.start()
