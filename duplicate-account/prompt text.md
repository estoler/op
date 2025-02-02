# Script Terms

# Service Account Creation Instructions

# Account Confirmation

–––––––––––––––––––––––––––––––––––––––––––––––––––––

# Get all shared vaults in the destination account (common_name, UUID, individuals, groups)
# Get all shared vaults in the source account (common_name, UUID, individuals, groups)
# Compare the lists and identify duplicates vaults (store s/d UUIDs)
# Get all groups in the destination account (common_name, UUID, individuals, vaults)
# Get all groups in the source account (common_name, UUID, individuals, vaults)
# Compare the lists and identify duplicates vaults (store s/d UUIDs)
# Prompt the user to accept duplicates (rename new vaults or skip)

# Create Exports Folder if not existing
# Setup Script Options
# Setup Logging (pass in parameters)
# Setup Rate Limiter
# Setup CSV/JSON exports
# Setup Status bar
# Setup notify Slack

## MIGRATION ##

# For each vault...
# Get source permissions
# Manage add source permissions to destination
# List all item UUIDs in the source vault
# Copy to destination vault with same common_name
# ATTACHMENTS WOULD HAVE TO BE FIGURED OUT
# Log item duplication
# Append log to exports
## CONSIDER EMPLOYEE VAULT

# JASON NOTES
Make sure no new vaults are created in the source when this is started