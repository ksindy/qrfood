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
    use_ssl = 'localhost' not in os.getenv("DATABASE_URL")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require' if use_ssl else None)
    return conn

def process_image(file: UploadFile, max_width: int = 1024) -> bytes:
    url_and_jpeg = scan_qr_image(file)
    uuid = url_and_jpeg[0].rstrip('/').split('/')[-1] 
    if not upload_image_to_s3(url_and_jpeg[1], "qr-jpgs-purgatory", uuid + ".jpg"):
        raise HTTPException(status_code=500, detail="Failed to upload image to S3.")
    return(uuid)

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
    # Upload to S3
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    try:
        s3_client.put_object(Body=image_bytes, Bucket=bucket_name, Key=object_name, ContentType='image/jpeg')
        return True
    except NoCredentialsError:
        return False

# async def upload_image(file: UploadFile = File(...)):
#     # Validate the file type
#     if not file.content_type.startswith('image/'):
#         raise HTTPException(status_code=400, detail="Invalid file type")

#     # Process the image file
#     processed_img_bytes = process_image(file)

#     # Save the processed image locally
#     save_image_locally(processed_img_bytes, f'{images_path}/image4.jpg')
#     # Upload the processed image to S3
#     success = upload_image_to_s3(
#         processed_img_bytes, 
#         'qr-food-images', 
#         'test.jpg'
#     )

# def save_image_locally(image_bytes: bytes, filename: str):
#     with open(filename, 'wb') as out_file:
#         out_file.write(image_bytes)

