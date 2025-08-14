from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import json
import os
import base64
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

API_BASE = "https://4gezooenuc.execute-api.us-east-2.amazonaws.com/dev"

def auth_headers():
    token = session.get("jwt")
    return {"Authorization": f"Bearer {token}"} if token else {}

def parent_path(path):
    if path == "/":
        return "/"
    return os.path.dirname(path.rstrip('/'))

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/folder")
def folder():
    api_url = f"{API_BASE}/folder/list"
    path = request.args.get("path", "/")

    payload = {"action": "list_contents", "path": path}
    resp = requests.post(api_url, json=payload, headers=auth_headers())
    if resp.status_code == 200:
        data = resp.json()
        return render_template("folder_view.html", path=path, folders=data.get("folders", []), files=data.get("files", []))
    elif resp.status_code == 401:
        flash("Session expired. Please log in again.", "warning")
        return redirect(url_for("login"))
    else:
        return f"Error: {resp.status_code} - {resp.text}"


@app.route("/folder/view/icon")
def folder_view_icon():
    path = request.args.get("path", "/")
    api_url = f"{API_BASE}/folder/list"

    payload = {
        "action": "list_contents",
        "path": path
    }

    print(f"auth_headers = {auth_headers()}")

    resp = requests.post(api_url, json=payload, headers=auth_headers())
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
    }

    resp = requests.post(f"{API_BASE}/file/download", json=payload, headers=auth_headers())
    if resp.status_code != 200:
        return f"Error downloading file: {resp.text}", 500

    outer = resp.json()

    url = outer.get("download_url")
    if not url:
        return "Error: No download URL received", 500

    return redirect(url)

@app.route("/newfolder", methods=["GET","POST"])
def newfolder():
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
        }
        try:
            resp = requests.post(api_url, json=payload, headers=auth_headers())
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
        }

        print(f"payload = {payload}")

        try:
            resp = requests.post(api_url, json=payload, headers=auth_headers())
            if resp.status_code == 200:
                flash("File uploaded successfully!", "success")
            else:
                flash(f"Upload failed: {resp.text}", "error")
        except Exception as e:
            flash(f"Exception during upload: {str(e)}", "error")

    return render_template("upload.html", folder_default=folder_default)

@app.route("/delete", methods=["GET"])
def delete():
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
    }

    try:
        resp = requests.post(api_url, json=payload, headers=auth_headers())
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
    file_id = request.args.get("file_id")
    return_to = request.args.get("return_to") or "/"

    if not file_id:
        flash("Missing file_id.", "error")
        return redirect(return_to)

    payload = {
        "action": "delete_file",
        "file_id": file_id,
    }

    try:
        resp = requests.post(f"{API_BASE}/file/delete", json=payload, headers=auth_headers())
        if resp.status_code == 200:
            flash("File deleted successfully.", "success")
        else:
            flash(f"File deletion failed: {resp.text}", "error")
    except Exception as e:
        flash(f"Exception during file deletion: {str(e)}", "error")

    return redirect(return_to)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        payload = {"email": email, "password": password, "action": "login_user"}
        api_url = f"{API_BASE}/login"
        resp = requests.post(api_url, json=payload)

        if resp.status_code == 200:
            data = resp.json()
            session["jwt"] = data["token"]
            session["display_name"] = data["user"]["display_name"]
            return redirect(url_for("folder_view_icon"))
        else:
            flash("Login failed: Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        display_name = request.form["display_name"]
        payload = {
            "email": email,
            "password": password,
            "display_name": display_name,
            "action": "register_user",
        }
        api_url = f"{API_BASE}/register"
        resp = requests.post(api_url, json=payload)
        if resp.status_code == 200:
            flash("Registration successful. You may now log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Registration failed: " + resp.text, "danger")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)