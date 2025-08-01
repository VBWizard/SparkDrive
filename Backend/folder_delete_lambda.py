import json
import os
import psycopg2
from datetime import datetime
import traceback
import boto3

DB_CONFIG = {
    'dbname': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"],
    'host': os.environ["DB_HOST"],
    'port': 5432,
}

def delete_files_in_folder(folder_id: str, user_id: str):
    BUCKET_NAME = os.environ["S3_BUCKET"]
    s3 = boto3.client('s3')
    key = ""
    query = ""
    print(f"delete_files_in_folder: Deleting all files in {folder_id}")

    try:
        conn = psycopg2.connect(connect_timeout=5, **DB_CONFIG )
        conn.autocommit = True
        with conn.cursor() as cur:
            query = "SELECT filename, s3_key FROM files WHERE folder_id = %s AND user_id = %s"
            cur.execute(query, (folder_id, user_id))
            files = cur.fetchall()

        print(f"delete_files_in_folder:\t{len(files)} files found to delete")

        for file in files:
            filename = file[0]
            key = file[1]

            # First delete from S3
            print(f"delete_files_in_folder:\tBucket={BUCKET_NAME}, File {filename}, Key={key} will be deleted from  S3")
            s3.delete_object(Bucket=BUCKET_NAME, Key=key)
            print(f"delete_files_in_folder:\tBucket={BUCKET_NAME}, File {filename}, Key={key} deleted from  S3")

            # Then delete from DB
            with conn.cursor() as cur:
                query = "DELETE FROM files WHERE s3_key = %s"
                cur.execute(query, (key,))
                conn.commit()
            print(f"delete_files_in_folder:\tFile {filename}, Key={key} deleted from the db")
    except Exception as e:
        print(f"[delete_files_in_folder] Error with folder_id={folder_id}, user_id={user_id}")
        print(f"Last S3 key: {key}")
        print(f"Last query: {query}")
        print(f"Exception: {e}")
        raise

    print(f"delete_files_in_folder: Deleted {len(files)} file(s) from S3 and database.")
    if cur: cur.close()
    if conn: conn.close()
    

def lambda_handler(event, context, depth=0):
    MAX_RECURSION_DEPTH = int(os.environ["MAX_DELETE_RECURSION_DEPTH"])

    # Parse input
    try:
        body = json.loads(event['body'])
        path = body.get("path")
        user_id = body.get("user_id")

        if not path or not path.startswith("/"):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid folder path"})}
        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_id"})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": "Malformed request", "details": str(e)})}

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

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(connect_timeout=5, **DB_CONFIG )
        conn.autocommit = True
        folder_id = ""
        with conn.cursor() as cur:
            print(f"Verifying that folder {path} exists for user {user_id}")
            cur.execute("SELECT folder_id FROM folders WHERE user_id = %s AND path = %s", (user_id, path))
            result = cur.fetchone()
            if not result:
                return {
                    "statusCode": 404,
                    "body": json.dumps({
                        "message": f"Folder {path} does not exist for user {user_id} at depth={MAX_RECURSION_DEPTH}",
                        "status": "error"
                    })
                }

            folder_id = result[0]

        print(f"Folder {path} exists. Checking for subfolders...")
        like_path = path.rstrip("/") + "/%"

        with conn.cursor() as cur:
            cur.execute("SELECT path FROM folders WHERE user_id = %s AND path LIKE %s AND path != %s", (user_id, like_path, path))
            subfolders = cur.fetchall()

        if not subfolders:
            print(f"No subfolders found")
        else:
            for (subpath,) in subfolders:
                print(f"\tSubfolder {subpath} found")
                event = {
                    "body": json.dumps({
                        "path": subpath,
                        "user_id": user_id
                    })
                }
                print(f"Recursively calling lambda_handler(event={event}, None, depth={depth + 1})")
                response = lambda_handler(event, None, depth + 1)
                if response.get("statusCode", 0) >= 400:
                    # Only log if we're at the top
                    if depth == 0:
                        print(f"Error during recursive delete of {subpath}: {response}")
                    return response

        # Remove the files in the folder
        delete_files_in_folder(folder_id, user_id)

        # Delete the folder
        with conn.cursor() as cur:
            cur.execute("DELETE FROM folders WHERE user_id = %s AND path = %s", (user_id, path))
            conn.commit()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Folder {path} deleted for user {user_id}",
                "status": "success",
                "path": path
            })
        }

    except Exception as e:
        if depth == 0:
            print(f"Unhandled exception at top-level: {e}")
            traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "status": "error"
            })
        }

    finally:
        if cur: cur.close()
        if conn: conn.close()
