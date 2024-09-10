import os
import sys
import subprocess
import csv
import json
import argparse
from datetime import datetime
from dateutil import tz

parser = argparse.ArgumentParser(
    "Expired Password Report Generator",
    "Generates a csv-like report listing all login item names that have not been updated in the number of data passed into the script.",
)

parser.add_argument(
    "--age",
    action="store",
    dest="age",
    help="Define the max number of days since the last update of a password item. Default is 90 days.",
    type=str,
)

args = parser.parse_args()

scriptPath = os.path.dirname(__file__)
outputPath = scriptPath  # Optionally choose an alternative output path here.
max_age_days = args.age if args.age else 90

# Sign out of the CLI
def signout():
    subprocess.run(["op signout"], shell=True, check=True)

# Check CLI version
def checkCLIVersion():
    r = subprocess.run(["op", "--version", "--format=json"], capture_output=True)
    major, minor = r.stdout.decode("utf-8").rstrip().split(".", 2)[:2]
    if not major == 2 and not int(minor) >= 25:
        signout()
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
    signout()
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

    parsedPasswords = [
        {
            "id": password["id"],
            "title": password["title"], 
            "updatedAt": password["updated_at"],
            "age": int(getAge(password["updated_at"]))
        } 
        for password in passwordList
    ]

    parsedPasswords = sorted(parsedPasswords, key=lambda x: x["age"], reverse=True)

    return parsedPasswords
 
# Get the age of the password item
def getAge(updated_at):
    creation_date = datetime.fromisoformat(updated_at).replace(tzinfo=tz.tzlocal())
    current_date = datetime.now(tz=tz.tzlocal())
    age_days = (current_date - creation_date).days
    return age_days

# Check if the password item is expired
def isExpired(parsedPasswords, max_age_days):
    return parsedPasswords["age"] >= int(max_age_days)

def main():
    checkCLIVersion()

    # Generate the CSV report
    with open(f"{outputPath}/expired-items.csv", "w", newline="") as outputFile:
        parsedPasswords = getPasswords(selectedVault)
        csvWriter = csv.writer(outputFile)
        fields = [
            "itemID",
            "itemName",
            "itemUpdatedAt",
            "itemAge"
        ]
        csvWriter.writerow(fields)

        expired_pw_count = 0 # Counter for expired passwords
        for password in parsedPasswords:
            if isExpired(password, max_age_days):
                csvWriter.writerow(
                    [
                        password["id"],
                        password["title"],
                        password["updatedAt"],
                        password["age"]
                    ]
                )
                expired_pw_count += 1
        
        print("\n🎉 Expired passwords report generated successfully 🎉")
        print("Total expired passwords: ", expired_pw_count, "\n")
        signout()

main()
