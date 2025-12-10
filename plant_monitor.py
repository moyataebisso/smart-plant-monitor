#!/usr/bin/env python3

from flask import Flask, request, jsonify
from datetime import datetime
import json
import subprocess
import os

app = Flask(__name__)
sensor_history = []

@app.route('/')
def home():
    latest = sensor_history[-1] if sensor_history else {}
    return f'''
    <html>
    <head>
        <title>Plant Monitor Pi</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            .reading {{ background: #f0f0f0; padding: 10px; margin: 5px; }}
        </style>
    </head>
    <body>
        <h1>🌱 Plant Monitor - Raspberry Pi</h1>
        <div class="reading">
            <h3>Current Readings:</h3>
            <p>🌡️ Temperature: {latest.get('temperature', '--')}°C</p>
            <p>💧 Humidity: {latest.get('humidity', '--')}%</p>
            <p>🌱 Moisture: {latest.get('moisture', '--')}%</p>
            <p>⏰ Last Update: {latest.get('timestamp', 'Never')}</p>
        </div>
        <p>
            <a href="/capture">📸 Take Photo</a> | 
            <a href="/history">📊 View History</a>
        </p>
    </body>
    </html>
    '''

@app.route('/sensor_data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        sensor_history.append(data)
        if len(sensor_history) > 100:
            sensor_history.pop(0)
        
        print(f"\n{'='*50}")
        print(f"📡 SENSOR DATA RECEIVED")
        print(f"🌡️  Temp: {data.get('temperature')}°C")
        print(f"💧 Humidity: {data.get('humidity')}%")
        print(f"🌱 Moisture: {data.get('moisture')}%")
        
        # Alert if dry
        if data.get('moisture', 100) < 30:
            print("⚠️  ALERT: Plant needs water!")
            capture_photo()
        
        print('='*50)
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/capture')
def capture_photo():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"plant_{timestamp}.jpg"
    
    try:
        result = subprocess.run(
            ['fswebcam', '-r', '640x480', '--no-banner', filename],
            capture_output=True, text=True, check=True
        )
        print(f"📸 Photo captured: {filename}")
        return jsonify({"photo": filename, "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/history')
def history():
    return jsonify(sensor_history[-20:])

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌱 PLANT MONITOR CDA - RASPBERRY PI")
    print("="*60)
    print("📡 Server running on port 5000")
    print("📸 Camera ready")
    print("🌐 Access at: http://[YOUR-PI-IP]:5000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=4999, debug=True)
