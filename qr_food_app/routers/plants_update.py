from fpdf import FPDF
from fastapi import FastAPI, APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
from typing import Optional
import datetime
from pydantic import BaseModel, validator
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
    

    @validator('removed', pre=True)
    def convert_removed_to_bool(cls, v):
        return v == 't'  # Convert 't' to True, other values to False

@router.get("/all_plants/", response_class=HTMLResponse)
async def get_all_plants(
    request:Request):
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        fi.pk, 
        fi.id, 
        fi.removed, 
        fi.plant, 
        max_stage.max_plant_stage, 
        fi.task, 
        fi.task_date, 
        fi.location, 
        fi.notes, 
        max_stage.max_update_time, 
        fi.harvest_date
    FROM 
        plants fi
    INNER JOIN (
        SELECT 
            id, 
            MAX(plant_stage) AS max_plant_stage, 
            MAX(update_time) AS max_update_time
        FROM 
            plants
        WHERE 
            harvest_date IS NULL 
            AND removed = FALSE
        GROUP BY 
            id
    ) AS max_stage ON fi.id = max_stage.id 
    WHERE 
        fi.plant_stage = max_stage.max_plant_stage
        AND fi.update_time = max_stage.max_update_time
    ORDER BY 
        fi.id;
""")
    rows = cursor.fetchall()
    all_plants = [PlantItem(pk=row[0], id=row[1], removed=row[2], plant=row[3], plant_stage=row[4], task=row[5], task_date=row[6], location=row[7], notes=row[8], update_time=row[9], harvest_date=row[10]) for row in rows]
    conn.commit()
    cursor.close()
    conn.close()
    return templates.TemplateResponse("all_plants.html", {"all_plants": all_plants, "request": request})

@router.get("/{item_id}/plant_update/", response_class=HTMLResponse)
async def edit_food_item(
    request: Request, 
    item_id: str):

    plant_name = ""
    plant_item = {}
    location_list=[]
    query_string = f"WHERE fi.id = '{item_id}' ORDER by fi.id, fi.plant_stage;"
    plant_items = await get_plant_items(query_string)
    
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
    print(plant_items)
    return templates.TemplateResponse("plant_update.html", {"locations": location_list, "request": request, "plant_items": plant_items, "plant_item": plant_item, "item_id": item_id, "plant_name": plant_name})

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
        f"""SELECT id, MAX(plant_stage) AS largest_stage
        FROM plants
        WHERE id = %s
            AND harvest_date IS NULL
            AND removed = FALSE
        GROUP BY id;""",
        (item_id,)
    )
    latest = cursor.fetchone()
    print(latest)
    plant_stage =  latest[1]+1 if latest else 1

    # create new entry for edit so needs a new PK
    item_pk = str(uuid4())
    # capture time of edit
    update_time = datetime.datetime.now()

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





