from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
import datetime
from uuid import uuid4
import qrcode
from fastapi.responses import FileResponse
from typing import Optional

app = FastAPI()

# Database configuration
DATABASE = {
    "user": "karlysindy",
    "password": "",
    "host": "https://qrfood.herokuapp.com/",
    "port": "5432",
    "dbname": "food"
}

# Connect to the database
def connect_to_db():
    conn = psycopg2.connect(**DATABASE)
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
    expiration_date: datetime.date
    reminder_date: datetime.date
    suggested_expiration_date: datetime.date

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

#This function generates a QR code for the given unique identifier and returns it as a PNG image.
@app.get("/food_items/{item_id}/qrcode")
async def get_qr_code(item_id: str):
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(item_id)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"qrcodes/{item_id}.png")

    return FileResponse(f"qrcodes/{item_id}.png", media_type="image/png")

# Write data to the database
@app.post("/food_items/")
async def create_food_item(item: FoodItem):
    conn = connect_to_db()
    cursor = conn.cursor()

    date_added = datetime.date.today()

    if item.id is None:
        item.id = str(uuid4())

    insert_query = sql.SQL("""
        INSERT INTO food_items (id, food, date_added, expiration_date, reminder_date, suggested_expiration_date)
        VALUES (%s, %s, %s, %s, %s, %s)
    """)

    cursor.execute(insert_query, (item.id, item.food, date_added, item.expiration_date, item.reminder_date, item.suggested_expiration_date))

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "success", "message": "Food item has been added.", "id": item.id}
