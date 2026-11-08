import urllib.request
import urllib.error
import json
import subprocess
import os
import sys

# 1. 取得 Windows Git Credential Manager 儲存的認證
proc = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=github.com\n",
    text=True,
    capture_output=True
)

creds = {}
for line in proc.stdout.strip().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        creds[k.strip()] = v.strip()

username = creds.get("username", "isbananaice")
token = creds.get("password")

print(f"Logged in user: {username}")
if not token:
    print("Error: No GitHub token found in git credential manager.")
    sys.exit(1)

repo_name = "SmartCity2-Infalsus-Review"
repo_desc = "智慧城市期中 - In Falsus 的影像辨識復盤系統 (YOLOv11 + 時序狀態機 + 打擊誤差視覺化)"

# 2. 檢查或建立 GitHub 倉庫
create_url = "https://api.github.com/user/repos"
payload = json.dumps({
    "name": repo_name,
    "description": repo_desc,
    "private": False, # 公開或私人倉庫
    "has_issues": True,
    "has_projects": True,
    "has_wiki": True
}).encode("utf-8")

req = urllib.request.Request(
    create_url,
    data=payload,
    headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SmartCity2-Agent"
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"Successfully created repository: {res.get('html_url')}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8")
    if e.code == 422: # 倉庫可能已存在
        print(f"Repository {repo_name} already exists or error: {err_body}")
    else:
        print(f"HTTP Error {e.code}: {err_body}")

# 3. 設定 Remote 並推送 main 分支
remote_url = f"https://github.com/{username}/{repo_name}.git"

# 檢查現有 remote
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
print(f"Added remote origin: {remote_url}")

# 執行 push
print("Pushing to GitHub (main branch)...")
push_proc = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
print("STDOUT:", push_proc.stdout)
print("STDERR:", push_proc.stderr)

if push_proc.returncode == 0:
    print(f"\n[成功] 專案已成功發布至 GitHub: https://github.com/{username}/{repo_name}")
else:
    print(f"\n[失敗] Push 過程遇到問題，返回碼: {push_proc.returncode}")
