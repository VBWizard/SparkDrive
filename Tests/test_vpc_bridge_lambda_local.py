import pytest
import jwt
import json
import os
from datetime import datetime, timedelta

# Setup for testing
JWT_SECRET = "testsecret"
os.environ["JWT_SECRET"] = JWT_SECRET

from vpc_bridge_lambda import lambda_handler

def make_token(user_id="00000000-0000-0000-0000-000000000000", exp_hours=12):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=exp_hours)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def make_event(action, path=None, file_id=None, token=None, jwt_token=None):
    body = {"action": action}
    if path:
        body["path"] = path
    if file_id:
        body["file_id"] = file_id

    return {
        "body": json.dumps(body),
        "headers": {
            "Authorization": f"Bearer {jwt_token}" if jwt_token else ""
        }
    }

def test_missing_token():
    event = make_event("list_contents", path="/Projects/SparkDrive")
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401

def test_invalid_token():
    event = make_event("list_contents", path="/Projects/SparkDrive", jwt_token="invalid.token.blob")
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401

def test_expired_token():
    expired_token = make_token(exp_hours=-1)
    event = make_event("list_contents", path="/Projects/SparkDrive", jwt_token=expired_token)
    result = lambda_handler(event, None)
    assert result["statusCode"] == 401

def test_unknown_action():
    valid_token = make_token()
    event = make_event("not_a_real_action", path="/SomePath", jwt_token=valid_token)
    result = lambda_handler(event, None)
    assert result["statusCode"] == 400
    assert "Unknown action" in result["body"]

# Additional success-path tests would require mock forwarding logic,
# which can be added using unittest.mock or moto for AWS mocking.
