#!/usr/bin/env python3
"""
Plant Monitor BLE Gateway
Receives data wirelessly from Arduino Nano 33 BLE
"""

import asyncio
import json
import requests
import struct
from datetime import datetime
from bleak import BleakScanner, BleakClient

# ThingSpeak
THINGSPEAK_KEY = "B9EE35QMFCVIWMBI"
THINGSPEAK_URL = "https://api.thingspeak.com/update"

# BLE UUIDs (must match Arduino)
PLANT_SERVICE_UUID = "12345678-1234-1234-1234-123456789012"
MOISTURE_UUID = "00000001-1234-1234-1234-123456789012"
TEMP_UUID = "00000002-1234-1234-1234-123456789012"
HUMIDITY_UUID = "00000003-1234-1234-1234-123456789012"
STATUS_UUID = "00000004-1234-1234-1234-123456789012"

last_upload = 0

async def find_plant_monitor():
    """Scan for PlantMonitorBLE device"""
    print("🔍 Scanning for PlantMonitorBLE...")
    
    devices = await BleakScanner.discover()
    for device in devices:
        if device.name and "Plant" in device.name:
            print(f"✅ Found: {device.name} at {device.address}")
            return device.address
    
    print("❌ PlantMonitorBLE not found")
    return None

async def connect_and_read(address):
    """Connect to Arduino and read data"""
    print(f"\n📡 Connecting to {address}...")
    
    async with BleakClient(address) as client:
        print("✅ Connected via BLE!")
        
        while client.is_connected:
            try:
                # Read all characteristics
                moisture_bytes = await client.read_gatt_char(MOISTURE_UUID)
                temp_bytes = await client.read_gatt_char(TEMP_UUID)
                humidity_bytes = await client.read_gatt_char(HUMIDITY_UUID)
                status_bytes = await client.read_gatt_char(STATUS_UUID)
                
                # Parse data
                moisture = int.from_bytes(moisture_bytes, 'little')
                temp = struct.unpack('<f', temp_bytes)[0]
                humidity = struct.unpack('<f', humidity_bytes)[0]
                status = status_bytes.decode('utf-8').rstrip('\x00')
                
                # Display
                print(f"\n{'='*50}")
                print(f"🌱 BLE DATA RECEIVED - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*50}")
                print(f"📊 Sensor Readings:")
                print(f"   Moisture: {moisture}%")
                print(f"   Temperature: {temp:.1f}°C")
                print(f"   Humidity: {humidity:.1f}%")
                print(f"   Status: {status}")
                
                # Check alerts
                if moisture < 30:
                    print("⚠️  ALERT: Plant needs water!")
                
                # Send to ThingSpeak
                send_to_cloud(moisture, temp, humidity, status)
                
                print('='*50)
                
                # Wait 15 seconds (ThingSpeak rate limit)
                await asyncio.sleep(15)
                
            except Exception as e:
                print(f"Error reading: {e}")
                await asyncio.sleep(5)

def send_to_cloud(moisture, temp, humidity, status):
    """Upload to ThingSpeak"""
    global last_upload
    import time
    
    # Rate limit check
    current = time.time()
    if current - last_upload < 15:
        print("⏳ ThingSpeak rate limit - waiting...")
        return
    
    payload = {
        'api_key': THINGSPEAK_KEY,
        'field1': round(temp, 1),
        'field2': round(humidity, 1),
        'field3': moisture,
        'field4': 1 if status == "DRY" else 0
    }
    
    try:
        r = requests.post(THINGSPEAK_URL, data=payload, timeout=10)
        if r.text and r.text != '0':
            print(f"☁️  ThingSpeak: Entry #{r.text}")
            last_upload = current
    except Exception as e:
        print(f"☁️  Upload error: {e}")

async def main():
    print("\n" + "="*60)
    print("   🌱 PLANT MONITOR BLE GATEWAY")
    print("   Wireless Edge → Gateway → Cloud")
    print("="*60 + "\n")
    
    while True:
        # Find device
        address = await find_plant_monitor()
        
        if address:
            try:
                await connect_and_read(address)
            except Exception as e:
                print(f"Connection lost: {e}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)
        else:
            print("Make sure Arduino is powered and running BLE code")
            print("Retrying in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Gateway stopped")
