from fpdf import FPDF
from fastapi import FastAPI, APIRouter, Form, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
from typing import Optional
import datetime
from pydantic import BaseModel, validator, BaseSettings
from qrcode import QRCode
from uuid import uuid4
import boto3
import tempfile
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.templating import Jinja2Templates

from ..utils import connect_to_db, get_plant_items

# Assuming you're in the routers directory 
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)
router = APIRouter()
app = FastAPI()

class Settings(BaseSettings):
    base_url: str
    class Config:
        env_file = '.env'

def get_settings():
    return Settings()

def get_months(days):
    if days > 30:
        month = days // 30
        day = days % 30
        return(f"{month} months {day} days")
    else:
        return(f"{days} days")
    
class PlantItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    removed: Optional[bool]
    plant: str
    plant_stage: int
    task: str
    task_date: datetime.date
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None
    day_from_zero: Optional[str] = None
    
    @validator('removed', pre=True)
    def convert_removed_to_bool(cls, v):
        return v == 't'  # Convert 't' to True, other values to False

@router.get("/all_plants/", response_class=HTMLResponse)
async def get_all_plants(
    request:Request, 
    settings: Settings = Depends(get_settings)):
    all_plants = []
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        WITH LatestUpdate AS (
            SELECT 
                id, plant_stage, MAX(update_time) AS max_update_time
            FROM 
                plants
            GROUP BY 
                id, plant_stage
        ),
        ViableUpdates AS (
            SELECT 
                lu.id, lu.plant_stage, lu.max_update_time
            FROM 
                LatestUpdate lu
            INNER JOIN 
                plants p ON p.id = lu.id AND p.plant_stage = lu.plant_stage AND p.update_time = lu.max_update_time
            WHERE 
                p.harvest_date IS NULL AND p.removed = FALSE
        )
        SELECT 
            p.*
        FROM 
            plants p
        INNER JOIN 
            ViableUpdates vu ON p.id = vu.id AND p.plant_stage = vu.plant_stage AND p.update_time = vu.max_update_time
        WHERE 
            p.harvest_date IS NULL AND p.removed = FALSE
        ORDER BY 
            p.id, p.task_date;
""")
    rows = cursor.fetchall()
    id = ""
    first_row = True
    for row in rows:
        if id != row[1] and first_row == False:
            print(task_date)
            print(zero_day_task_date)
            day_from_zero = get_months((datetime.date.today() - zero_day_task_date).days)
            all_plants.append(PlantItem(id=id, pk=pk, removed=removed, plant=plant, plant_stage=plant_stage, task=task, task_date=task_date, location=location, notes=notes, update_time=update_time, harvest_date=harvest_date, day_from_zero=day_from_zero))
            zero_day_task_date = row[6]
        elif first_row == True:    
            zero_day_task_date = row[6]
            first_row = False
            zero_day_task_date = row[6]
        task_date = row[6]
        id = row[1]
        pk=row[0]
        removed=row[2]
        plant=row[3]
        plant_stage=row[4]
        task=row[5]
        location=row[7]
        notes=row[8]
        update_time=row[9]
        harvest_date=row[10]
    day_from_zero = get_months((datetime.date.today() - zero_day_task_date).days)
    all_plants.append(PlantItem(pk=row[0], id=row[1], removed=row[2], plant=row[3], plant_stage=row[4], task=row[5], task_date=row[6], day_from_zero=day_from_zero, location=row[7], notes=row[8], update_time=row[9], harvest_date=row[10])) 
    conn.commit()
    cursor.close()
    conn.close()
    return templates.TemplateResponse("all_plants.html", {"all_plants": all_plants, "request": request, "base_url": settings.base_url})

@router.get("/{item_id}/plant_update/", response_class=HTMLResponse)
async def edit_food_item(
    request: Request, 
    item_id: str, 
    settings: Settings = Depends(get_settings)):

    plant_name = ""
    plant_item = {}
    plant_items = []
    record_day_zero = False
    location_list=[]
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        WITH LatestUpdates AS (
            SELECT 
                id,
                plant_stage,
                MAX(update_time) AS max_update_time
            FROM 
                plants
            WHERE 
                id = %s
            GROUP BY 
                id, plant_stage
        )
        SELECT p.*
        FROM 
            plants p
        INNER JOIN 
            LatestUpdates lu ON p.id = lu.id 
            AND p.plant_stage = lu.plant_stage 
            AND p.update_time = lu.max_update_time
        WHERE 
            p.harvest_date IS NULL 
            AND p.removed = FALSE
        ORDER BY 
            p.task_date ASC; 
        """,  (item_id, ))
    rows = cursor.fetchall()
    for row in rows:
        task_date = row[6]
        if record_day_zero == False:
            day_from_zero = 0
            zero_date = task_date
            record_day_zero = True
        else:
            day_from_zero = (task_date - zero_date).days
            if day_from_zero > 30:
                month = day_from_zero // 30
                day = day_from_zero % 30
                day_from_zero = f"{month} month(s) {day} day(s)"
        plant_items.append(PlantItem(pk=row[0], id=row[1], removed=row[2], plant=row[3], plant_stage=row[4], task=row[5], task_date=row[6], location=row[7], notes=row[8], update_time=row[9], harvest_date=row[10], day_from_zero=day_from_zero))
    conn.commit()
    cursor.close()
    conn.close()
    
    for item in plant_items:
        if item.location not in location_list:
            location_list.append(item.location)
        if str(item.id) == item_id:
            plant_item = {
                "id": item.id,
                "plant": item.plant,
                "plant_stage": item.plant_stage,
                "task": item.task,
                "location": item.location,
                "notes": item.notes,
                "harvest_date": item.harvest_date,
                }
            plant_name = item.plant
            plant_name = plant_name.capitalize()
    return templates.TemplateResponse("plant_update.html", {"locations": location_list, "request": request, "plant_items": plant_items, "plant_item": plant_item, "item_id": item_id, "plant_name": plant_name,  "base_url": settings.base_url})

@router.post("/{item_id}/plant_update/", response_class=HTMLResponse)
async def update_plant_item(
    item_id: str,
    removed: bool = Form(...),
    plant_name: str = Form(...),
    task: Optional[str] = Form(None), 
    task_date: datetime.date = Form(...), 
    location: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    harvest_date: Optional[datetime.date] = Form(None)
):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute(
        """
            WITH LatestUpdate AS (
            SELECT id, MAX(update_time) AS max_update_time
            FROM plants
            WHERE id = %s
            GROUP BY id
            )
            SELECT p.id, MAX(p.plant_stage) AS largest_stage
            FROM plants p
            INNER JOIN LatestUpdate lu ON p.id = lu.id AND p.update_time = lu.max_update_time
            WHERE p.harvest_date IS NULL AND p.removed = FALSE
            GROUP BY p.id;
        """,
        (item_id,)
    )
    latest = cursor.fetchone()
    plant_stage =  latest[1]+1 if latest else 1

    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())
    # capture time of edit
    update_time = datetime.datetime.now()

    plant_name = plant_name.lower().strip()

    cursor.execute(
        "INSERT INTO plants (pk, id, removed, plant, plant_stage, task, task_date, location, notes, update_time, harvest_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, removed, plant_name, plant_stage, task, task_date, location, notes, update_time, harvest_date)
    )

    conn.commit()
    cursor.close()
    conn.close()

    url = router.url_path_for("edit_food_item", item_id=item_id)
    response = RedirectResponse(url=url, status_code=303)
    return response

@router.post("/{item_id}/remove_plant/", response_class=HTMLResponse)
async def change_removed_to_true(item_id: str, plant_stage: int =  Form(...), pk: str =  Form(...)):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Find the latest entry based on the "update_time" column for the passed-in item.id
    cursor.execute("""
        SELECT * FROM plants
        WHERE id = %s
            AND plant_stage = %s
            AND pk = %s
        ORDER BY update_time DESC
        LIMIT 1
    """, (item_id, plant_stage, pk))
    row = cursor.fetchone()
    item = PlantItem(pk=row[0], id=row[1], removed=row[2], plant=row[3], plant_stage=row[4], task=row[5], task_date=row[6], location=row[7], notes=row[8], update_time=row[9], harvest_date=row[10])
    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())
    removed = True

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Create a new entry with the same info, but add the current time to the "update_time" column and "date_consumed" column
    current_time = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO plants (pk, id, removed, plant, plant_stage, task, task_date, location, notes, update_time, harvest_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (item_pk, item_id, removed, item.plant, item.plant_stage, item.task, item.task_date, item.location, item.notes, current_time, item.harvest_date)
    )

    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to the root page
    return RedirectResponse("/all_plants/", status_code=303)




