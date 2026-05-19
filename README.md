


# ⚙️ J.A.R.V.I.S. OS // Next-Gen Desktop Agent

![Python Version](https://img.shields.io/badge/Python-3.11%2B-cyan?style=for-the-badge&logo=python)
![Groq Engine](https://img.shields.io/badge/Powered_by-Groq_LPU-f37021?style=for-the-badge)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6_WebEngine-41cd52?style=for-the-badge)
![License](https://img.shields.io/badge/License-GNU-blue?style=for-the-badge)

> *"Just a rather very intelligent system."*

**J.A.R.V.I.S. OS** is a custom-built, fully autonomous AI overlay for Windows. It moves beyond standard text-based chatbots by wiring a state-of-the-art Large Language Model directly into the local operating system. 

By running on **Groq's LPU inference hardware**, the system achieves near-instantaneous cognition, allowing it to process voice commands, analyze on-screen visual data, monitor hardware telemetry, and execute physical machine automation with zero perceived latency.

---

## 🧠 System Architecture

The codebase is highly modular, splitting cognitive and physical tasks into dedicated autonomic threads.

### 1. The Neural Core (`core/brain.py`)
* **Speed Engine:** Utilizes the Groq SDK to run **Llama 3.3 70B** at hundreds of tokens per second.
* **Sliding Window Memory:** Implements a strict, self-trimming context window (saving the last 10 interactions) to maintain perfect conversational awareness without ever hitting token overflow limits.
* **Persistent Storage:** Asynchronously writes critical user facts to a local `memory.json` drive for long-term recall.

### 2. The Optical Array (`core/eyes.py`)
* **Vision Pipeline:** Captures base64-encoded screen states and webcam feeds.
* **Multimodal Analysis:** Routes image data through Meta's **Llama 4 Scout** model, cross-wiring visual findings directly back into the primary text memory stream.

### 3. The Autonomic Nervous System (`core/monitor.py` & `utils/automation.py`)
* **Live Telemetry:** Background daemon threads continuously poll `psutil` and Windows `netsh` to track CPU loads, physical RAM allocation, and real-time Wi-Fi bandwidth (Up/Down).
* **Threat Detection:** Automatically interrupts the AI's standard loop to verbally warn the user if network uplinks drop or hardware thresholds exceed 90%.
* **PC Automation:** Grants the AI execution rights to manipulate the host machine via `pyautogui` and `os` (Launch VS Code/Chrome, adjust audio gain, take screenshots, or force hibernation).

### 4. The Holographic HUD (`gui/hud.py`)
* **DWM Bypass:** Uses Qt window flags (`SplashScreen | FramelessWindowHint`) to completely strip Windows 11 window borders, creating a genuine floating interface.
* **WebEngine Dashboard:** Renders an animated, high-performance HTML/CSS/JS dashboard that catches live JSON telemetry signals from the Python backend.

---

## ⚡ Quick Start Guide

### Prerequisites
* Python 3.11 or higher
* Active microphone and webcam
* A free [Groq API Key](https://console.groq.com/keys)

### Installation
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/jarvis.git](https://github.com/YOUR_USERNAME/jarvis.git)
   cd jarvis
   ```



2. **Install core dependencies:**
```bash
pip install -r requirements.txt
```


3. **Configure the Neural Link:**
Rename the `.env.example` file to `.env` and insert your API key:
```env
GROQ_API_KEY=your_groq_api_key_here

```


4. **Initiate Cold Start:**
```bash
python main.py

```





## 📦 Compiling to Standalone Executable

To run J.A.R.V.I.S. as a silent, background desktop application without opening a terminal, compile the source code using PyInstaller.

```bash
pyinstaller --noconfirm --windowed --add-data "assets;assets" --hidden-import="psutil" --hidden-import="groq" --hidden-import="edge_tts" --hidden-import="cv2" main.py

```

*Note: After compilation, you must manually place your `.env` file into the `dist/main` folder next to the generated `main.exe`.*

---

## 🛡️ License & Disclaimer

This project is licensed under the **GNU License**.

**Security Warning:** This software bridges a generative AI model with local machine execution protocols (closing apps, altering power states). It is intended for developer experimentation. Review the `automation.py` execution chains before modifying the core system prompts.

```

```
