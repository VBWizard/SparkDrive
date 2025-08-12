import json
import os
import bcrypt
import jwt
import psycopg2
import datetime

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_EXP_HOURS = 12
DB_CONFIG = {
    'dbname': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"],
    'host': os.environ["DB_HOST"],
    'port': 5432,
}

def handler(event, context):
    try:
        body = json.loads(event["body"])
        email = body["email"].strip().lower()
        password = body["password"]

        if not email or not password:
            return respond(400, "Email and password are required.")

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, password_hash, display_name FROM users WHERE email = %s", (email,))
                row = cur.fetchone()
                if not row:
                    return respond(401, "User not found")

            user_id, password_hash, display_name = row

        
        if not bcrypt.checkpw(password.encode(), password_hash):
            return respond(401, "Incorrect password.")

        payload = {
            "user_id": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "token": token,
                "user": {
                    "user_id": user_id,
                    "email": email,
                    "display_name": display_name
                }
            })
        }

    except Exception as e:
        return respond(500, f"Login error: {str(e)}")

def respond(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }
