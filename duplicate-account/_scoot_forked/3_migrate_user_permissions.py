#!/usr/bin/python3
import argparse
from ast import List
import csv
import json
import logging
import os
import pickle
import subprocess
import sys
from typing import Tuple

########
# ACTION REQUIRED: ADJUST THESE TO YOUR NEEDS
######

# Use the name associated with the source (outgoing) account
sourceAccount = "KnoxIT"

# Use the name associated with the destination account
destinationAccount = "KnoxIT-express"

# Configure script options
parser = argparse.ArgumentParser(
    "Migrate user and optionally group permissions from source to detination accounts",
    "This script will read the vaultPermissions.pickle file in the script directory and apply vault permissions from the source account stored in that file to users in the destination account",
    "Optionally set the --groups option to apply group permissions where groups of identical names exist in both and source and destination account.",
)

# Add arguments if desired.
parser.add_argument(
    "--groups",
    action="store_true",
    help="Attempt to apply group permissions in addition to individual vault permissions when groups of the same name exist in both source and destination accounts.",
    required=False,
)

# parser.add_argument(
#     "--file",
#     action="store",
#     dest="filepath",
#     help="Specify the path to the csv file.",
#     required=True,
# )

# args.groups |
args = parser.parse_args()

# Configure paths
scriptPath = os.path.dirname(__file__)
outputPath = scriptPath  # Change this path if desired.

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logFileHandler = logging.FileHandler(filename=f"{scriptPath}/scriptLog.log")
logStreamHandler = logging.StreamHandler()
logFormatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(funcName)s: %(message)s"
)
logStreamHandler.setFormatter(logFormatter)
logFileHandler.setFormatter(logFormatter)
logger.addHandler(logFileHandler)
logger.addHandler(logStreamHandler)


def main():
    checkCLIVersion()
    if not args.groups:
        logger.info(
            "Permission Migration Script started with no options. Will attempt to assign individual permissions to vaults in the destination account."
        )
    if args.groups:
        logger.info(
            "Permission Migration Script started with the --groups option. Will attemp to assign both individual and group permissions to vaults in the destination account."
        )
    # The script operators 1Password user UUIDs
    myUUIDSource = getMyUUID(sourceAccount)
    myUUIDDest = getMyUUID(destinationAccount)

    # Get the list of vaults from the destination account so the script can
    destinationVaults = getVaultList(destinationAccount)

    # Get email mapping data
    global emailMapping
    emailMapping = readEmailMapCsv()

    # Read input file to obtain vault details from source account
    sourceVaultPermissionData = readPickle()

    for sourceVault in sourceVaultPermissionData:

        # Get required source vault data
        sourceVaultID = sourceVault["sourceVaultID"]
        sourceVaultName = sourceVault["sourceVaultName"]
        sourceVaultUsers = sourceVault["vaultUsers"]
        sourceVaultGroups = sourceVault["vaultGroups"]

        # Identify destinationVault and matches current sourceVault
        destinationVault = next(
            (vault for vault in destinationVaults if vault["name"] == sourceVaultName),
            None,
        )

        # Grant permissions on destination vaults to the users and optionally to groups
        grantVaultPermissions(destinationVault, sourceVaultUsers, sourceVaultGroups)


# Check CLI version to make sure things go smoothly
def checkCLIVersion():
    r = subprocess.run(["op", "--version", "--format=json"], capture_output=True)
    major, minor = r.stdout.decode("utf-8").rstrip().split(".", 2)[:2]
    if not major == 2 and not int(minor) >= 25:
        logger.error(
            "❌ You must be using version 2.25 or greater of the 1Password CLI. Please visit https://developer.1password.com/docs/cli/get-started to download the lastest version."
        )
        sys.exit(
            "❌ You must be using version 2.25 or greater of the 1Password CLI. Please visit https://developer.1password.com/docs/cli/get-started to download the lastest version."
        )


# Get the operator's UUID if required, and also force `op` to sign in if not already signed in.
def getMyUUID(account=""):
    logger.info("Ensuring you're signed into 1Password and obtaining your User ID.\n")

    # Sign into specified account
    logger.info(f"Signing into your account {account}")
    signinCmd = subprocess.run(
        ["op", "signin", f"--account={account}"], capture_output=True
    )
    if signinCmd.returncode != 0:
        logger.critical(f"Unable to sign in. Error: {signinCmd.stderr.decode('utf-8')}")
        sys.exit(f"🔴 Unable to sign in. Error: {r.stderr.decode('utf-8')}")
    logger.info(f"Signed in to account {account}")
    # Get User UUID for the account
    logger.info("Getting your UUID")
    r = subprocess.run(
        ["op", "whoami", f"--account={account}", "--format=json"], capture_output=True
    )
    if r.returncode != 0:
        logger.critical(
            f"🔴 Unable to get your user UUID in. Error: {r.stderr.decode('utf-8')}"
        )
        sys.exit(
            f"🔴 Unable to get your user UUID. Make sure you are are signed into the 1Password CLI. Error: {r.stderr.decode('utf-8')}"
        )

    logger.info(f"Obtained your User ID: {json.loads(r.stdout)['user_uuid']} \n")
    return json.loads(r.stdout)["user_uuid"]


# Read the python binary data stored in the script path.
def readPickle():
    logger.info(f"Read input file called {outputPath}/vaultPermissions.pickle")
    if os.path.exists(f"{outputPath}/vaultPermissions.pickle"):
        logger.info("Pickle located")
        with open(f"{outputPath}/vaultPermissions.pickle", "rb") as permissionsPickle:
            permissionData = pickle.load(permissionsPickle)
            return permissionData
    else:
        logger.error(
            "Unable to locate pickle containing vault permission data. Ensure the vaultPermissions.pickle file is in the same directory as this script. If you do not have a vaultPermissions.pickle file, re-run script 1 with the --permissions flag to generate a new permissions report and pickle file."
        )
        return None


# Read CSV from specified path. CSV should contain mappings between old emails and new emails for all users.
# oldEmail,newEmail
# Returns a list of tuples [(oldEmail, newEmail)]
def readEmailMapCsv():
    emailMap = []
    with open(
        f"{scriptPath}/emailmap.csv", "r", newline="", encoding="utf-8"
    ) as inputFile:
        csvReader = csv.reader(inputFile, skipinitialspace=True)
        next(csvReader)
        for oldEmail, newEmail in csvReader:
            emailMap.append((oldEmail, newEmail))
    return emailMap


# Look for a row in the email mapping list matching the user's source
# email and return source and destination emails.
# defaults to source email if no mapping is found
def findEmailMapping(sourceUser) -> Tuple[str, str]:
    logger.info(
        f"Looking for matching email address in email mapping file for old address {sourceUser['email']}"
    )
    return next(
        (
            emailPair
            for emailPair in emailMapping
            if emailPair[0] == sourceUser["email"]
        ),
        (sourceUser["email"], sourceUser["email"]),
    )


# Obtain a list of vaults in destination account so we have vault name and UUID mappings.
def getVaultList(account=""):

    logger.info(f"Getting a list of vaults and their details. This may take a moment.")
    try:
        getVaultsCommand = subprocess.run(
            [
                "op",
                "vault",
                "list",
                "--permission=manage_vault",
                f"--account={account}",
                "--format=json",
            ],
            check=True,
            capture_output=True,
        )
        logger.info("Obtained a list of vaults.")
        return json.loads(getVaultsCommand.stdout)
    except Exception as err:
        logger.error(
            f"Encountered an error getting the list of vaults you have access to: {err}"
        )

        return


# Grant the user permissions in the destination account based on source account
def grantVaultPermissions(destinationVault, sourceVaultUsers, sourceVaultGroups):
    logger.info(
        f"Updating permissions on vault '{destinationVault['name']}' | {destinationVault['id']} in destination account"
    )

    for sourceUser in sourceVaultUsers:
        userSourceEmail, userDestinationEmail = findEmailMapping(sourceUser)
        if userSourceEmail == userDestinationEmail:
            logger.info(
                f"No email mapping found for {sourceUser['email']}. Defaulting to {sourceUser['email']}"
            )
        else:
            logger.info(
                f"Mapping {userSourceEmail} in source account to {userDestinationEmail} in destination account."
            )
        userPermissions: List = sourceUser["permissions"]
        userPermissionsString = ",".join(userPermissions)
        logger.info(
            f"Granting '{sourceUser['name']}' the following permissions on vault {destinationVault['name']}: {userPermissionsString}"
        )
        # Migrate user permissions using the destinaion email address from the mapping file
        results = subprocess.run(
            [
                "op",
                "vault",
                "user",
                "grant",
                f"--vault={destinationVault['id']}",
                f"--user={userDestinationEmail}",
                f"--permissions={userPermissionsString}",
                f"--account={destinationAccount}",
                "--no-input",
            ],
            capture_output=True,
        )
        if results.returncode != 0:
            logger.error(
                f"Unable to set your permissions on '{destinationVault['name']}' | {destinationVault['id']} in destination account. Error: {results.stderr.decode('utf-8')}"
            )
        logger.info(
            f"Completed updating your permissions on vault with '{destinationVault['name']}' | {destinationVault['id']} in destination account. {results.stdout.decode('utf-8')}"
        )

    # If the --groups flag was set when running the script, attempt to migrate group permissions
    if args.groups:

        for group in sourceVaultGroups:

            groupName = group["name"]
            groupPermissions: List = group["permissions"]
            groupPermissionsString = ",".join(groupPermissions)
            logger.info(
                f"Granting {group['name']} the following permissions on vault {destinationVault['name']}: '{groupPermissionsString}"
            )

            # Migrate group permissions
            results = subprocess.run(
                [
                    "op",
                    "vault",
                    "group",
                    "grant",
                    f"--vault={destinationVault['id']}",
                    f"--group={groupName}",
                    f"--permissions={groupPermissionsString}",
                    f"--account={destinationAccount}",
                    "--no-input",
                ],
                capture_output=True,
            )
            if results.returncode != 0:
                logger.error(
                    f"Unable to set your permissions on '{destinationVault['name']}' | {destinationVault['id']} in destination account. Error: {results.stderr.decode('utf-8')}"
                )
            logger.info(
                f"Completed updating your permissions on vault with '{destinationVault['name']}' | {destinationVault['id']} in destination account. {results.stdout.decode('utf-8')}"
            )


if __name__ == "__main__":
    main()
