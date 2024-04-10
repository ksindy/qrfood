from fastapi import HTTPException, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, APIRouter, Form, Request, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
import os
from typing import Optional
from ..utils import get_food_items, connect_to_db
import datetime

# Assuming you're in the routers directory 
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)
router = APIRouter()
app = FastAPI()

@router.get("/{item_id}/update/", response_class=HTMLResponse)
async def edit_food_item(
    request: Request, 
    item_id: str,
    upload_photo: Optional[str] = None):
    image_url = ""
    if upload_photo == "yes":
        image_url = f"https://{os.getenv('QR_IMAGES_BUCKET')}.s3.amazonaws.com/{item_id}"
    food_item = {}
    location_list=[]
    query_string = ";"
    rows = await get_food_items(query_string)
    for row in rows:
        if row[8] not in location_list:
            location_list.append(row[8])
        if str(row[1]) == item_id: #if the qr id exists and not consumed then info will be available to update in modal
            print(row)
            if upload_photo == "yes" or row[9]:
                image_url = f"https://{os.getenv('QR_IMAGES_BUCKET')}.s3.amazonaws.com/{item_id}"
            else:
                image_url = ""
            food_item = {
                "id": row[1],
                "food": row[2],
                "date_added":row[3],
                "expiration_date": row[4],
                "notes": row[5],
                "date_consumed": row[7],
                "location": row[8],
                "image_url": image_url
            }

    return templates.TemplateResponse("edit.html", {"locations": location_list, "request": request, "item": food_item, "item_id": item_id})

@router.post("/{item_id}/update/")
async def update_food_item(
    item_id: str, 
    food: str = Form(...), 
    expiration_date: datetime.date = Form(...), 
    location: Optional[str] = Form(...),
    otherLocation: Optional[str] = Form(None),
    notes: Optional[str] = Form(None), 
    date_consumed: Optional[datetime.date] = Form(None),
    upload_photo: Optional[str] = None):
    
    conn = connect_to_db()
    cursor = conn.cursor()
    print(otherLocation)
    # if location == "other" and otherLocation:
    #     location = otherLocation 
    # if upload_photo == "yes":


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

    return RedirectResponse(url="/", status_code=303)

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