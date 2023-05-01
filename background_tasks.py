# background_tasks.py
from database import connect_to_db, check_date_range
from alert import send_slack_alert
import time
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

async def check_database_task(days_range):
    while True:
        conn = connect_to_db()
        results = check_date_range(conn, days_range)
        conn.close()

        if results:
            for result in results:
                message = f"Alert: A date within the specified range was found: {result}"
                send_slack_alert(message)

        time.sleep(24 * 60 * 60)  # Sleep for a day

@app.on_event("startup")
async def on_startup(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_database_task(days_range=7))  # Replace 7 with the desired range in days