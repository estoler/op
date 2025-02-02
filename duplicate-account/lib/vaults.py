import json
import subprocess

def getVaults():

    v = json.loads(
            subprocess.run(
            ["op vault list --format=json"],
            check=True,
            shell=True,
            capture_output=True
        ).stdout
    )

    vaultList = []

    for v in v:
        vaultList.append({
            "vault_id": v["id"],
            "vault_name": v["name"],
            "vault_item_count": v["items"],
            "vault_users": getVaultUsers(v["id"]),
            "vault_groups": getVaultGroups(v["id"])
        })
    
    # print(vaultList)

    return(vaultList)

def getVaultUsers(id):
    
    u = json.loads(
            subprocess.run(
            [f"op vault user list {id} --format=json"],
            check=True,
            shell=True,
            capture_output=True
        ).stdout
    )

    users = []

    for u in u:
        if u["state"] == "ACTIVE":
            users.append({
                "id": u["id"],
                "name": u["name"],
                "email": u["email"],
                "type": u["type"],
                "permissions": u["permissions"]
            })
    
    return(users)

def getVaultGroups(id: str, env: str):

    g = json.loads(
            subprocess.run(
            [f"op vault group list {id} --format=json"],
            check=True,
            shell=True,
            capture_output=True
        ).stdout
    )

    groups = []

    for g in g:
        if g["state"] == "ACTIVE" and g["name"] != "Owners":
            groups.append({
                "id": g["id"],
                "name": g["name"]
                # "permissions": g["permissions"]
            })
    
    return(groups)