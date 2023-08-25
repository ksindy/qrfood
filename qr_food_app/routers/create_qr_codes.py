from fpdf import FPDF
from fastapi import FastAPI, APIRouter
import os
from typing import Optional
import datetime
from pydantic import BaseModel
from qrcode import QRCode
from uuid import uuid4
import boto3
import tempfile
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter()
app = FastAPI()

class QRRequest(BaseModel):
    data: str
    file_name: str

aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
#aws_session_token = 'YOUR_AWS_SESSION_TOKEN'  # Optional
s3 = boto3.client('s3',
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)

@router.get("/create_qr_codes/{N}")
async def create_qr_codes(N: int):
    # Generate N QR codes
    bucket_name = "qrfoodcodes"
    pdf = FPDF(unit = "in", format='A4') # Creating PDF in A4 size

    qr_per_row = 8  # The number of QR codes per row in the PDF. Adjust as necessary.
    qr_per_col = 10  # The number of QR codes per column in the PDF. Adjust as necessary.
    qr_counter = 0  # Counter for QR codes generated so far

    for i in range(N):
        # Generate UUID
        item_id = str(uuid4())

        # Create QR code
        qr = QRCode()
        qr.add_data(f"https://qrfood.herokuapp.com/{item_id}/")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the image to an in-memory buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Save QR code to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(temp_file, "PNG")
        temp_file.close()

        # Upload QR code to S3
        with open(temp_file.name, "rb") as file:
            s3.upload_fileobj(file, bucket_name, f"{item_id}.png")

        # Start a new page if we've filled the current one
        if qr_counter % (qr_per_row * qr_per_col) == 0:
            pdf.add_page()

        # Calculate the position of the QR code on the page
        x = (qr_counter % qr_per_row) * 1.2 + 0.1  # 1" size and 0.2" space
        y = (qr_counter // qr_per_row % qr_per_col) * 1.2 + 0.1  # 1" size and 0.2" space

        # Add QR code to the PDF
        pdf.image(temp_file.name, x = x, y = y, w = 1, h = 1) # 1"x1" size QR code
        
        # Delete the temporary file
        os.remove(temp_file.name)
        
        qr_counter += 1  # Increment the counter

    # Save the PDF to a temporary file
    pdf_output = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    pdf.output(pdf_output.name)

    # Return the PDF as a StreamingResponse
    file = open(pdf_output.name, "rb")
    headers = {'Content-Disposition': 'attachment; filename="out.pdf"'}
    return StreamingResponse(file, headers=headers, media_type="application/pdf")