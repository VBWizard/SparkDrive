from flask import Flask, render_template, request, redirect, flash
import requests
import json
import os
import base64
from config import SECRET_KEY
from user_context import USER_ID

app = Flask(__name__)
app.secret_key = SECRET_KEY

API_BASE = "https://4gezooenuc.execute-api.us-east-2.amazonaws.com/dev"

def parent_path(path):
    if path == "/":
        return "/"
    return os.path.dirname(path.rstrip('/'))

@app.route("/")
def home():
    return folder_view()

@app.route("/folder")
def folder_view():
    path = request.args.get("path", "/")
    user_id = USER_ID
    api_url = f"{API_BASE}/folder/list"

    payload = {
        "action": "list_contents",
        "user_id": user_id,
        "path": path
    }

    resp = requests.post(api_url, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        folders = data.get("folders", [])
        files = data.get("files", [])
        return render_template("folder_view.html", path=path, folders=folders, files=files)
    else:
        return f"Error loading folder: {resp.text}", 500

@app.route("/folder/view/icon")
def folder_view_icon():
    path = request.args.get("path", "/")
    user_id = USER_ID
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
    user_id = USER_ID
    payload = {
        "action": "download_file",
        "file_id": file_id,
        "user_id": user_id
    }

    resp = requests.post(f"{API_BASE}/file/download", json=payload)
    if resp.status_code != 200:
        return f"Error downloading file: {resp.text}", 500

    print(f"resp = {resp}")

    outer = resp.json()
    print(f"outer = {outer}")

    url = outer.get("download_url")
    if not url:
        return "Error: No download URL received", 500

    return redirect(url)

@app.route("/newfolder", methods=["GET","POST"])
def newfolder():
    user_id = USER_ID
    api_url = f"{API_BASE}/newfolder"
    folder_default = request.args.get("path", "/")
    new_folder_name = request.form.get("new_folder_name","")
    return_to = request.args.get("return_to") or request.form.get("return_to") or "/"
    
    if request.method =="POST":
        path = f"{folder_default if folder_default != '/' else ''}/{new_folder_name}"
        if path == "/":
            flash("Parent folder and New Folder Name are requred", "error")
            return redirect("/newfolder")
        payload = {
            "action": "create_folder",
            "path": path,
            "user_id": user_id
        }
        print(f"newfolder: payload = {payload}")
        try:
            resp = requests.post(api_url, json=payload)
            if resp.status_code == 200 or resp.status_code == 201:
                flash(f"Folder {path} created successfully!", "success")
            else:
                flash(f"Folder creation failed: {resp.text}", "error")
            return redirect(return_to)
        except Exception as e:
            flash(f"Exception during folder creation: {str(e)}", "error")

    return render_template("new_folder.html", folder_default=folder_default)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    user_id = USER_ID
    api_url = f"{API_BASE}/upload"
    folder_default = request.args.get("path", "/")

    if request.method == "POST":
        folder = request.form.get("folder")
        file = request.files.get("file")

        if not folder or not file:
            flash("Folder path and file are required.", "error")
            return redirect("/upload")

        encoded_content = base64.b64encode(file.read()).decode("utf-8")

        payload = {
            "folder": folder.strip(),
            "filename": file.filename,
            "content": encoded_content,
            "user_id": user_id
        }

        try:
            resp = requests.post(api_url, json=payload)
            if resp.status_code == 200:
                flash("File uploaded successfully!", "success")
            else:
                flash(f"Upload failed: {resp.text}", "error")
        except Exception as e:
            flash(f"Exception during upload: {str(e)}", "error")

    return render_template("upload.html", folder_default=folder_default)

@app.route("/delete", methods=["GET"])
def delete():
    user_id = USER_ID
    api_url = f"{API_BASE}/deletefolder"

    path = request.args.get("path", "{no path}}")
    return_to_error = request.referrer or "/"               # back to where user clicked
    return_to_success = parent_path(path)                   # one level up

    if "view" in request.referrer:
        return_to_success = f"/folder/view/icon?path={parent_path(path)}"
    else:
        return_to_success = f"/folder?path={parent_path(path)}"

    if path == "{no path}":
        flash("Folder to delete must be specified as path", "error")
        return redirect(return_to_error)

    if path == "/":
        flash("The root folder cannot be deleted", "error")
        return redirect(return_to_error)

    payload = {
        "action": "delete_folder",
        "path": path,
        "user_id": user_id
    }

    try:
        resp = requests.post(api_url, json=payload)
        if resp.status_code == 200:
            flash(f"Folder {path} deleted successfully!", "success")
            return redirect(return_to_success)  # success = go up
        else:
            flash(f"Folder deletion failed: {resp.text}", "error")
            return redirect(return_to_error)    # failure = go back
    except Exception as e:
        flash(f"Exception during folder deletion: {str(e)}", "error")
        return redirect(return_to_error)

@app.route("/deletefile", methods=["GET"])
def delete_file():
    user_id = USER_ID
    file_id = request.args.get("file_id")
    return_to = request.args.get("return_to") or "/"

    if not file_id:
        flash("Missing file_id.", "error")
        return redirect(return_to)

    payload = {
        "action": "delete_file",
        "file_id": file_id,
        "user_id": user_id
    }

    try:
        resp = requests.post(f"{API_BASE}/file/delete", json=payload)
        if resp.status_code == 200:
            flash("File deleted successfully.", "success")
        else:
            flash(f"File deletion failed: {resp.text}", "error")
    except Exception as e:
        flash(f"Exception during file deletion: {str(e)}", "error")

    return redirect(return_to)

if __name__ == "__main__":
    app.run(debug=True)
