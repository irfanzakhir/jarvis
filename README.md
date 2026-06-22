
# ⚙️ J.A.R.V.I.S. OS // Next-Gen Desktop Agent

![Python Version](https://img.shields.io/badge/Python-3.11%2B-cyan?style=for-the-badge&logo=python)
![Groq Engine](https://img.shields.io/badge/Powered_by-Groq_LPU-f37021?style=for-the-badge)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6_WebEngine-41cd52?style=for-the-badge)
![License](https://img.shields.io/badge/License-GNU-blue?style=for-the-badge)

> *"Just a rather very intelligent system."*

**J.A.R.V.I.S. OS** is a custom-built, fully autonomous AI overlay for Windows. It moves beyond standard text-based chatbots by wiring a state-of-the-art Large Language Model directly into the local operating system. 

By running on **Groq's LPU inference hardware**, the system achieves near-instantaneous cognition, allowing it to process voice commands, analyze on-screen visual data, monitor hardware telemetry, and execute physical machine automation with zero perceived latency.

---

## 📂 Project Repository Architecture

```text
jarvis_git/
├── .env                         # Critical security keys (Local deployment only)
├── .gitignore                   # Class-4 environment containment rules
├── requirements.txt             # Cross-platform production pip dependencies
├── main.py                      # Main tactical orchestration engine
├── core/
│   ├── brain.py                 # Llama-3 neural core & memory managers
│   ├── eyes.py                  # Vision pipeline & Llama 4 Scout stream
│   └── monitor.py               # Hardware telemetry polling & background daemons
├── apps/
│   └── map_intel.py             # Spatial Intelligence Suite (PyQt6 + Leaflet JS)
├── gui/
│   └── hud.py                   # Frameless DWM-bypassing holographic layout
└── utils/
    └── automation.py            # Local OS execution chains (pyautogui/os hooks)

```

---

## 🧠 Core Systems Detail

### 1. The Neural Core (`core/brain.py`)

* **Speed Engine:** Utilizes the Groq SDK to run **Llama 3.3 70B** at hundreds of tokens per second.
* **Sliding Window Memory:** Implements a strict, self-trimming context window (saving the last 10 interactions) to maintain perfect conversational awareness without ever hitting token overflow limits.
* **Persistent Storage:** Asynchronously writes critical user facts to a local JSON memory drive for long-term recall.

### 2. The Optical Array (`core/eyes.py`)

* **Vision Pipeline:** Captures base64-encoded screen states and webcam feeds.
* **Multimodal Analysis:** Routes image data through Meta's **Llama 4 Scout** model, cross-wiring visual findings directly back into the primary text memory stream.

### 3. The Autonomic Nervous System (`core/monitor.py` & `utils/automation.py`)

* **Live Telemetry:** Background daemon threads continuously poll `psutil` and Windows network configurations to track CPU loads, physical RAM allocation, and real-time network bandwidth.
* **Threat Detection:** Automatically interrupts the AI's standard loop to verbally warn the user if network uplinks drop or hardware thresholds exceed 90%.
* **PC Automation:** Grants the AI execution rights to manipulate the host machine via `pyautogui` and `os` commands (Launch IDEs, adjust audio gain, take screenshots, or force hibernation).

### 4. The Holographic HUD (`gui/hud.py`)

* **DWM Bypass:** Uses Qt window flags (`SplashScreen | FramelessWindowHint`) to completely strip Windows 11 borders, creating a genuine floating interface.
* **WebEngine Dashboard:** Renders an animated, high-performance HTML/CSS/JS dashboard that catches live JSON telemetry signals from the Python backend.

### 5. Spatial Intelligence Module (`apps/map_intel.py`)

* **The Single-Process Chromium Diet:** Overrides default multi-threaded Qt allocations via system environment modifications (`--single-process`), dropping background RAM usage by up to 70% while silencing raw console debugging dumps.
* **The Altitude Matrix:** Translates Esri location taxonomy metadata (`PointAddress`, `Neighborhood`, `Locality`, `City`, `State`) directly into optimized Leaflet orbital zoom indexes.
* **The 1.5km Flight Guard:** Measures spatial delta between current position coordinates and new targets; prevents automated overrides from steamrolling custom manual zoom refinements if coordinates are within a tight $1.5\text{ km}$ threshold.
* **Two-Way Click Refinement:** Manual viewport coordinate selections pipe telemetry upward back into the UI HUD through intercepted JavaScript page title mutations.

---

## ⚡ Quick Start Guide

### Prerequisites

* Python 3.11 or higher
* Active microphone and webcam
* A free [Groq API Key](https://console.groq.com/keys)

### Installation

1. **Clone the repository:**
```bash
git clone [https://github.com/YOUR_USERNAME/jarvis_git.git](https://github.com/YOUR_USERNAME/jarvis_git.git)
cd jarvis_git

```


2. **Establish the Sandbox Environment:**
```bash
python -m venv venv
# Activate on Windows:
.\venv\Scripts\activate

```


3. **Install Core Dependencies:**
```bash
pip install -r requirements.txt

```


4. **Configure the Neural Link:**
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here

```


5. **Initiate Cold Start:**
```bash
python main.py

```



---

## 📻 Inter-Process Telemetry Tutorial (UDP JSON-RPC)

The Spatial Intelligence app runs an active internal radio station on **UDP Port 7777**. Any script, background terminal, or automated voice engine can instantly snap the map's focus, alter coordinates, or trigger orbital adjustments by firing non-blocking network datagrams.

### Map Telemetry Interface Specification

The app accepts standardized JSON-RPC envelopes containing a `command` parameter:

#### A. Fly to Location (`locate`)

Moves the lens to a specific geographic region with automated fallback layers.

```json
{
  "command": "locate",
  "place": "Munnar, Kerala"
}

```

#### B. Scale Viewport (`zoom`)

Adjusts magnification dynamically by a factor of steps.

```json
{
  "command": "zoom",
  "direction": "in",
  "factor": 2
}

```

### Quick Python Transmitter Script

Drop this snippet into any utility file to test remote execution while `map_intel.py` is actively running:

```python
import socket
import json

def dispatch_tactical_packet(packet_dict):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = json.dumps(packet_dict).encode('utf-8')
    client.sendto(payload, ("127.0.0.1", 7777))
    print(f"[PACKET DISPATCHED] -> {packet_dict}")

# Fly to target sector
dispatch_tactical_packet({"command": "locate", "place": "Vagamon, Kerala"})

# Zoom in closer
dispatch_tactical_packet({"command": "zoom", "direction": "in", "factor": 2})

```

---

## 📦 Compiling to Standalone Executable

To compile J.A.R.V.I.S. as a silent, background desktop application without leaving a hanging terminal window open, compress your workspace via PyInstaller.

```bash
pyinstaller --noconfirm --windowed --add-data "assets;assets" --hidden-import="psutil" --hidden-import="groq" --hidden-import="edge_tts" --hidden-import="cv2" main.py

```

> ⚠️ **Post-Compilation Directive:** After compilation completes, you must manually copy your local security `.env` file directly into the newly generated `dist/main/` folder immediately adjacent to the generated `main.exe` binary.

---

## 🛡️ License & Disclaimer

This project is licensed under the **GNU License**.

**Security Warning:** This software bridges a generative AI model with local machine execution protocols (closing applications, reading clipboard data, adjusting power states). It is strictly designed for developer research and local experimentation. Always verify safety constraints in the execution chains inside `utils/automation.py` before deploying wide-permission access keys.

```

```
