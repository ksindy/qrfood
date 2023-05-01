from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
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

def sort_food_items_by_expiration_date(food_items):
    return sorted(food_items, key=lambda x: x.expiration_date)

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
            notes VARCHAR(255),
            update_time TIMESTAMP NOT NULL,
            date_consumed DATE
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
    notes: Optional[str] = None
    days_old: Optional[int] = None
    days_left: Optional[int] = None
    update_time: Optional[datetime.datetime] = None
    date_consumed: Optional[datetime.date] = None

@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request, sort_by_expiration_date: bool = False):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fi.pk, fi.id, fi.food, fi.date_added, fi.expiration_date, fi.notes, fi.update_time, fi.date_consumed
        FROM food_items fi
        INNER JOIN (
            SELECT id, MAX(update_time) AS max_update_time
            FROM food_items
            GROUP BY id
        ) AS mfi ON fi.id = mfi.id AND fi.update_time = mfi.max_update_time
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    food_items = [FoodItem(pk=row[0], id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], notes=row[5], update_time=row[6], date_consumed=row[7]) for row in rows]
    if sort_by_expiration_date:
        food_items = sort_food_items_by_expiration_date(food_items)
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
            "notes": item[5],
            "date_consumed": item[6]
        })

    return result

@app.get("/{item_id}/update/", response_class=HTMLResponse)
async def edit_food_item(
    request: Request, 
    item_id: str, 
    food: Optional[str] = Form(None), 
    expiration_date: Optional[datetime.date] = Form(None), 
    notes: Optional[str] = Form(None)):

    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_items WHERE id = %s ORDER BY update_time DESC LIMIT 1", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")

    food_item = FoodItem(id=item[1], food=item[2], date_added=item[3], expiration_date=item[4], notes=item[5], date_consumed=item[6])

    return templates.TemplateResponse("edit.html", {"request": request, "item": food_item})

@app.post("/{item_id}/update/", response_class=HTMLResponse)
async def update_food_item(
    item_id: str, 
    food: str = Form(...), 
    expiration_date: datetime.date = Form(...), 
    notes: Optional[str] = Form(None), 
    date_consumed: Optional[datetime.date] = Form(None)):
    
    conn = connect_to_db()
    cursor = conn.cursor()

    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())
    # capture time of edit
    dt = datetime.datetime.now()

    # get date_added from original entry and add to updated entry
    cursor.execute("SELECT date_added FROM food_items WHERE id=%s", (item_id,))
    date_added_row = cursor.fetchone()
    date_added = date_added_row[0] if date_added_row is not None else None

    cursor.execute(
        "INSERT INTO food_items (pk, id, food, date_added, expiration_date, notes, update_time, date_consumed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, food, date_added, expiration_date, notes, dt, date_consumed),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse("/", status_code=303)

@app.get("/{item_id}/add/", response_class=HTMLResponse)
async def view_add_food_item(request: Request, item_id:str):

    return templates.TemplateResponse("add.html", {"request": request, "item_id": item_id, "notes": None})

@app.post("/{item_id}/add/", response_class=HTMLResponse)
async def add_food_item(
    item_id: str,
    food: str = Form(...),
    expiration_date: datetime.date = Form(...),
    notes: Optional[str] = Form(None)
):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Generate a unique ID for the new food item
    #item_id = str(uuid4())
    item_pk = str(uuid4())
    # Capture the current time
    update_time = datetime.datetime.now()
    date_consumed = None

    # Insert the new food item into the database
    cursor.execute(
        "INSERT INTO food_items (pk, id, food, date_added, expiration_date, notes, update_time, date_consumed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, food, datetime.date.today(), expiration_date, notes, update_time, date_consumed),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse("/", status_code=303)

@app.get("/{item_id}/view/", response_class=HTMLResponse)
async def view_food_item(request: Request, item_id: str):
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_items WHERE id = %s ORDER BY update_time DESC LIMIT 1", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if not item:
        raise HTTPException(status_code=404, detail="Food item not found")

    days_old = (datetime.date.today() - item[3]).days
    days_left = (item[4] - datetime.date.today()).days

    food_item = FoodItem(id=item[1], food=item[2], date_added=item[3], days_old=days_old, days_left=days_left ,expiration_date=item[4], notes=item[5], date_consumed=item[6])

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

    cursor.execute("SELECT * FROM food_items WHERE id = %s ORDER BY update_time DESC LIMIT 1", (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if item:
        return RedirectResponse(url=f"/{item_id}/view/")
    else:
        # Add the new UUID to the database before redirecting to the update page
        return RedirectResponse(url=f"/{item_id}/add/")


