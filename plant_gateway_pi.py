#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
SMART PLANT HEALTH MONITOR - RASPBERRY PI GATEWAY
═══════════════════════════════════════════════════════════════════════════════
SEIS 744 - IoT with Machine Learning Capstone Project

This script runs on the Raspberry Pi and:
1. Receives sensor data from Arduino via MQTT
2. Captures plant photos on demand or when issues detected
3. Uploads data to ThingSpeak cloud
4. Provides a web interface for monitoring

SETUP:
    sudo apt install -y mosquitto mosquitto-clients python3-pip fswebcam
    pip3 install paho-mqtt requests flask --break-system-packages
    
RUN:
    python3 plant_gateway_pi.py
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
import subprocess
import os
import sys
from datetime import datetime
from threading import Thread

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ paho-mqtt not installed. Run:")
    print("   pip3 install paho-mqtt --break-system-packages")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run:")
    print("   pip3 install requests --break-system-packages")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify, render_template_string, send_from_directory
except ImportError:
    print("❌ flask not installed. Run:")
    print("   pip3 install flask --break-system-packages")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - UPDATE THESE VALUES FOR YOUR SETUP
# ═══════════════════════════════════════════════════════════════════════════════

# ThingSpeak Configuration
THINGSPEAK_WRITE_KEY = "B9EE35QMFCVIWMBI"  # Your ThingSpeak Write API Key
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# MQTT Configuration (Mosquitto broker on this Pi)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_SENSOR = "plant/sensor"
MQTT_TOPIC_COMMAND = "plant/command"

# Camera Configuration
PHOTO_DIR = os.path.expanduser("~/plant-monitor/photos")
CAMERA_DEVICE = "/dev/video0"

# Web Server
WEB_PORT = 5000

# Timing
THINGSPEAK_INTERVAL = 15  # Seconds between uploads (ThingSpeak free tier limit)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════════════════════════

sensor_history = []
last_upload_time = 0
latest_data = {
    "temp": "--",
    "humidity": "--",
    "moisture": "--",
    "light": "--",
    "status": "Waiting for data...",
    "timestamp": "Never"
}
app = Flask(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CAMERA FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def setup_camera():
    """Ensure photo directory exists and camera is accessible"""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    print(f"📁 Photo directory: {PHOTO_DIR}")
    
    if os.path.exists(CAMERA_DEVICE):
        print(f"📸 Camera detected at {CAMERA_DEVICE}")
        return True
    else:
        print(f"⚠️  Camera not found at {CAMERA_DEVICE}")
        print("   Make sure USB webcam is connected")
        return False


def capture_photo(reason="manual"):
    """Capture a photo of the plant"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"plant_{reason}_{timestamp}.jpg"
    filepath = os.path.join(PHOTO_DIR, filename)
    
    try:
        result = subprocess.run(
            ['fswebcam', '-r', '1280x720', '--no-banner', '-D', '1', filepath],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            print(f"📸 Photo captured: {filename} ({file_size:,} bytes)")
            return {"success": True, "filename": filename, "path": filepath, "size": file_size}
        else:
            error_msg = result.stderr if result.stderr else "Unknown error"
            print(f"❌ Photo capture failed: {error_msg}")
            return {"success": False, "error": error_msg}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Camera timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "fswebcam not installed. Run: sudo apt install fswebcam"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# THINGSPEAK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def upload_to_thingspeak(data):
    """Upload sensor data to ThingSpeak cloud"""
    global last_upload_time
    
    current_time = time.time()
    time_since_last = current_time - last_upload_time
    
    if time_since_last < THINGSPEAK_INTERVAL:
        remaining = int(THINGSPEAK_INTERVAL - time_since_last)
        print(f"⏳ ThingSpeak rate limit: {remaining}s until next upload")
        return False
    
    payload = {
        'api_key': THINGSPEAK_WRITE_KEY,
        'field1': data.get('temp', 0),
        'field2': data.get('humidity', 0),
        'field3': data.get('moisture', 0),
        'field4': data.get('light', 0),
        'field5': 1 if data.get('status') == 'HEALTHY' else 0
    }
    
    try:
        response = requests.post(THINGSPEAK_URL, data=payload, timeout=10)
        if response.status_code == 200 and response.text != '0':
            last_upload_time = current_time
            print(f"☁️  ThingSpeak: Upload success (entry #{response.text})")
            return True
        else:
            print(f"❌ ThingSpeak: Upload failed (response: {response.text})")
            return False
    except Exception as e:
        print(f"❌ ThingSpeak error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MQTT MESSAGE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def on_mqtt_connect(client, userdata, flags, rc):
    """Called when connected to MQTT broker"""
    if rc == 0:
        print("✅ MQTT: Connected to broker")
        client.subscribe(MQTT_TOPIC_SENSOR)
        print(f"📡 MQTT: Subscribed to '{MQTT_TOPIC_SENSOR}'")
    else:
        print(f"❌ MQTT: Connection failed with code {rc}")


def on_mqtt_disconnect(client, userdata, rc):
    """Called when disconnected from MQTT broker"""
    if rc != 0:
        print("⚠️  MQTT: Unexpected disconnection, will try to reconnect...")


def on_mqtt_message(client, userdata, msg):
    """Called when MQTT message received from Arduino"""
    global latest_data
    
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        sensor_history.append(data.copy())
        if len(sensor_history) > 1000:
            sensor_history.pop(0)
        
        latest_data = data
        
        print()
        print("═" * 60)
        print(f"🌱 SENSOR DATA RECEIVED - {data['timestamp']}")
        print("═" * 60)
        print(f"   🌡️  Temperature: {data.get('temp', 'N/A')}°C ({data.get('temp_source', 'unknown')})")
        print(f"   💨 Humidity:    {data.get('humidity', 'N/A')}%")
        print(f"   💧 Moisture:    {data.get('moisture', 'N/A')}% (raw: {data.get('moisture_raw', 'N/A')})")
        print(f"   ☀️  Light:       {data.get('light', 'N/A')}%")
        print(f"   📊 Status:      {data.get('status', 'UNKNOWN')}")
        
        upload_to_thingspeak(data)
        
        status = data.get('status', '')
        if status in ['NEEDS_WATER', 'OVERWATERED', 'TOO_HOT', 'TOO_COLD']:
            print(f"📸 Auto-capturing photo due to: {status}")
            capture_photo(reason=status.lower())
        
        print("═" * 60)
        
    except json.JSONDecodeError:
        print(f"⚠️  MQTT: Invalid JSON received: {msg.payload}")
    except Exception as e:
        print(f"❌ MQTT: Error processing message: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# WEB INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🌱 Plant Health Monitor</title>
    <meta http-equiv="refresh" content="10">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            min-height: 100vh;
        }
        h1 { color: #2e7d32; text-align: center; margin-bottom: 30px; }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .card h2 { margin-top: 0; color: #388e3c; border-bottom: 2px solid #c8e6c9; padding-bottom: 10px; }
        .reading {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .reading:last-child { border-bottom: none; }
        .label { color: #666; font-size: 1.1em; }
        .value { font-weight: bold; font-size: 1.4em; }
        .healthy { color: #2e7d32; }
        .warning { color: #ff9800; }
        .danger { color: #d32f2f; }
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1em;
        }
        .status-healthy { background: #c8e6c9; color: #2e7d32; }
        .status-warning { background: #fff3e0; color: #f57c00; }
        .status-danger { background: #ffcdd2; color: #c62828; }
        .actions { 
            text-align: center; 
            margin: 25px 0;
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: bold;
            text-decoration: none;
            display: inline-block;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .btn-photo { background: #1976d2; color: white; }
        .btn-history { background: #7b1fa2; color: white; }
        .btn-photos { background: #00897b; color: white; }
        .timestamp { color: #999; font-size: 0.9em; text-align: center; margin-top: 20px; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }
        .footer a { color: #1976d2; }
    </style>
</head>
<body>
    <h1>🌱 Smart Plant Health Monitor</h1>
    
    <div class="card">
        <h2>📊 Current Readings</h2>
        <div class="reading">
            <span class="label">🌡️ Temperature</span>
            <span class="value">{{ data.temp }}°C</span>
        </div>
        <div class="reading">
            <span class="label">💨 Humidity</span>
            <span class="value">{{ data.humidity }}%</span>
        </div>
        <div class="reading">
            <span class="label">💧 Soil Moisture</span>
            <span class="value {% if data.moisture != '--' %}{% if data.moisture|int < 30 %}danger{% elif data.moisture|int > 80 %}warning{% else %}healthy{% endif %}{% endif %}">
                {{ data.moisture }}%
            </span>
        </div>
        <div class="reading">
            <span class="label">☀️ Light Level</span>
            <span class="value">{{ data.light }}%</span>
        </div>
        <div class="reading">
            <span class="label">📋 Plant Status</span>
            <span class="status-badge {% if data.status == 'HEALTHY' %}status-healthy{% elif data.status == 'NEEDS_WATER' %}status-danger{% else %}status-warning{% endif %}">
                {{ data.status }}
            </span>
        </div>
    </div>
    
    <div class="actions">
        <a href="/capture" class="btn btn-photo">📸 Take Photo</a>
        <a href="/history" class="btn btn-history">📜 Data History</a>
        <a href="/photos" class="btn btn-photos">🖼️ View Photos</a>
    </div>
    
    <p class="timestamp">Last updated: {{ data.timestamp }}</p>
    
    <div class="footer">
        <p>SEIS 744 - IoT with Machine Learning</p>
        <p><a href="https://thingspeak.com/channels" target="_blank">View ThingSpeak Dashboard →</a></p>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, data=latest_data)

@app.route('/capture')
def web_capture():
    result = capture_photo(reason="web")
    return jsonify(result)

@app.route('/history')
def web_history():
    return jsonify({"count": len(sensor_history), "readings": sensor_history[-100:]})

@app.route('/photos')
def list_photos():
    try:
        photos = sorted(os.listdir(PHOTO_DIR), reverse=True)
        photos = [p for p in photos if p.endswith('.jpg')][:50]
        return jsonify({"count": len(photos), "directory": PHOTO_DIR, "photos": photos})
    except Exception as e:
        return jsonify({"error": str(e), "photos": []})

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)

@app.route('/api/data', methods=['POST'])
def api_receive_data():
    global latest_data
    try:
        data = request.json
        data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sensor_history.append(data.copy())
        if len(sensor_history) > 1000:
            sensor_history.pop(0)
        latest_data = data
        print(f"📡 HTTP API: Received data - Moisture: {data.get('moisture')}%")
        upload_to_thingspeak(data)
        return jsonify({"status": "ok", "message": "Data received"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/latest')
def api_latest():
    return jsonify(latest_data)


# ═══════════════════════════════════════════════════════════════════════════════
# MQTT CLIENT THREAD
# ═══════════════════════════════════════════════════════════════════════════════

def start_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_mqtt_connect
    client.on_disconnect = on_mqtt_disconnect
    client.on_message = on_mqtt_message
    
    while True:
        try:
            print(f"📡 MQTT: Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except ConnectionRefusedError:
            print("❌ MQTT: Connection refused - is Mosquitto running?")
            print("   Run: sudo systemctl start mosquitto")
            time.sleep(5)
        except Exception as e:
            print(f"❌ MQTT: Error - {e}")
            time.sleep(5)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def get_ip_address():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"


def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║   🌱 SMART PLANT HEALTH MONITOR - RASPBERRY PI GATEWAY        ║")
    print("║   SEIS 744 - IoT with Machine Learning Capstone               ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    print("🔧 INITIALIZING SYSTEM...")
    print("─" * 65)
    
    camera_ok = setup_camera()
    print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📡 MQTT Topic:  {MQTT_TOPIC_SENSOR}")
    print(f"☁️  ThingSpeak:  ...{THINGSPEAK_WRITE_KEY[-6:]}")
    print("─" * 65)
    print()
    
    mqtt_thread = Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    time.sleep(2)
    
    pi_ip = get_ip_address()
    
    print()
    print("═" * 65)
    print("✅ GATEWAY READY!")
    print("═" * 65)
    print()
    print(f"🌐 Web Interface: http://{pi_ip}:{WEB_PORT}")
    print(f"📸 Photo Capture: http://{pi_ip}:{WEB_PORT}/capture")
    print(f"📊 Data History:  http://{pi_ip}:{WEB_PORT}/history")
    print()
    print("📡 Waiting for sensor data from Arduino...")
    print("   Press Ctrl+C to stop")
    print()
    print("═" * 65)
    print()
    
    try:
        app.run(host='0.0.0.0', port=WEB_PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Gateway stopped by user")
        print("✅ Goodbye!")


if __name__ == '__main__':
    main()
