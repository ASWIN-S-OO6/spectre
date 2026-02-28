# 🛡️ Spectre

**Spectre** is a highly advanced, web-based AI Pentesting OS and Terminal environment. Built on top of a fully-fledged Kali Linux Docker container, it provides a seamless dual-mode experience: run direct Linux shell commands, or engage **Agent Mode** to have an LLM automatically orchestrate vulnerability scans, directory bruteforcing, and reconnaissance.

![Spectre UI](https://img.shields.io/badge/UI-React%20%2B%20AntD-blue) ![Backend](https://img.shields.io/badge/Backend-Python%20Flask-green) ![Platform](https://img.shields.io/badge/Platform-Docker%20Kali-lightgrey)

---

## ✨ Key Features

*   **Dual Engine (Agent / Shell Mode):** Toggle between raw Kali CLI interactions and Natural Language AI translations dynamically from the header. Basic commands bypass the AI for zero latency, while complex intents are translated into multi-tool attack chains.
*   **Multi-API Architecture:** Supports Anthropic, OpenAI, Groq, and Gemini natively.
*   **XFCE-Style Web OS System:** Floating, fully isolated, multi-tab terminal ecosystem. Includes a dedicated `< />` System Logs sidebar to monitor deep Python tracebacks without bleeding errors into your active terminal.
*   **Built-in Tor Anonymity:** Integrated Tor network routing. Just type `toron` and all terminal traffic is forcibly routed through `proxychains4`. Supports auto-rotation and live status monitoring.
*   **Kali Context Protocol (MCP):** Dynamic on-demand tool installation and execution capabilities giving the AI agent direct access to `nmap`, `radare2`, `sqlmap`, `gobuster`, etc.

## 🚀 Quick Start (Docker)

The fastest and most stable way to run Spectre is via Docker. 

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/spectre.git
cd spectre
```

**2. Build & Launch the Container**
Because this project compiles a full React Vite frontend onto a Python server natively, **you must build the container** to generate the assets:
```bash
docker compose up --build -d
```

**3. Access the OS**
Once the container is running, simply access the web-interface:
👉 **[http://localhost:7777](http://localhost:7777)**

---

## 💻 Commands Reference

Spectre intercepts specific keywords when entered into the terminal:

### Pentest Modules
- `scan <target>`: Trigger a full foundational reconnaissance suite.
- `dirs <target>`: AI-assisted directory and hidden endpoint discovery.
- `passwords <svc://host>`: AI-generated password wordlist attack.
- `portscan <target>`: High-speed port scanning + AI analysis.
- `vulnscan <target>`: Deep vulnerability assessment.

### Tools & Utilities
- `shell <cmd>`: Force run exact Kali command.
- `ask <question>`: Chat natively with the loaded LLM.
- `clear`: Purge the current terminal screen.
- `savelog`: Save the current terminal session to disk.

### Tor Anonymity
- `toron [interval]`: Engage Tor with optional auto-rotation interval (seconds).
- `toroff`: Disable proxychains and return to clear web.
- `newip`: Force jump to a new Tor exit node immediately.
- `torstatus`: Check active Tor pooling status.
- `myip`: Show true IP vs Current Tor Exit.

---

## 🛠️ Tech Stack & Architecture

- **Frontend:** React 18, TypeScript, Vite, Ant Design (AntD), Socket.IO-Client
- **Backend:** Python 3, Flask, Flask-SocketIO, LiteLLM
- **Environment:** Kali Linux Rolling (Docker), Python-Tornet

*Disclaimer: Spectre is built for authorized penetration testing and educational purposes only. The creators are not responsible for any misuse or damage caused by this software.*
