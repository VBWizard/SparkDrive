import json
import boto3
import base64
import os

s3 = boto3.client('s3')
sns = boto3.client('sns')

BUCKET_NAME = os.environ['S3_BUCKET']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if 'body' in event else event

        folder = body.get('folder', '').lstrip('/')
        filename = body.get('filename')
        content_b64 = body.get('content')
        user_id = body.get("user_id")

        if not folder or not filename or not content_b64:
            return _response(400, "Missing folder, filename, or content.")
        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user_id"})}

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
