![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-app-lightgrey)
[![GitHub stars](https://img.shields.io/github/stars/g1forfun/Pi-Monitor?style=social)](https://github.com/g1forfun/Pi-Monitor/stargazers)

# 🖥️ Pi 5 Performance Dashboard
⭐️ If you like this project, give it a star!

A real-time system monitoring dashboard built for the Raspberry Pi 5, using **Flask**, **Socket.IO**, and **Chart.js**. Tracks key performance metrics including CPU usage, memory, temperature, fan speed, network I/O, disk activity, and PMIC power draw — all in a sleek, dark-themed UI.
All you need for Raspberry Pi 5 monitoring.

---

## 📸 Screenshot
![Image](https://github.com/user-attachments/assets/39701724-cd86-4025-8676-d90e1f1b3896)

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
