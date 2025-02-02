# 2 Grant Group Full Permissions

## Introduction
This script will:
* sign the script operator into both __source__ and __destination__ 1Password accounts, the script operator must be a member of the Owners group in both accounts. 
* grant or revoke the "migration_admins" group full access to all shared vaults in __source__  and __destination__ accounts depending on if the script is run using the `--grant` or `--revoke` flags.

## Prepration
### Your environment
* Install the 1Password desktop application and CLI appropriate for your operating system. 
  * Get started with 1Password CLI: [Get Started with `op` CLI](https://developer.1password.com/docs/cli)
  * Download 1Password Desktop App: [Download 1Password](https://1password.com/downloads/)
* Add both __source__ and __destination__ 1Password accounts the 1Password Desktop app
* [Enable the integration](https://developer.1password.com/docs/cli/get-started#step-2-turn-on-the-1password-desktop-app-integration) between the desktop application and the CLI
* Download the script to a directory on your computer. 

### The script
The script requires you to update two values found near the top of the script:
* The name of the _source_ account as it is known to the 1Password CLI
* The name of the _destination_ account as it is known to the 1Password CLI


Once you've added both accounts to the CLI, you can see the account names by issuing `op signin` to bring up the interactive account picker, and looking at the names. E.g., 
```
$ op sign-in
  KnoxIT-express (knoxit-express.1password.com)
  KnoxIT (knoxit.1password.com)
```
`knoxIT-express` and `KnoxIT` are the account names. If `knoxIT-express` is the _source_ account, you would add that as the `sourceAccount` in the script, and `KnoxIT` as the `destinationAccount`. 

e.g., you will see the following code near the top of the script, which you must update with the correct values. 
```
########
# ACTION REQUIRED: ADJUST THESE TO YOUR NEEDS
######
specialGroup = "migration_admins"

# Use the name associated with the source (outgoing) account
sourceAccount = "KnoxIT"

# Use the name associated with the destination account
destinationAccount = "KnoxIT-express"
```

## Usage
* Using your terminal, navigate to the script directory or open the script in your favourite IDE. 
* Ensure you've correctly defined the `sourceAccount` and `destinationAccount` values
* Run the script from your terminal or IDE (e.g., `python3 2_grant_group_full_permissions.py --grant` (or `--revoke` to revoke permissions once migration is complete))

## Behaviours
* You will be asked to authenticate into each account. 
* The script will grant or revoke (based on the flag you pass when running the script) permissions for the `migration_admins` group in both __source__ and __destination__ accounts simultaneously. 
* All logs are written to a file in the script directory called `scriptLog.log` and to the console. 
* This took about 12 minutes to complete with 250 shared vaults on macOS. 

