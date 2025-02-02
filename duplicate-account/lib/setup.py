import os
import sys
import json
import subprocess

# Sign out of the CLI
def signOut():
    subprocess.run(["op signout"], shell=True, check=True)

# Check CLI version
def checkCLIVersion():
    r = subprocess.run(["op --version --format=json"], shell=True, capture_output=True)
    major, minor = r.stdout.decode("utf-8").rstrip().split(".", 2)[:2]
    if not major == 2 and not int(minor) >= 25:
        signOut()
        sys.exit(
            "❌ You must be using version 2.25 or greater of the 1Password CLI. Please visit https://developer.1password.com/docs/cli/get-started to download the lastest version."
        )

# Get the UUID of the user running the CLI script for use elsewhere in the script.

def getCredDetails():

    account = json.loads(
            subprocess.run(
            ["op account get --format=json"],
            check=True,
            shell=True,
            capture_output=True
        ).stdout
    )

    if account and account["type"] == "BUSINESS" and account["state"] == "ACTIVE":
        print(
                f"\nConnected to account: ",
                account["name"]
                # f"({account["id"]})"
        )
    
    else:
        print("Not an active business account")
    
    user = json.loads(
        subprocess.run(
            ["op user get --me --format=json"], 
            check=True, 
            shell=True, 
            capture_output=True
        ).stdout
    )

    if not user["type"] == "SERVICE_ACCOUNT" and user["state"] == "ACTIVE":
        print("Not signed in with an active Service Account")
        # signOut()
        # print(user)
    
    else:
        print("Logged in as: ", user["name"])

# Prompt the user to accept terms before continuing

def acceptTerms():
    print("\nPlease accept the terms before continuing...\n")

    choice = input("Confirm by typing 'Y': ")

    if choice != "Y":
        signOut()
        sys.exit(
            "\n👋 You didn't agree so we can't continue! Exiting the script now.\n"
        )

def setEnv(env):
    
    if env == "src":
        try:
            token = os.environ["SVC_SOURCE"]

        except:
            token = input(
                "\nCreate a service account token in the SOURCE account with Read access to vaults that should be migrated"
                "\nPlease enter the service account key for the SOURCE account: \n",
            )
        
    elif env == "dest":
        try:
            token = os.environ["SVC_DESTINATION"]

        except:
            token = input(
                "\nCreate a service account token in the DESTINATION account with Read access to vaults that should be migrated"
                "\nPlease enter the service account key for the DESTINATION account: \n",
            )

    os.environ["OP_SERVICE_ACCOUNT_TOKEN"] = token

def promptCheck():

    choice = input("\nDo these look correct? (y/n): ")

    if not choice == "y": 
        
        sys.exit("\nStart the script over and try again")