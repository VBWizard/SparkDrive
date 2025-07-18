import json
import os
import psycopg2
import uuid
import base64

# Helper to validate parameters
def validate_required_fields(payload, required, context_label):
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"[{context_label}] Missing required field(s): {', '.join(missing)}")

def lambda_handler(event, context):
    print("🔥 [BOOT] Lambda triggered.")
    
    try:
        print("📦 [EVENT] Full event payload:")
        print(json.dumps(event, indent=2))
    except Exception as e:
        print(f"💥 [ERROR] Failed to stringify full event: {str(e)}")

    for record in event.get("Records", []):
        try:
            print("📨 [RECORD] Raw record body:")
            print(record['body'])

            outer = json.loads(record['body'])               # SNS envelope
            message_str = outer.get('Message')
            if not message_str:
                raise ValueError("Missing 'Message' field in SNS envelope")

            message = json.loads(message_str)                # Actual inner payload
            print("✅ [LOG] Parsed inner upload event:")
            print(json.dumps(message, indent=2))

            validate_required_fields(
                message,
                ["user_id", "folder", "filename", "s3_key", "file_size"],
                "log_upload_lambda"
            )
            insert_metadata_to_rds(message)

        except Exception as e:
            print(f"🚫 [ERROR] Failed to process record: {type(e).__name__} - {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Upload event(s) processed."})
    }

def insert_metadata_to_rds(event_data):
    conn = None
    if 'filename' not in event_data or 's3_key' not in event_data or 'user_id' not in event_data or 'file_size' not in event_data:
        raise ValueError(f"Invalid event data: expected filename, s3_key, user_id and file_size, got {event_data}")
    try:
        conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            port=os.environ['DB_PORT'],
            dbname=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            connect_timeout=3
        )
        cursor = conn.cursor()

        file_id = str(uuid.uuid4())
        user_id = event_data.get('user_id')
        user_uuid = str(uuid.UUID(user_id.strip()))
        print(f"[DEBUG] Raw user_id: {repr(user_id)}")
        print(f"[DEBUG] converted user_uuid: {repr(user_uuid)}")
        folder_id = str(uuid.UUID(event_data['folder']))  # now passed as a UUID string        
        size_bytes = int(event_data.get('file_size'))
        filename = event_data.get('filename')
        s3_key = event_data.get('s3_key')
        content_b64 = event_data.get('content', '')

        if not filename or not s3_key or not user_id:
            raise ValueError("Missing required metadata: filename, s3_key or user_id")
    except Exception as e:
        print(f"💥 [ERROR] {type(e).__name__}: {str(e)}")
        return

    try:
        query = """
            INSERT INTO files (file_id, user_id, folder_id, filename, s3_key, size_bytes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (file_id, user_uuid, folder_id, filename, s3_key, size_bytes)
        cursor.execute(query, values)
        conn.commit()
        print(f"✅ [DB] Inserted file metadata (file_id={file_id}) into RDS.")

    except Exception as e:
        print(f"💥 [DB ERROR] {type(e).__name__}: {str(e)}")
    finally:
        if conn:
            conn.close()

def base64_decode_length_safe(content):
    """Used to estimate file size from base64 content"""
    import base64
    try:
        return base64.b64decode(content or "")
    except:
        return b""
