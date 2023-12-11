from fastapi import UploadFile
import os
import psycopg2
from PIL import Image
import io
import boto3
from botocore.exceptions import NoCredentialsError

def upload_image_to_s3(image_bytes: bytes, bucket_name: str, object_name: str):
    # Upload to S3
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    try:
        s3_client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_name, ContentType='image/jpeg')
        return True
    except NoCredentialsError:
        return False


# Connect to the database
def connect_to_db():
    use_ssl = 'localhost' not in os.getenv("DATABASE_URL")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require' if use_ssl else None)
    return conn

# DATABASE_URL = os.getenv("DATABASE_URL")
# async def connect_to_async_db() -> Database:
#     database = Database(DATABASE_URL)
#     await database.connect()
#     return database

def process_image(file: UploadFile, max_width: int = 1024) -> Image:
    # Read image file
    image_bytes = file.file.read()
    file.file.close()

    with Image.open(io.BytesIO(image_bytes)) as img:
        # Correct orientation based on EXIF data
        img = correct_orientation(img)

        # Resize the image
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * ratio)
            img = img.resize((max_width, new_height), Image.ANTIALIAS)

        # Convert img to byte array for further processing or saving
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', optimize=True, quality=80)
        img_byte_arr = img_byte_arr.getvalue()

        return img_byte_arr

def correct_orientation(img: Image) -> Image:
    exif = img._getexif()
    if exif is not None:
        orientation_key = 274  # cf ExifTags
        if orientation_key in exif:
            orientation = exif[orientation_key]
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    return img

def save_image_locally(image_bytes: bytes, filename: str):
    with open(filename, 'wb') as out_file:
        out_file.write(image_bytes)

