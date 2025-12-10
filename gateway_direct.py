#!/usr/bin/env python3
import serial, json, time, os, subprocess, requests
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template_string, send_from_directory

SERIAL_PORT = "/dev/ttyACM0"
THINGSPEAK_KEY = "B9EE35QMFCVIWMBI"
UBIDOTS_TOKEN = "BBUS-1ea23e11323d2dfb696bf5e5a550919f793"
UBIDOTS_DEVICE = "plant-monitor"
PHOTO_DIR = os.path.expanduser("~/plant-monitor/photos")
DATA_LOG = os.path.expanduser("~/plant-monitor/data_log.csv")

sensor_history = []
last_thingspeak = 0
last_ubidots = 0
last_scheduled_photo = 0
latest_data = {"temp": "--", "humidity": "--", "moisture": "--", "status": "Waiting...", "timestamp": "Never"}
data_count = 0
app = Flask(__name__)

def init_csv():
    if not os.path.exists(DATA_LOG):
        with open(DATA_LOG, 'w') as f:
            f.write("timestamp,temp,humidity,moisture,status\n")

def log_csv(data):
    with open(DATA_LOG, 'a') as f:
        f.write(f"{data.get('timestamp','')},{data.get('temp','')},{data.get('humidity','')},{data.get('moisture','')},{data.get('status','')}\n")

def capture_photo(reason="manual"):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    filename = f"plant_{reason}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(PHOTO_DIR, filename)
    try:
        subprocess.run(['fswebcam', '-r', '1280x720', '--no-banner', filepath], capture_output=True, timeout=10)
        if os.path.exists(filepath):
            print(f"📸 Photo: {filename}")
            return {"success": True, "filename": filename}
    except Exception as e:
        print(f"❌ Camera: {e}")
    return {"success": False}

def upload_thingspeak(data):
    global last_thingspeak
    if time.time() - last_thingspeak < 15:
        return
    try:
        r = requests.post("https://api.thingspeak.com/update", data={
            'api_key': THINGSPEAK_KEY,
            'field1': data.get('temp', 0),
            'field2': data.get('humidity', 0),
            'field3': data.get('moisture', 0),
            'field5': 1 if data.get('status') == 'HEALTHY' else 0
        }, timeout=10)
        if r.status_code == 200 and r.text != '0':
            last_thingspeak = time.time()
            print(f"☁️  ThingSpeak: #{r.text}")
    except Exception as e:
        print(f"❌ ThingSpeak: {e}")

def upload_ubidots(data):
    global last_ubidots
    if not UBIDOTS_TOKEN or UBIDOTS_TOKEN == "YOUR_UBIDOTS_TOKEN":
        return
    if time.time() - last_ubidots < 10:
        return
    try:
        url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE}/"
        headers = {"X-Auth-Token": UBIDOTS_TOKEN, "Content-Type": "application/json"}
        payload = {
            "temperature": data.get('temp', 0),
            "humidity": data.get('humidity', 0),
            "moisture": data.get('moisture', 0),
            "status": 1 if data.get('status') == 'HEALTHY' else 0
        }
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code in [200, 201]:
            last_ubidots = time.time()
            print(f"📊 Ubidots: OK")
    except Exception as e:
        print(f"❌ Ubidots: {e}")

def read_serial():
    global latest_data, data_count, last_scheduled_photo
    print(f"📡 Connecting to {SERIAL_PORT}...")
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, 115200, timeout=2)
            print("✅ Arduino connected!")
            while True:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith('{'):
                        try:
                            data = json.loads(line)
                            data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            data_count += 1
                            latest_data = data
                            sensor_history.append(data.copy())
                            if len(sensor_history) > 500:
                                sensor_history.pop(0)
                            print(f"\n🌱 #{data_count} | Temp:{data.get('temp')}°C | Moisture:{data.get('moisture')}% | {data.get('status')}")
                            log_csv(data)
                            upload_thingspeak(data)
                            upload_ubidots(data)
                            if data.get('status') == 'NEEDS_WATER':
                                capture_photo('needs_water')
                            if time.time() - last_scheduled_photo > 1800:
                                capture_photo('scheduled')
                                last_scheduled_photo = time.time()
                        except:
                            pass
        except Exception as e:
            print(f"⚠️ Serial error: {e}, retrying...")
            time.sleep(5)

HTML = '''<!DOCTYPE html>
<html><head><title>🌱 Plant Monitor</title><meta http-equiv="refresh" content="10">
<style>body{font-family:Arial;max-width:500px;margin:0 auto;padding:20px;background:#e8f5e9}
h1{color:#2e7d32;text-align:center}.card{background:white;border-radius:15px;padding:20px;margin:15px 0}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee}
.val{font-weight:bold;font-size:1.2em}.ok{color:green}.bad{color:red}
.btn{display:inline-block;padding:10px 20px;margin:5px;background:#1976d2;color:white;border-radius:20px;text-decoration:none}
.center{text-align:center}</style></head>
<body><h1>🌱 Plant Monitor</h1><p class="center">📊 {{count}} readings collected</p>
<div class="card">
<div class="row"><span>🌡️ Temp</span><span class="val">{{d.temp}}°C</span></div>
<div class="row"><span>💨 Humidity</span><span class="val">{{d.humidity}}%</span></div>
<div class="row"><span>💧 Moisture</span><span class="val {{'bad' if d.moisture != '--' and d.moisture|int < 30 else 'ok'}}">{{d.moisture}}%</span></div>
<div class="row"><span>📊 Status</span><span class="val {{'ok' if d.status == 'HEALTHY' else 'bad'}}">{{d.status}}</span></div>
</div>
<div class="center"><a href="/capture" class="btn">📸 Photo</a><a href="/photos" class="btn">🖼️ Gallery</a></div>
<p class="center" style="color:#999">Updated: {{d.timestamp}}</p>
<p class="center"><a href="https://thingspeak.com/channels">ThingSpeak</a> | <a href="https://stem.ubidots.com">Ubidots</a></p>
</body></html>'''

@app.route('/')
def home():
    return render_template_string(HTML, d=latest_data, count=data_count)

@app.route('/capture')
def web_capture():
    return jsonify(capture_photo("web"))

@app.route('/photos')
def list_photos():
    try:
        return jsonify(sorted([f for f in os.listdir(PHOTO_DIR) if f.endswith('.jpg')], reverse=True)[:20])
    except:
        return jsonify([])

@app.route('/photos/<f>')
def serve_photo(f):
    return send_from_directory(PHOTO_DIR, f)

@app.route('/api/latest')
def api_latest():
    return jsonify(latest_data)

if __name__ == '__main__':
    print("\n🌱 PLANT MONITOR GATEWAY - SEIS 744\n")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    init_csv()
    Thread(target=read_serial, daemon=True).start()
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "localhost"
    s.close()
    print(f"🌐 Web UI: http://{ip}:5000")
    print(f"☁️  ThingSpeak: Enabled")
    print(f"📊 Ubidots: {'Enabled' if UBIDOTS_TOKEN != 'YOUR_UBIDOTS_TOKEN' else 'Disabled'}")
    print(f"📸 Auto-photo: Every 30 minutes\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
