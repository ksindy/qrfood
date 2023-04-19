from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
import datetime
from uuid import uuid4
import qrcode
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import Optional
import os
from PIL import Image
import os
import boto3
from botocore.exceptions import NoCredentialsError

app = FastAPI()
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# Connect to the database
def connect_to_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    return conn

# Initialize the database
def init_db():
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            id UUID PRIMARY KEY,
            food VARCHAR(255) NOT NULL,
            date_added DATE NOT NULL,
            expiration_date DATE NOT NULL,
            reminder_date DATE NOT NULL,
            suggested_expiration_date DATE NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

init_db()

# Define the request model
class FoodItem(BaseModel):
    id: Optional[str] = None
    food: str
    date_added: datetime.date
    expiration_date: datetime.date
    reminder_date: datetime.date
    suggested_expiration_date: datetime.date
    days_old: Optional[int] = None

@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM food_items")
    items = cur.fetchall()
    cur.close()
    conn.close()

    food_items = [FoodItem(id=row[0], food=row[1], date_added=row[2], expiration_date=row[3], reminder_date=row[4], suggested_expiration_date=row[5]) for row in items]

    return templates.TemplateResponse("index.html", {"request": request, "food_items": food_items})

@app.get("/food_items/")
async def get_food_items():
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_items")
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    result = []
    for item in items:
        result.append({
            "id": item[0],
            "food": item[1],
            "date_added": item[2],
            "expiration_date": item[3],
            "reminder_date": item[4],
            "suggested_expiration_date": item[5]
        })

    return result

@app.get("/{item_id}/update/", response_class=HTMLResponse)
async def edit_food_item(request: Request, item_id: str, food: Optional[str] = Form(None), expiration_date: Optional[datetime.date] = Form(None), reminder_date: Optional[datetime.date] = Form(None), suggested_expiration_date: Optional[datetime.date] = Form(None)):
    conn = connect_to_db()
    cursor = conn.cursor()

    if request.method == "POST" and food and expiration_date and reminder_date and suggested_expiration_date:
        update_query = sql.SQL("""
            UPDATE food_items
            SET food = %s, expiration_date = %s, reminder_date = %s, suggested_expiration_date = %s
            WHERE id = %s
        """)
        
    cursor.execute("SELECT * FROM food_items WHERE id=%s", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")

    food_item = FoodItem(id=item[0], food=item[1], date_added=item[2], expiration_date=item[3], reminder_date=item[4], suggested_expiration_date=item[5])

    return templates.TemplateResponse("edit.html", {"request": request, "item": food_item})

@app.post("/{item_id}/update/", response_class=HTMLResponse)
async def update_food_item(item_id: str, food: str = Form(...), expiration_date: datetime.date = Form(...), reminder_date: datetime.date = Form(...), suggested_expiration_date: datetime.date = Form(...)):
    conn = connect_to_db()
    cursor = conn.cursor()

    update_query = sql.SQL("""
        UPDATE food_items
        SET food = %s, expiration_date = %s, reminder_date = %s, suggested_expiration_date = %s
        WHERE id = %s
    """)

    cursor.execute(update_query, (food, expiration_date, reminder_date, suggested_expiration_date, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse("/", status_code=303)
    
@app.get("/add", response_class=HTMLResponse)
async def view_add_food_item(request: Request):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM food_items")
    items = cur.fetchall()
    cur.close()
    conn.close()

    food_items = [FoodItem(id=row[0], food=row[1], date_added=row[2], expiration_date=row[3], reminder_date=row[4], suggested_expiration_date=row[5]) for row in items]

    return templates.TemplateResponse("add.html", {"request": request})

@app.post("/add", response_class=HTMLResponse)
async def add_food_item(
    food: str = Form(...),
    expiration_date: datetime.date = Form(...),
    reminder_date: datetime.date = Form(...),
    suggested_expiration_date: datetime.date = Form(...),
):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Generate a unique ID for the new food item
    item_id = str(uuid4())

    # Insert the new food item into the database
    cursor.execute(
        "INSERT INTO food_items (id, food, date_added, expiration_date, reminder_date, suggested_expiration_date) VALUES (%s, %s, %s, %s, %s, %s)",
        (item_id, food, datetime.date.today(), expiration_date, reminder_date, suggested_expiration_date),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse("/", status_code=303)

@app.get("/{item_id}/view/", response_class=HTMLResponse)
async def view_food_item(request: Request, item_id: str):
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_items WHERE id=%s", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")

    days_old = (datetime.date.today() - item[2]).days

    food_item = FoodItem(id=item[0], food=item[1], date_added=item[2], days_old=days_old ,expiration_date=item[3], reminder_date=item[4], suggested_expiration_date=item[5])

    return templates.TemplateResponse("view.html", {"request": request, "item": food_item})

# Configure the S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=["AWS_SECRET_ACCESS_KEY"],
    region_name="us-east-2",
)

BUCKET_NAME = "qrfoodcodes"


@app.get("/create_qr_code/")
async def create_qr_code():
    # Generate a unique UUID
    item_id = str(uuid4())

    # Create a QR code
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )
    qr.add_data(f"https://qrfood.herokuapp.com/{item_id}/")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the QR code to a BytesIO object
    buffer = BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)
    file_name = f"{item_id}.png"
    # Save the QR code to the S3 bucket
    object_key = f"{item_id}.png"
    try:
        s3_client.upload_file(
  file_name,
  BUCKET_NAME,
            object_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": "image/png",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save QR code to S3 bucket: {str(e)}")

    # Build the public URL for the uploaded QR code
    qr_code_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_key}"

    # Return the QR code URL as a response
    return JSONResponse(content={"qr_code_url": qr_code_url})


# BUCKET_NAME = "qrfoodcodes"
# # Initialize the S3 client
# s3 = boto3.client('s3')
# @app.get("/create_qr_code/")
# async def create_qr_code():
#     # Generate a unique UUID
#     item_id = str(uuid4())

#     # Create a QR code
#     qr = qrcode.QRCode(
#         version=1,
#         box_size=10,
#         border=4,
#     )
#     qr.add_data(f"https://qrfood.herokuapp.com/{item_id}/")
#     qr.make(fit=True)
#     img = qr.make_image(fill_color="black", back_color="white")

#     # Save the QR code to a BytesIO object
#     buffer = BytesIO()
#     img.save(buffer, "PNG")
#     buffer.seek(0)

#     # Save the QR code to the S3 bucket
#     object_name = f"{item_id}.png"
#     try:
#         #s3.upload_fileobj(buffer, BUCKET_NAME, object_name, ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/png'})
#         s3.upload_fileobj(buffer, BUCKET_NAME, object_name, ExtraArgs={'ACL': 'public-read'})
#     except NoCredentialsError:
#         raise HTTPException(status_code=500, detail="AWS credentials not found")

#     # Generate the public URL for the QR code
#     qr_code_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"

#     # Return a redirect to the QR code image
#     return RedirectResponse(qr_code_url)


@app.get("/{item_id}/")
async def handle_qr_scan(item_id: str):
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_items WHERE id = %s", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if item:
        return RedirectResponse(url=f"/{item_id}/view/")
    else:
        # Add the new UUID to the database before redirecting to the update page
        conn = connect_to_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO food_items (id, food, date_added, expiration_date, reminder_date, suggested_expiration_date) VALUES (%s, %s, %s, %s, %s, %s)",
            (item_id, "", datetime.date.today(), datetime.date.today(), datetime.date.today(), datetime.date.today()),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return RedirectResponse(url=f"/{item_id}/update/")


