#!/usr/bin/env python3
"""
AI Pentester - Main GUI Application
Launches with API key prompt, then presents an interactive terminal.
Now includes full Tor / Proxychains anonymity layer.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_engine import GeminiEngine
from pentest_modules.dir_bruteforce import DirectoryBruteforce
from pentest_modules.password_attack import PasswordAttack
from pentest_modules.port_scanner import PortScanner
from pentest_modules.vuln_scanner import VulnScanner
from pentest_modules.recon import Recon
from utils.terminal_handler import TerminalHandler


class APIKeyDialog:
    """Initial dialog to collect the Gemini API key."""

    def __init__(self, root):
        self.root = root
        self.api_key = None
        self.dialog = tk.Toplevel(root)
        self.dialog.title("🔑 AI Pentester - Enter Gemini API Key")
        self.dialog.geometry("520x300")
        self.dialog.configure(bg="#1a1a2e")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 260
        y = (self.dialog.winfo_screenheight() // 2) - 150
        self.dialog.geometry(f"+{x}+{y}")
        self._build_ui()

    def _build_ui(self):
        title_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        title_frame.pack(pady=(20, 10))

        tk.Label(
            title_frame, text="🛡️ AI PENTESTER",
            font=("Consolas", 22, "bold"), fg="#00ff41", bg="#1a1a2e",
        ).pack()
        tk.Label(
            title_frame, text="Gemini-Powered Penetration Testing",
            font=("Consolas", 11), fg="#888888", bg="#1a1a2e",
        ).pack()

        key_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        key_frame.pack(pady=20, padx=30, fill="x")

        tk.Label(
            key_frame, text="Enter your Google Gemini API Key:",
            font=("Consolas", 10), fg="#e0e0e0", bg="#1a1a2e", anchor="w",
        ).pack(fill="x")

        self.key_entry = tk.Entry(
            key_frame, font=("Consolas", 12), bg="#16213e", fg="#00ff41",
            insertbackground="#00ff41", show="•", relief="flat", borderwidth=5,
        )
        self.key_entry.pack(fill="x", pady=(5, 0), ipady=5)
        self.key_entry.bind("<Return>", lambda e: self._submit())
        self.key_entry.focus_set()

        self.show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            key_frame, text="Show Key", variable=self.show_var,
            command=self._toggle_show, font=("Consolas", 9),
            fg="#888888", bg="#1a1a2e", selectcolor="#1a1a2e",
            activebackground="#1a1a2e", activeforeground="#00ff41",
        ).pack(anchor="w", pady=(5, 0))

        btn_frame = tk.Frame(self.dialog, bg="#1a1a2e")
        btn_frame.pack(pady=10)
        self.submit_btn = tk.Button(
            btn_frame, text="🚀 Launch AI Pentester",
            font=("Consolas", 12, "bold"), bg="#0f3460", fg="#00ff41",
            activebackground="#16213e", activeforeground="#00ff41",
            relief="flat", padx=20, pady=8, command=self._submit,
        )
        self.submit_btn.pack()

    def _toggle_show(self):
        self.key_entry.configure(show="" if self.show_var.get() else "•")

    def _submit(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Missing Key", "Please enter your Gemini API Key.")
            return
        if len(key) < 20:
            messagebox.showwarning("Invalid Key", "API Key seems too short.")
            return
        self.api_key = key
        self.dialog.destroy()

    def _on_close(self):
        self.root.destroy()
        sys.exit(0)


class PentestTerminal:
    """Main terminal interface with full Tor / Proxychains support."""

    BANNER = r"""
╔══════════════════════════════════════════════════════════════════════╗
║           🛡️  PENTESTER - AI Powered Terminal  🛡️            ║
║                                                                      ║
║  Pentesting Commands:                                                ║
║    scan <target>            Full reconnaissance scan                 ║
║    dirs <target>            AI directory discovery (no wordlist!)     ║
║    passwords <svc://target> AI password attack                       ║
║    portscan <target>        Intelligent port scanning                ║
║    vulnscan <target>        Vulnerability assessment                 ║
║    ask <question>           Ask Gemini anything about pentesting     ║
║    shell <command>          Run a raw shell command                  ║
║                                                                      ║
║  Anonymity (Tor / Proxychains):                                      ║
║    toron                    Start Tor + enable proxychains routing   ║
║    toroff                   Stop Tor + disable routing               ║
║    newip                    Get a new Tor exit IP immediately        ║
║    torstatus                Show Tor status & current exit IP        ║
║    autorotate <seconds>     Auto-change IP every N seconds           ║
║    stoprotate               Stop auto IP rotation                    ║
║    myip                     Show your current public IP              ║
║                                                                      ║
║  General:                                                            ║
║    help                     Show this help                           ║
║    clear                    Clear terminal                           ║
║    savelog                  Save session log to file                 ║
║    exit                     Exit                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

    def __init__(self, root, api_key):
        self.root = root
        self.root.title("🛡️ AI Pentester Terminal")
        self.root.geometry("1100x750")
        self.root.configure(bg="#0d1117")

        self.engine = GeminiEngine(api_key)
        self.output_queue = queue.Queue()

        # Terminal handler with Tor manager
        self.terminal = TerminalHandler(self.write_output)

        self.modules = {
            "dirs":     DirectoryBruteforce(self.engine),
            "passwords": PasswordAttack(self.engine),
            "portscan": PortScanner(self.engine),
            "vulnscan": VulnScanner(self.engine),
            "recon":    Recon(self.engine),
        }

        self._build_ui()
        self._process_queue()
        self.write_output(self.BANNER, "#00ff41")
        self.write_output("[+] Gemini Engine initialized.\n", "#00ff41")
        self.write_output("[+] Kali tools loaded.\n", "#00ff41")
        self.write_output("[+] Tor / Proxychains ready (type 'toron' to enable).\n", "#58a6ff")
        self.write_output("[+] Type 'help' for commands.\n\n", "#888888")

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # Status bar
        status_frame = tk.Frame(self.root, bg="#161b22", height=30)
        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            status_frame,
            text=" 🛡️ AI Pentester  |  Gemini: ✓  |  Tor: ❌ OFF  |  Kali: ✓",
            font=("Consolas", 10), fg="#58a6ff", bg="#161b22", anchor="w",
        )
        self.status_label.pack(fill="x", padx=10, pady=5)

        # Output
        self.output = scrolledtext.ScrolledText(
            self.root, font=("Consolas", 11), bg="#0d1117", fg="#c9d1d9",
            insertbackground="#00ff41", relief="flat", borderwidth=0,
            wrap="word", state="disabled",
        )
        self.output.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        for tag, fg in [
            ("green", "#00ff41"), ("red", "#ff4444"), ("yellow", "#ffaa00"),
            ("blue", "#58a6ff"), ("white", "#c9d1d9"), ("cyan", "#00d4ff"),
            ("magenta", "#ff79c6"),
        ]:
            self.output.tag_configure(tag, foreground=fg)

        # Input
        input_frame = tk.Frame(self.root, bg="#161b22")
        input_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(
            input_frame, text="ai-pentester@kali:~$ ",
            font=("Consolas", 12, "bold"), fg="#00ff41", bg="#161b22",
        ).pack(side="left")

        self.input_entry = tk.Entry(
            input_frame, font=("Consolas", 12), bg="#0d1117", fg="#c9d1d9",
            insertbackground="#00ff41", relief="flat", borderwidth=3,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.input_entry.bind("<Return>", self._on_enter)
        self.input_entry.focus_set()

        tk.Button(
            input_frame, text="▶ Run", font=("Consolas", 10, "bold"),
            bg="#238636", fg="white", activebackground="#2ea043",
            relief="flat", padx=15, command=lambda: self._on_enter(None),
        ).pack(side="right", padx=(5, 0))

    def write_output(self, text, color="#c9d1d9"):
        self.output_queue.put((text, color))

    def _process_queue(self):
        while not self.output_queue.empty():
            text, color = self.output_queue.get_nowait()
            if text == "__CLEAR__":
                self.output.configure(state="normal")
                self.output.delete("1.0", "end")
                self.output.configure(state="disabled")
                continue
            self.output.configure(state="normal")
            tag = {
                "#00ff41": "green", "#ff4444": "red", "#ffaa00": "yellow",
                "#58a6ff": "blue", "#c9d1d9": "white", "#00d4ff": "cyan",
                "#ff79c6": "magenta",
            }.get(color, "white")
            self.output.insert("end", text, tag)
            self.output.see("end")
            self.output.configure(state="disabled")
        self.root.after(100, self._process_queue)

    def _update_status_bar(self):
        tor = "✅ ON" if self.terminal.anonymity_enabled else "❌ OFF"
        self.status_label.configure(
            text=f" 🛡️ AI Pentester  |  Gemini: ✓  |  Tor: {tor}  |  Kali: ✓"
        )

    # ------------------------------------------------------------------ #
    #  Command dispatch
    # ------------------------------------------------------------------ #
    def _on_enter(self, event):
        cmd = self.input_entry.get().strip()
        if not cmd:
            return
        self.input_entry.delete(0, "end")
        self.write_output(f"ai-pentester@kali:~$ {cmd}\n", "#00ff41")
        threading.Thread(target=self._execute_command, args=(cmd,), daemon=True).start()

    def _execute_command(self, cmd):
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        try:
            # ── Anonymity commands ──
            if command == "toron":
                interval = int(args) if args.isdigit() else 0
                self.terminal.enable_anonymity(auto_rotate_interval=interval)
                self.root.after(0, self._update_status_bar)

            elif command == "toroff":
                self.terminal.disable_anonymity()
                self.root.after(0, self._update_status_bar)

            elif command == "newip":
                self.terminal.tor.new_identity()

            elif command == "torstatus":
                self.terminal.tor.status()

            elif command == "autorotate":
                secs = int(args) if args.isdigit() else 60
                self.terminal.tor.auto_rotate(interval=secs)

            elif command == "stoprotate":
                self.terminal.tor.stop_auto_rotate()

            elif command == "myip":
                self._show_both_ips()

            elif command == "savelog":
                self.terminal.save_session_log()

            # ── Standard pentest commands ──
            elif command == "help":
                self.write_output(self.BANNER, "#00ff41")

            elif command == "clear":
                self.output_queue.put(("__CLEAR__", ""))

            elif command == "exit":
                self.terminal.disable_anonymity()
                self.terminal.kill_all()
                self.root.after(0, self.root.destroy)

            elif command == "shell":
                if not args:
                    self.write_output("[!] Usage: shell <command>\n", "#ff4444")
                    return
                self.terminal.run(args, timeout=300)

            elif command == "scan":
                if not args:
                    self.write_output("[!] Usage: scan <target>\n", "#ff4444")
                    return
                self.modules["recon"].execute(args, self.write_output)

            elif command == "dirs":
                if not args:
                    self.write_output("[!] Usage: dirs <target>\n", "#ff4444")
                    return
                self.modules["dirs"].execute(args, self.write_output)

            elif command == "passwords":
                if not args:
                    self.write_output("[!] Usage: passwords <svc://target>\n", "#ff4444")
                    return
                self.modules["passwords"].execute(args, self.write_output)

            elif command == "portscan":
                if not args:
                    self.write_output("[!] Usage: portscan <target>\n", "#ff4444")
                    return
                self.modules["portscan"].execute(args, self.write_output)

            elif command == "vulnscan":
                if not args:
                    self.write_output("[!] Usage: vulnscan <target>\n", "#ff4444")
                    return
                self.modules["vulnscan"].execute(args, self.write_output)

            elif command == "ask":
                if not args:
                    self.write_output("[!] Usage: ask <question>\n", "#ff4444")
                    return
                self._ask_gemini(args)

            else:
                self._natural_language_command(cmd)

        except Exception as e:
            self.write_output(f"[ERROR] {e}\n", "#ff4444")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def _show_both_ips(self):
        self.write_output("[*] Checking public IP...\n", "#58a6ff")
        real = self.terminal.tor._get_real_ip()
        self.write_output(f"  Real IP   : {real}\n", "#ff4444")
        if self.terminal.anonymity_enabled:
            self.terminal.tor._show_ip(label="Tor Exit IP")
        else:
            self.write_output("  Tor       : not enabled\n", "#888888")

    def _ask_gemini(self, question):
        self.write_output("[*] Asking Gemini AI...\n", "#58a6ff")
        response = self.engine.ask(question)
        self.write_output(f"\n{response}\n\n", "#00d4ff")

    def _natural_language_command(self, cmd):
        self.write_output("[*] Interpreting with Gemini AI...\n", "#58a6ff")
        interp = self.engine.interpret_command(cmd)
        self.write_output(f"[AI] {interp['explanation']}\n", "#00d4ff")

        if interp.get("action") and interp.get("target"):
            action, target = interp["action"], interp["target"]
            if action in self.modules:
                self.write_output(f"[*] Executing: {action} → {target}\n", "#ffaa00")
                self.modules[action].execute(target, self.write_output)
            elif action == "shell" and interp.get("shell_cmd"):
                self.terminal.run(interp["shell_cmd"])
            else:
                if interp.get("shell_cmd"):
                    self.terminal.run(interp["shell_cmd"])
        else:
            self.write_output("[*] Could not map to an action. Try 'help'.\n", "#888888")


def main():
    root = tk.Tk()
    root.withdraw()

    dialog = APIKeyDialog(root)
    root.wait_window(dialog.dialog)

    if dialog.api_key is None:
        sys.exit(0)

    root.deiconify()
    PentestTerminal(root, dialog.api_key)
    root.mainloop()


if __name__ == "__main__":
    main()