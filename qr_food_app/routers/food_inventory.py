from fastapi import HTTPException, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi import FastAPI, APIRouter, Form, Request, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import os
import json
from typing import Optional
from ..utils import get_food_items, connect_to_db
import datetime
from uuid import uuid4

# Assuming you're in the routers directory 
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)
router = APIRouter()
app = FastAPI()
BUCKET_NAME = os.getenv("BUCKET_NAME")

def get_months(days):
    if days > 30:
        month = days // 30
        day = days % 30
        return(f"{month} months {day} days")
    else:
        return(f"{days} days")
# Define the request model for FoodItem and PlantItem

class FoodItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    food: str
    date_added: datetime.date
    expiration_date: datetime.date
    notes: Optional[str] = None
    days_old: Optional[int] = None
    update_time: Optional[datetime.datetime] = None
    date_consumed: Optional[datetime.date] = None
    location: Optional[str] = None
    days_left: Optional[str] = None
    image_url: Optional[str] = Field(None, description="The full URL to the image stored in S3")

@router.get("/food/", response_class=HTMLResponse)
async def read_items(request: Request, sort_by_expiration_date: bool = False, sort_order: Optional[str] = None, item_id: Optional[str] = None, upload_photo: Optional[str] = None):
    food_items = []
    location_list=[]
    query_string = ""
    if sort_by_expiration_date:
        order = "ASC" if sort_order == "asc" else "DESC"
        query_string = f" ORDER BY fi.expiration_date {order}"
        query_string += ";"
    rows = await get_food_items(query_string)
    for row in rows:
        if row[8] not in location_list:
            location_list.append(row[8])
        days_left = get_months((row[4] - datetime.date.today()).days)
        food_items.append(FoodItem(pk=row[0], id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], notes=row[5], update_time=row[6], date_consumed=row[7], location=row[8], image_url=row[9], days_left=days_left))
    if item_id:
        print('item_id')
        food_item = {}
        print(item_id)
        query_string = f"AND fi.id = '{item_id}'"
        rows = await get_food_items(query_string)
        print(f"rows {rows}")
        for row in rows:
            if row[8] not in location_list:
                location_list.append(row[8])
            if str(row[1]) == item_id: #if the qr id exists and not consumed then info will be available to update in modal
                food_item = FoodItem(
                    id=row[1],
                    food=row[2],
                    date_added=row[3],
                    expiration_date=row[4],
                    notes=row[5],
                    date_consumed=row[7],
                    location=row[8],
                    image_url=row[9]
                )
                food_item = food_item.model_dump_json()
        return templates.TemplateResponse("index.html", {"request": request, "food_items": food_items, "locations": location_list, "food_item": food_item})
    return templates.TemplateResponse("index.html", {"request": request, "food_items": food_items, "locations": location_list})

@router.post("/food/{item_id}/update/")
async def update_food_item(
    item_id: str, 
    food: Optional[str] = Form(None), 
    date_added: Optional[datetime.date] = Form(None), 
    expiration_date: Optional[datetime.date] = Form(None), 
    location: Optional[str] = Form(None),
    notes: Optional[str] = Form(None), 
    date_consumed: Optional[datetime.date] = Form(None),
    image_url:Optional[str] = Form(None)):
    print(f"here: {image_url} {notes}")
    print(image_url)
    # Find the latest entry based on the "update_time" column for the passed-in item.id

    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute(f"""
        SELECT * FROM food_items
        WHERE id = '{item_id}'
        ORDER BY update_time DESC
        LIMIT 1
        """, (item_id,))
        item = cursor.fetchone()
        # create new entry for edit so needs a new PK
        item_pk = str(uuid4())
        current_time = datetime.datetime.now()

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        food = food if food is not None else item[2]
        date_added = date_added if date_added is not None else item[3]
        expiration_date = expiration_date if expiration_date is not None else item[4]
        notes = notes if notes is not None else item[5]
        date_consumed = date_consumed if date_consumed is not None else item[7]
        location = location if location is not None else item[8]
        if image_url == 'yes' and item_id:
            image_url = f"https://{BUCKET_NAME}.s3.us-east-2.amazonaws.com/{item_id}.jpg"
        image_url = image_url if image_url is not None else item[9]
    
        cursor.execute(
        "INSERT INTO food_items (pk, id, food, date_added, expiration_date, notes, update_time, date_consumed, location, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, food, date_added, expiration_date, notes, current_time, date_consumed, location, image_url, ),
    )

        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return {"message": f"Update DB Successfully {image_url}"}

@router.post("/{item_id}/consumed/")
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
    return RedirectResponse(url="/", status_code=303)

@router.get("/{item_id}/view")
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