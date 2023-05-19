# background_tasks.py
from ..database import connect_to_db, check_date_range
from fastapi import BackgroundTasks, FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi import APIRouter
import os
from twilio.rest import Client
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import datetime

# Define the request model
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

router = APIRouter()
templates_path = os.path.join(os.path.dirname(__file__), "../templates")
templates = Jinja2Templates(directory=templates_path)
app = FastAPI()
TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']
TWILIO_PHONE_NUMBER = os.environ['TWILIO_PHONE_NUMBER']

def send_text_alert(to_phone_number, message):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone_number
    )

@router.get("/send-notification/", response_class=HTMLResponse)
async def test_notification(request: Request):
    return templates.TemplateResponse("alert.html", {"request": request})

@router.post("/send-notification/", response_class=HTMLResponse)
async def send_notification(request: Request, background_tasks: BackgroundTasks, user_phone_number: str = Form(...), days_food_expires: int = Form(...)):
    # while True:
    conn = connect_to_db()
    results = check_date_range(conn, days_food_expires)
    conn.close()
    if results:
        days_dict = {}
        message = "Alert: \n"
        for row in results:
            food_item = FoodItem(pk=row[0], id=row[1], food=row[2], date_added=row[3], expiration_date=row[4], notes=row[5], update_time=row[6], date_consumed=row[7]) 
            days_to_expiration = food_item.expiration_date - datetime.date.today()
            if days_to_expiration.days not in days_dict:
                days_dict[days_to_expiration.days] = [food_item.food]        
            else:
                days_dict[days_to_expiration.days].append(food_item.food)
        for day in sorted(days_dict.keys()):
            foods = days_dict[day]
            remaining_foods = len(foods) - 3
            if remaining_foods > 0:
                message += f"{','.join(foods[:3])} and {remaining_foods} more will expire in {day} days.\n" 
            else:
                message += f"{''.join(foods)} will expire in {day} days.\n"
        send_text_alert(user_phone_number, message)