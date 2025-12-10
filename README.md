# 🌱 Smart Plant Health Monitor

## SEIS 744 - IoT with Machine Learning
### University of Saint Thomas - Capstone Project

Edge-to-cloud IoT system monitoring plant health with sensors, edge intelligence, and cloud analytics.

## Architecture
```
┌─────────────────┐   USB    ┌─────────────────┐   HTTP   ┌──────────────┐
│ Arduino Nano    │─────────►│ Raspberry Pi    │─────────►│ ThingSpeak   │
│ 33 BLE (CDA)    │  Serial  │ (GDA)           │────────►│ Ubidots      │
└─────────────────┘          └─────────────────┘          └──────────────┘
```

## Features

- ✅ Real-time soil moisture, temperature, humidity monitoring
- ✅ Edge intelligence - local decisions without cloud dependency
- ✅ Buzzer alerts when plant needs water
- ✅ Automatic camera capture every 30 minutes
- ✅ Web dashboard on Raspberry Pi
- ✅ Dual cloud upload: ThingSpeak + Ubidots
- ✅ CSV data logging for analysis
- ✅ Edge Impulse ready for ML model deployment

## Hardware

| Component | Purpose |
|-----------|---------|
| Arduino Nano 33 BLE Sense | Edge device (CDA) |
| TinyML Shield | Grove sensor connections |
| Grove Moisture Sensor | Soil moisture (A6) |
| Grove Buzzer | Audio alerts (D12) |
| Raspberry Pi 4 | Gateway device (GDA) |
| USB Webcam | Plant photos |

## Software

- **Arduino:** C++ with Arduino_HTS221 library
- **Raspberry Pi:** Python 3, Flask, pyserial, requests
- **Cloud:** ThingSpeak, Ubidots
- **ML Platform:** Edge Impulse

## Quick Start

### Arduino
```bash
cd arduino/plant_sensor
arduino-cli lib install "Arduino_HTS221"
arduino-cli compile --fqbn arduino:mbed_nano:nano33ble plant_sensor.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:mbed_nano:nano33ble plant_sensor.ino
```

### Raspberry Pi
```bash
cd raspberry-pi
pip3 install flask pyserial requests --break-system-packages
python3 gateway_direct.py
```

### Web UI
Open browser: `http://[PI_IP]:5000`

## Lab Module Mapping

| Lab | Concept | Implementation |
|-----|---------|----------------|
| Lab 02 | System Performance | 5-second sensor intervals |
| Lab 03 | Data Simulation | Default values fallback |
| Lab 05 | JSON Serialization | All data exchange |
| Lab 06 | MQTT Protocol | Architecture supports MQTT |
| Lab 07 | Cloud Integration | ThingSpeak + Ubidots HTTP |
| Lab 08 | CoAP Patterns | RESTful web endpoints |
| Lab 09-10 | TinyML/Edge AI | Local decisions, Edge Impulse ready |

## Cloud Dashboards

- **ThingSpeak:** https://thingspeak.com/channels
- **Ubidots:** https://stem.ubidots.com/app/devices/

## Edge Impulse ML

Project configured for plant health image classification:
- Training labels: `healthy`, `needs_water`, `dry`
- Model: Transfer learning on plant images
- Deployment: TensorFlow Lite for Arduino

## Project Structure
```
smart-plant-monitor/
├── README.md
├── arduino/
│   └── plant_sensor/
│       └── plant_sensor.ino
├── raspberry-pi/
│   └── gateway_direct.py
└── docs/
    └── ARCHITECTURE.md
```

## Author

SEIS 744 - IoT with Machine Learning  
University of Saint Thomas  
December 2025
