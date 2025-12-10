#!/usr/bin/env python3
"""
Plant Monitor MQTT Gateway - Runs on Pi
Subscribes to MQTT and forwards to ThingSpeak
"""

import paho.mqtt.client as mqtt
import json
import requests
import time
from datetime import datetime

# MQTT Configuration
MQTT_BROKER = "localhost"  # Pi itself is the broker
MQTT_PORT = 1883
MQTT_TOPIC = "plant/sensors"

# ThingSpeak
THINGSPEAK_KEY = "B9EE35QMFCVIWMBI"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

last_upload = 0

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to MQTT broker (code: {rc})")
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Subscribed to {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    """Process incoming MQTT messages"""
    global last_upload
    
    try:
        # Parse JSON from MQTT
        data = json.loads(msg.payload.decode())
        
        # Display
        print(f"\n{'='*60}")
        print(f"🌱 MQTT MESSAGE RECEIVED - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"📊 Sensor Data:")
        print(f"   Moisture: {data.get('moisture', 0)}%")
        print(f"   Temperature: {data.get('temp', 22.5)}°C")
        print(f"   Status: {data.get('status', 'UNKNOWN')}")
        
        # Alert
        if data.get('moisture', 0) < 30:
            print("⚠️  ALERT: Plant needs water!")
        
        # Upload to ThingSpeak (rate limited)
        current = time.time()
        if current - last_upload >= 15:
            send_to_cloud(data)
            last_upload = current
        else:
            remaining = 15 - (current - last_upload)
            print(f"⏳ ThingSpeak rate limit: {remaining:.0f}s")
            
        print('='*60)
        
    except Exception as e:
        print(f"Error: {e}")

def send_to_cloud(data):
    """Upload to ThingSpeak"""
    payload = {
        'api_key': THINGSPEAK_KEY,
        'field1': data.get('temp', 22.5),
        'field2': data.get('humidity', 45),
        'field3': data.get('moisture', 0),
        'field4': 1 if data.get('status') == 'DRY' else 0
    }
    
    try:
        response = requests.post(THINGSPEAK_URL, data=payload, timeout=10)
        if response.text and response.text != '0':
            print(f"☁️  ThingSpeak: Entry #{response.text}")
    except Exception as e:
        print(f"☁️  Upload error: {e}")

# Setup MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("\n" + "="*60)
print("   🌱 PLANT MONITOR - MQTT GATEWAY")
print("   Wireless via MQTT Protocol")
print("="*60)

print(f"\n📡 Connecting to MQTT broker at {MQTT_BROKER}...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

print("⏳ Waiting for sensor data via MQTT...\n")

# Start loop
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n👋 Stopped")
    client.disconnect()
