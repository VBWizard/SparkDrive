import boto3
import json
import time

def lambda_handler(event, context):
    results = {}
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "path": "/Projects/SparkDrive"
    }

    try:
        lambda_client = boto3.client("lambda")
        print("📤 Invoking check_folder_exists_lambda...")
        start = time.time()
        response = lambda_client.invoke(
            FunctionName="check_folder_exists_lambda",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
        print("✅ Lambda invoke completed in", round(time.time() - start, 3), "seconds")
        result = json.loads(response["Payload"].read())
        body = json.loads(result["body"])

        results["check_folder_lambda"] = "ok" if body.get("exists") else "not found"
    except Exception as e:
        results["check_folder_lambda"] = f"error: {type(e).__name__} - {str(e)}"

    results["summary"] = "All systems go" if all(v == "ok" for v in results.values()) else "Some checks failed"
    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }
