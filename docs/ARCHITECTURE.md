# System Architecture

## CDA-GDA-Cloud Pattern

This project implements the Constrained Device Application (CDA) and Gateway Device Application (GDA) architecture from SEIS 744.

### CDA - Arduino Nano 33 BLE Sense
- Reads sensors every 5 seconds
- Makes local decisions (edge intelligence)
- Triggers buzzer alerts immediately
- Sends JSON via USB Serial

### GDA - Raspberry Pi
- Receives serial data from Arduino
- Uploads to ThingSpeak (15-sec intervals)
- Uploads to Ubidots (10-sec intervals)
- Captures photos every 30 minutes
- Serves web dashboard on port 5000
- Logs all data to CSV

### Cloud Services
- **ThingSpeak:** Primary data storage and visualization
- **Ubidots:** Secondary dashboard with different visualizations

### Edge Intelligence
The Arduino makes local decisions without requiring cloud connectivity:
- Moisture < 30% → NEEDS_WATER status + buzzer alert
- Moisture > 80% → OVERWATERED status
- All processing happens on-device in milliseconds

## Data Flow
```
Sensors → Arduino (5s) → JSON Serial → Pi → ThingSpeak (15s)
                                         → Ubidots (10s)
                                         → CSV Log
                                         → Web UI
                                         → Photos (30m)
```
