from fpdf import FPDF
from fastapi import FastAPI, APIRouter, Form, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, validator, BaseSettings
from qrcode import QRCode
from uuid import uuid4
import boto3, asyncpg
import tempfile, databases, sqlalchemy
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from ..utils import connect_to_db, connect_to_async_db

# Assuming you're in the routers directory 
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)
router = APIRouter()
app = FastAPI()

def is_current_week(date):
    today = datetime.today()
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)
    return start_week.date() <= date <= end_week.date()

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
dt = datetime.now()
class ChickenItem(BaseModel):
    chicken_name: str
    age: str
    egg_today: int = 0
    egg_week: int = 0
    egg_month: int = 0
    egg_total: int = 0

class EggData(BaseModel):
    chickenName: str
    timeOfDay: str
    eggDate: date

    # @validator('removed', pre=True)
    # def convert_removed_to_bool(cls, v):
    #     return v == 't'  # Convert 't' to True, other values to False

chickens = ["nugget", "dawn", "wolf", "chewbawka"]
chickens_birthday_str = "2023-04-05"
flock = {}
def calculate_age(birthdate_str):
    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
    today = date.today()
    total_months = (today.year - birthdate.year) * 12 + today.month - birthdate.month
    if today.day < birthdate.day:
        total_months -= 1
    years = total_months // 12
    months = total_months % 12
    year_str = f"{years} year{'s' if years != 1 else ''}"
    month_str = f"{months} month{'s' if months != 1 else ''}"
    if years > 0:
        return f"{year_str} and {month_str} old"
    else:
        return f"{month_str} old"

for ind_chicken in chickens:
    chickens_age = calculate_age(chickens_birthday_str)
    flock[ind_chicken] = ChickenItem(chicken_name=ind_chicken, age=chickens_age)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
print(DATABASE_URL)
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

@router.on_event("startup")
async def startup():
    await database.connect()

@router.on_event("shutdown")
async def shutdown():
    await database.disconnect()

query_today = """
SELECT chicken_name, COUNT(*) as total_today
FROM chicken_eggs
WHERE egg_date = CURRENT_DATE AND removed = FALSE
GROUP BY chicken_name;
"""

query_week = """
SELECT chicken_name, COUNT(*) as total_this_week
FROM chicken_eggs
WHERE egg_date >= date_trunc('week', CURRENT_DATE) AND removed = FALSE
GROUP BY chicken_name;
"""

query_month = """
SELECT chicken_name, COUNT(*) as total_this_month
FROM chicken_eggs
WHERE egg_date >= date_trunc('month', CURRENT_DATE) AND removed = FALSE
GROUP BY chicken_name;
"""

query_total = """
SELECT chicken_name, COUNT(*) as total_overall
FROM chicken_eggs
WHERE removed = FALSE
GROUP BY chicken_name;
"""
    
@router.get("/egg_totals/", response_class=HTMLResponse)
async def get_egg_totals(
    request:Request, 
    settings: Settings = Depends(get_settings)):

    try:
        results_today = await database.fetch_all(query_today)
        results_week = await database.fetch_all(query_week)
        results_month = await database.fetch_all(query_month)
        results_overall = await database.fetch_all(query_total)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    for chicken in results_today:
        flock[chicken['chicken_name']].egg_today = chicken['total_today']
        
    for chicken in results_week:
        flock[chicken['chicken_name']].egg_week=chicken['total_this_week']

    for chicken in results_month:
        flock[chicken['chicken_name']].egg_month=chicken['total_this_month']

    for chicken in results_overall:
        flock[chicken['chicken_name']].egg_total=chicken['total_overall']

    return templates.TemplateResponse("chicken_eggs.html", {"request": request, "flock": flock})


@router.post("/egg_totals/", response_class=HTMLResponse)
async def add_egg(egg_data: EggData):
    newTotal = ""
    try:
        item_pk = str(uuid4())
        date_modified = datetime.now()
        chicken_name = egg_data.chickenName.lower()
        egg_date = egg_data.eggDate
        egg_time_of_day = egg_data.timeOfDay
        removed = False
        insert_query = """
        INSERT INTO chicken_eggs (pk, date_modified, chicken_name, egg_date, egg_time_of_day, removed)
        VALUES (:item_pk, :date_modified, :chicken_name, :egg_date, :egg_time_of_day, :removed)
        """
        
        values = {
            "item_pk": item_pk,
            "date_modified": date_modified,
            "chicken_name": chicken_name,
            "egg_date": egg_date,
            "egg_time_of_day": egg_time_of_day,
            "removed": removed
        }
        await database.execute(insert_query, values)
        results_overall = await database.fetch_all(query_total)
        for chicken in results_overall:
            print(chicken)
            print(chicken_name)
            if chicken["chicken_name"] == chicken_name:
                newTotal=chicken['total_overall']
                print(newTotal)
        return JSONResponse({"status": "success", 
                             "message": "Egg data added successfully.",
                             "flock": {
                                chicken_name: {
                                "egg_total": newTotal
                                },
                            }})
    except Exception as e:
        # return RedirectResponse("/egg_totals/", status_code=303)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    # Redirect to the root page
    
