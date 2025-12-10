#!/usr/bin/env python3
"""
Final MQTT Gateway - Shows ALL sensor data
"""

import paho.mqtt.client as mqtt
import json
import requests
import time
from datetime import datetime

THINGSPEAK_KEY = "B9EE35QMFCVIWMBI"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
MQTT_TOPIC = "plant/sensors"

last_upload = 0

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global last_upload
    
    try:
        data = json.loads(msg.payload.decode())
        
        print(f"\n{'='*60}")
        print(f"🌱 SENSOR DATA - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"📊 Readings:")
        print(f"   Moisture: {data.get('moisture', 0)}% (raw: {data.get('moisture_raw', 0)})")
        print(f"   Temperature: {data.get('temp', 0)}°C")
        print(f"   Humidity: {data.get('humidity', 0)}%")
        print(f"   Light: {data.get('light', 0)}%")
        print(f"   Status: {data.get('status', 'UNKNOWN')}")
        print(f"   DHT Working: {data.get('dht_ok', False)}")
        
        # Send ALL fields to ThingSpeak
        current = time.time()
        if current - last_upload >= 15:
            payload = {
                'api_key': THINGSPEAK_KEY,
                'field1': data.get('temp', 0),
                'field2': data.get('humidity', 0),
                'field3': data.get('moisture', 0),
                'field4': data.get('light', 0)
            }
            
            try:
                r = requests.post(THINGSPEAK_URL, data=payload)
                if r.text != '0':
                    print(f"☁️ ThingSpeak: Entry #{r.text}")
                    last_upload = current
            except:
                pass
        else:
            print(f"⏳ Rate limit: {15-(current-last_upload):.0f}s")
            
        print('='*60)
        
    except Exception as e:
        print(f"Error: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("\n🌱 PLANT MONITOR - FINAL VERSION")
print("Showing ALL sensor data\n")

client.connect("localhost", 1883, 60)
client.loop_forever()
