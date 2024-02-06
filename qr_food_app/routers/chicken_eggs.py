from fpdf import FPDF
from fastapi import FastAPI, APIRouter, Form, Request, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import os
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, validator, BaseSettings
from qrcode import QRCode
from uuid import uuid4
import boto3
import tempfile
from fastapi.responses import StreamingResponse
from io import BytesIO
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from ..utils import connect_to_db

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    latest_egg_date: Optional[date] = None
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
# DATABASE_URL = os.getenv("DATABASE_URL")
# database = None
# logger.info(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

# @router.on_event("startup")
# async def startup():
#     try: 
#         global database
#         database = Database(DATABASE_URL)
#         await database.connect()
#         logger.info("Database connected.")
#     except Exception as e:
#         logger.error(f"Failed to connect to the database: {e}")
#         raise

# @router.on_event("shutdown")
# async def shutdown():
#     await database.disconnect()
#     logger.info("Database disconnected.")


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

query_latest_egg_date = """
SELECT DISTINCT ON (chicken_name) chicken_name, egg_date
FROM chicken_eggs
WHERE removed = FALSE
ORDER BY chicken_name, egg_date DESC;
"""
    
@router.get("/egg_totals/", response_class=HTMLResponse)
async def get_egg_totals(
    request:Request, 
    settings: Settings = Depends(get_settings)):
    try:
        conn = connect_to_db()
        cursor = conn.cursor()

        results_today = cursor.execute(query_today)
        results_today= cursor.fetchall()
        results_week = cursor.execute(query_week)
        results_week = cursor.fetchall()
        results_month = cursor.execute(query_month)
        results_month = cursor.fetchall()
        results_overall = cursor.execute(query_total)
        results_overall = cursor.fetchall()
        latest_egg_date = cursor.execute(query_latest_egg_date)
        latest_egg_date = cursor.fetchall()
        # try:
        #     results_today = await database.fetch_all(query_today)
        #     results_week = await database.fetch_all(query_week)
        #     results_month = await database.fetch_all(query_month)
        #     results_overall = await database.fetch_all(query_total)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    for chicken in results_today:
        flock[chicken[0]].egg_today = chicken[1]
        
    for chicken in results_week:
        flock[chicken[0]].egg_week=chicken[1]

    for chicken in results_month:
        flock[chicken[0]].egg_month=chicken[1]

    for chicken in results_overall:
        flock[chicken[0]].egg_total=chicken[1]

    for chicken in latest_egg_date:
        flock[chicken[0]].latest_egg_date=chicken[1]

    cursor.close()
    conn.close()
    print(flock)
    return templates.TemplateResponse("chicken_eggs.html", {"request": request, "flock": flock})


@router.post("/egg_totals/")
async def add_egg(egg_data: EggData):
    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        item_pk = str(uuid4())
        date_modified = datetime.now()
        chicken_name = egg_data.chickenName.lower()
        egg_date = egg_data.eggDate
        egg_time_of_day = egg_data.timeOfDay
        removed = False

        # Insert query with parameter placeholders for PostgreSQL
        insert_query = """
        INSERT INTO chicken_eggs (pk, date_modified, chicken_name, egg_date, egg_time_of_day, removed)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (item_pk, date_modified, chicken_name, egg_date, egg_time_of_day, removed))
        conn.commit()  # Commit the transaction

        # Fetch the new total
        total_query = "SELECT COUNT(*) FROM chicken_eggs WHERE chicken_name = %s"
        cursor.execute(total_query, (chicken_name,))
        newTotal = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return JSONResponse(content = {
            "status": "success", 
            "message": "Egg data added successfully.",
            "flock": {chicken_name: {"egg_total": newTotal}}
        }, status_code=200)

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


