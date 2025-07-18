import json
import uuid
import os
import psycopg2
from datetime import datetime

def lambda_handler(event, context):
    # Parse input
    try:
        body = json.loads(event['body'])
        path = body.get("path")
        if not path or not path.startswith("/"):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid folder path"})}
        user_id = body.get("user_id")
        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_id"})}
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": "Malformed request", "details": str(e)})}

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
        
        # Check if folder exists
        cur.execute("SELECT 1 FROM folders WHERE user_id = %s AND path = %s", (user_id, path))
        if cur.fetchone():
            return {"statusCode": 200, "body": json.dumps({"message": "Folder already exists"})}

        # Create folder
        folder_id = str(uuid.uuid4())
        now = datetime.utcnow()
        cur.execute("""
            INSERT INTO folders (folder_id, user_id, path, created_at, modified_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (folder_id, user_id, path, now, now))
        
        conn.commit()
        return {"statusCode": 201, "body": json.dumps({"message": "Folder created", "folder_id": folder_id})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": "Database error", "details": str(e)})}
    
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
