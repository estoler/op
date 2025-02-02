# 3 Migrate User Permissions

## Introduction
⚠️ __Ensure you have a vaultPermissions.pickle file. If you do not have a vaultPermissions.pickle file, re-run the latest version of Script 1 using the `--permissions` option to regenerate the vault_permissions_report.csv and vaultPermissions.pickle.__

❓ What is vaultPermissions.pickle? A .pickle file is a binary file created by the Pickle module in the Python standard library. In this case, it contains identical data to the vault_permissions_report.csv, except in a more Python-friendly format. This makes it easier and more reliable to take data obtained while running Script 1 and use it in this script (Script 3)


Assuming all users exist in at least the "Invited" state in the _destination_ account, this script will:
* sign the script operator into both __source__ and __destination__ 1Password accounts, the script operator must be a member of the Owners group in both accounts. 
* read data about vault permissions from the _source_ account stored in a vaultPermissions.pickle file produced when you ran Script 1 and which must be in the same directory as this script. 
* obtains a list of vaults from the _destination_ account so they can be matched with vaults from the _source_ account. 
* for each vault, grant users the vault permissions in a _desintaion_ vault based on the permissions they had on a vault of the same name from the _source_ (based on data obtained from the pickle file)
* optionally attempt to migrate group permissions for each vault from the __source__ to __destination__ account if using the `--groups` flag when running the script. 
  * ⚠️ This requires groups already exist in the _destination_ account and have names that are identical to those in the _source_ account.

## Prepration
### Your environment
* Install the 1Password desktop application and CLI appropriate for your operating system. 
  * Get started with 1Password CLI: [Get Started with `op` CLI](https://developer.1password.com/docs/cli)
  * Download 1Password Desktop App: [Download 1Password](https://1password.com/downloads/)
* Add both __source__ and __destination__ 1Password accounts the 1Password Desktop app
* [Enable the integration](https://developer.1password.com/docs/cli/get-started#step-2-turn-on-the-1password-desktop-app-integration) between the desktop application and the CLI
* Download the script to a directory on your computer. 
* Ensure the vaultPermissions.pickle file you obtained from the first script is in the same directory as this script (Script 3)

### The script
The script requires you to update two values near the top of the script:
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
* Ensure you've correctly defined the `sourceAccount` and `destinationAccount` values.
* Ensure the vaultPermissions.pickle file is in the same directory as this script
  * 💡 If you do not have the vaultPermissions.pickle file, re-run Script 1 using the `--permissions` flag to recreate the vault permissions report and vaultPermissions.pickle file based on the current permissions in the _source_ account. 
* Run the script from your terminal or IDE (e.g., `python3 3_migrate_user_permissions.py`)

## Behaviours
* You will be asked to authenticate into each account. 
* The script will read the vault data from the vaultPermissions.pickle file obtained from the _source_ account with Script 1.
* It will assign those permissions to users, and optionally groups.
* All logs are written to a file in the script directory called `scriptLog.log` and to the console. 


