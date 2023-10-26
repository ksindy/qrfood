from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import psycopg2
import datetime
from uuid import uuid4
from fastapi.responses import StreamingResponse
from io import BytesIO
from typing import Optional
import tempfile
import os
from PIL import Image
import os
from .routers import background_tasks, create_qr_codes, plants, plants_edit
from dotenv import load_dotenv
from os import getenv

load_dotenv()  # take environment variables from .env.
app = FastAPI()
app.include_router(background_tasks.router)
app.include_router(create_qr_codes.router)
app.include_router(plants.router)
app.include_router(plants_edit.router)
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# Connect to the database
def connect_to_db():
    use_ssl = 'localhost' not in os.getenv("DATABASE_URL")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require' if use_ssl else None)
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
            date_consumed DATE,
            location VARCHAR(255)
            )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plants (
            pk UUID PRIMARY KEY,
            id UUID NOT NULL,
            plant VARCHAR(255) NOT NULL,
            date_added DATE NOT NULL,
            treatment VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            notes VARCHAR(255),
            update_time TIMESTAMP NOT NULL,
            harvest_date TIMESTAMP
            )
    """)
    conn.commit()
    cursor.close()
    conn.close()
init_db()

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_PHONE_NUMBER = os.environ['TWILIO_PHONE_NUMBER']

# Define the request model for FoodItem and PlantItem
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
    location: Optional[str] = None

class PlantItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    plant: str
    date_added: datetime.date
    treatment: str
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None

async def get_food_items(query_string):
    conn = connect_to_db()
    cur = conn.cursor()

    query = """
        SELECT fi.pk, fi.id, fi.food, fi.date_added, fi.expiration_date, fi.notes, fi.update_time, fi.date_consumed, fi.location
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

    food_items = [FoodItem(pk=row[0], days_left=(row[4] - datetime.date.today()).days, id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], notes=row[5], update_time=row[6], date_consumed=row[7], location=row[8]) for row in rows]

    return food_items

@app.get("/", response_class=HTMLResponse)
async def read_items(request: Request, sort_by_expiration_date: bool = False, sort_order: Optional[str] = None):
    query_string = ""
    if sort_by_expiration_date:
        order = "ASC" if sort_order == "asc" else "DESC"
        query_string = f" ORDER BY fi.expiration_date {order}"
        query_string += ";"
    food_items = await get_food_items(query_string)
    return templates.TemplateResponse("index.html", {"request": request, "food_items": food_items})

@app.get("/favicon.ico")
def read_favicon():
    raise HTTPException(status_code=204, detail="No content")

@app.get("/{item_id}/update/", response_class=HTMLResponse)
async def edit_food_item(
    request: Request, 
    item_id: str):

    food_item = {}
    location_list=[]
    query_string = ";"
    food_items = await get_food_items(query_string)
    for item in food_items:
        if item.location not in location_list:
            location_list.append(item.location)
        if str(item.id) == item_id:
            food_item = {
                "id": item.id,
                "food": item.food,
                "date_added": item.date_added,
                "expiration_date": item.expiration_date,
                "notes": item.notes,
                "date_consumed": item.date_consumed,
                "location": item.location
                }
    return templates.TemplateResponse("edit.html", {"locations": location_list, "request": request, "item": food_item, "item_id": item_id})

@app.post("/{item_id}/update/")
async def update_food_item(
    item_id: str, 
    food: str = Form(...), 
    expiration_date: datetime.date = Form(...), 
    notes: Optional[str] = Form(None), 
    date_consumed: Optional[datetime.date] = Form(None),
    location: Optional[str] = Form(None)):
    
    conn = connect_to_db()
    cursor = conn.cursor()

    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())
    # capture time of edit
    dt = datetime.datetime.now()

    # get date_added from original entry and add to updated entry
    cursor.execute("SELECT date_added FROM food_items WHERE id=%s", (item_id,))
    date_added_row = cursor.fetchone()
    date_added = date_added_row[0] if date_added_row is not None else datetime.date.today()

    cursor.execute(
        "INSERT INTO food_items (pk, id, food, date_added, expiration_date, notes, update_time, date_consumed, location) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, food, date_added, expiration_date, notes, dt, date_consumed, location),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"success": True, "message": "Successfully updated the food item."}

# @app.get("/{item_id}/view/", response_class=HTMLResponse)
# async def view_food_item(request: Request, item_id: str):
#     conn = connect_to_db()
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM food_items WHERE id = %s ORDER BY update_time DESC LIMIT 1", (item_id,))
#     item = cursor.fetchone()

#     cursor.close()
#     conn.close()

#     if not item:
#         raise HTTPException(status_code=404, detail="Food item not found")

#     days_old = (datetime.date.today() - item[3]).days
#     days_left = (item[4] - datetime.date.today()).days

#     food_item = FoodItem(id=item[1], food=item[2], date_added=item[3], days_old=days_old, days_left=days_left ,expiration_date=item[4], notes=item[5], date_consumed=item[6], location=item[7])

#     return templates.TemplateResponse("view.html", {"request": request, "item": food_item})

@app.get("/consumed_items/", response_class=HTMLResponse)
async def read_updated_items(request: Request, sort_by_expiration_date: bool = False):
    conn = connect_to_db()
    cur = conn.cursor()

    query = """
        SELECT fi.pk, fi.id, fi.food, fi.date_added, fi.expiration_date, fi.notes, fi.update_time, fi.date_consumed, fi.location
        FROM food_items fi
        INNER JOIN (
            SELECT id, MAX(update_time) AS max_update_time
            FROM food_items
            GROUP BY id
        ) AS mfi ON fi.id = mfi.id AND fi.update_time = mfi.max_update_time
        WHERE fi.date_consumed IS NOT NULL;
    """

    if sort_by_expiration_date:
        query += " ORDER BY fi.expiration_date"

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    food_items = [FoodItem(pk=row[0], id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], notes=row[5], update_time=row[6], date_consumed=row[7], location=row[8]) for row in rows]

    return templates.TemplateResponse("consumed.html", {"request": request, "food_items": food_items})

@app.get("/{item_id}/view")
async def handle_qr_scan(item_id: str):
    conn = connect_to_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM food_items
        WHERE id = %s
        ORDER BY update_time DESC
        LIMIT 1
    """, (item_id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if item and item[7] is None:
        return RedirectResponse(url=f"/{item_id}/view/")
    else:
        # Add the new UUID to the database before redirecting to the update page
        return RedirectResponse(url=f"/{item_id}/update/")
    
@app.post("/{item_id}/consumed/")
async def add_consumed_date(item_id: str):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Find the latest entry based on the "update_time" column for the passed-in item.id
    cursor.execute("""
        SELECT * FROM food_items
        WHERE id = %s
        ORDER BY update_time DESC
        LIMIT 1
    """, (item_id,))
    item = cursor.fetchone()
    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Create a new entry with the same info, but add the current time to the "update_time" column and "date_consumed" column
    current_time = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO food_items (pk, id, food, date_added, expiration_date, notes, update_time, date_consumed, location) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, item[2], item[3], item[4], item[5], current_time, current_time, item[7]),
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to the root page
    return RedirectResponse("/", status_code=303)

@app.get("/{item_id}/")
async def handle_qr_scan(item_id: str):
    # Add the new UUID to the database before redirecting to the update page
    return RedirectResponse(url=f"/{item_id}/update/")