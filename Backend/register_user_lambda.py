import json
import os
import uuid
import bcrypt
import psycopg2
import psycopg2.extras

JWT_SECRET = os.environ["JWT_SECRET"]
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
        display_name = body.get("display_name")

        if not email or not password:
            return respond(400, "Email and password are required.")

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user_id = str(uuid.uuid4())

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, email, password_hash, display_name)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, email, password_hash, display_name))
        
        return respond(200, "User registered successfully.")

    except psycopg2.errors.UniqueViolation:
        return respond(409, "Email already registered.")
    except Exception as e:
        return respond(500, f"Registration error: {str(e)}")

def respond(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }
