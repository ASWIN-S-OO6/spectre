#!/usr/bin/env python3
"""
AI Pentester — Web-based terminal served over Flask + SocketIO.
Open http://localhost:7777 in any browser. No VNC needed.
"""

import os
import sys
import threading
import subprocess
import shlex
import json
import re
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_engine import AIEngine
from pentest_modules.dir_bruteforce import DirectoryBruteforce
from pentest_modules.password_attack import PasswordAttack
from pentest_modules.port_scanner import PortScanner
from pentest_modules.vuln_scanner import VulnScanner
from pentest_modules.recon import Recon
from utils.terminal_handler import TerminalHandler

frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
app = Flask(__name__, static_folder=frontend_dist, static_url_path="/")
app.config["SECRET_KEY"] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

# ── Global state ─────────────────────────────────────────────────
engine: AIEngine | None = None
terminal: TerminalHandler | None = None
modules: dict = {}
g_username: str = "spectre"
g_hostname: str = "kali"


def send_output(text: str, color: str = "#c9d1d9", terminal_id: str = None):
    """Send output to the browser terminal."""
    data = {"text": text, "color": color}
    if terminal_id:
        data["terminalId"] = terminal_id
    socketio.emit("output", data)


def send_system_log(level: str, source: str, message: str):
    """Broadcasts background system and AI engine traces to the React sidebar."""
    socketio.emit("system_log", {
        "level": level,
        "source": source,
        "message": message
    })


@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/<path:path>")
def serve_static(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.exists(full_path):
        return app.send_static_file(path)
    return app.send_static_file("index.html")


@socketio.on("connect")
def handle_connect():
    # When a new client connects, assign a unique terminal ID
    terminal_id = request.sid
    send_output(
        "\r\n🛡️  SPECTRE — Agent Powered Terminal\r\n"
        "──────────────────────────────────────────\r\n"
        "Enter your API key to begin.\r\n\r\n",
        color="#00ff41",
        terminal_id=terminal_id
    )
    send_system_log("info", "Connection", f"New client connected: {terminal_id}")


@socketio.on("set_api_key")
def handle_api_key(data):
    global engine, terminal, modules, agent_mode, g_username, g_hostname
    key = data.get("key", "").strip()
    provider = data.get("provider", "gemini")
    agent_mode = data.get("agent_mode", True)
    g_username = data.get("username", "spectre")
    g_hostname = data.get("hostname", "kali")
    terminal_id = data.get("terminalId", request.sid)

    if not key and agent_mode:
        send_output("[✗] API key cannot be empty in Agent Mode.\r\n", color="#ff4444", terminal_id=terminal_id)
        send_system_log("warning", "Auth", "API key empty in Agent Mode.")
        return

    try:
        # If Agent Mode is off and no key provided, just initialize empty
        if not agent_mode and not key:
            key = "NO_KEY"
            
        send_system_log("info", "Auth", "Authenticating provider...")
        engine = AIEngine(key, provider=provider)
        terminal = TerminalHandler(send_output, socketio.emit, terminal_id)
        modules = {
            "dirs":      DirectoryBruteforce(engine),
            "passwords": PasswordAttack(engine),
            "portscan":  PortScanner(engine),
            "vulnscan":  VulnScanner(engine),
            "recon":     Recon(engine),
        }
        
        mode_str = "Agent Mode: ON" if agent_mode else "Shell Mode: ON"
        send_output(f"[✓] {provider.capitalize()} Engine connected! ({mode_str})\r\n", color="#00ff41", terminal_id=terminal_id)
        send_output("[✓] All Kali tools loaded.\r\n", color="#00ff41", terminal_id=terminal_id)
        send_output("[✓] Tor/Proxychains ready (type 'toron').\r\n", color="#58a6ff", terminal_id=terminal_id)
        send_output("\r\nType 'help' for commands.\r\n\r\n", color="#888888", terminal_id=terminal_id)
        emit("authenticated", {"ok": True}, room=request.sid)
        
        send_system_log("success", "System", f"Workstation connected successfully to {g_hostname}. AI Provider: {provider}")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e)}"
        send_output(f"[✗] Initialization error: {err_msg} \r\n", color="#ff4444", terminal_id=terminal_id)
        send_system_log("error", "Boot", f"Failed to mount core terminal dependencies. Traceback: {str(e)}")
        emit("authenticated", {"ok": False, "error": err_msg}, room=request.sid)

@socketio.on("toggle_agent_mode")
def handle_toggle_agent_mode(data):
    global agent_mode
    terminal_id = data.get("terminalId", request.sid)
    agent_mode = data.get("enabled", False)
    mode_str = "ON (AI Parsing)" if agent_mode else "OFF (Direct Shell)"
    send_output(f"\r\n[*] Agent Mode is now {mode_str}.\r\n", "#58a6ff", terminal_id)
    send_system_log("info", "AIEngine", f"Agent Mode toggled to {mode_str}")


HELP_TEXT = r"""
╔══════════════════════════════════════════════════════════════════════╗
║           🛡️  SPECTRE — Command Reference  🛡️                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  Pentesting:                                                         ║
║    scan <target>             Full reconnaissance                     ║
║    dirs <target>             AI directory discovery                   ║
║    passwords <svc://host>    AI password attack                      ║
║    portscan <target>         Port scanning + AI analysis             ║
║    vulnscan <target>         Vulnerability assessment                ║
║    ask <question>            Ask Gemini anything                     ║
║    shell <command>           Run any Kali command                    ║
║                                                                      ║
║  Anonymity (Tor):                                                    ║
║    toron                     Start Tor (auto-rotate IP every 2s)     ║
║    toroff                    Stop Tor                                ║
║    newip                     New Tor exit IP now                     ║
║    torstatus                 Tor pool status                         
║    autorotate <secs>         Change rotation interval                ║
║    stoprotate                Stop auto-rotation                      ║
║    myip                      Show real IP vs Tor IP                  ║
║                                                                      ║
║  General:                                                            ║
║    help / clear / savelog / exit                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""


@socketio.on("command")
def handle_command(data):
    cmd = data.get("cmd", "").strip()
    term_id = data.get("terminalId", request.sid)
    if not cmd:
        return
    if not engine:
        send_output("[!] Set your API key first.\r\n", {"text": "[!] Set your API key first.\r\n", "color": "#ff4444", "terminalId": term_id})
        send_system_log("warning", "Auth", "Command received before API key set.")
        return

    # Echo the command
    send_output(f"{g_username}@{g_hostname}:~$ {cmd}\r\n", "#00ff41", term_id)
    send_system_log("info", "Shell", f"Executed manual trigger: {cmd}")

    # Run in a background thread so we don't block
    threading.Thread(target=_execute, args=(cmd, term_id), daemon=True).start()


def _execute(cmd: str, term_id: str):
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    try:
        if command == "help":
            send_output(HELP_TEXT + "\r\n", "#00ff41", term_id)
            send_system_log("info", "Shell", "Displayed help text.")

        elif command == "clear":
            socketio.emit("clear", room=term_id)
            send_system_log("info", "Shell", "Cleared terminal output.")

        elif command == "exit":
            send_output("[*] Goodbye.\r\n", "#ffaa00", term_id)
            send_system_log("info", "Shell", "User exited.")

        elif command == "savelog":
            terminal.save_session_log()
            send_system_log("info", "Shell", "Session log saved.")

        elif command == "toron":
            interval = int(args) if args.isdigit() else 2
            terminal.enable_anonymity(auto_rotate_interval=interval, terminal_id=term_id)
            send_system_log("info", "Tor", f"Tor enabled with auto-rotate interval: {interval}s")

        elif command == "toroff":
            terminal.disable_anonymity(terminal_id=term_id)
            send_system_log("info", "Tor", "Tor disabled.")

        elif command == "newip":
            terminal.tor.new_identity()
            send_output("[*] Requested new Tor identity.\r\n", "#58a6ff", term_id)
            send_system_log("info", "Tor", "Requested new Tor identity.")

        elif command == "torstatus":
            terminal.tor.status()
            send_output("[*] Checked Tor status pool.\r\n", "#58a6ff", term_id)
            send_system_log("info", "Tor", "Checked Tor status.")

        elif command == "autorotate":
            secs = int(args) if args.isdigit() else 2
            terminal.tor.auto_rotate(interval=secs)
            send_output(f"[*] Set auto-rotate interal to {secs}s\r\n", "#58a6ff", term_id)
            send_system_log("info", "Tor", f"Tor auto-rotate interval set to {secs}s.")

        elif command == "stoprotate":
            terminal.tor.stop_auto_rotate()
            send_output("[*] Stopped auto-rotate.\r\n", "#58a6ff", term_id)
            send_system_log("info", "Tor", "Tor auto-rotate stopped.")

        elif command == "myip":
            real = terminal.tor.get_real_ip()
            send_output(f"[*] Real IP : {real}\r\n", "#ff4444", term_id)
            if terminal.anonymity_enabled:
                terminal.tor._show_current_ip()
            else:
                send_output("[*] Tor: not enabled\r\n", "#888888", term_id)
            send_system_log("info", "Tor", "Displayed IP information.")

        # ── Shell ──
        elif command == "shell":
            if not args:
                send_output("[!] Usage: shell <command>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Shell", "Shell command used without arguments.")
                return
            terminal.run(args, timeout=300, terminal_id=term_id)
            send_system_log("info", "Shell", f"Executed shell command: {args}")

        # ── Pentest modules ──
        elif command == "scan":
            if not args:
                send_output("[!] Usage: scan <target>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Module", "Scan command used without target.")
                return
            send_system_log("info", "Module", f"Initiating full reconnaissance on {args}")
            modules["recon"].execute(args, lambda text, color="#c9d1d9": send_output(text, color, term_id))

        elif command == "dirs":
            if not args:
                send_output("[!] Usage: dirs <target>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Module", "Dirs command used without target.")
                return
            send_system_log("info", "Module", f"Initiating directory bruteforce on {args}")
            modules["dirs"].execute(args, lambda text, color="#c9d1d9": send_output(text, color, term_id))

        elif command == "passwords":
            if not args:
                send_output("[!] Usage: passwords <svc://target>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Module", "Passwords command used without target.")
                return
            send_system_log("info", "Module", f"Initiating password attack on {args}")
            modules["passwords"].execute(args, lambda text, color="#c9d1d9": send_output(text, color, term_id))

        elif command == "portscan":
            if not args:
                send_output("[!] Usage: portscan <target>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Module", "Portscan command used without target.")
                return
            send_system_log("info", "Module", f"Initiating port scan on {args}")
            modules["portscan"].execute(args, lambda text, color="#c9d1d9": send_output(text, color, term_id))

        elif command == "vulnscan":
            if not args:
                send_output("[!] Usage: vulnscan <target>\r\n", "#ff4444", term_id)
                send_system_log("warning", "Module", "Vulnscan command used without target.")
                return
            send_system_log("info", "Module", f"Initiating vulnerability scan on {args}")
            modules["vulnscan"].execute(args, lambda text, color="#c9d1d9": send_output(text, color, term_id))

        elif command == "ask":
            if not args:
                send_output("[!] Usage: ask <question>\r\n", "#ff4444", term_id)
                send_system_log("warning", "AIEngine", "Ask command used without question.")
                return
            send_output("[*] Asking Gemini...\r\n", "#58a6ff", term_id)
            send_system_log("info", "AIEngine", f"Asking Gemini: {args}")
            response = engine.ask(args)
            send_output(f"\r\n{response}\r\n\r\n", "#00d4ff", term_id)
            send_system_log("info", "AIEngine", "Received response from Gemini.")

        else:
            if not agent_mode:
                # Direct shell execution when Agent Mode is OFF
                send_system_log("info", "Process", "Agent Mode disabled. Directing command to Kali terminal wrapper.")
                terminal.run(cmd, terminal_id=term_id)
                return

            # Natural language → Gemini interprets
            send_output("[*] Interpreting with Gemini AI...\r\n", "#58a6ff", term_id)
            send_system_log("info", "AIEngine", f"Sending interpretation payload to provider...")
            
            interp = engine.interpret_command(cmd)
            send_output(f"[AI] {interp['explanation']}\r\n", "#00d4ff", term_id)
            
            if "Parsing failed" in interp['explanation']:
                 send_system_log("error", "Exception", f"AI Interpreter failed: {interp['explanation']}")

            if interp.get("action") and interp.get("target"):
                action, target = interp["action"], interp["target"]
                if action in modules:
                    send_output(f"[*] Executing: {action} → {target}\r\n", "#ffaa00", term_id)
                    send_system_log("info", "AIEngine", f"AI interpreted action: {action} on target: {target}")
                    modules[action].execute(target, lambda text, color="#c9d1d9": send_output(text, color, term_id))
                elif action == "shell" and interp.get("shell_cmd"):
                    terminal.run(interp["shell_cmd"], terminal_id=term_id)
            elif interp.get("shell_cmd"):
                terminal.run(interp["shell_cmd"], terminal_id=term_id)
            else:
                send_output("[*] Could not map to action. Try 'help'.\r\n", "#888888")

    except Exception as e:
        send_output(f"[ERROR] {e}\r\n", "#ff4444")


if __name__ == "__main__":
    print("[✓] Server starting on http://0.0.0.0:7777")
    socketio.run(app, host="0.0.0.0", port=7777, debug=False, log_output=False)