from fastapi import UploadFile, HTTPException
import os
import psycopg2
from PIL import Image
import pillow_heif 
import pillow_heif
import io
import boto3
from botocore.exceptions import NoCredentialsError
from pyzbar.pyzbar import decode
from typing import Tuple, Union

class UnsupportedFileTypeError(Exception):
    pass

class QRCodeNotFoundError(Exception):
    pass

# Connect to the database
def connect_to_db():
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
    return conn

def process_image(file: UploadFile, max_width: int = 1024) -> bytes:
    url_and_jpeg = scan_qr_image(file)
    uuid = url_and_jpeg[0].rstrip('/').split('/')[-1]
    object_name = uuid + ".jpg"
    if not upload_image_to_s3(url_and_jpeg[1], os.getenv("QR_IMAGES_BUCKET"), object_name):
        raise HTTPException(status_code=500, detail="Failed to upload image to S3.")
    s3_url = f"https://{os.getenv('QR_IMAGES_BUCKET')}.s3.amazonaws.com/{object_name}"
    return uuid

def scan_qr_image(file: UploadFile):
    # Read the file bytes
    file_bytes = file.file.read()
    file.file.close()

    # Check file type
    content_type = file.content_type
    if content_type == "image/heic":
        # Process HEIF files
        heif_file = pillow_heif.read_heif(file_bytes)
        image = Image.frombytes(
            heif_file.mode, 
            heif_file.size, 
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
    elif content_type == "image/jpeg":
        # Process JPG files
        image = Image.open(io.BytesIO(file_bytes))
    else:
        return "Error: Unsupported file type. Please upload a HEIF or JPG image."

    # Convert image to JPEG format for consistency
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=85)
    img_byte_arr.seek(0)
    
    # Decode QR code from the image
    decoded_objects = decode(image)
    decoded_data = [obj.data.decode('utf-8') for obj in decoded_objects]

    # Return decoded data and image in JPEG format
    if decoded_data:
        return decoded_data[0], img_byte_arr
    else:
        return "No QR code found.", img_byte_arr

def upload_image_to_s3(image_bytes: bytes, bucket_name: str, object_name: str):
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    try:
        s3_client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_name, ContentType='image/jpeg')
        return {"message": "Upload successful", "imageUrl": f"https://{bucket_name}.s3.amazonaws.com/{object_name}"}
    except NoCredentialsError:
        return {"message": "Upload failed due to credential issues"}

async def get_food_items(query_string):
    conn = connect_to_db()
    cur = conn.cursor()

    query = """
        SELECT fi.pk, fi.id, fi.food, fi.date_added, fi.expiration_date, fi.notes, fi.update_time, fi.date_consumed, fi.location, fi.image_url
        FROM food_items fi
        INNER JOIN (
            SELECT id, MAX(update_time) AS max_update_time
            FROM food_items
            GROUP BY id
        ) AS mfi ON fi.id = mfi.id AND fi.update_time = mfi.max_update_time
        WHERE date_consumed IS NULL
       
    """
    query = query + query_string
        
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

