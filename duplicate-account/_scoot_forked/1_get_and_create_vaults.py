#!/usr/bin/python3
import argparse
import concurrent.futures
import csv
import json
import logging
import os
import pickle
import subprocess
import sys


########
# ACTION REQUIRED: ADJUST THESE TO YOUR NEEDS
######

# If delegating the migration of vault data to multiple people
# optionally create a group with those users and grant the group
# elevated permissions to preserve the day-to-day permissions of other users and groups

# Use the name associated with the source (outgoing) account
sourceAccount = "KnoxIT"

# Use the name associated with the destination account
destinationAccount = "KnoxIT-express"

# Configure script options
parser = argparse.ArgumentParser(
    "Recreate vaults from source account in destination account",
    "This script recreates the shared vaults from a source account in a destination account.",
)

# If set, attempts to migrate items between source and destination account
parser.add_argument(
    "--items",
    action="store_true",
    help="Make a best effort to migrating vault items.",
    required=False,
)

# Does not create vaults, just generates permission report.
parser.add_argument(
    "--permissions",
    action="store_true",
    help="Only generate the permissions report for the source account.",
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
    logger.info("Beginning script")
    checkCLIVersion()
    if args.permissions:
        logger.info(
            "Running script in Permission mode. This will only generate a report of vault permissions in the source account. No vaults will be created. "
        )
    if args.items:
        logger.info(
            "Running with Item Migration enabled, this will attempt to copy items from the source to destination account."
        )

    if not args.permissions and not args.items:
        logger.info(
            "Script running in standard mode. Vaults will be created in the destination account and a premissions report will be generated. Items will not be copied."
        )
    # The script operators 1Password user UUIDs
    myUUIDSource = getMyUUID(sourceAccount)
    myUUIDDest = getMyUUID(destinationAccount)

    sourceVaultList = getVaultList(sourceAccount)
    logger.info(f"There are {len(sourceVaultList)} vaults in source account.")

    # Create csv file and write header for permissions report
    with open(
        f"{outputPath}/vault_permissions_report.csv", "w", newline=""
    ) as outputFile:
        csvWriter = csv.writer(outputFile)
        fields = [
            "vaultName",
            "vaultUUID",
            "userName",
            "groupName",
            "email",
            "userOrGroupUUID",
            "permissions",
        ]
        csvWriter.writerow(fields)

    # Spawn two threads. Once to create the permissions report,
    # the other to create the vaults
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Write vault report
        # try:
        reportThread = executor.submit(writeVaultPermissionsReport, sourceVaultList)
        # except Exception as err:
        # logger.error("There was an error writing the vault permissions report.", err)
        # Create new vaults in destination account if report only flag not set.
        if not args.permissions:
            for sourceVault in sourceVaultList:
                if (
                    "Private Vault" in sourceVault["name"]
                    or "Employee Vault" in sourceVault["name"]
                    or sourceVault["name"] == "Private"
                    or sourceVault["name"] == "Employee"
                ):
                    logger.info(f"Skipping Employee vault")
                    continue

                if "Imported Shared Folders Metadata" in sourceVault["name"]:
                    logger.info(f"Skipping LastPass Import Metadata vault")
                    continue

                vaultCreationThread = executor.submit(
                    createVaultFrom, sourceVault, destinationAccount
                )
                newVault = json.loads(vaultCreationThread.result())

                # If not migrating items, revoke script-runner's access to newly-created vaults
                if not args.items:
                    setUserVaultPermissions(
                        newVault, myUUIDDest, "", destinationAccount
                    )

                # If --items flag passed, attempt to migrate items between accounts.
                if args.items:
                    # Get users' current permissions for the oldVault
                    userVaultPermissions = getUserVaultPermissions(
                        sourceVault["id"], myUUIDSource, sourceAccount
                    )
                    # Grant script runner full permissions on source vault to facilitate item move
                    grantOwnerPermissions(
                        sourceVault["id"], myUUIDSource, sourceAccount
                    )

                    # Attempt to copy items from source vault to destination vault.
                    copyVaultItemsToNewAccount(sourceVault, newVault)

                    # Set the user's permissions to the original value for the source vault
                    setUserVaultPermissions(
                        sourceVault, myUUIDSource, userVaultPermissions, sourceAccount
                    )

                    # Set the user's permissions to the newly-created vault to match those of the source vault
                    setUserVaultPermissions(
                        newVault, myUUIDDest, userVaultPermissions, destinationAccount
                    )
                if vaultCreationThread.exception():
                    logger.error(
                        "There was an error creating vaults in the destination account.",
                        vaultCreationThread.exception(),
                    )
        reportThread.exception()
    logger.info(f"Script completed.")


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


# Lists all of the non-employee vaults available to the signed-in 1Password user. Returns a json-like Python object
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


# Create a vault in the destination account based on a vault passed to the function
def createVaultFrom(sourceVault, account=""):
    logger.info(
        f"Creating vault with name {sourceVault['name']} in destination account"
    )
    r = subprocess.run(
        [
            "op",
            "vault",
            "create",
            sourceVault["name"],
            f"--account={account}",
            "--format=json",
        ],
        capture_output=True,
    )
    if r.returncode != 0:
        logger.error(
            f"There was an issue creating a vault with name {sourceVault['name']}, error: ",
            r.stderr.decode("utf-8"),
        )

    # Announce Vault created!
    logger.info(
        f"Created new vault called {json.loads(r.stdout)['name']} with UUID {json.loads(r.stdout)['id']}"
    )

    # Capture the json object represnring the newly-created vault
    return r.stdout


# Get the groups assigned to each vault along with their permissions. Returns json-formatted string.
# Returned value likely needs to be passed to json.loads()
def getGroupVaultAssignments(vault, account=""):
    logger.info(f"Getting groups assigned to vault {vault['name']} | {vault['id']}")
    r = subprocess.run(
        [
            "op",
            "vault",
            "group",
            "list",
            f"{vault['id']}",
            f"--account={account}",
            "--format=json",
        ],
        capture_output=True,
    )
    if r.returncode != 0:
        logger.error(
            f"Unable to get a list of groups with access to vault with UUID {vault['id']} and cannot record Owner's permissions. {r.stderr.decode('utf-8')}"
        )

    # a list of json objects representing groups and their permissions. For each element
    # in the list, access the name with group["name"] and permissions with group["permisisons"]
    logger.info(
        f"Obtained a list of groups assigned to the vault {vault['name']} | {vault['id']}"
    )
    for vaultGroup in json.loads(r.stdout):

        logger.info(
            f"Tracking that group {vaultGroup['name']} | {vaultGroup['id']} has the following permissions {vaultGroup['permissions']} on vault {vault['name']} | {vault['id']}"
        )
    return r.stdout


# Get the users assigned to each vault along with their permissions. Returns json-formatted string.
# Returned value likely needs to be passed to json.loads()
def getUserVaultAssignments(vault, account=""):
    logger.info(f"Getting users assigned to vault {vault['name']} | {vault['id']}")
    r = subprocess.run(
        [
            "op",
            "vault",
            "user",
            "list",
            f"{vault['id']}",
            f"--account={account}",
            "--format=json",
        ],
        capture_output=True,
    )
    if r.returncode != 0:
        logger.error(
            f"Unable to get a list of groups with access to vault with UUID {vault['id']} and cannot record Owner's permissions. {r.stderr.decode('utf-8')}"
        )
        next

    # a list of json objects representing groups and their permissions. For each element
    # in the list, access the name with group["name"] and permissions with group["permisisons"]
    logger.info(
        f"Obtained a list of groups assigned to the vault {vault['name']} | {vault['id']}"
    )
    for vaultGroup in json.loads(r.stdout):

        logger.info(
            f"Tracking that group {vaultGroup['name']} | {vaultGroup['id']} has the following permissions {vaultGroup['permissions']} on vault {vault['name']} | {vault['id']}"
        )
    return r.stdout


# Get a specific user's permissions for a specific vault.
def getUserVaultPermissions(vaultID, userID, account):
    logger.info(f"Getting your permissions for vault with UUID {vaultID} in {account}")
    r = subprocess.run(
        [
            "op",
            "vault",
            "user",
            "list",
            f"{vaultID}",
            f"--account={account}",
            "--format=json",
        ],
        capture_output=True,
    )
    if r.returncode != 0:
        logger.error(
            f"Unable to get a list of groups with access to vault with UUID {vaultID} and cannot record Owner's permissions. {r.stderr.decode('utf-8')}"
        )

    jsonData = json.loads(r.stdout)
    # Extract the user object from the list of users returned
    userDetails = [user for user in jsonData if user["id"] == userID]
    # From the user object, get an `op`-friendly list of their current vault permissions
    if not userDetails:
        return ""
    userPermissions = ",".join(userDetails[0]["permissions"])
    logger.info(
        f"Obtained your permissions for vault with UUID {vaultID}: {userPermissions}"
    )
    return userPermissions


def writeVaultPermissionsReport(vaults):
    vaultPermissionsObject = []

    with open(
        f"{outputPath}/vault_permissions_report.csv", "a", newline=""
    ) as outputFile:
        csvWriter = csv.writer(outputFile)
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
            vaultUserList = json.loads(getUserVaultAssignments(vault, sourceAccount))
            vaultGroupList = json.loads(getGroupVaultAssignments(vault, sourceAccount))
            vaultPermissionsObject.append(
                {
                    "sourceVaultName": vault["name"],
                    "sourceVaultID": vault["id"],
                    "vaultUsers": vaultUserList,
                    "vaultGroups": vaultGroupList,
                }
            )
            # Write human-readable CSV
            for user in vaultUserList:
                csvWriter.writerow(
                    [
                        vault["name"],
                        vault["id"],
                        user["name"],
                        None,
                        user["email"],
                        user["id"],
                        user["permissions"],
                    ]
                )
                print(
                    vault["name"],
                    vault["id"],
                    user["name"],
                    user["email"],
                    user["id"],
                    user["permissions"],
                )
            for group in vaultGroupList:
                csvWriter.writerow(
                    [
                        vault["name"],
                        vault["id"],
                        None,
                        group["name"],
                        None,
                        group["id"],
                        group["permissions"],
                    ]
                )
                print(
                    vault["name"],
                    vault["id"],
                    group["name"],
                    group["id"],
                    group["permissions"],
                )
        logger.info(f"Completed writing report of empty vaults.")
    logger.info(f"Writing pickled permission data.")

    # Write pickle data to disk for permissions migration script
    with open(f"{outputPath}/vaultPermissions.pickle", "wb") as outputPickle:
        pickle.dump(vaultPermissionsObject, outputPickle, pickle.HIGHEST_PROTOCOL)


# Copy items from a vault in the source account to a vault of the same name
# and which must already exist in the destination account.
def copyVaultItemsToNewAccount(sourceVault, destVault):
    # Get a list of items from the source vault and pipe it to the next command

    logger.info(
        f"Copying items from vault {sourceVault['name']} | {sourceVault['id']} in source account {sourceAccount} to the destination vault with ID {destVault['id']} in account {destinationAccount}"
    )
    logger.info(
        f"Getting a list of items from source vault {sourceVault['name']} | {sourceVault['id']}"
    )
    listItemsCmd = subprocess.run(
        [
            "op",
            "item",
            "list",
            f"--vault={sourceVault['id']}",
            "--format=json",
            f"--account={sourceAccount}",
        ],
        stdout=subprocess.PIPE,
    )
    if listItemsCmd.returncode != 0:

        logger.error(
            f"There was an error getting the list of items from vault {sourceVault['name'] | sourceVault['id'] } {getItemsCmd.stderr.decode('utf-8')} \n{getItemsCmd}"
        )
    # using the results from listItemCmd above as input, get the items in the vault
    logger.info(
        f"Getting details of each item in vault {sourceVault['name']} | {sourceVault['id']}"
    )

    # Check if the vault is empty and return early.
    if len(json.loads(listItemsCmd.stdout)) == 0:

        logger.info(
            f"Vault {sourceVault['name']} | {sourceVault['id']} has zero items, continue to next vault."
        )
        return
    getItemsCmd = subprocess.run(
        ["op", "item", "get", "--format=json", f"--account={sourceAccount}"],
        input=listItemsCmd.stdout,
        stdout=subprocess.PIPE,
    )

    if getItemsCmd.returncode != 0:
        error = ""
        if getItemsCmd.stderr:
            error = getItemsCmd.stderr.decode("utf-8")
        logger.error(f"There was an error getting an item {error}: {getItemsCmd}")
    # From the list of items, create items in the destination account.
    logger.info(
        f"Creating items in destination vault {destVault['name']} | {destVault['id']} in {destinationAccount}"
    )

    createItems = subprocess.run(
        [
            "op",
            "item",
            "create",
            f"--vault={destVault['id']}",
            f"--account={destinationAccount}",
        ],
        input=getItemsCmd.stdout,
        capture_output=True,
    )

    if createItems.returncode != 0:
        logger.error(
            f"There was an issue duplicating an item, {createItems.stderr.decode('utf-8')}"
        )
    logger.info(
        f"Finished copying items in {sourceVault['name']} | {sourceVault['id']} in {sourceAccount} to {destVault['name']} | {destVault['id']} in {destinationAccount}"
    )


def grantOwnerPermissions(vaultID, userID, account):
    ownerPermissions = "view_items,create_items,edit_items,archive_items,delete_items,view_and_copy_passwords,view_item_history,import_items,export_items,copy_and_share_items,print_items,manage_vault"
    logger.info(f"Updating permissions on vault with UUID: {vaultID}")
    results = subprocess.run(
        [
            "op",
            "vault",
            "user",
            "grant",
            f"--vault={vaultID}",
            f"--user={userID}",
            f"--permissions={ownerPermissions}",
            f"--account={account}",
            "--no-input",
        ],
        capture_output=True,
    )
    if results.returncode != 0:
        logger.error(
            f"Unable to set your permissions on vault with UUID: {vaultID}. Error: {results.stderr.decode('utf-8')}"
        )
    logger.info(f"Completed updating your permissions on vault with UUID {vaultID}")


# remove all permissions for specified user on specified vault
def setUserVaultPermissions(vault, userID, desiredPermissions, account):
    allPermissions = "view_items,create_items,edit_items,archive_items,delete_items,view_and_copy_passwords,view_item_history,import_items,export_items,copy_and_share_items,print_items,manage_vault"
    logger.info(
        f"Resetting your permissions on vault: {vault['name']} | {vault['id']} in account {account}"
    )

    # First, permissions must be revoked to clean the slate
    subprocess.run(
        [
            "op",
            "vault",
            "user",
            "revoke",
            f"--vault={vault['id']}",
            f"--user={userID}",
            f"--account={account}",
            "--no-input",
        ],
        capture_output=True,
    )
    # If the user had no access originally, then return early after revoking all permissions.
    if desiredPermissions == "":
        logger.info(
            f"Revoked your permissions on vault: {vault['name']} | {vault['id']}."
        )
        return
    # Then apply the pre-script permissions
    results = subprocess.run(
        [
            "op",
            "vault",
            "user",
            "grant",
            f"--vault={vault['id']}",
            f"--user={userID}",
            f"--permissions={desiredPermissions}",
            f"--account={account}",
            "--no-input",
        ],
        capture_output=True,
    )
    if results.returncode != 0:
        logger.error(
            f"Unable to reset Owner permissions on vault: {vault['name']} | {vault['id']}. Error: {results.stderr.decode('utf-8')}"
        )
    logger.info(f"Reset your permissions on vault: {vault['name']} | {vault['id']}.")


if __name__ == "__main__":
    main()
