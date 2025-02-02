## https://gist.github.com/scottisloud/76d791eb35d6e719da2c163d424be95f

## Introduction
This gist contains three scripts to assist with migrating vaults and their data from one 1Password account (the "_source_" account) to another ("_destination_") account.

The three scripts are:

* __SCRIPT 1__ Create vaults in the _destination_ account based on vaults in the _source_ account.
* __SCRIPT 2 (OPTIONAL)__ Grant the migration_admins full access to all shared vaults in both accounts to facilitate the migration of items to the new account.
* __SCRIPT 3__ Grant individuals (but not groups) vault permissions in the _destination_ account based on their permissions in the _source_ account. (ONLY to be run after users are provisioned to the new account).

Please be sure to read the README file for each script prior to running it.

### Order of Operations
For each _source_ account:

1. Run __Script 1__ to create vaults in the _destination_ account and generate a list of vault permissions from the _source_ account.
2. Optionally run __Script 2__. Prior to running the script, create a group of the same name in all _source_ and _destination_ accounts containing users you are delegating the task of manually migrating items between accounts. Run Script 2 ensuring the "special group" variable is set to the name of the group.
3. Run __Script 3__ once all users from the Source account have been provisioned to the Destination account. If using SCIM provisionig, this can be done while users are still in the "Invited" state.
❓ What is vaultPermissions.pickle? A .pickle file is a binary file created by the Pickle module in the Python standard library. In this case, it contains identical data to the vault_permissions_report.csv, except in a more Python-friendly format. This makes it easier and more reliable to take data obtained while running Script 1 and use it in Script 3