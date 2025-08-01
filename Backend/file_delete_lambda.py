import json
import os
import psycopg2
import boto3
import traceback

DB_CONFIG = {
    'dbname': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"],
    'host': os.environ["DB_HOST"],
    'port': 5432,
}

s3 = boto3.client("s3")
BUCKET_NAME = os.environ["S3_BUCKET"]

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        file_id = body.get("file_id")
        user_id = body.get("user_id")

        if not file_id or not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing file_id or user_id"})
            }

        conn = psycopg2.connect(connect_timeout=5, **DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        # Verify the file exists and get S3 key
        cur.execute("SELECT s3_key, filename FROM files WHERE file_id = %s AND user_id = %s", (file_id, user_id))
        result = cur.fetchone()

        if not result:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "File not found"})
            }

        s3_key, filename = result

        print(f"Deleting file from S3: {s3_key}")
        s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)

        print(f"Deleting file record from DB: {file_id}")
        cur.execute("DELETE FROM files WHERE file_id = %s", (file_id,))

        return {
            "statusCode": 200,
            "body": json.dumps({"status": "success", "message": f"File {filename} deleted."})
        }

    except Exception as e:
        print("Unhandled exception:", e)
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
