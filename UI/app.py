from flask import Flask, render_template, request, redirect
import requests
import json

app = Flask(__name__)

API_BASE = "https://4gezooenuc.execute-api.us-east-2.amazonaws.com/dev"


@app.route("/")
def home():
    return folder_view("/")

@app.route("/folder")
def folder_view():
    path = request.args.get("path", "/")
    user_id = "00000000-0000-0000-0000-000000000000"
    api_url = f"{API_BASE}/folder/list"

    payload = {
        "action": "list_contents",
        "user_id": user_id,
        "path": path
    }

    print(f"Request: url={api_url}, json={payload}")
    resp = requests.post(api_url, json=payload)
    print(f"Response: {resp}")
    print(f"Response JSON: {resp.json()}")

    if resp.status_code == 200:
        data = resp.json()  # This is already the full dict with "folders" and "files"
        folders = data.get("folders", [])
        files = data.get("files", [])
        return render_template("folder_view.html", path=path, folders=folders, files=files)
    else:
        return f"Error loading folder: {resp.text}", 500

@app.route("/folder/view/icon")
def folder_view_icon():
    path = request.args.get("path", "/")
    user_id = "00000000-0000-0000-0000-000000000000"
    api_url = f"{API_BASE}/folder/list"

    payload = {
        "action": "list_contents",
        "user_id": user_id,
        "path": path
    }

    resp = requests.post(api_url, json=payload)
    if resp.status_code != 200:
        return f"Error loading folder: {resp.text}", 500

    data = resp.json()
    folders = data.get("folders", [])
    files = data.get("files", [])
    return render_template("folder_view_icons.html", path=path, folders=folders, files=files)

@app.route("/download/<file_id>")
def download(file_id):
    payload = {
        "action": "download_file",
        "file_id": file_id,
        "user_id": "00000000-0000-0000-0000-000000000000"
    }

    resp = requests.post(f"{API_BASE}/file/download", json=payload)

    if resp.status_code != 200:
        return f"Error downloading file: {resp.text}", 500

    # ✅ Parse the nested JSON string from inside "body"
    print(f"resp={resp}")
    outer = resp.json()
    print(f"outer={outer}")
    url = outer.get("download_url")

    if not url:
        return "Error: No download URL received", 500

    return redirect(url)




if __name__ == "__main__":
    app.run(debug=True)
