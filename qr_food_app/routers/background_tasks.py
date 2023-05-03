# background_tasks.py
from ..database import connect_to_db, check_date_range
from fastapi import BackgroundTasks, FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi import APIRouter
import os
from twilio.rest import Client
from fastapi.templating import Jinja2Templates

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
async def send_notification(request: Request, background_tasks: BackgroundTasks, user_phone_number: str = Form(...)):
    while True:
        conn = connect_to_db()
        results = check_date_range(conn, 7)
        conn.close()
        if results:
            print("Found results!")
            for result in results:
                message = f"Alert: A date within the specified range was found: {result}"
                send_text_alert(user_phone_number, message)

        # background_tasks.add_task(write_notification, email, message="some notification")
        # return {"message": "Notification sent in the background"}