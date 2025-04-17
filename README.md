![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-app-lightgrey)
# 🖥️ Pi 5 Performance Dashboard

A real-time system monitoring dashboard built for the Raspberry Pi 5, using **Flask**, **Socket.IO**, and **Chart.js**. Tracks key performance metrics including CPU usage, memory, temperature, fan speed, network I/O, disk activity, and PMIC power draw — all in a sleek, dark-themed UI.

---

## 📸 Screenshot

![Pi 5 Dashboard](https://raw.githubusercontent.com/g1forfun/Pi-Monitor/main/assets/pi-monitor-dashboard.png)

---

## 🚀 Features

- Live-updating charts for:
  - CPU usage (%)
  - Memory usage (%)
  - CPU temperature
  - CPU and GPU frequency
  - Fan Speed (RPM)
  - Disk usage (%)
  - Disk I/O (MB/s)
  - Network I/O (MB/s)
  - PMIC power draw (W)
- Auto-min/max tracking for power
- Socket.IO WebSocket updates
- Bootstrap 5 + dark mode styling
- Optional floating stat indicators

---

## 📦 Requirements

- Python 3.7+
- Raspberry Pi 5
- Flask
- `psutil` and related system tools
- (Optional) `vcgencmd`, `zramctl`, or any sensors you want to add

---

## 🛠️ Installation

```bash
# Clone the repo
git clone https://github.com/g1forfun/Pi-Monitor.git
cd Pi-Monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run it
python app.py
