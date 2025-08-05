import json
import psycopg2
import os

def get_direct_subfolders(folders, current_path):
    current_path = current_path.rstrip("/")
    prefix = current_path + "/" if current_path != "" else "/"

    seen = set()
    results = []

    for folder in folders:
        full_path = folder["path"].rstrip("/")

        if full_path == current_path:
            continue  # skip self

        if not full_path.startswith(prefix):
            continue

        suffix = full_path[len(prefix):]
        parts = suffix.split("/")

        if len(parts) >= 1:
            name = parts[0]
            if name not in seen:
                seen.add(name)
                results.append({
                    "name": name,
                    "path": prefix + name
                })

    return results

def lambda_handler(event, context):
    # Extract query parameters
    print(f"[DEBUG] folder_list_lambda triggered")
    print(f"[DEBUG] event = {json.dumps(event)}")

    user_id = event.get("user_id")
    folder_path = event.get("path")


    if not user_id or not folder_path:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "folder_list_lambda: Missing user_id or path"})
        }

    # Database credentials from environment variables
    db_host = os.environ["DB_HOST"]
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]

    try:
        conn = psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        cur = conn.cursor()

        # Get folder_id from path and user
        cur.execute("""
            SELECT folder_id FROM folders
            WHERE user_id = %s AND path = %s
        """, (user_id, folder_path))

        row = cur.fetchone()
        if not row:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Folder not found"})
            }

        folder_id = row[0]

        # 🔽 Get child folders
        prefix = folder_path.rstrip("/") + "/%"
        depth = folder_path.count("/") + 1

        cur.execute("""
            SELECT path
            FROM folders
            WHERE user_id = %s
              AND path LIKE %s
        """, (user_id, prefix))

        folders = []
        for r in cur.fetchall():
            child_path = r[0]
            name = child_path.rsplit("/", 1)[-1]
            folders.append({"name": name, "path": child_path})

        folders = get_direct_subfolders(folders, folder_path)

        # 📄 Get files in the folder
        cur.execute("""
            SELECT file_id, filename, size_bytes, uploaded_at
            FROM files
            WHERE user_id = %s AND folder_id = %s
            ORDER BY uploaded_at DESC
        """, (user_id, folder_id))

        files = [
            {
                "file_id": str(row[0]),
                "filename": row[1],
                "size_bytes": row[2],
                "uploaded_at": row[3].strftime("%m/%d/%Y %H:%M:%S")
            }
            for row in cur.fetchall()
        ]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "folders": folders,
                "files": files
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
