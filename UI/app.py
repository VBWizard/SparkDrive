# app.py
import json
from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route("/folders")
def list_folders():
    user_id = request.args.get("user_id", "00000000-0000-0000-0000-000000000000")
    path = request.args.get("path", "/Test/Boogie")

    api_url = "https://4gezooenuc.execute-api.us-east-2.amazonaws.com/dev/folder/list"
    payload = {
        "action": "list_folders",
        "user_id": user_id,
        "path": path
    }
    print(f"api_url={api_url}")
    print(f"payload={payload}")

    try:
        response = requests.post(api_url, json=payload)
        files = response.json().get("files", [])
    except Exception as e:
        files = []
        print(f"[ERROR] Failed to fetch folder listing: {e}")

 # 🧪 Mock file list (normally from API)
    # files = [
    #     {
    #         "file_id": "1a2b3c",
    #         "filename": "sparkcore.docx",
    #         "size_bytes": 123456,
    #         "uploaded_at": "2025-07-01T10:00:00Z"
    #     },
    #     {
    #         "file_id": "4d5e6f",
    #         "filename": "vbslegacy.vbs",
    #         "size_bytes": 789,
    #         "uploaded_at": "1999-10-31T23:59:59Z"
    #     },
    #     {
    #         "file_id": "7g8h9i",
    #         "filename": "register5.txt",
    #         "size_bytes": 22,
    #         "uploaded_at": "2025-07-09T15:30:12.722228"
    #     }
    # ]
    
    print(f"files={files}")
    return render_template("folders.html", files=files, user_id=user_id, path=path)

if __name__ == "__main__":
    app.run(debug=True)
