import json
import boto3
import base64
import os
import jwt

s3 = boto3.client('s3')
sns = boto3.client('sns')

BUCKET_NAME = os.environ['S3_BUCKET']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
JWT_SECRET = os.environ["JWT_SECRET"]


# NOTE: duplicated from vpc_bridge_lambda, will extract into shared layer later
# Verify JWT from Authorization header
def verify_jwt(headers):
    auth_header = next((v for k, v in headers.items() if k.lower() == "authorization"), None)
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def lambda_handler(event, context):
    try:
        headers = event.get("headers", {})
        print(f"[DEBUG] vpc_bridge_lambda event: {json.dumps(event)}")

        # Unwrap body if present
        if isinstance(event.get("body"), str):
            try:
                body = json.loads(event["body"])
            except json.JSONDecodeError:
                return {"statusCode": 400, "body": json.dumps({"status": "error", "message": "Invalid JSON in body."})}
        else:
            body = event

        try:
            jwt_payload = verify_jwt(headers)
        except ValueError as e:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": str(e)})
            }
        user_id = jwt_payload["user_id"]

        folder = body.get('folder')
        folder = folder if folder == '/' else folder.lstrip('/')
        filename = body.get('filename')
        content_b64 = body.get('content')
        if not all([folder, filename, content_b64, user_id]):
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "status": "error",
                    "message": "Missing folder, filename, content or user_id."
                })
            }

        try:
            file_bytes = base64.b64decode(content_b64)
        except Exception as decode_error:
            return _response(400, f"Invalid base64 content: {str(decode_error)}")

        # Validate folder
        folder_check = check_folder_exists(user_id, body.get('folder'))
        if not folder_check.get("exists"):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Folder does not exist"})
            }

        # Use real folder_id from check
        folder_id = folder_check["folder_id"]
        folder = folder_id
        s3_key = f"{folder}/{filename}"
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_bytes)
        file_size = len(file_bytes)
        # 🔥 Publish event to SNS
        message = {
            "event": "upload",
            "folder": folder,
            "filename": filename,
            "s3_key": s3_key,
            "file_size" : file_size,
            "user_id": user_id
        }
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message)
        )

        return _response(200, "File uploaded successfully.", {"key": s3_key})

    except Exception as e:
        return _response(500, f"Upload failed: {str(e)}")

def _response(status_code, message, data=None):
    body = {
        "status": "success" if status_code == 200 else "error",
        "message": message
    }
    if data:
        body.update(data)
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }

def check_folder_exists(user_id, path):
    lambda_client = boto3.client("lambda")
    payload = {
        "user_id": user_id,
        "path": path
    }

    response = lambda_client.invoke(
        FunctionName="check_folder_exists_lambda",
        InvocationType="RequestResponse",
        Payload=json.dumps(payload)
    )

    result = json.loads(response['Payload'].read())
    return json.loads(result['body'])  # returns { "exists": true, "folder_id": "..." }
