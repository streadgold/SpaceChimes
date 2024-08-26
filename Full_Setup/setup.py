#!/usr/bin/python3
import os
import distro
import sys
import subprocess
import argparse
import shutil
from pathlib import Path

# ANSI escape codes for some colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'
RESET = '\033[0m'  # Reset color to default

# Get the user's home directory
home_dir = Path.home()

# Get the current working directory
current_dir = Path.cwd()

print(f"{CYAN}--------Installing Space Chimes Libraries--------{RESET}")

def run_command(cmd):
    print("{}".format(cmd))
    print((subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)).decode("utf-8"))

def run_install(packages, method):
    if method == "sudo apt-get":
        method = "sudo apt-get -y"
        install_string = "{} install {}".format(method, packages)
        run_command(install_string)
    else:
        install_string = "{} install {} --break-system-packages".format(method, packages)
        try:
            run_command(install_string)
        except Exception as e:
            install_string = "{} install {}".format(method, packages)
            run_command(install_string)

def main():
    run_command("sudo apt-get update")
    run_command("sudo apt-get -y upgrade")
    run_command("sudo apt-get -y autoremove")
    run_install("python3-skyfield", "sudo apt-get") #required for nightshade
    run_install("python3-geopy", "sudo apt-get") #required for nightshade
    run_install("python3-pyaudio", "sudo apt-get") #pandas is used for correlating the NASA VV page with wiki

    print(f"{GREEN}Rename credentials_template.py to credentials.py")
    print(f"{GREEN}Insert your username and password for Space-Track.org into the credentials.py file")
    print(f"{RED}Don't upload credentials to github")

if __name__ == '__main__':
    main()
