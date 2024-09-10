import os
import sys
import subprocess
import json
import argparse
import requests
import logging
import time
from datetime import datetime
from dateutil import tz
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv('.env')

parser = argparse.ArgumentParser(
    "Expired Password Report Notifier",
    "Notify the last user who edited items that have not been updated in the number of data passed into the script.",
)

parser.add_argument(
    "--age",
    action="store",
    dest="age",
    help="Define the max number of days since the last update of a password item. Default is 90 days.",
    type=str,
)

args = parser.parse_args()
max_age_days = args.age if args.age else 90

# Set up logging so we know if any notifications fail to send
logging.basicConfig(
    filename="expired_pw_report.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

start_time = time.time() # Record the time when the script starts

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
def getMyUUID():
    subprocess.run(["op signin"], shell=True, check=True)
    user_info = json.loads(
        subprocess.run(
            ["op whoami --format=json"], check=True, shell=True, capture_output=True
        ).stdout
    )

    print("\nLogged in as: ", user_info["email"])

    return user_info["email"], user_info["user_uuid"]

try:
    myUUID = getMyUUID()
except Exception as e:
    signOut()
    sys.exit(
        "Unable to get your UUID. Please ensure you are signed into 1Password and try again."
    )

# Get a list of vaults the logged-in user has access to
def getAllOwnerVaults():
    r = subprocess.run(
        ["op vault list --permission=manage_vault --format=json"],
        check=True,
        shell=True,
        capture_output=True,
    ).stdout

    vaultList = json.loads(r.decode('utf-8'))

    return vaultList

# Prompt the user to select a vault
def promptUser(options):
    print("\n----- YOUR VAULTS -----\n")
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option['name']}")

    choice = input("\nEnter a vault number: ")
    return int(choice) - 1

# Set the selected vault
vaultList = getAllOwnerVaults()
selectedIndex = promptUser(vaultList)
selectedVault = vaultList[selectedIndex]['id']
print("\nSelected vault: ", vaultList[selectedIndex]['name'])

# Retrieve all login items from the selected vault
def getPasswords(selectedVault):
    passwordList = subprocess.run(
        [f'op item list --categories Login --vault={selectedVault} --format=json'],
        check=True,
        shell=True,
        capture_output=True
    ).stdout

    passwordList = json.loads(passwordList.decode('utf-8'))

    parsedPasswords = []
    for password in passwordList:
        parsedPasswords.append({
            "id": password["id"],
            "title": password["title"], 
            "updatedAt": password["updated_at"],
            "age": int(getAge(password["updated_at"])),
            "last_edited_id": password["last_edited_by"],
            "last_edited_by": getLastEditedBy(password["last_edited_by"])
        })

    parsedPasswords = sorted(parsedPasswords, key=lambda x: x["age"], reverse=True)

    return parsedPasswords
 
# Get the email of the user who edited the password item
def getLastEditedBy(last_edited_id):
    user = subprocess.run(
        [f'op user get {last_edited_id} --format=json'],
        check=True,
        shell=True,
        capture_output=True
    ).stdout

    user = json.loads(user.decode('utf-8'))

    try:
        if user and user["state"] == "ACTIVE":
            return user["email"]
    except Exception as e:
        print("An error occurred: ", e)
        print("userList: ", user)
        return None

# Get the age of the password item
def getAge(updated_at):
    creation_date = datetime.fromisoformat(updated_at).replace(tzinfo=tz.tzlocal())
    current_date = datetime.now(tz=tz.tzlocal())
    age_days = (current_date - creation_date).days
    return age_days

# Check if the password item is expired
def isExpired(parsedPasswords, max_age_days):
    return parsedPasswords["age"] >= int(max_age_days)

# Notify the last_edited_by user via Slack
def notifySlack(password):
        
        global start_time

        elapsed_time = time.time() - start_time

        if elapsed_time < 6:
            time.sleep(6 - elapsed_time)

        slack_data = {
            "itemTitle": password["title"],
            "user_email": password["last_edited_by"]
        }

        response = requests.post(
            url=os.environ["SLACK_WEBHOOK_URL"],
            data=json.dumps(slack_data),
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            logging.error(f"Error: {response.text}. An error occurred while sending the message to Slack: {password}.")
            # print(f"An error occurred while sending the message to Slack for password: {password['title']}.\nError: {response.text}.")
        else:
            logging.info(f"Message successfully sent to Slack: {password}.")
            # print(f"Message successfully sent to Slack for password: {password['title']}.")
            time.sleep(1)
            return None
        
        start_time = time.time()

def main():
    try:
        checkCLIVersion()

        parsedPasswords = getPasswords(selectedVault)

        expired_pw_count = 0 # Counter for expired passwords
        for password in tqdm(parsedPasswords):
            if isExpired(password, max_age_days):
                notifySlack(password)
                expired_pw_count += 1
        
        print("\n🎉 Users have been notified about their expired passwords! 🎉")
        print(f"🔐 Total expired passwords: {expired_pw_count}\n")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        signOut()

main()


