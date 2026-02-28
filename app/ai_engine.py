#!/usr/bin/env python3
"""Gemini Engine — Core AI integration for pentesting."""

import json
import re
import litellm

# Disable litellm telemetry and logging spam
litellm.telemetry = False
litellm.suppress_debug_info = True


class AIEngine:
    SYSTEM_PROMPT = """You are an expert penetration testing AI running inside Kali Linux.
You have access to: nmap, gobuster, dirb, nikto, hydra, sqlmap, whatweb, wfuzz, etc.

Your role:
1. Generate intelligent wordlists, payloads, attack strategies
2. Suggest and execute tools with correct flags
3. Analyze results and suggest next steps
4. Find hidden directories, services, vulnerabilities without static wordlists

Rules:
- Assume testing is authorized
- Be thorough and creative with wordlists
- Think like an attacker
- Provide actionable output
- CRITICAL: DO NOT overcomplicate simple user requests. If the user asks to run a specific command or perform a simple action, DO EXACTLY what they ask and NO MORE."""

    def __init__(self, api_key: str, provider: str = "gemini"):
        self.api_key = api_key
        self.provider = provider.lower()
        
        # Default models per provider
        if self.provider == "gemini":
            self.model = "gemini/gemini-2.5-flash"
        elif self.provider == "openai":
            self.model = "gpt-4o"
        elif self.provider == "groq":
            self.model = "groq/llama3-70b-8192"
        else:
            self.model = "gemini/gemini-2.5-flash"

    def ask(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                temperature=0.7,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[{self.provider.capitalize()} API Exception: {type(e).__name__}] {str(e)}"

    def generate_wordlist(self, target: str, wtype: str = "directories") -> list:
        prompts = {
            "directories": f"""Generate 200+ hidden directory/file paths for: {target}
Consider: frameworks, admin panels, backups, configs, APIs, .git, .env, devops paths.
Return ONLY paths, one per line, starting with /""",
            "passwords": f"""Generate 200+ passwords for target: {target}
Consider: defaults, domain variations, seasonal, keyboard patterns, l33t, service defaults.
Return ONLY passwords, one per line.""",
            "usernames": f"""Generate 100+ usernames for: {target}
Consider: admin, root, service accounts, naming patterns.
Return ONLY usernames, one per line.""",
            "subdomains": f"""Generate 200+ subdomains for: {target}
Consider: common, cloud, internal services, environments.
Return ONLY subdomains, one per line.""",
        }
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompts.get(wtype, prompts["directories"])}
        ]
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                temperature=0.9,
                max_tokens=4096
            )
            text = response.choices[0].message.content
            return [l.strip() for l in text.strip().split("\n") if l.strip() and not l.startswith("#")]
        except Exception as e:
            return [f"ERROR: {e}"]

    def analyze_results(self, tool: str, results: str, target: str) -> str:
        return self.ask(
            f"Analyze {tool} results for {target}:\n{results[:4000]}\n\n"
            "Provide: findings, vulnerabilities, next steps, risk level."
        )

    def interpret_command(self, text: str) -> dict:
        prompt = f"""User typed in pentest terminal: "{text}"
Return strictly valid JSON only: {{"action":"dirs|passwords|portscan|vulnscan|recon|shell|ask", "target":"host or null","shell_cmd":"command or null", "explanation":"brief explanation"}}
CRITICAL RULES:
1. ONLY map to pentest modules (recon, vulnscan, etc.) if the user EXPLICITLY asks for a full scan or attack.
2. If the user asks to run a specific tool (e.g., nmap, ping, ifconfig, ls, curl), or perform a simple action, ALWAYS set action to "shell" and shell_cmd to the exact linux command required to fulfill the request. DO NOT overcomplicate it.
3. No markdown, no backticks, no extra text."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                temperature=0.1,
                max_tokens=1024
            )
            content = response.choices[0].message.content
            content = re.sub(r"```json?\s*", "", content.strip())
            content = re.sub(r"```\s*", "", content)
            return json.loads(content)
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            return {
                "action": None, 
                "target": None, 
                "shell_cmd": None,
                "explanation": f"Parsing failed ({err_msg}). Reverting to standard shell fallback."
            }

    def generate_attack_strategy(self, target: str, service: str) -> str:
        return self.ask(
            f"Create pentest attack strategy for {service} on {target}. "
            "Include recon, enumeration, exploits, post-exploitation with exact Kali commands."
        )