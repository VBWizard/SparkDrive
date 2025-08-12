import json
import boto3
import os
import jwt

lambda_client = boto3.client('lambda')
JWT_SECRET = os.environ["JWT_SECRET"]

# Helper to invoke an internal Lambda
def invoke_lambda(lambda_name, payload):
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode()
    )
    body = response['Payload'].read().decode()
    return json.loads(body)

# Verify JWT from Authorization header
def verify_jwt(headers):
    auth_header = headers.get("Authorization")
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
    print(f"[DEBUG] vpc_bridge_lambda event: {json.dumps(event)}")

    try:
        headers = event.get("headers", {})
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")

        if not action:
            return error_response("Missing action parameter")

        # Verify JWT and extract user_id
        try:
            jwt_payload = verify_jwt(headers)
        except ValueError as e:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": str(e)})
            }

        user_id = jwt_payload["user_id"]
        path = body.get("path")

        if action == "list_contents":
            if not path:
                return error_response("Missing path")
            return forward("folder_list_lambda", {
                "user_id": user_id,
                "path": path
            })

        elif action == "create_folder":
            if not path:
                return error_response("Missing path")
            return forward("folder_create_lambda", {
                "body": json.dumps({
                    "user_id": user_id,
                    "path": path
                })
            })

        elif action == "download_file":
            file_id = body.get("file_id")
            if not file_id:
                return error_response("Missing file_id")

            share_result = forward("file_share_lambda", {
                "body": json.dumps({
                    "user_id": user_id,
                    "file_id": file_id
                })
            })
            if "error" in share_result.get("body", ""):
                return share_result

            token = json.loads(share_result["body"])["token"]
            result = forward("file_download_lambda", {
                "queryStringParameters": {
                    "token": token
                }
            })
            print("📦 file_download_lambda response:", result)
            return result

        elif action == "delete_folder":
            if not path:
                return error_response("Missing path")
            return forward("folder_delete_lambda", {
                "body": json.dumps({
                    "user_id": user_id,
                    "path": path
                })
            })

        elif action == "delete_file":
            file_id = body.get("file_id")
            if not file_id:
                return error_response("Missing file_id")
            return forward("file_delete_lambda", {
                "body": json.dumps({
                    "user_id": user_id,
                    "file_id": file_id
                })
            })

        else:
            return error_response(f"Unknown action: {action}")

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "vpc_bridge_lambda: " + str(e)})
        }

def forward(lambda_name_env_var, payload):
    lambda_name = os.environ.get(lambda_name_env_var)
    if not lambda_name:
        return error_response(f"Missing env var for {lambda_name_env_var}")
    print(f"Forwarding to {lambda_name} with payload {payload}")
    return invoke_lambda(lambda_name, payload)

def error_response(message):
    return {
        "statusCode": 400,
        "body": json.dumps({"error": message})
    }
