import json
import uuid
import os
import psycopg2
from datetime import datetime, timedelta, timezone
import boto3

ses = boto3.client('ses')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        file_id = body.get("file_id")
        email = body.get("email")
        user_id = body.get("user_id")

        if not file_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing file_id"})
            }

        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_id"})}

        # Determine expiration based on presence of email
        if email:
            expires_in_minutes = int(os.environ.get("EMAIL_TOKEN_TTL", "30"))
        else:
            expires_in_minutes = int(os.environ.get("UI_TOKEN_TTL", "5"))

        token = str(uuid.uuid4())[:8]  # short token for testing
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        download_url = f"https://api.sparkdrive.com/file/download?token={token}"

        # DB config
        db_host = os.environ["DB_HOST"]
        db_name = os.environ["DB_NAME"]
        db_user = os.environ["DB_USER"]
        db_password = os.environ["DB_PASSWORD"]

        conn = psycopg2.connect(
            host=db_host,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT 1 FROM files
            WHERE file_id = %s AND user_id = %s
        """, (file_id, user_id))

        if cur.fetchone() is None:
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized file access"})}

        # Insert into file_shares
        cur.execute("""
            INSERT INTO file_shares (
                share_id, file_id, token, email, expires_at, created_at, modified_at
            ) VALUES (
                %s, %s, %s, %s, %s, NOW(), NOW()
            )
        """, (
            str(uuid.uuid4()),
            file_id,
            token,
            email,
            expires_at
        ))

        conn.commit()

        # Optional email
        if email:
            sender = os.environ.get("SES_SENDER_EMAIL")
            subject = "Your SparkDrive File Link"
            body_text = f"Here's your file download link:\n{download_url}\n\nThis link will expire in {expires_in_minutes} minutes."

            ses.send_email(
                Source=sender,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body_text}}
                }
            )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "token": token,
                "download_url": download_url
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
