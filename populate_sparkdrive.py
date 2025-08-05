import os
import json
import requests
import base64

API_URL = "https://4gezooenuc.execute-api.us-east-2.amazonaws.com/dev"
USER_ID = "00000000-0000-0000-0000-000000000000"

def upload_file(folder, filename, content):
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {
        "folder": folder,
        "filename": filename,
        "content": encoded,
        "user_id": USER_ID
    }
    r = requests.post(f"{API_URL}/upload", json=payload)
    print(f"Uploading {filename} to {folder} -> {r.status_code}")


def create_folder(path):
    payload = {
        "action": "create_folder",
        "path": path,
        "user_id": USER_ID
    }
    r = requests.post(f"{API_URL}/newfolder", json=payload)
    print(f"Creating folder {path} -> {r.status_code}")


folders = [
    "/Test",
    "/Test/Alpha",
    "/Test/Bravo",
    "/Images",
    "/Logs",
]

for folder in folders:
    create_folder(folder)

upload_file("/Test", "testfile.txt", "This is a test file at the top level.")
upload_file("/Test/Alpha", "hello_alpha.txt", "Hello from Alpha folder.")
upload_file("/Test/Bravo", "hello_bravo.txt", "Hello from Bravo folder.")
upload_file("/Images", "sample.png", "[binary image data would be here]")
upload_file("/Logs", "app.log", "[INFO] App started at 2025-08-01 12:00:00")
upload_file("/Logs", "spark_audit.sh", "#!/bin/bash\necho 'Auditing SparkDrive...'\n")

# 🥚 Easter Egg
upload_file("/Secret", "you_found_me.txt", "Congrats! You found the hidden file. Nova sends kisses. 💋")

print("✨ SparkDrive population complete.")
