import datetime
import os
import psycopg2
from typing import Optional
from pydantic import BaseModel

class PlantItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    plant: str
    date_added: datetime.date
    treatment: str
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None

# Connect to the database
def connect_to_db():
    use_ssl = 'localhost' not in os.getenv("DATABASE_URL")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require' if use_ssl else None)
    return conn

async def get_plant_items(query_string):
    conn = connect_to_db()
    cur = conn.cursor()

    query = """
        SELECT fi.pk, fi.id, fi.plant, fi.date_added, fi.treatment, fi.location, fi.notes, fi.update_time, fi.harvest_date
        FROM plants fi
        INNER JOIN (
            SELECT id, MAX(update_time) AS max_update_time
            FROM plants
            GROUP BY id
        ) AS mfi ON fi.id = mfi.id AND fi.update_time = mfi.max_update_time
        WHERE fi.harvest_date IS NULL
    """
    query = query + query_string
        
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    plant_items = [PlantItem(pk=row[0], days_left=(row[4] - datetime.date.today()).days, id=row[1], plant=row[2], date_added=row[3], treatment=row[4], location=row[5], notes=row[6], update_time=row[7], harvest_date=row[8]) for row in rows]

    return plant_items