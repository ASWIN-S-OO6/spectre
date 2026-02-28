#!/usr/bin/env python3
import asyncio
import os
import subprocess
import shlex
import typing
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Kali Linux Attack Server")

def _run_cmd(cmd_list: list) -> str:
    """Helper to run a shell command safely"""
    try:
        result = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\n[ERROR] Return Code {result.returncode}: {result.stderr.strip()}"
        return output
    except Exception as e:
        return f"[EXCEPTION] {e}"

@mcp.tool()
def run_kali_tool(command: str, args: str = "") -> str:
    """Execute arbitrary Kali Linux tools (e.g. nmap, sqlmap) safely.
    
    Args:
        command: The base command to run (e.g., "nmap")
        args: The arguments string (e.g., "-sC -sV 192.168.1.1")
    """
    cmd_list = [command]
    if args:
        cmd_list.extend(shlex.split(args))
        
    # Basic security check - prevent chaining multiple commands
    if any(c in "".join(cmd_list) for c in [";", "|", "&", ">", "<"]):
        return "[ERROR] Command chaining or redirection is blocked for security."
        
    return _run_cmd(cmd_list)

@mcp.tool()
def install_package(package_name: str) -> str:
    """Install missing Kali tools dynamically via apt-get.
    
    Args:
        package_name: The name of the apt package to install.
    """
    cmd_list = ["sudo", "apt-get", "install", "-y", package_name]
    output = _run_cmd(cmd_list)
    if "E: Unable to locate package" in output:
        return f"Package '{package_name}' not found."
    return output

@mcp.tool()
def reverse_engineer_binary(file_path: str) -> str:
    """Perform preliminary reverse engineering on a binary file using radare2.
    
    Args:
        file_path: Absolute path to the binary file to analyze.
    """
    if not os.path.exists(file_path):
        return f"[ERROR] File '{file_path}' does not exist."
        
    # Example RE using radare2 (rabin2 for info)
    info_cmd = ["rabin2", "-I", file_path]
    strings_cmd = ["rabin2", "-zzq", file_path] # Get limited strings
    
    info_out = _run_cmd(info_cmd)
    
    # Run a quick automated analysis
    r2_cmd = ["r2", "-qc", "aaa; afl | head -n 20", file_path]
    r2_out = _run_cmd(r2_cmd)
    
    return f"--- Binary Info ---\n{info_out}\n\n--- Top Functions ---\n{r2_out}"

@mcp.tool()
def directory_bruteforce(target_url: str, wordlist_path: str = "/usr/share/wordlists/dirb/common.txt") -> str:
    """Run gobuster to find hidden directories.
    
    Args:
        target_url: The full URL to attack (e.g. http://10.10.10.10)
        wordlist_path: Absolute path to wordlist
    """
    cmd_list = [
        "gobuster", "dir", "-u", target_url, "-w", wordlist_path,
        "-t", "20", "-q", "-z", "--no-color"
    ]
    return _run_cmd(cmd_list)

if __name__ == "__main__":
    print("Kali Linux FastMCP Server running on stdio")
    mcp.run()
