import datetime
import os
import psycopg2
from typing import Optional
from pydantic import BaseModel, validator

class PlantItem(BaseModel):
    pk: Optional[str] = None
    id: Optional[str] = None
    plant: str
    plant_stage: int
    task: str
    task_date:datetime.date
    location: str
    notes: Optional[str] = None
    update_time: Optional[datetime.datetime] = None
    harvest_date: Optional[datetime.datetime] = None
    removed: Optional[bool] = None 

@validator('removed', pre=True)
def convert_removed_to_bool(cls, v):
    return v == 't'  # Convert 't' to True, other values to False

# Connect to the database
def connect_to_db():
    use_ssl = 'localhost' not in os.getenv("DATABASE_URL")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require' if use_ssl else None)
    return conn

async def get_plant_items(query_string):
    conn = connect_to_db()
    cur = conn.cursor()

    query = """
        SELECT fi.pk, fi.id, fi.removed, fi.plant, fi.plant_stage, fi.task, fi.task_date, fi.location, fi.notes, fi.update_time, fi.harvest_date
        FROM plants fi
        INNER JOIN (
            SELECT id, plant_stage, MAX(update_time) AS max_update_time
            FROM plants
            WHERE harvest_date IS NULL AND removed = FALSE
            GROUP BY id, plant_stage
        ) AS mfi ON fi.id = mfi.id AND fi.plant_stage = mfi.plant_stage AND fi.update_time = mfi.max_update_time
        ORDER BY fi.id, fi.plant_stage
    """
    query = query + query_string
        
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    plant_items = [PlantItem(pk=row[0], id=row[1], removed=row[2], plant=row[3], plant_stage=row[4], task=row[5], task_date=row[6], location=row[7], notes=row[8], update_time=row[9], harvest_date=row[10]) for row in rows]

    return plant_items