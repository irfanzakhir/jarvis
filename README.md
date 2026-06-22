# ⚙️ J.A.R.V.I.S. OS // Next-Gen Autonomous Desktop Agent

![Python Version](https://img.shields.io/badge/Python-3.11%2B-cyan?style=for-the-badge&logo=python)
![Groq Engine](https://img.shields.io/badge/Powered_by-Groq_LPU-f37021?style=for-the-badge)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6_WebEngine-41cd52?style=for-the-badge)
![License](https://img.shields.io/badge/License-GNU-blue?style=for-the-badge)

> *"Just a rather very intelligent system."*

**J.A.R.V.I.S. OS** is a custom-built, fully autonomous AI overlay for Windows 11. It moves beyond standard text-based chatbots by wiring a state-of-the-art Large Language Model directly into the local operating system's autonomic nervous system. 

By executing inference on **Groq's LPU hardware architecture**, the system processes high-speed vocal commands, executes multimodal visual screen comprehension, tracks local machine telemetry, and dispatches physical UI macro automation with zero perceived latency.

---

## 📂 Exhaustive System Architecture

```text
JARVIS2.0/
├── apps/                        # Standalone Situational & Reconnaissance Cockpits
│   ├── map_intel.py             # GIS Tactical Navigation Grid (PyQt6 + Leaflet JS + UDP RPC)
│   ├── news_intel.py            # Global Situation Room (Asynchronous Reflowing News Matrix)
│   └── weather_intel.py         # Orbital Atmospheric Telemetry & Open-Meteo Radar
├── assets/                      # Bundled Media & Hardware Textures
│   └── sound_effects/           # UI auditory feedback chirps & radar sweeps
├── build/                       # Temporary PyInstaller compilation staging artifacts
├── core/                        # Autonomic Cognitive Core & Local Daemons
│   ├── __pycache__/
│   ├── brain.py                 # Master Orchestration Core (Llama-3.3 70B + Multi-Tool Router)
│   ├── ears.py                  # Continuous local Speech-to-Text (STT) audio capture loop
│   ├── eyes.py                  # Multimodal optical pipeline (Screen capture + Webcam feeds)
│   ├── kinetic.py               # Kinetic OS Design System (C++ hardware shaders & chrome)
│   ├── memory.py                # JarvisMemory SQLite semantic cognition & vector context drive
│   ├── monitor.py               # Hardware telemetry polling daemons (CPU, RAM, Netsh Up/Down)
│   ├── mouth.py                 # High-speed in-memory neural Text-to-Speech (TTS) engine
│   ├── security.py              # Class-4 containment field, API validation, & Win32 socket armor
│   └── watchdog.py              # Background optical threat detection daemon (Object tracking)
├── dist/                        # Compiled Standalone Windows Binary output directory
├── gui/                         # Holographic Front-End Presentation Layer
│   ├── __pycache__/
│   ├── hud.py                   # Frameless, DWM-bypassing transparent desktop overlay
│   └── widgets.py               # Reusable modular PyQt6 / QtWebEngine dashboard components
├── utils/                       # Low-Level System Intercept Hooks
│   ├── __pycache__/
│   └── automation.py            # Local OS execution chains (PyAutoGUI UI & raw OS macro hooks)
├── venv/                        # Isolated Python Virtual Sandbox
├── .env                         # Environment keys & secure uplinks (Local deployment only)
├── .gitignore                   # Repository containment rules & local cache exclusion
├── main.py                      # Primary application bootloader & global process supervisor
└── requirements.txt             # Strict cross-platform production dependency roster

```

---

## 🧠 Deep-Dive Module Specifications

### 1. The Cognitive Front-End (`core/`)

* **`brain.py`:** The central decision matrix. Implements a multi-tool execution parser that intercepts over-eager LLM double-dispatches (The *Concrete Wall* pattern). Features a sliding-window context memory that self-trims to maintain optimized token depth without losing conversational continuity. Maintains long-term spatial context via an internal *Hippocampus* memory anchor.
* **`ears.py` & `mouth.py`:** The acoustic bridge. Reads local microphone hardware arrays and streams high-speed vocal responses back out through system audio pipes directly from memory buffers.
* **`eyes.py`:** The visual cortex. Captures base64-encoded display matrices and forwards them to **Llama 3.2 11B Vision** to grant Jarvis real-time contextual awareness of active desktop windows.
* **`memory.py`:** Interrogates an asynchronous local SQLite database (`jarvis_cognition.db`) to inject historical user constraints and personal facts dynamically into base system prompts.
* **`kinetic.py`:** Injects custom hardware shaders across the entire OS suite, rendering pitch-black obsidian glass containers, custom draggable title bars, and neon chasing laser borders.

### 2. The Autonomic Nervous System (`core/monitor.py` & `utils/automation.py`)

* **Hardware Telemetry:** Non-blocking background worker threads continually poll `psutil` to track core temperatures, memory swapping, and network packet velocity.
* **Machine Automation:** Employs raw Win32 API hooks and UI macro scripts to take physical control of the host machine (Adjusting volume gain, manipulating IDEs, reading screen coordinates, or forcing sleep states).

### 3. The Spatial Reconnaissance Cockpit (`apps/map_intel.py`)

* **Single-Process Chromium Diet:** Overrides QtWebEngine environment variables (`--single-process`), slashing RAM allocation by 70% and completely muffling console hardware acceleration warnings.
* **The Altitude Matrix:** Automatically maps Esri geospatial ontology tags (`Country`, `State`, `City`, `Neighborhood`, `StreetAddress`) directly into precise orbital camera zoom levels.
* **The 1.5km Self-Aware Flight Guard:** Intercepts redundant global coordinate lookups during manual zoom commands; preserves user UI interaction if the lens is already focused within a $1.5\text{ km}$ threshold.
* **Localhost UDP Radio Station:** Listens actively on **UDP Port 7777** for asynchronous JSON-RPC command envelopes (`locate`, `zoom`), enabling non-blocking inter-process camera flights.

---

## 🛠️ Autonomous Tool Roster (15 Native Directives)

The orchestration engine routes user intent through 15 strictly anchored functional schemas:

| Tool Directive | Internal JSON Schema | Operational Scope |
| --- | --- | --- |
| **`pilot_browser`** | `action`, `url`, `selector`, `text` | Navigates web URLs, injects text, clicks DOM elements, or terminates browser sessions. |
| **`pilot_desktop`** | `action`, `app_name`, `element_name`, `text` | Executes native UI automation across desktop windows or dispatches raw macro keystrokes. |
| **`control_application`** | `action`, `app_name` | Spawns fresh executable processes, switches foreground focus, or hard-kills active apps. |
| **`search_network`** | `query` | Interrogates public search indexes for real-time general knowledge aggregation. |
| **`open_situation_room`** | `layer`, `custom_query` | Deploys the asynchronous `news_intel.py` matrix filtered by global geopolitical vectors. |
| **`open_tactical_map`** | `location` | Deploys `map_intel.py` and locks low-Earth orbit satellite imagery onto target sectors. |
| **`control_map_zoom`** | `direction`, `steps` | Beams JSON-RPC packets over UDP Port 7777 to dynamically alter active map camera altitudes. |
| **`open_atmospheric_radar`** | `location` | Deploys `weather_intel.py` to stream live Open-Meteo barometric vitals and 5-day forecasts. |
| **`analyze_screen`** | *(None - Captures Base64)* | Compares user vocal questions against real-time base64 visual desktop captures. |
| **`vision_click`** | `target_element` | Employs spatial pixel calculation to locate and left-click specific UI buttons on screen. |
| **`engage_watchdog`** | `target_object` | Spawns an isolated optical background thread to actively watch webcam feeds for target entities. |
| **`disarm_watchdog`** | *(None)* | Safely terminates and detaches active optical background surveillance threads. |
| **`control_hardware`** | `action` (`vol_up`, `mute`, `sleep`, etc.) | Dispatches physical motherboard instructions to adjust gain, capture buffers, or trigger sleep states. |
| **`manage_dashboard`** | `action` (`minimize`, `maximize`, etc.) | Modifies the holographic floating HUD presentation layout states. |
| **`remember_fact`** | `fact` | Commits permanent user traits or critical preferences into the SQLite cognition vector drive. |

---

## ⚡ Setup & Cold Start Protocol

### Prerequisites

* Windows 11 OS (64-bit)
* Python 3.11+
* Dedicated hardware microphone & optical camera array
* A verified [Groq Cloud API Key](https://console.groq.com/keys)

### Local Deployment

1. **Clone the Master Repository:**
```bash
git clone [https://github.com/YOUR_GITHUB_NAME/jarvis_git.git](https://github.com/YOUR_GITHUB_NAME/jarvis_git.git)
cd jarvis_git

```


2. **Initialize the Virtual Sandbox:**
```bash
python -m venv venv
.\venv\Scripts\activate

```


3. **Mount Cross-Platform Dependencies:**
```bash
pip install -r requirements.txt

```


4. **Establish Security Keys:**
Create a secure `.env` file in the project root adjacent to `main.py`:
```env
GROQ_API_KEY=your_groq_api_key_here
NEWS_API_KEY=your_worldnews_api_key_here

```


5. **Turn the Key:**
```bash
python main.py

```



---

## 📻 Inter-Process Telemetry Specification (UDP Port 7777)

You can remotely control the Spatial Intelligence module (`apps/map_intel.py`) from any external script or command prompt while the application is active.

### Supported JSON-RPC Command Packets

#### A. Target Intercept (`locate`)

```json
{
  "command": "locate",
  "place": "Manhattan, New York"
}

```

#### B. Optical Optics (`zoom`)

```json
{
  "command": "zoom",
  "direction": "out",
  "factor": 2
}

```

### Python Datagram Transmitter Snippet

```python
import socket
import json

def blast_ipc_packet(payload_dict):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(payload_dict).encode('utf-8'), ("127.0.0.1", 7777))

# Soar across the globe to London instantly
blast_ipc_packet({"command": "locate", "place": "Big Ben, London"})

```

---

## 📦 PyInstaller Standalone Binary Compilation

To run Jarvis silently in the Windows background without an open console terminal, compile the suite into a single native binary:

```bash
pyinstaller --noconfirm --windowed --add-data "assets;assets" --hidden-import="psutil" --hidden-import="groq" --hidden-import="edge_tts" --hidden-import="cv2" main.py

```

> ⚠️ **Mandatory Post-Build Action:** PyInstaller completely ignores local environment files for security reasons. You must manually copy your `.env` file into the generated `dist/main/` folder directly next to `main.exe` before execution.

---

## 🛡️ Operational License & Security Disclaimer

This core architecture is released under the **GNU General Public License v3.0**.

**CRITICAL HAZARD WARNING:** This software grants a generative neural network automated access to physical host execution layers (`os.system`, process termination, clipboard monitoring, power state alterations). It is engineered strictly for local developer experimentation and academic research. Review all execution paths inside `utils/automation.py` before attaching wide-permission access keys.

```

```
