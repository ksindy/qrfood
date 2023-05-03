# background_tasks.py
from ..database import connect_to_db, check_date_range
from fastapi import BackgroundTasks, FastAPI
from fastapi import APIRouter
import os
from twilio.rest import Client

router = APIRouter()

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

@router.post("/send-notification/{user_phone_number}/")
async def send_notification(user_phone_number: str, background_tasks: BackgroundTasks):
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