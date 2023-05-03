# background_tasks.py
from database import connect_to_db, check_date_range
import time
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()
def write_notification(email: str, message=""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}"
        email_file.write(content)

async def check_database_task(days_range):
    while True:
        conn = connect_to_db()
        results = check_date_range(conn, 7)
        conn.close()

        if results:
            print("Found results!")
            for result in results:
                message = f"Alert: A date within the specified range was found: {result}"
                write_notification("karlysindy@gmail.com", message)

        time.sleep(24 * 60 * 60)  # Sleep for a day

@app.post("/send-notification/{email}")
async def on_startup(email:str, background_tasks: BackgroundTasks):
    background_tasks.add_task(check_database_task, email)  # Replace 7 with the desired range in days