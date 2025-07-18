import json
import boto3
import os

lambda_client = boto3.client('lambda')

# Helper to invoke an internal Lambda
def invoke_lambda(lambda_name, payload):
    response = lambda_client.invoke(
        FunctionName=lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload).encode()
    )
    body = response['Payload'].read().decode()
    return json.loads(body)

def lambda_handler(event, context):
    print(f"[DEBUG] vpc_bridge_lambda event: {json.dumps(event)}")

    try:
        # Parse the incoming POST body
        body = json.loads(event.get("body", "{}"))

        action = body.get("action")
        user_id = body.get("user_id")
        path = body.get("path")

        if not action:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "vpc_bridge_lambda: Missing 'action' parameter", "lambda": "vpc_bridge_lambda"})
            }


        if not action or not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing action or user_id"})
            }

        elif action == "list_files":
            if not path:
                return error_response("Missing path")
            return forward("folder_list_lambda", {
                    "user_id": user_id,
                    "path": path
            })
        elif action == "list_folders":
            if not path:
                return error_response("Missing path")
            return forward("folder_list_lambda", {
                    "user_id": user_id,
                    "path": path
            })
        elif action == "create_folder":
            path = body.get("path")
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

            # Step 1: Call file_share_lambda
            share_result = forward("file_share_lambda", {
                "body": json.dumps({
                    "user_id": user_id,
                    "file_id": file_id
                })
            })

            if "error" in share_result.get("body", ""):
                return share_result

            token = json.loads(share_result["body"])["token"]

            # Step 2: Call file_download_lambda
            return forward("file_download_lambda", {
                "queryStringParameters": {
                    "token": token
                }
            })

        else:
            return error_response(f"Unknown action: {action}")

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "vpc_bridge_lambda: " + str(e)})
        }

# Generic forwarder
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
