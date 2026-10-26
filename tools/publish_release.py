import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.error

def get_auth_token():
    try:
        url = subprocess.check_output(["git", "remote", "get-url", "origin"]).decode().strip()
        m = re.search(r"https://[^:]+:([^@]+)@", url)
        if m:
            return m.group(1)
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "")

TOKEN = get_auth_token()
REPO = "alexis0eu/Mod-Yandex-Music"

def publish(tag, name, body, exe_path):
    if not TOKEN:
        print("[-] GitHub token not found in git remote origin or GITHUB_TOKEN!")
        sys.exit(1)
    
    print(f"[+] Creating release {tag} on {REPO}...")
    url = f"https://api.github.com/repos/{REPO}/releases"
    payload = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"token {TOKEN}",
        "User-Agent": "YandexMusicMod-Deployer",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[+] Release created successfully! ID: {res['id']}")

    file_size = os.path.getsize(exe_path)
    file_name = os.path.basename(exe_path)
    print(f"[+] Uploading {file_name} ({file_size / (1024*1024):.1f} MB)...")

    upload_url = res["upload_url"].split("{")[0] + f"?name={file_name}"
    
    with open(exe_path, "rb") as f:
        file_bytes = f.read()

    req = urllib.request.Request(upload_url, data=file_bytes, headers={
        "Authorization": f"token {TOKEN}",
        "User-Agent": "YandexMusicMod-Deployer",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(file_size)
    })

    with urllib.request.urlopen(req) as resp:
        asset_info = json.loads(resp.read().decode("utf-8"))
        print(f"[+] Download URL: {asset_info['browser_download_url']}")
