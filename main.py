from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
import datetime
from uuid import uuid4
from qrcode import QRCode
import qrcode
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import Optional
import tempfile
import os
from PIL import Image
import os
import io
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
            pk UUID PRIMARY KEY,
            id UUID NOT NULL,
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
    pk: Optional[str] = None
    id: Optional[str] = None
    food: str
    date_added: datetime.date
    expiration_date: datetime.date
    reminder_date: datetime.date
    suggested_expiration_date: datetime.date
    days_old: Optional[int] = None
    days_left: Optional[int] = None

@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM food_items")
    items = cur.fetchall()
    cur.close()
    conn.close()

    food_items = [FoodItem(pk=row[0], id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], reminder_date=row[5], suggested_expiration_date=row[6]) for row in items]

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
            "id": item[1],
            "food": item[2],
            "date_added": item[3],
            "expiration_date": item[4],
            "reminder_date": item[5],
            "suggested_expiration_date": item[6]
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

    food_item = FoodItem(id=item[1], food=item[2], date_added=item[3], expiration_date=item[4], reminder_date=item[5], suggested_expiration_date=item[6])

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
    
@app.get("/{item_id}/add/", response_class=HTMLResponse)
async def view_add_food_item(request: Request, item_id:str):

    return templates.TemplateResponse("add.html", {"request": request, "item_id": item_id})

@app.post("/{item_id}/add/", response_class=HTMLResponse)
async def add_food_item(
    item_id: str,
    food: str = Form(...),
    expiration_date: datetime.date = Form(...),
    reminder_date: datetime.date = Form(...),
    suggested_expiration_date: datetime.date = Form(...),
):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Generate a unique ID for the new food item
    #item_id = str(uuid4())
    item_pk = str(uuid4())

    # Insert the new food item into the database
    cursor.execute(
        "INSERT INTO food_items (id, food, date_added, expiration_date, reminder_date, suggested_expiration_date) VALUES (%s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, food, datetime.date.today(), expiration_date, reminder_date, suggested_expiration_date),
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

    days_old = (datetime.date.today() - item[3]).days
    days_left = (item[4] - datetime.date.today()).days

    food_item = FoodItem(id=item[1], food=item[2], date_added=item[3], days_old=days_old, days_left=days_left ,expiration_date=item[4], reminder_date=item[5], suggested_expiration_date=item[6])

    return templates.TemplateResponse("view.html", {"request": request, "item": food_item})

class QRRequest(BaseModel):
    data: str
    file_name: str

aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
#aws_session_token = 'YOUR_AWS_SESSION_TOKEN'  # Optional
s3 = boto3.client('s3',
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)

@app.get("/create_qr_code/")
async def create_qr_code():
    # Generate UUID
    item_id = str(uuid4())
    bucket_name = "qrfoodcodes"

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
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    img.save(temp_file, "PNG")
    temp_file.close()

    # Upload QR code to S3
    with open(temp_file.name, "rb") as file:
        s3.upload_fileobj(file, bucket_name, f"{item_id}.png")

    # Return the image as a StreamingResponse
    return StreamingResponse(buffer, media_type="image/png")
    #raise HTTPException(status_code=500, detail=f"Failed to save QR code to S3 bucket: {str(e)}")


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
        return RedirectResponse(url=f"/{item_id}/add/")
        conn = connect_to_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO food_items (pk, id, food, date_added, expiration_date, reminder_date, suggested_expiration_date) VALUES (%s, %s, %s, %s, %s, %s)",
            (item_id, "", datetime.date.today(), datetime.date.today(), datetime.date.today(), datetime.date.today()),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return RedirectResponse(url=f"/{item_id}/update/")


