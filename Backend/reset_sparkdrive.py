import psycopg2
import boto3
import os

DB_CONFIG = {
    'dbname': os.environ["DB_NAME"],
    'user': os.environ["DB_USER"],
    'password': os.environ["DB_PASSWORD"],
    'host': os.environ["DB_HOST"],
    'port': 5432,
}

BUCKET_NAME = os.environ["S3_BUCKET"]

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

# Clean file_shares (optional, but safe)
cur.execute("DELETE FROM file_shares")
print("Deleted all records from file_shares")

# Clean files
cur.execute("DELETE FROM files")
print("Deleted all records from files")

# Clean folders, except for root ('/')
cur.execute("DELETE FROM folders WHERE path != '/'")
print("Deleted all folders except root")

# Clean S3 bucket
s3 = boto3.client('s3')
objects = s3.list_objects_v2(Bucket=BUCKET_NAME)
if 'Contents' in objects:
    keys_to_delete = [{'Key': obj['Key']} for obj in objects['Contents']]
    s3.delete_objects(Bucket=BUCKET_NAME, Delete={'Objects': keys_to_delete})
    print(f"Deleted {len(keys_to_delete)} object(s) from S3")
else:
    print("S3 bucket already empty")

cur.close()
conn.close()
print("SparkDrive reset complete.")
