import os
import psycopg2
import boto3
from urllib.parse import urlparse

DATABASE_URL = ['postgres://frdzidjeclcxty:16551cea6bdcb55a4b5033306cd719c6cd73163cfc03e202c0500553e92ad12a@ec2-3-234-204-26.compute-1.amazonaws.com:5432/d521nossmt6tfl']
url = urlparse(DATABASE_URL[0])
conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

# Query the unique ids from the food_items table
cur = conn.cursor()
cur.execute("SELECT DISTINCT id FROM food_items;")
ids_from_db = [row[0] for row in cur.fetchall()]
conn.close()

# Print the unique ids to stdout
print("DB ids:")
for id in ids_from_db:
    print(id)

# Set up the S3 connection
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Get the list of filenames from the qrfoodcodes bucket, stripping the file extension
bucket_name = 'qrfoodcodes'
objects = s3_client.list_objects_v2(Bucket=bucket_name)
ids_from_s3 = [obj['Key'].split('.')[0] for obj in objects['Contents']]
print("S3 ids:")
for id in ids_from_s3:
    print(id)

# Compare the lists and find the unique ids
unique_ids = list(set(ids_from_s3) - set(ids_from_db))
print("\nUnique IDs:")
for unique_id in unique_ids:
    print(unique_id)
