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
    plant: str
    plant_stage: int
    task: str
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None
    removed: Optional[bool] = None 

    @validator('removed', pre=True)
    def convert_removed_to_bool(cls, v):
        return v == 't'  # Convert 't' to True, other values to False

@router.get("/plants/", response_class=HTMLResponse)
async def list_plant_items(
    request: Request):

    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fi.pk, fi.id, fi.plant, fi.plant_stage, fi.task, fi.location, fi.notes, fi.update_time, fi.harvest_date, fi.removed
        FROM plants fi
        INNER JOIN (
            SELECT id, MAX(plant_stage) AS max_plant_stage, MAX(update_time) AS max_update_time
            FROM plants
            WHERE harvest_date IS NULL AND removed = FALSE
            GROUP BY id
        ) AS mfi ON fi.id = mfi.id AND fi.plant_stage = mfi.max_plant_stage AND fi.update_time = mfi.max_update_time
        ORDER BY fi.id, fi.plant_stage;
    """)
    plant_items = cursor.fetchall()
    
    # for item in plant_items:
    #     plant_item = {
    #         "id": item[1],
    #         "plant": item[3],
    #         "plant_stage": item[4],
    #         "task": item[5],
    #         "location": item[6],
    #         "notes": item[7],
    #         "harvest_date": item[9],
    #         }

    return templates.TemplateResponse("plants.html", { "request": request, "plant_items": plant_items})
