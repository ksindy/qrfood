# database.py
import os
import psycopg2
from datetime import datetime, timedelta

DATABASE_URL = os.environ['DATABASE_URL']

def connect_to_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def check_date_range(conn, days_range):
    with conn.cursor() as cur:
        current_date = datetime.now().date()
        min_date = current_date - timedelta(days=days_range)
        max_date = current_date + timedelta(days=days_range)

        query = f"SELECT * FROM your_table WHERE date_column >= '{min_date}' AND date_column <= '{max_date}';"
        cur.execute(query)
        results = cur.fetchall()

    return results
