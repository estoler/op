#!/usr/bin/python3
import argparse
import concurrent.futures
import json
import logging
import os
import subprocess
import sys

########
# ACTION REQUIRED: ADJUST THESE TO YOUR NEEDS
######

## If delegating the migration of vault data to multiple people
## optionally create a group with those users and grant the group
## elevated permissions to preserve the day-to-day permissions of other users and groups
specialGroup = "migration_admins"

# Use the name associated with the source (outgoing) account
sourceAccount = "KnoxIT"

# Use the name associated with the destination account
destinationAccount = "KnoxIT-express"

# Configure script options
parser = argparse.ArgumentParser(
    "Grant or revoke migration_admins group full access to all vaults in both source and destination accounts",
    "This script will grant or revoke the migration_admins' access to all shared vaults in the account for the purposes of facilitatin the migration of vault items from the source to destination account.",
    "Use the --grant or --revoke permission to determine the action taken by the script.",
)


parser.add_argument(
    "--grant",
    action="store_true",
    dest="grantPermissions",
    help="Use this flag to grant the 'migration_admins' group full vault permissions in both source and destination accounts",
    required=False,
)

parser.add_argument(
    "--revoke",
    action="store_true",
    dest="revokePermissions",
    help="Use this flag to revoke the 'migration_admins' group's permissions in both source and destination accounts",
    required=False,
)
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
    if not args.grantPermissions and not args.revokePermissions:
        sys.exit(
            "Unable to run script. Please pass either the --grant or --revoke flags when running the script."
        )
    checkCLIVersion
    myUUIDSource = getMyUUID(sourceAccount)
    myUUIDDest = getMyUUID(destinationAccount)
    if (
        args.grantPermissions or args.revokePermissions
    ):  # TODO why does this conditional exist?
        sourceVaultList = getVaultList(sourceAccount)
        destinationVaultList = getVaultList(destinationAccount)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            futures.append(
                executor.submit(processVaults, sourceVaultList, sourceAccount)
            )
            futures.append(
                executor.submit(processVaults, destinationVaultList, destinationAccount)
            )

            for future in concurrent.futures.as_completed(futures):
                if future.exception():
                    logger.error(
                        f"There was an error processing some permission changes: {future.exception()}"
                    )


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


def processVaults(vaults, account):
    for vault in vaults:
        if (
            "Private Vault" in vault["name"]
            or "Employee Vault" in vault["name"]
            or vault["name"] == "Private"
            or vault["name"] == "Employee"
        ):
            logger.info(f"Skipping Employee vault")
            continue

        if "Imported Shared Folders Metadata" in vault["name"]:
            logger.info(f"Skipping LastPass Import Metadata vault")
            continue

        addRemoveFullPermissions(vault, account, "", specialGroup)


def addRemoveFullPermissions(vault, account, userID="", groupID=""):
    ownerPermissions = "view_items,create_items,edit_items,archive_items,delete_items,view_and_copy_passwords,view_item_history,import_items,export_items,copy_and_share_items,print_items,manage_vault"
    logger.info(
        f"Updating permissions on vault '{vault['name']}' | {vault['id']} in account '{account}'"
    )

    target = "group"
    id = groupID

    # If user info is passed instead of group info
    if groupID == "":
        target = "user"
        id = userID

    action = "grant"
    if args.revokePermissions:
        action = "revoke"

    results = subprocess.run(
        [
            "op",
            "vault",
            target,
            action,
            f"--vault={vault['id']}",
            f"--{target}={id}",
            f"--permissions={ownerPermissions}",
            f"--account={account}",
            "--no-input",
        ],
        capture_output=True,
    )
    if results.returncode != 0:
        logger.error(
            f"Unable to set your permissions on '{vault['name']}' | {vault['id']} in account '{account}'. Error: {results.stderr.decode('utf-8')}"
        )
    logger.info(
        f"Completed updating your permissions on vault with '{vault['name']}' | {vault['id']} in account '{account}'"
    )


if __name__ == "__main__":
    main()
