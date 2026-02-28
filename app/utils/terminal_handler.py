#!/usr/bin/env python3
"""Terminal Handler — Uses tornet for IP rotation and global proxychains."""

import subprocess
import threading
import os
import time
import shlex
import json
from datetime import datetime
from pathlib import Path

try:
    import tornet
except ImportError:
    tornet = None


class TerminalHandler:
    def __init__(self, output_fn=None, emit_fn=None, terminal_id=None):
        self.out = output_fn or print
        self.emit = emit_fn
        self.terminal_id = terminal_id
        self.anonymity_enabled = False
        self.procs = {}
        self.log = []
        self._log_dir = Path("/opt/ai-pentester/reports/sessions")
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        self._auto_rotate_thread = None
        self._stop_rotate_event = threading.Event()

    def enable_anonymity(self, auto_rotate_interval=60):
        if tornet is None:
            self.out("[ANON] ✗ 'tornet' package is not installed.\r\n", "#ff4444")
            return
            
        self.out("\r\n[ANON] ═══ Enabling Tor Anonymity via TorNet ═══\r\n", "#ff79c6")
        try:
            # We initialize locally, which spins up tor
            tornet.initialize_environment()
            
            # Retry loop for Tor circuit establishment (can be slow)
            max_retries = 5
            ip = None
            
            for attempt in range(max_retries):
                self.out(f"[ANON] Attaching to Tor circuit (Attempt {attempt + 1}/{max_retries})... \r\n", "#8be9fd", terminal_id=self.terminal_id)
                time.sleep(3)
                ip = tornet.get_current_ip()
                if ip:
                    break
            
            if ip:
                self.anonymity_enabled = True
                self.out(f"[ANON] ✓ Tor active. Exit IP: {ip}\r\n", "#00ff41", terminal_id=self.terminal_id)
                if self.emit:
                    self.emit("tor_ip_update", {"ip": ip, "status": "On (Shared)"})

                if auto_rotate_interval > 0:
                    self._start_auto_rotate(auto_rotate_interval)
            else:
                self.out("[ANON] ✗ TorNet timed out fetching IP. Please click again.\r\n", "#ff4444", terminal_id=self.terminal_id)
        except Exception as e:
            self.out(f"[ANON] ✗ TorNet error: {e}\r\n", "#ff4444", terminal_id=self.terminal_id)

    def _start_auto_rotate(self, interval):
        self.stop_auto_rotate()
        self._stop_rotate_event.clear()
        
        def loop():
            while not self._stop_rotate_event.is_set():
                if self._stop_rotate_event.wait(interval):
                    break
                try:
                    new_ip = tornet.change_ip()
                    if new_ip and self.emit:
                        # We don't print to terminal to avoid spam
                        self.emit("tor_ip_update", {"ip": new_ip, "status": "On (Rotating)"})
                except Exception:
                    pass
                    
        self._auto_rotate_thread = threading.Thread(target=loop, daemon=True)
        self._auto_rotate_thread.start()

    def stop_auto_rotate(self):
        self._stop_rotate_event.set()
        if self._auto_rotate_thread:
            self._auto_rotate_thread.join(timeout=2)
            self._auto_rotate_thread = None

    def disable_anonymity(self):
        self.stop_auto_rotate()
        if tornet:
            tornet.stop_services()
        self.anonymity_enabled = False
        self.out("[ANON] ✓ Direct connection restored\r\n", "#ffaa00")
        if self.emit:
            self.emit("tor_ip_update", {"ip": "Direct", "status": "Off"})

    def run(self, command, timeout=300, use_tor=None, label="", terminal_id=None):
        if use_tor is None: 
            use_tor = self.anonymity_enabled
            
        target_tid = terminal_id or self.terminal_id
        parts = shlex.split(command) if isinstance(command, str) else list(command)
        if use_tor: 
            parts = ["proxychains4", "-q"] + parts
            
        tag = label or parts[0]
        self.out(f"[RUN] {' '.join(parts)}\r\n", "#888888", terminal_id=target_tid)
        t0 = time.time()
        try:
            proc = subprocess.Popen(parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, bufsize=1)
            self.procs[tag] = proc
            stdout, stderr = [], []
            def rd(s,b,c):
                for l in iter(s.readline, ""): b.append(l); self.out(f"  {l}", c, terminal_id=target_tid)
                s.close()
            t1=threading.Thread(target=rd,args=(proc.stdout,stdout,"#c9d1d9"))
            t2=threading.Thread(target=rd,args=(proc.stderr,stderr,"#ffaa00"))
            t1.start(); t2.start()
            proc.wait(timeout=timeout)
            t1.join(5); t2.join(5)
            self.procs.pop(tag, None)
            r = {"stdout":"".join(stdout),"stderr":"".join(stderr),"returncode":proc.returncode}
            self.log.append({"ts":datetime.now().isoformat(),"cmd":" ".join(parts),
                             "tor":use_tor,"rc":r["returncode"],"dur":round(time.time()-t0,2)})
            return r
        except subprocess.TimeoutExpired:
            self.out(f"[!] Timed out ({timeout}s)\r\n","#ff4444", terminal_id=target_tid)
            return {"stdout":"","stderr":"timeout","returncode":-1}
        except FileNotFoundError:
            self.out(f"[!] Not found: {parts[0]}\r\n","#ff4444", terminal_id=target_tid)
            return {"stdout":"","stderr":"not found","returncode":-2}
        except Exception as e:
            self.out(f"[!] {e}\r\n","#ff4444", terminal_id=target_tid)
            return {"stdout":"","stderr":str(e),"returncode":-3}

    def kill_all(self):
        for t,p in list(self.procs.items()):
            p.kill(); self.out(f"[KILL] {t}\r\n","#ff4444")

    def save_session_log(self):
        p = self._log_dir / f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(p,"w") as f: json.dump(self.log, f, indent=2)
        self.out(f"[LOG] Saved → {p}\r\n", "#00ff41")