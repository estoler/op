import json
import subprocess

def createGroup(groups):
    for g in groups:
        subprocess.run(
            [f"op group create {g["name"]} "],
            check=True,
            shell=True,
            capture_output=True
        ).stdout

        print(f"Created group: {g["name"]}")
        
