#!/usr/bin/env python3
"""
Plant Monitor Gateway - Complete IoT System
SEIS 744 Capstone Project
"""

import serial
import json
import time
import requests
from datetime import datetime

# THINGSPEAK CONFIGURATION - YOUR ACTUAL KEY
THINGSPEAK_WRITE_KEY = "B9EE35QMFCVIWMBI"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
THINGSPEAK_CHANNEL = "https://thingspeak.com/channels/YOUR_CHANNEL_ID"

# Global storage
latest_data = {}
data_history = []
last_upload = 0

def read_arduino():
    """Read from Arduino Nano via USB"""
    print("🔍 Looking for Arduino...")
    
    # Try different ports
    ports = ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyACM1']
    
    for port in ports:
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            print(f"✅ Arduino found on {port}")
            print("📡 Receiving data from edge device...\n")
            
            while True:
                line = ser.readline().decode('utf-8').strip()
                
                # Look for JSON data
                if line.startswith('JSON:'):
                    try:
                        data = json.loads(line[5:])
                        process_data(data)
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            continue
    
    print("⚠️  Arduino not found - entering test mode")
    test_mode()

def process_data(data):
    """Process Arduino data and send to cloud"""
    global latest_data, last_upload
    latest_data = data
    data_history.append(data)
    
    # Display
    print(f"\n{'='*60}")
    print(f"🌱 PLANT MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"📊 Edge Device Data:")
    print(f"   Temperature:  {data.get('temp', 0):.1f}°C")
    print(f"   Humidity:     {data.get('humidity', 0):.1f}%")
    print(f"   Moisture:     {data.get('moisture', 0)}%")
    print(f"   Status:       {data.get('status', 'UNKNOWN')}")
    
    # Check alerts
    moisture = data.get('moisture', 0)
    if moisture < 30:
        print("\n⚠️  ALERT: Plant needs water!")
        print("   Action: Capturing photo...")
        capture_photo()
    elif moisture > 80:
        print("\n⚠️  WARNING: Soil too wet!")
    else:
        print("\n✅ Plant status: Healthy")
    
    # Rate limit ThingSpeak (15 seconds)
    current_time = time.time()
    if current_time - last_upload >= 15:
        send_to_cloud(data)
        last_upload = current_time
    else:
        wait_time = 15 - (current_time - last_upload)
        print(f"⏳ ThingSpeak rate limit: wait {wait_time:.0f}s")
    
    print('='*60)

def capture_photo():
    """Take photo with Pi camera"""
    try:
        import subprocess
        filename = f"plant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        subprocess.run(['fswebcam', '-r', '640x480', '--no-banner', filename], 
                      capture_output=True, check=True, timeout=5)
        print(f"   📸 Photo saved: {filename}")
    except:
        print("   📸 Camera not available (normal if not connected)")

def send_to_cloud(data):
    """Send to ThingSpeak"""
    
    # Map status to numeric value for ThingSpeak
    status_map = {
        'DRY': 1,
        'HEALTHY': 2,
        'WET': 3,
        'UNKNOWN': 0
    }
    
    # Prepare payload
    payload = {
        'api_key': THINGSPEAK_WRITE_KEY,
        'field1': round(data.get('temp', 0), 1),
        'field2': round(data.get('humidity', 0), 1),
        'field3': data.get('moisture', 0),
        'field4': status_map.get(data.get('status', 'UNKNOWN'), 0)
    }
    
    try:
        print("\n☁️  Uploading to ThingSpeak...")
        response = requests.post(THINGSPEAK_URL, data=payload, timeout=10)
        
        if response.status_code == 200:
            entry = response.text.strip()
            if entry and entry != '0':
                print(f"   ✅ Success! Entry #{entry}")
                print(f"   📊 View at: https://thingspeak.com/channels/YOUR_CHANNEL")
            else:
                print("   ⏳ Rate limited (this is normal)")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("   ⚠️  Upload timeout - will retry")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")

def test_mode():
    """Run without Arduino for testing"""
    print("\n🧪 TEST MODE - Simulating sensor data")
    print("   (Connect Arduino to use real data)\n")
    
    while True:
        # Simulate realistic data
        import random
        
        moisture = random.randint(20, 60)
        status = 'DRY' if moisture < 30 else 'WET' if moisture > 80 else 'HEALTHY'
        
        fake_data = {
            'device': 'CDA',
            'temp': 22.0 + random.uniform(-2, 2),
            'humidity': 45.0 + random.uniform(-5, 5),
            'moisture': moisture,
            'status': status,
            'timestamp': int(time.time())
        }
        
        process_data(fake_data)
        time.sleep(15)  # Respect ThingSpeak rate limit

def check_requirements():
    """Check and install requirements"""
    required = ['serial', 'requests']
    
    for module in required:
        try:
            __import__(module)
        except ImportError:
            print(f"Installing {module}...")
            import subprocess
            subprocess.run(['pip3', 'install', f'py{module}', '--break-system-packages'], 
                         capture_output=True)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("   🌱 PLANT MONITOR GATEWAY (GDA)")
    print("   SEIS 744 - Internet of Things with ML")
    print("   UST Graduate Programs in Software")
    print("="*60)
    
    # Check requirements
    check_requirements()
    
    print("\n📋 Configuration:")
    print(f"   ThingSpeak API: {THINGSPEAK_WRITE_KEY[:4]}...{THINGSPEAK_WRITE_KEY[-4:]}")
    print("   Update Rate: Every 15 seconds (free tier)")
    print("   Mode: Edge → Gateway → Cloud")
    
    print("\n🚀 Starting gateway services...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        read_arduino()
    except KeyboardInterrupt:
        print("\n\n👋 Gateway stopped")
        print(f"   Processed {len(data_history)} readings")
