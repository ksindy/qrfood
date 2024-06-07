from fastapi import FastAPI, Request, Form, HTTPException, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, validator
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2 import sql
import datetime
from uuid import uuid4
from typing import Optional
import os
from dotenv import load_dotenv
from .routers import background_tasks, create_qr_codes, plants_update, chicken_eggs, food_inventory
from os import getenv
from .utils import connect_to_db, upload_image_to_s3

load_dotenv()  # take environment variables from .env.
app = FastAPI()
app.include_router(background_tasks.router)
app.include_router(chicken_eggs.router)
app.include_router(create_qr_codes.router)
app.include_router(food_inventory.router)
app.include_router(plants_update.router)
images_path = os.path.join(os.path.dirname(__file__), "images")
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
    
# Connect to the database
def connect_to_db():
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url)
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
            removed BOOL,
            plant VARCHAR(255) NOT NULL,
            plant_stage INT,
            task VARCHAR(255) NOT NULL,
            task_date DATE NOT NULL,
            location VARCHAR(255) NOT NULL,
            notes VARCHAR(255),
            update_time TIMESTAMP NOT NULL,
            harvest_date TIMESTAMP
            )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL
            )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chicken_eggs (
            pk UUID PRIMARY KEY,
            date_modified TIMESTAMP NOT NULL,
            chicken_name VARCHAR(255) NOT NULL,
            egg_date DATE NOT NULL,
            egg_time_of_day VARCHAR(255) NOT NULL,
            removed BOOL)
    """)
    conn.commit()
    cursor.close()
    conn.close()
init_db()

TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_PHONE_NUMBER = os.environ['TWILIO_PHONE_NUMBER']

class PlantItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    plant: str
    plant_stage: int
    task: str
    task_date: datetime.date
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None
    removed: Optional[bool] = None 
    
    @validator('removed', pre=True)
    def convert_removed_to_bool(cls, v):
        return v == 't'  # Convert 't' to True, other values to False

class User(BaseModel):
    id: int
    username: str
    email: str
    hashed_password: str

@app.post("/register")
async def register_user(user: User):
    # TODO: Add user registration logic
    return {"message": "User registration placeholder"}

# @app.post("/login")
# async def login_user(credentials: Credentials):
#     # TODO: Add login logic
#     return {"message": "User login placeholder"}

@app.get("/logout") 
async def logout_user():
    # TODO: Add logout logic
    return {"message": "User logout placeholder"}

@app.get("/", response_class=HTMLResponse)
async def redirect():
    return RedirectResponse(url=f"/food/")

@app.get("/favicon.ico")
def read_favicon():
    raise HTTPException(status_code=204, detail="No content")

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...), itemId: str = Form(...)):
    object_name = f"{itemId}.jpg"
    image_bytes = await file.read()
    bucket_name = os.getenv("BUCKET_NAME")
    response = upload_image_to_s3(image_bytes, bucket_name, object_name)
    return response
    
    # if not file.content_type.startswith('image/'):
    #     raise HTTPException(status_code=400, detail="Invalid file type")
    
    # uuid = process_image(file)
    # return RedirectResponse(url=f"/{uuid}/?upload_photo=yes", status_code=303)

@app.get("/{item_id}/")
async def check_item(item_id: str, upload_photo: Optional[str] = None):
    conn = connect_to_db()
    cursor = conn.cursor()

    # Check if the ID exists in food_items and date_consumed is NULL for the latest entry
    cursor.execute("""
        SELECT COUNT(*) FROM food_items 
        WHERE id = %s 
        AND date_consumed IS NULL 
        AND update_time = (SELECT MAX(update_time) FROM food_items WHERE id = %s)
    """, (item_id, item_id))
    food_item_count = cursor.fetchone()[0]
    if food_item_count > 0:
        cursor.close()
        conn.close()
        if upload_photo == 'yes':
            return RedirectResponse(url=f"/{item_id}/food/?item_id={item_id}&upload_photo=yes")
        else:
            return RedirectResponse(url=f"/food/?item_id={item_id}", status_code=303)

        # Check if the ID exists in plants and harvest_date is NULL for the latest entry and highest plant_stage
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
    plant_item_count = cursor.fetchone()

    if plant_item_count:
        if upload_photo == 'yes':
            return RedirectResponse(url=f"/{item_id}/plant_update/?upload_photo=yes")
        else:
            return RedirectResponse(url=f"/{item_id}/plant_update")
    elif upload_photo == 'yes':
        return RedirectResponse(url=f"/{item_id}/food/?item_id={item_id}&upload_photo=yes")
    else:
        return RedirectResponse(url=f"/food/?item_id={item_id}", status_code=303)





