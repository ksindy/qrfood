# background_tasks.py
from ..database import connect_to_db, check_date_range
from fastapi import BackgroundTasks, FastAPI
from fastapi import APIRouter

router = APIRouter()

app = FastAPI()
def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)

@router.get("/send-notification/{email}/")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    while True:
        conn = connect_to_db()
        results = check_date_range(conn, 7)
        conn.close()

        if results:
            print("Found results!")
            for result in results:
                message = f"Alert: A date within the specified range was found: {result}"
                write_notification(email, message)

        background_tasks.add_task(write_notification, email, message="some notification")
        return {"message": "Notification sent in the background"}