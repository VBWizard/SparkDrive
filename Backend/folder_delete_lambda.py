import json
import os
import psycopg2
from datetime import datetime

def lambda_handler(event, context):

    MAX_RECURSION_DEPTH = 30
    depth = 0
    # Parse input
    try:
        body = json.loads(event['body'])
        path = body.get("path")
        user_id = body.get("user_id")
        try:
            depth = int(body.get("depth"))
        except:
            depth = 0

        if not path or not path.startswith("/"):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid folder path"})}
        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_id"})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": "Malformed request", "details": str(e)})}

    # Recursion depth check. Reject if method has been called recursively too many times
    print(f"Recursion check: lambda_handler has been called {depth} times. Max allowed recursion = {MAX_RECURSION_DEPTH}")
    if depth > MAX_RECURSION_DEPTH:
        return {
            "statusCode": 429,
            "body": json.dumps({
                "status": "error",
                "message": f"Folder delete aborted after {MAX_RECURSION_DEPTH} levels of recursion.",
                "retry_after": "manual review"
            })
        }
    # Connect to RDS
    try:
        conn = psycopg2.connect(
            host=os.environ["DB_HOST"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            port=5432
        )
        cur = conn.cursor()
        
        print(f"Verifying that folder {path} exists for user {user_id}")
        # Check if folder exists - return an error if it doesn't
        cur.execute("SELECT 1 FROM folders WHERE user_id = %s AND path = %s", (user_id, path))
        if not cur.fetchone():
            return {"statusCode": 404, "body": json.dumps({"message": f"Folder {path} does not exists for user {user_id}", "status": "error"})}

        print(f"Folder {path} exists for user {user_id}. Deleting if it has no subfolders")
        # Folder exists so see if there are any subfolders
        like_path = path.rstrip("/") + "/%"
        cur.execute("SELECT path FROM folders WHERE user_id = %s AND path like %s", (user_id, like_path))
        # There are so for now just return an error. We'll add recursion logic later
        if cur.fetchone():
            return {"statusCode": 429, "body": json.dumps({"message": "Subfolders exist - recursive deletion is TBD", "status": "error"})}


        cur.execute("DELETE FROM folders WHERE user_id = %s and path = %s", (user_id, path))        
        conn.commit()
        return {"statusCode": 200, "body": json.dumps({"message": f"Folder {path} deleted for user {user_id}", "status": "success", "path": path})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": "Database error", "details": str(e), "status": "error"})}
    
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
