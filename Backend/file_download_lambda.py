import json
import os
import boto3
import psycopg2
from datetime import datetime, timezone

s3 = boto3.client('s3')

def lambda_handler(event, context):
    token = event.get("queryStringParameters", {}).get("token")
    
    if not token:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing download token"})
        }
    
    # DB config
    db_host = os.environ["DB_HOST"]
    db_name = os.environ["DB_NAME"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    s3_bucket = os.environ["S3_BUCKET"]

    try:
        conn = psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        cur = conn.cursor()
        
        # Look up token
        cur.execute("""
            SELECT fs.file_id, f.s3_key, fs.expires_at
            FROM file_shares fs
            JOIN files f ON fs.file_id = f.file_id
            WHERE fs.token = %s
        """, (token,))
        
        row = cur.fetchone()
        if not row:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Invalid or expired token"})
            }
        
        file_id, s3_key, expires_at = row
        
        # Check expiration
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return {
                    "statusCode": 403,
                    "body": json.dumps({"error": "Token has expired"})
                }

        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_bucket, 'Key': s3_key},
            ExpiresIn=300  # 5 minutes
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"download_url": presigned_url})
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
