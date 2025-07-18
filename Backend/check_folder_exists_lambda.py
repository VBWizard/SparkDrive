import json
import os
import psycopg2
import uuid

def lambda_handler(event, context):
    try:
        # Parse event
        user_id = event.get("user_id")
        path = event.get("path")

        if not user_id or not path:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing user_id or path"})
            }

        # Convert user_id safely
        user_id = str(uuid.UUID(user_id))

        # Connect to DB
        conn = psycopg2.connect(
            host=os.environ["DB_HOST"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            port=5432
        )
        cur = conn.cursor()

        # Look up folder
        cur.execute(
            "SELECT folder_id FROM folders WHERE user_id = %s AND path = %s",
            (user_id, path)
        )
        row = cur.fetchone()

        if row:
            return {
                "statusCode": 200,
                "body": json.dumps({"exists": True, "folder_id": str(row[0])})
            }
        else:
            return {
                "statusCode": 200,
                "body": json.dumps({"exists": False})
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Exception", "details": str(e)})
        }
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
