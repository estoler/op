from lib import setup, vaults
from dotenv import load_dotenv
import argparse
import logging
import time
import os

load_dotenv('.env')

# Configure script options
# https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument
parser = argparse.ArgumentParser(
    "✨ Account Migration Assistant ✨",
    "",
    "Recreate vaults from source account in destination account",
    "This script recreates the shared vaults from a source account in a destination account."
)

# Set the domain for the source account
parser.add_argument(
    "-s",
    "--source",
    action="store",
    dest="srcAcct",
    help="Define the source account using the full domain (bluemountainsit.1password.com)",
    type=str,
    required=True
)

# Set the domain for the destination account
parser.add_argument(
    "-d",
    "--destination",
    action="store",
    dest="destAcct",
    help="Define the destination account using the full domain (bluemountainsit.1password.com)",
    type=str,
    required=True
)

# If set, attempts to migrate items between source and destination account
parser.add_argument(
    "--items",
    action="store_true",
    help="Make a best effort to migrating vault items.",
    required=False
)

# Does not create vaults, just generates permission report.
parser.add_argument(
    "--permissions",
    action="store_true",
    help="Only generate the permissions report for the source account.",
    required=False
)

parser.add_argument(
    "--output-file",
    action="store",
    dest="outputPath",
    help="Modify the path for all output files. Default is an 'exports' subdirectory in the main directory.",
    type=str,
    required=False
)

args = parser.parse_args()

# Configure paths
scriptPath = os.path.dirname(__file__)
outputPath = scriptPath  ### Update this to reflect whether or not an arg was passed

# Set up logging so we know if any notifications fail to send
logging.basicConfig(
    filename=f"{outputPath}/scriptLog.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Record the time when the script starts
start_time = time.time()

def main():

    try:
        setup.checkCLIVersion()
        setup.acceptTerms()
        setup.setEnv("src")
        print("\n--------------------SOURCE ACCOUNT--------------------")
        setup.getCredDetails()
        setup.setEnv("dest")
        print("\n------------------DESTINATION ACCOUNT------------------")
        setup.getCredDetails()
        setup.promptCheck()

        setup.setEnv("src")
        srcVaults = vaults.getVaults()
        setup.setEnv("dest")
        destVaults = vaults.getVaults()
        print(srcVaults)

    
    except Exception as e:
        print(f'An error has occured: {e}')
    
    finally:
        setup.signOut()

main()